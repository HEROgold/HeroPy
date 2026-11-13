"""Batch the loading of typed relationships over the rows that one query returned.

Rows that one SELECT returns form a cohort. The first read of a typed relationship on any
cohort member loads it for every live member of that cohort with one ``IN`` query per chunk,
on the session the rows belong to. Loaded values are cached on the instances and dropped
again on commit and rollback.

Storage sits behind :class:`Loader`. This module ships the link-table loader; foreign-key
storage plugs in by registering another :class:`Loader` with :func:`register_loader`.
"""

from __future__ import annotations

import contextvars
import weakref
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from sqlalchemy import Column, ForeignKey, Index, Table, UniqueConstraint, event, inspect, select, tuple_
from sqlalchemy.orm import Session
from sqlmodel import SQLModel

from herogold.orm.core.utils import LinkInfo, Relationship, _fk_columns, _pk_columns

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import InstanceState

    from herogold.orm.core.model import _BaseModel

__all__ = [
    "CHUNK_SIZE",
    "AsyncLoadError",
    "Cohort",
    "LinkLoader",
    "Loader",
    "UnbatchedLoadError",
    "build_links",
    "forbid_unbatched",
    "forget_cached",
    "forget_cached_name",
    "internal_write",
    "is_internal_write",
    "link_for",
    "load_typed",
    "register_loader",
]

CHUNK_SIZE = 500
"""Most values in one ``IN`` list. Postgres drivers cap bound parameters at 32,767."""

_CACHE_KEY = "rel"
_COHORT_KEY = "cohort"

_forbid_unbatched: contextvars.ContextVar[bool] = contextvars.ContextVar("herogold_forbid_unbatched", default=False)
_internal_write: contextvars.ContextVar[bool] = contextvars.ContextVar("herogold_internal_write", default=False)
_LOADERS: dict[tuple[type, str], Loader] = {}


class UnbatchedLoadError(RuntimeError):
    """Raised by a lazy load that no other row shares, while unbatched loads are forbidden."""


class AsyncLoadError(RuntimeError):
    """Raised when a relationship is read in an async session outside ``run_sync``."""


@dataclass(frozen=True)
class Cohort:
    """The persistent rows of one session that a relationship loads together."""

    session: Session
    states: list[InstanceState[Any]]


class Loader(Protocol):
    """Loads one relationship for a whole cohort."""

    def load_for(self, cohort: Cohort, relationship: Relationship[Any]) -> None:
        """Query once per chunk and store each member's value with :func:`store`."""
        ...


class LinkLoader:
    """Loader for relationships stored in an association table."""

    def __init__(self, info: LinkInfo[Any]) -> None:
        """Keep the link table description."""
        self.info = info

    def load_for(self, cohort: Cohort, relationship: Relationship[Any]) -> None:
        """Load ``relationship`` for every member of ``cohort`` with ``IN`` queries on the cohort's session."""
        info = self.info
        width = len(info.owner_cols)
        owner_columns = [info.table.c[name] for name in info.owner_cols]
        grouped: dict[tuple[object, ...], list[Any]] = {tuple(state.identity or ()): [] for state in cohort.states}
        keys = list(grouped)
        for start in range(0, len(keys), CHUNK_SIZE):
            chunk = keys[start : start + CHUNK_SIZE]
            wanted = [k[0] for k in chunk] if width == 1 else chunk
            owner_in = owner_columns[0].in_(wanted) if width == 1 else tuple_(*owner_columns).in_(wanted)
            query = (
                select(*owner_columns, info.target)
                .select_from(info.table)
                .join(info.target, info.target_join())
                .where(owner_in, *info.target.default_criteria())
            )
            for row in cohort.session.execute(query):
                grouped[tuple(row[:width])].append(row[width])
        shape = relationship.shape
        for state in cohort.states:
            found = grouped[tuple(state.identity or ())]
            store(state, relationship.name, found if shape.many else (found[0] if found else None))


