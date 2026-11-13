"""Repositories and querysets: explicit-session access to one model, with soft-delete aware queries.

A `Repository` takes a session from the caller and never commits. A `QuerySet` is an immutable, chainable
wrapper around a `Select` that applies the model's `default_criteria()`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar, cast, get_args, get_origin

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.orm.attributes import set_attribute
from sqlmodel import col, select

from herogold.orm.core import loading
from herogold.orm.core.configure import GENERATED
from herogold.orm.core.model import BaseModel

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator

    from sqlalchemy import ColumnElement
    from sqlalchemy.engine import CursorResult
    from sqlmodel import Session
    from sqlmodel.sql.expression import SelectOfScalar

__all__ = ["QuerySet", "Repository", "Upserted"]

_NOT_COPIED = frozenset({"id", "created_at", "updated_at", "deleted_at"})
"""Fields `Repository.upsert` leaves alone when it copies a new row onto a stored one."""

_ALIVE = "alive"
_ALL = "all"
_ONLY_DELETED = "only"


def _substitute(arg: object, origin: type, args: tuple[object, ...]) -> object:
    """Replace the type variable `arg` of generic class `origin` by the matching entry of `args`."""
    params = getattr(origin, "__parameters__", ())
    if isinstance(arg, TypeVar) and arg in params and params.index(arg) < len(args):
        return args[params.index(arg)]
    return arg


def _utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(UTC)


class QuerySet[T: BaseModel]:
    """Immutable, chainable query over one model.

    Rows hidden by `Model.default_criteria()` (soft-deleted rows for `BaseModel`) are left out unless
    `with_deleted()` or `only_deleted()` is called. Every builder returns a new queryset.
    """

    def __init__(
        self,
        session: Session,
        model: type[T],
        stmt: SelectOfScalar[T] | None = None,
        *,
        deleted: str = _ALIVE,
        window: tuple[int, int | None] | None = None,
    ) -> None:
        """Wrap `stmt` (default: select every row of `model`) for use on `session`.

        `window` is the (offset, limit) already applied to `stmt`, kept so that slices compose with it.
        """
        self._session = session
        self._model = model
        self._stmt: SelectOfScalar[T] = select(model) if stmt is None else stmt
        self._deleted = deleted
        self._window = window

    def _clone(
        self,
        stmt: SelectOfScalar[T] | None = None,
        *,
        deleted: str | None = None,
        window: tuple[int, int | None] | None = None,
    ) -> QuerySet[T]:
        """Return a copy with the given parts replaced."""
        return QuerySet(
            self._session,
            self._model,
            self._stmt if stmt is None else stmt,
            deleted=self._deleted if deleted is None else deleted,
            window=self._window if window is None else window,
        )

    def _criteria(self) -> list[ColumnElement[bool]]:
        """Return the model criteria for the current deleted-row mode.

        The model's own `soft_delete_criteria()` is what `with_deleted()` removes from
        `default_criteria()` and what `only_deleted()` negates, so a model that redefines
        "alive" there is honoured.
        """
        criteria = self._model.default_criteria()
        if self._deleted == _ALIVE:
            return criteria
        alive = self._soft_delete_criterion()
        if alive is None:  # no soft delete: nothing to remove or negate
            return criteria
        criteria = [criterion for criterion in criteria if not criterion.compare(alive)]
        if self._deleted == _ONLY_DELETED:
            criteria.append(sa.not_(alive))
        return criteria

    def _soft_delete_criterion(self) -> ColumnElement[bool] | None:
        """Return the model's `soft_delete_criteria()`, or None when the model has no soft delete."""
        soft_delete = getattr(self._model, "soft_delete_criteria", None)
        return None if soft_delete is None else soft_delete()

    def _refuse_if_soft_delete_is_unapplied(self, call: str) -> None:
        """Raise TypeError when the model has a soft-delete criterion that `default_criteria()` does not apply.

        `with_deleted()` and `only_deleted()` work on the entry of `default_criteria()` that equals
        `soft_delete_criteria()`. Without that entry they would return the wrong rows without saying so.
        """
        alive = self._soft_delete_criterion()
        if alive is None or any(criterion.compare(alive) for criterion in self._model.default_criteria()):
            return
        msg = (
            f"{self._model.__name__}.{call}() cannot tell which default_criteria() entry hides deleted rows, "
            f"because none equals soft_delete_criteria(). Include soft_delete_criteria() in default_criteria(), or "
            f"override soft_delete_criteria() to return the criterion that default_criteria() uses for 'alive'."
        )
        raise TypeError(msg)

    @property
    def _bounds(self) -> tuple[int, int | None]:
        """Return the (offset, limit) applied so far, (0, None) when there is none."""
        return self._window or (0, None)

    def _refuse_after_window(self, call: str) -> None:
        """Raise when a filter is added after `limit()` or `offset()`, which SQL would apply first."""
        if self._window is not None:
            msg = (
                f"{call}() after limit() or offset() would filter before the window, not after it; "
                f"call {call}() before limit() and offset()"
            )
            raise TypeError(msg)

    @property
    def select(self) -> SelectOfScalar[T]:
        """Return the raw `Select` with the model criteria applied, as an escape hatch."""
        return self._stmt.where(*self._criteria())

    def where(self, *criteria: ColumnElement[bool]) -> QuerySet[T]:
        """Return a queryset narrowed by `criteria`. Raises TypeError after `limit()` or `offset()`."""
        self._refuse_after_window("where")
        return self._clone(self._stmt.where(*criteria))

    def filter_by(self, **kwargs: object) -> QuerySet[T]:
        """Return a queryset narrowed by column equality. Raises TypeError after `limit()` or `offset()`."""
        self._refuse_after_window("filter_by")
        return self._clone(self._stmt.filter_by(**kwargs))

    def order_by(self, *columns: Any) -> QuerySet[T]:  # noqa: ANN401
        """Return a queryset ordered by `columns`."""
        return self._clone(self._stmt.order_by(*columns))

    def limit(self, count: int) -> QuerySet[T]:
        """Return a queryset limited to `count` rows."""
        return self._clone(self._stmt.limit(count), window=(self._bounds[0], count))

    def offset(self, count: int) -> QuerySet[T]:
        """Return a queryset that skips `count` rows."""
        return self._clone(self._stmt.offset(count), window=(count, self._bounds[1]))

    def with_deleted(self) -> QuerySet[T]:
        """Return a queryset that includes soft-deleted rows.

        Other `default_criteria()` entries, such as a tenant filter, still apply. Raises TypeError when the model
        has a soft-delete criterion that `default_criteria()` does not contain.
        """
        self._refuse_if_soft_delete_is_unapplied("with_deleted")
        return self._clone(deleted=_ALL)

    def only_deleted(self) -> QuerySet[T]:
        """Return a queryset of soft-deleted rows only."""
        if not hasattr(self._model, "deleted_at"):
            msg = f"{self._model.__name__} has no deleted_at column"
            raise TypeError(msg)
        self._refuse_if_soft_delete_is_unapplied("only_deleted")
        return self._clone(deleted=_ONLY_DELETED)

    def all(self) -> list[T]:
        """Load every matching row."""
        return list(self._session.exec(self.select))

    def first(self) -> T | None:
        """Return the first matching row, or None."""
        return self._session.exec(self.select.limit(1)).first()

    def one(self) -> T:
        """Return the only matching row. Raises if there are none or several."""
        return self._session.exec(self.select).one()

    def exists(self) -> bool:
        """Return whether any row matches, with one EXISTS statement."""
        inner = self.select.with_only_columns(sa.literal(1), maintain_column_froms=True)  # keep FROM when there is no WHERE
        return bool(self._session.exec(select(sa.exists(inner))).one())

    def count(self) -> int:
        """Return the number of matching rows."""
        subquery = self.select.order_by(None).subquery()
        return self._session.exec(select(sa.func.count()).select_from(subquery)).one()

    def in_bulk(self, by: str | tuple[str, ...] = "id") -> dict[Any, T]:
        """Load matching rows in one statement and key them by a column, or by a tuple of columns."""
        names = (by,) if isinstance(by, str) else by
        found: dict[Any, T] = {}
        for row in self.all():
            key = tuple(getattr(row, name) for name in names)
            found[key[0] if isinstance(by, str) else key] = row
        return found

    def _bulk_criterion(self) -> ColumnElement[bool]:
        """Return the single where clause a bulk write uses."""
        if self._window is not None:
            msg = "bulk writes do not work on a sliced queryset"
            raise TypeError(msg)
        clause = self.select.whereclause
        return sa.true() if clause is None else clause

    def update(self, **values: object) -> int:
        """Update every matching row with one UPDATE statement and return the row count."""
        stmt = sa.update(self._model).where(self._bulk_criterion()).values(**values)
        result = cast("CursorResult[Any]", self._session.exec(stmt, execution_options={"synchronize_session": "fetch"}))
        loading.forget_cached(self._session)  # a bulk write can move rows between relationships of any model
        return result.rowcount

    def soft_delete(self) -> int:
        """Set `deleted_at` on every matching row with one UPDATE statement and return the row count."""
        if not hasattr(self._model, "deleted_at"):
            msg = f"{self._model.__name__} has no deleted_at column; use purge()"
            raise TypeError(msg)
        return self.update(deleted_at=_utc_now())

    def purge(self) -> int:
        """Hard-delete every matching row with one DELETE statement and return the row count."""
        stmt = sa.delete(self._model).where(self._bulk_criterion())
        result = cast("CursorResult[Any]", self._session.exec(stmt, execution_options={"synchronize_session": "fetch"}))
        loading.forget_cached(self._session)
        return result.rowcount

    def __iter__(self) -> Iterator[T]:
        """Iterate over every matching row (loads them all)."""
        return iter(self.all())

    def __bool__(self) -> bool:
        """Return whether any row matches, with EXISTS instead of COUNT.

        A queryset has no `__len__` on purpose: `list(qs)`, `tuple(qs)` and `sorted(qs)` call it as a size hint
        and would run a COUNT before the SELECT. Use `count()`.
        """
        return self.exists()

    def __contains__(self, item: object) -> bool:
        """Return whether a row, or an id, is among the matching rows."""
        pk = item.id if isinstance(item, self._model) else item
        if pk is None:
            return False
        return self.where(col(self._model.id) == pk).exists()

    def __getitem__(self, index: slice) -> list[T]:
        """Return rows by position. Only forward slices work, `qs[7]` raises TypeError."""
        if not isinstance(index, slice):
            msg = "a queryset has no single index; use .first(), .offset(n).first() or a slice"
            raise TypeError(msg)
        start = index.start or 0
        if index.step not in (None, 1) or start < 0 or (index.stop is not None and index.stop < 0):
            msg = "only forward slices without a step are supported"
            raise ValueError(msg)
        base_offset, base_limit = self._bounds
        queryset = self.offset(base_offset + start)
        if index.stop is not None:
            size = max(index.stop - start, 0)
            if base_limit is not None:
                size = min(size, max(base_limit - start, 0))
            return queryset.limit(size).all()
        if base_limit is not None:
            return queryset.limit(max(base_limit - start, 0)).all()
        return queryset.all()


