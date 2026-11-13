"""Batch the loading of typed relationships over the rows that one query returned.

Rows that one SELECT returns form a cohort. The first read of a typed relationship on any
cohort member loads it for every live member of that cohort with one ``IN`` query per chunk,
on the session the rows belong to. Loaded values are cached on the instances and dropped
again on commit and rollback.

Storage sits behind :class:`Loader`. This module ships the link-table loader and the
foreign-key loader. ``configure()`` registers the right one for each relationship with
:func:`register_loader`.
"""

from __future__ import annotations

import contextvars
import weakref
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy import event, inspect, select, tuple_
from sqlalchemy.orm import Session
from sqlmodel import SQLModel

if TYPE_CHECKING:
    from collections.abc import Generator

    from sqlalchemy.orm import InstanceState

    from herogold.orm.core.model import _BaseModel
    from herogold.orm.core.utils import LinkInfo, Relationship

__all__ = [
    "CHUNK_SIZE",
    "AsyncLoadError",
    "Cohort",
    "FkLoader",
    "LinkLoader",
    "Loader",
    "UnbatchedLoadError",
    "forbid_unbatched",
    "forget_cached",
    "forget_cached_name",
    "internal_write",
    "is_internal_write",
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


class FkLoader:
    """Loader for relationships stored in a foreign-key column, on the owner or on the target."""

    def __init__(self, owner: type[_BaseModel], target: type[_BaseModel], column: str, *, on_owner: bool) -> None:
        """Keep the models and the foreign-key column name, which sits on ``owner`` when ``on_owner`` else on ``target``."""
        self.owner = owner
        self.target = target
        self.column = column
        self.on_owner = on_owner

    def load_for(self, cohort: Cohort, relationship: Relationship[Any]) -> None:
        """Load ``relationship`` for every member of ``cohort`` with ``IN`` queries on the cohort's session."""
        if self.on_owner:
            self._load_by_owner_column(cohort, relationship)
        else:
            self._load_by_target_column(cohort, relationship)

    def _load_by_owner_column(self, cohort: Cohort, relationship: Relationship[Any]) -> None:
        """Many-to-one: select the targets whose key is among the cohort's foreign-key values."""
        table = self.owner.__table__
        column = table.c[self.column]
        attr = self.owner.__mapper__.get_property_by_column(column).key
        owner_pk = next(iter(table.primary_key.columns))
        values: dict[InstanceState[Any], object] = {}
        missing: dict[object, InstanceState[Any]] = {}
        for state in cohort.states:
            if attr in state.dict:
                values[state] = state.dict[attr]
            else:  # expired by a commit: read the whole cohort's keys in one query instead of one refresh per row
                missing[state.identity[0] if state.identity else None] = state
        keys = list(missing)
        for chunk in _chunks(keys):
            for key, value in cohort.session.execute(select(owner_pk, column).where(owner_pk.in_(chunk))):
                values[missing[key]] = value
        target_pk = next(iter(self.target.__table__.primary_key.columns))
        target_attr = self.target.__mapper__.get_property_by_column(target_pk).key
        wanted = list({v for v in values.values() if v is not None})
        found: dict[object, Any] = {}
        for chunk in _chunks(wanted):
            query = select(self.target).where(target_pk.in_(chunk), *self.target.default_criteria())
            for row in cohort.session.execute(query).scalars():
                found[getattr(row, target_attr)] = row
        for state in cohort.states:
            store(state, relationship.name, found.get(values.get(state)))

    def _load_by_target_column(self, cohort: Cohort, relationship: Relationship[Any]) -> None:
        """One-to-many: select the targets whose foreign-key column holds one of the cohort's ids."""
        column = self.target.__table__.c[self.column]
        attr = self.target.__mapper__.get_property_by_column(column).key
        target_pk = next(iter(self.target.__table__.primary_key.columns))
        grouped: dict[object, list[Any]] = {state.identity[0]: [] for state in cohort.states if state.identity}
        for chunk in _chunks(list(grouped)):
            query = select(self.target).where(column.in_(chunk), *self.target.default_criteria()).order_by(target_pk)
            for row in cohort.session.execute(query).scalars():
                grouped[getattr(row, attr)].append(row)
        many = relationship.shape.many
        for state in cohort.states:
            found = grouped.get(state.identity[0] if state.identity else None, [])
            store(state, relationship.name, found if many else (found[0] if found else None))


def _chunks(values: list[Any]) -> Generator[list[Any]]:
    """Split ``values`` into lists of at most ``CHUNK_SIZE``."""
    for start in range(0, len(values), CHUNK_SIZE):
        yield values[start : start + CHUNK_SIZE]


def register_loader(owner: type, name: str, loader: Loader) -> None:
    """Use ``loader`` for the typed relationship ``name`` on ``owner`` and its subclasses."""
    _LOADERS[owner, name] = loader


def store(state: InstanceState[Any], name: str, value: object) -> None:
    """Cache ``value`` as the loaded relationship ``name`` of ``state``'s instance."""
    state.info.setdefault(_CACHE_KEY, {})[name] = value


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


def _find_loader(owner: type, name: str) -> Loader:
    """Return the loader registered for ``name`` on ``owner`` or the nearest base class."""
    for cls in owner.__mro__:
        loader = _LOADERS.get((cls, name))
        if loader is not None:
            return loader
    msg = f"{owner.__name__}.{name} has no storage yet. Call herogold.orm.configure() after all models exist."
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