def register_loader(owner: type, name: str, loader: Loader) -> None:
    """Use ``loader`` for the typed relationship ``name`` on ``owner`` and its subclasses."""
    _LOADERS[owner, name] = loader


def store(state: InstanceState[Any], name: str, value: object) -> None:
    """Cache ``value`` as the loaded relationship ``name`` of ``state``'s instance."""
    state.info.setdefault(_CACHE_KEY, {})[name] = value


def link_for(owner: type, name: str) -> LinkInfo[Any]:
    """Return the link table description of the link-table relationship ``name`` on ``owner``."""
    loader = _find_loader(owner, name)
    if not isinstance(loader, LinkLoader):
        msg = f"{owner.__name__}.{name} is not stored in a link table."
        raise TypeError(msg)
    return loader.info


def build_links(*models: type[_BaseModel]) -> None:
    """Create link tables for the typed relationships of ``models`` and register their loaders.

    Call this once every model exists and before ``create_all``. Foreign-key storage
    replaces this step for relationships that can use a column.
    """
    for model in models:
        seen: set[str] = set()
        for cls in model.__mro__:
            for name, attr in vars(cls).items():
                if name in seen:
                    continue
                seen.add(name)
                if isinstance(attr, Relationship) and attr._declared:  # noqa: SLF001
                    register_loader(model, name, LinkLoader(_build_link_table(model, attr)))


def load_typed(relationship: Relationship[Any], instance: _BaseModel) -> object:
    """Return the value of a typed relationship, loading it for the instance's cohort when needed."""
    state = inspect(instance)
    cached = state.info.get(_CACHE_KEY, {})
    if relationship.name in cached:
        return cached[relationship.name]
    shape = relationship.shape
    if state.key is None:  # transient or pending: nothing stored, and a query would autoflush it
        return [] if shape.many else None
    session = state.session
    if session is None:  # detached: one query of its own
        session = type(instance).session
        members = [state]
    else:
        members = _cohort_members(state, session, relationship.name)
    _check_async(session, relationship)
    if _forbid_unbatched.get() and len(members) <= 1:
        msg = (
            f"Unbatched load of {type(instance).__name__}.{relationship.name}: the row has no cohort to share the query. "
            "Load it with the rows it belongs to, or leave forbid_unbatched_loads()."
        )
        raise UnbatchedLoadError(msg)
    _find_loader(type(instance), relationship.name).load_for(Cohort(session, members), relationship)
    return state.info[_CACHE_KEY][relationship.name]


@contextmanager
def forbid_unbatched() -> Generator[None]:
    """Make a lazy load that no other row shares raise :class:`UnbatchedLoadError` inside the block."""
    token = _forbid_unbatched.set(True)
    try:
        yield
    finally:
        _forbid_unbatched.reset(token)


def _build_link_table(owner: type[_BaseModel], relationship: Relationship[Any]) -> LinkInfo[Any]:
    """Return the link table of ``relationship`` on ``owner``, creating it in the metadata when missing."""
    target = cast("type[_BaseModel]", relationship.resolve())
    owner_pk, owner_cols = _pk_columns(owner, prefix=str(owner.__tablename__))
    target_pk, target_cols = _pk_columns(target, prefix=relationship.name)
    name = f"{owner.__tablename__}_{relationship.name}"
    table = owner.metadata.tables.get(name)
    if table is None:
        constraints: list[Column[Any] | Index | UniqueConstraint | ForeignKey] = []
        if not relationship.shape.many:
            constraints.append(UniqueConstraint(*owner_cols, name=f"uq_{name}"))
        table = Table(
            name,
            owner.metadata,
            *_fk_columns(owner, owner_cols),
            *_fk_columns(target, target_cols),
            *constraints,
            Index(f"ix_{name}_tgt", *target_cols),
        )
    return LinkInfo(table, owner_pk, owner_cols, target_pk, target_cols, target)