@dataclass(frozen=True, slots=True)
class Upserted[T]:
    """One row handled by `Repository.upsert`."""

    row: T
    """The stored row, new or existing."""
    created: bool
    """True when no stored row matched and `row` is the added one."""
    restored: bool
    """True when a soft-deleted stored row matched and was brought back."""


class Repository[T: BaseModel]:
    """Access to the rows of one model through a caller-owned session. Never commits.

    Subclass with the model as type argument, `class Sales(Repository[Sale])`, or build one with
    `Repository[Sale](session)`. A repository is a collection of its alive rows looked up by id:
    `bool`, `in`, iteration, `repo[id]` and `del repo[id]`. It has no `len`, because `list(repo)` would run a
    COUNT first; use `repo.qs().count()`.
    """

    _model: type[T] | None = None
    _model_arg: Any = None
    """The type argument of the `Repository[...]` base as written, a class or a type variable."""

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        """Read the model from the `Repository[Model]` base, also through generic intermediate classes.

        Raises:
            TypeError: The model is not a class and the subclass is not itself generic.

        """
        super().__init_subclass__(**kwargs)
        arg = cls._model_arg
        for base in cls.__dict__.get("__orig_bases__", ()):
            origin = get_origin(base)
            if origin is Repository:
                arg = get_args(base)[0]
            elif isinstance(origin, type) and issubclass(origin, Repository):
                arg = _substitute(origin._model_arg, origin, get_args(base))  # noqa: SLF001
        cls._model_arg = arg
        if arg is None:
            return
        if isinstance(arg, type):
            cls._model = arg  # ty: ignore[invalid-assignment]
            return
        cls._model = None
        if arg not in getattr(cls, "__parameters__", ()):
            msg = f"{cls.__name__}: the model {arg!r} is not a class; subclass Repository[Model] with a model class"
            raise TypeError(msg)

    def __init__(self, session: Session) -> None:
        """Use `session` for every operation. The caller commits."""
        self.session = session

    @property
    def model(self) -> type[T]:
        """Return the model this repository serves."""
        if self._model is not None:
            return self._model
        origin = getattr(self, "__orig_class__", None)
        if origin is None:
            msg = f"{type(self).__name__} has no model; subclass Repository[Model] or build Repository[Model](session)"
            raise TypeError(msg)
        return get_args(origin)[0]

    def qs(self) -> QuerySet[T]:
        """Return a fresh queryset over the alive rows."""
        return QuerySet(self.session, self.model)

    def add(self, row: T) -> T:
        """Add `row` to the session and return it."""
        self.session.add(row)
        loading.forget_cached(self.session)  # the new row may belong to a cached relationship value
        return row

    def add_all(self, rows: Iterable[T]) -> list[T]:
        """Add every row to the session and return them."""
        added = list(rows)
        self.session.add_all(added)
        loading.forget_cached(self.session)
        return added

    def delete(self, row: T) -> None:
        """Soft-delete `row` when the model has `deleted_at`, else delete it."""
        if hasattr(row, "deleted_at"):
            row.deleted_at = _utc_now()
            self.session.add(row)
        else:
            self.session.delete(row)
        loading.forget_cached(self.session)  # a cached relationship value may still hold the row

    def purge(self, row: T) -> None:
        """Hard-delete `row`, even when the model supports soft delete."""
        self.session.delete(row)
        loading.forget_cached(self.session)

    def upsert(self, rows: Iterable[T], update: Callable[[T, T], None] | None = None) -> list[Upserted[T]]:
        """Add or update each row, matched on the model's `natural_key` or else on `id`.

        One SELECT finds the stored rows, soft-deleted ones included. A match is restored and gets the new
        row's field values, or `update(stored, new)` runs instead when given. A row without a match is added.
        Nothing is committed.
        """
        new_rows = list(rows)
        if not new_rows:
            return []
        names = tuple(self.model.natural_key) or ("id",)
        existing = self._stored_by_key(new_rows, names)

        results: list[Upserted[T]] = []
        for new in new_rows:
            key = self._key_of(new, names)
            stored = None if key is None else existing.get(key)
            if stored is None:
                self.session.add(new)
                if key is not None:
                    existing[key] = new
                results.append(Upserted(new, created=True, restored=False))
                continue
            restored = getattr(stored, "deleted_at", None) is not None
            if restored:
                stored.deleted_at = None
            if update is not None:
                update(stored, new)
            elif stored is not new:
                self._copy_fields(stored, new)
            self.session.add(stored)
            results.append(Upserted(stored, created=False, restored=restored))
        loading.forget_cached(self.session)
        return results

    @staticmethod
    def _key_of(row: T, names: tuple[str, ...]) -> Any:  # noqa: ANN401
        """Return the match key of `row`, or None when a key field is unset."""
        values = tuple(getattr(row, name) for name in names)
        if any(value is None for value in values):
            return None
        return values[0] if len(names) == 1 else values

    @staticmethod
    def _copy_fields(stored: T, new: T) -> None:
        """Copy the fields that `new` set onto `stored`, leaving ids, timestamps and unset fields alone.

        A field counts as set when the caller passed it or assigned it (`new.model_fields_set`).
        The same goes for the foreign-key columns that `configure()` generated, which are not
        pydantic fields: they are copied only when present in the instance state.
        """
        for name in new.model_fields_set:
            if name not in _NOT_COPIED and name in type(stored).model_fields:
                setattr(stored, name, getattr(new, name))
        state_dict = inspect(new).dict
        for column in type(stored).__table__.columns:
            if GENERATED in column.info and column.key in state_dict:
                set_attribute(stored, column.key, state_dict[column.key])

    def _stored_by_key(self, rows: list[T], names: tuple[str, ...]) -> dict[Any, T]:
        """Load the stored rows, soft-deleted included, that match any of `rows`, in one SELECT."""
        keys = [key for row in rows if (key := self._key_of(row, names)) is not None]
        if not keys:
            return {}
        columns = [col(getattr(self.model, name)) for name in names]
        size = max(loading.CHUNK_SIZE // len(columns), 1)  # bound parameters per IN list stay under the driver limit
        found: dict[Any, T] = {}
        for start in range(0, len(keys), size):
            chunk = keys[start : start + size]
            match = columns[0].in_(chunk) if len(columns) == 1 else sa.tuple_(*columns).in_(chunk)
            found.update(self.qs().with_deleted().where(match).in_bulk(names[0] if len(names) == 1 else names))
        return found

    def __iter__(self) -> Iterator[T]:
        """Iterate over every alive row (loads them all)."""
        return iter(self.qs())

    def __bool__(self) -> bool:
        """Return whether any alive row exists, with one EXISTS statement."""
        return bool(self.qs())

    def __contains__(self, item: object) -> bool:
        """Return whether an id, or a row, is among the alive rows."""
        return item in self.qs()

    def __getitem__(self, key: int) -> T:
        """Return the alive row with id `key`. Raises KeyError if absent or deleted, TypeError for a slice."""
        if isinstance(key, slice):
            msg = "repo[a:b] would read as ids; slice a queryset instead: repo.qs()[a:b]"
            raise TypeError(msg)
        row = self.qs().where(col(self.model.id) == key).first()
        if row is None:
            raise KeyError(key)
        return row

    def __delitem__(self, key: int) -> None:
        """Soft-delete the alive row with id `key`, or delete it when the model has no `deleted_at`."""
        queryset = self.qs().where(col(self.model.id) == key)
        count = queryset.soft_delete() if hasattr(self.model, "deleted_at") else queryset.purge()
        if count == 0:
            raise KeyError(key)