def _find_loader(owner: type, name: str) -> Loader:
    """Return the loader registered for ``name`` on ``owner`` or the nearest base class."""
    for cls in owner.__mro__:
        loader = _LOADERS.get((cls, name))
        if loader is not None:
            return loader
    msg = f"{owner.__name__}.{name} has no storage yet. Call build_links({owner.__name__}) after all models exist."
    raise LookupError(msg)


def _cohort_members(state: InstanceState[Any], session: Session, name: str) -> list[InstanceState[Any]]:
    """Return the live persistent cohort members of ``session`` that still lack ``name``, plus ``state``."""
    cohort = state.info.get(_COHORT_KEY)
    members = [
        s
        for s in (list(cohort) if cohort is not None else [])
        if s is not state
        and s.obj() is not None
        and s.persistent
        and s.session is session
        and name not in s.info.get(_CACHE_KEY, {})
    ]
    return [state, *members]


def _inside_run_sync() -> bool:
    """Return True when the call runs inside ``AsyncSession.run_sync`` (a SQLAlchemy greenlet)."""
    from sqlalchemy.util.concurrency import in_greenlet  # noqa: PLC0415  # needs the optional greenlet package

    return in_greenlet()


def _check_async(session: Session, relationship: Relationship[Any]) -> None:
    """Raise :class:`AsyncLoadError` when ``session`` is an async session used without ``run_sync``."""
    if not session.get_bind().dialect.is_async or _inside_run_sync():
        return
    msg = (
        f"Cannot lazy-load '{relationship.name}' with plain attribute access on an async session. "
        f"Load it inside 'await session.run_sync(lambda sync_session: ...)'."
    )
    raise AsyncLoadError(msg)


def _on_load(target: SQLModel, context: Any) -> None:  # noqa: ANN401
    """Add a freshly loaded row to the cohort of its statement execution."""
    state = inspect(target)
    cohort = context.attributes.setdefault((_COHORT_KEY, type(target)), weakref.WeakSet())
    cohort.add(state)
    state.info[_COHORT_KEY] = cohort


def forget_cached(session: Session, model: type | None = None) -> None:
    """Forget the cached relationship values of the session's rows, only those of ``model`` when given.

    Bulk statements (`UPDATE`, `DELETE`) change rows without touching the loaded instances, so
    the code that runs them calls this to keep the caches from going stale.
    """
    for instance in list(session.identity_map.values()):
        if model is None or isinstance(instance, model):
            inspect(instance).info.pop(_CACHE_KEY, None)


@contextmanager
def internal_write() -> Generator[None]:
    """Mark column writes made by the relationship machinery itself, which keeps the caches in step on its own.

    A direct write of a foreign-key column by the caller drops the affected cached values. Inside this block it does not.
    """
    token = _internal_write.set(True)
    try:
        yield
    finally:
        _internal_write.reset(token)


def is_internal_write() -> bool:
    """Return True inside :func:`internal_write`."""
    return _internal_write.get()


def forget_cached_name(state: InstanceState[Any], name: str) -> None:
    """Forget the cached value of the single relationship ``name`` of ``state``'s instance."""
    state.info.get(_CACHE_KEY, {}).pop(name, None)


def _drop_cache(session: Session) -> None:
    """Forget every cached relationship value of the session's rows."""
    forget_cached(session)


def _on_refresh_or_expire(target: SQLModel, *_args: object) -> None:
    """Drop the cached relationship values of an instance that was refreshed or expired."""
    inspect(target).info.pop(_CACHE_KEY, None)


def _drop_cache_after_commit(session: Session) -> None:
    """Drop cached relationship values once a commit ended the transaction."""
    _drop_cache(session)


def _drop_cache_after_rollback(session: Session) -> None:
    """Drop cached relationship values once a rollback ended the transaction."""
    _drop_cache(session)


event.listen(SQLModel, "load", _on_load, propagate=True)
event.listen(SQLModel, "refresh", _on_refresh_or_expire, propagate=True)
event.listen(SQLModel, "expire", _on_refresh_or_expire, propagate=True)
event.listen(Session, "after_commit", _drop_cache_after_commit)
event.listen(Session, "after_rollback", _drop_cache_after_rollback)
