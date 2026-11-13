"""Write through a typed relationship: related lists and assignment of single-valued relationships.

A many-valued relationship reads as a :class:`RelatedList`. Its writes go to the owner's session and
are never committed. A write is queued on the session and applied at these points:

* ``before_flush``, for every write whose rows already have ids;
* ``after_flush_postexec``, for writes that waited for ids a flush just assigned. Changes made in
  ``after_flush`` are lost, because SQLAlchemy resets the state after that event;
* ``before_commit``;
* before a read of any typed relationship on the same session.

A foreign-key column write is a plain attribute set when the id it stores is known. When the id
only exists after a flush, the write waits and then runs as one ``UPDATE`` per column and chunk of
rows, and the loaded attribute is set without marking the row dirty, so no second flush is needed.
Link-table writes run on ``session.connection()``, inside the caller's transaction, batched into one
statement per consecutive run of the same kind.
"""

from __future__ import annotations

import copy
import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self, cast

from sqlalchemy import bindparam, delete, event, inspect, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import get_attribute, set_attribute, set_committed_value

from herogold.orm.core import loading

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sqlalchemy import Table
    from sqlalchemy.orm import SessionTransaction

    from herogold.orm.core.configure import Placement
    from herogold.orm.core.utils import Relationship

__all__ = ["RelatedList", "assign", "settle", "wrap"]

_QUEUE = "herogold_related_writes"
"""Key in ``Session.info`` of the list of writes that wait to be applied."""


@dataclass(eq=False)
class _Write:
    """One queued relationship write."""

    kind: str
    """``fk`` sets a column, ``add`` and ``remove`` and ``clear`` change link rows."""
    rel: Relationship[Any]
    owner: Any = None
    target: Any = None
    row: Any = None
    """For ``fk``: the row that holds the column."""
    attr: str = ""
    """For ``fk``: the mapped attribute of the column."""
    key: Any = None
    """For ``fk``: the row whose primary key the column stores, or None."""
    scopes: frozenset[SessionTransaction] = frozenset()
    """The SAVEPOINTs that were open when the write was queued; rolling one back drops the write."""

    @property
    def group(self) -> tuple[str, str]:
        """Return the storage this write touches; writes of one group apply in the order they were made."""
        if self.kind == "fk":
            return "fk", f"{self.row.__table__.name}.{self.attr}"
        return "link", cast("Table", _placement(self.rel).table).name

    def ready(self, *, after_flush: bool) -> bool:
        """Return True when every row this write needs has a primary key."""
        if self.kind == "fk":
            if self.key is not None and _pk(self.key) is None:
                return False
            return not after_flush or inspect(self.row).key is not None
        if inspect(self.owner).key is None:  # a link row needs both rows to exist, not only to have ids
            return False
        return self.kind == "clear" or inspect(self.target).key is not None


class RelatedList(list):
    """The rows of a many-valued relationship. Writes go through the owner's session."""

    def __init__(self, rel: Relationship[Any], owner: object, items: Iterable[Any] = ()) -> None:
        """Hold ``items`` for ``rel`` on ``owner``, which is kept by weak reference."""
        super().__init__(items)
        self._rel = rel
        self._owner = weakref.ref(owner)

    def append(self, item: Any) -> None:  # noqa: ANN401
        """Relate ``item`` to the owner. Appending a row that is already in the list does nothing."""
        if any(x is item for x in self):
            return
        _add(self._rel, self._owner_row(), item)
        super().append(item)

    def extend(self, items: Iterable[Any]) -> None:
        """Relate each of ``items`` to the owner."""
        for item in list(items):
            self.append(item)

    def remove(self, item: Any) -> None:  # noqa: ANN401
        """Unrelate ``item``. Raises ``ValueError`` when it is not in the list."""
        index = next((i for i, x in enumerate(self) if x is item), None)
        if index is None:
            msg = "list.remove(x): x not in list"
            raise ValueError(msg)
        _remove(self._rel, self._owner_row(), item)
        super().__delitem__(index)

    def clear(self) -> None:
        """Unrelate every item."""
        if not self:
            return
        _clear(self._rel, self._owner_row(), list(self))
        super().clear()

    def pop(self, index: int = -1) -> Any:  # noqa: ANN401  # ty: ignore[incompatible-method-override]
        """Unrelate and return the item at ``index``."""
        item = self[index]
        self.remove(item)
        return item

    def __delitem__(self, index: int | slice) -> None:  # ty: ignore[incompatible-method-override]
        """Unrelate the item or items at ``index``."""
        for item in [self[index]] if isinstance(index, int) else self[index]:
            self.remove(item)

    def __iadd__(self, items: Iterable[Any]) -> Self:
        """Relate each of ``items``, like :meth:`extend`."""
        self.extend(items)
        return self

    def insert(self, index: int, item: Any) -> None:  # noqa: ANN401, ARG002  # ty: ignore[incompatible-method-override]
        """Raise ``TypeError``: the database stores no order."""
        msg = "a related list has no stored order; use append"
        raise TypeError(msg)

    def __setitem__(self, index: Any, value: Any) -> None:  # noqa: ANN401
        """Raise ``TypeError``: remove the item and append the new one."""
        msg = "a related list cannot replace items; use remove and append"
        raise TypeError(msg)

    def __copy__(self) -> list[Any]:
        """Return a plain list. A copy of a related list must not replay its writes, and has no owner to write to."""
        return list(self)

    def __deepcopy__(self, memo: dict[int, Any]) -> list[Any]:
        """Return a plain list of deep copies of the items."""
        return copy.deepcopy(list(self), memo)

    def __reduce_ex__(self, protocol: object) -> tuple[Any, ...]:
        """Pickle as a plain list: the owner is a weak reference and the relationship belongs to the class."""
        return (list, (list(self),))

    def _owner_row(self) -> Any:  # noqa: ANN401
        owner = self._owner()
        if owner is None:
            msg = "the owner of this related list no longer exists"
            raise ReferenceError(msg)
        return owner


def wrap(state: Any, name: str, items: list[Any]) -> list[Any]:  # noqa: ANN401
    """Return ``items`` as the related list of the relationship ``name`` of ``state``'s instance."""
    owner = state.obj()
    if owner is None or isinstance(items, RelatedList):
        return items
    return RelatedList(getattr(type(owner), name), owner, items)


def assign(rel: Relationship[Any], owner: Any, value: Any) -> None:  # noqa: ANN401
    """Set a single-valued relationship to ``value`` (a row or None), keeping the paired relationship in step."""
    if rel.shape.many:
        if isinstance(value, RelatedList) and value._owner() is owner:  # noqa: SLF001  # ``rows += more`` assigns the list back
            return
        msg = f"{rel.name} holds many rows: use append, extend, remove or clear"
        raise TypeError(msg)
    session = _session_of(owner)
    _adopt(session, value)
    placement = _placement(rel)
    state = inspect(owner)
    if placement.storage.name == "OWNER_COLUMN":
        attr = _attr(type(owner), cast("str", placement.column))
        old_id = get_attribute(owner, attr)
        _set_fk(session, owner, attr, value)
        _detach(session, rel.resolve(), old_id, rel.pair, owner)
        _attach(rel.pair, value, owner)
    else:  # one-to-one read from the other side: the pair's column lives on the target
        target_model = rel.resolve()
        attr = _attr(target_model, cast("str", placement.column))
        previous = getattr(owner, rel.name)
        if previous is value:
            return
        if previous is not None:
            _set_fk(session, previous, attr, None)
            _attach(rel.pair, previous, None, left=owner)
        if value is not None:
            _detach(session, type(owner), get_attribute(value, attr), rel, value)
            _set_fk(session, value, attr, owner)
            _attach(rel.pair, value, owner)
    loading.store(state, rel.name, value)


def settle(session: Session) -> None:
    """Apply the session's queued writes now, flushing when some of them wait for ids."""
    if not session.info.get(_QUEUE):
        return
    _run(session, after_flush=False)
    if session.info.get(_QUEUE):
        session.flush()


def _add(rel: Relationship[Any], owner: Any, item: Any) -> None:  # noqa: ANN401
    session = _session_of(owner)
    _adopt(session, item)
    pair = rel.pair
    if _placement(rel).table is not None:
        _enqueue(session, _Write("add", rel, owner, item))
    else:
        attr = _attr(type(item), cast("str", _placement(rel).column))
        _detach(session, type(owner), get_attribute(item, attr), rel, item)
        _set_fk(session, item, attr, owner)
    _attach(pair, item, owner)


def _remove(rel: Relationship[Any], owner: Any, item: Any) -> None:  # noqa: ANN401
    session = _session_of(owner)
    if _placement(rel).table is not None:
        _enqueue(session, _Write("remove", rel, owner, item))
    else:
        _set_fk(session, item, _attr(type(item), cast("str", _placement(rel).column)), None)
    _attach(rel.pair, item, None, left=owner)


def _clear(rel: Relationship[Any], owner: Any, items: list[Any]) -> None:  # noqa: ANN401
    session = _session_of(owner)
    if _placement(rel).table is not None:
        _enqueue(session, _Write("clear", rel, owner))
        for item in items:
            _attach(rel.pair, item, None, left=owner)
    else:
        for item in items:
            _remove(rel, owner, item)


def _set_fk(session: Session, row: Any, attr: str, key: Any) -> None:  # noqa: ANN401
    """Store the primary key of ``key`` (None clears it) in the column ``attr`` of ``row``."""
    write = _Write("fk", None, row=row, attr=attr, key=key)
    queue = session.info.get(_QUEUE, [])
    if write.ready(after_flush=False) and not any(w.group == write.group for w in queue):
        _set_column(row, attr, None if key is None else _pk(key))
    else:
        _enqueue(session, write)


def _set_column(row: Any, attr: str, value: object) -> None:  # noqa: ANN401
    """Write a foreign-key column for a relationship write; the caches are kept in step by the caller."""
    with loading.internal_write():
        set_attribute(row, attr, value)


def _enqueue(session: Session, write: _Write) -> None:
    write.scopes = _open_savepoints(session)
    session.info.setdefault(_QUEUE, []).append(write)


def _open_savepoints(session: Session) -> frozenset[SessionTransaction]:
    """Return the SAVEPOINT transactions of ``session`` that are open now, innermost first to outermost."""
    open_now: set[SessionTransaction] = set()
    transaction = session.get_nested_transaction()
    while transaction is not None:
        if transaction.nested:
            open_now.add(transaction)
        transaction = transaction.parent
    return frozenset(open_now)


def _attach(pair: Relationship[Any] | None, holder: Any, item: Any, *, left: Any = None) -> None:  # noqa: ANN401
    """Update ``holder``'s loaded value of ``pair`` after ``item`` joined it, or after ``left`` left it.

    Nothing happens for a many-valued ``pair`` that is not loaded: the next read loads it.
    """
    if pair is None or holder is None:
        return
    state = inspect(holder)
    cached: Any = loading.peek(state, pair.name)
    if pair.shape.many:
        if cached is loading.MISSING:
            return
        if item is not None and not any(x is item for x in cached):
            list.append(cached, item)
        elif item is None:
            _drop(cached, left)
    elif item is not None or cached is loading.MISSING or cached is left:
        loading.store(state, pair.name, item)


def _detach(session: Session, model: type[Any], ident: object, rel: Relationship[Any] | None, item: Any) -> None:  # noqa: ANN401
    """Take ``item`` out of the loaded value of ``rel`` on the row ``model`` has under ``ident``, if it is in memory."""
    if rel is None or ident is None:
        return
    holder = session.identity_map.get(model.__mapper__.identity_key_from_primary_key((ident,)))
    if holder is None:
        return
    state = inspect(holder)
    cached: Any = loading.peek(state, rel.name)
    if cached is loading.MISSING:
        return
    if rel.shape.many:
        _drop(cached, item)
    elif cached is item:
        loading.store(state, rel.name, None)


def _drop(values: list[Any], item: Any) -> None:  # noqa: ANN401
    """Remove ``item`` from ``values`` by identity without writing."""
    for index, value in enumerate(values):
        if value is item:
            list.__delitem__(values, index)
            return


def _session_of(owner: Any) -> Session:  # noqa: ANN401
    session = inspect(owner).session
    if session is None:
        msg = f"{type(owner).__name__} is not in a session: add it to one before changing its relationships"
        raise RuntimeError(msg)
    return session


def _adopt(session: Session, row: Any) -> None:  # noqa: ANN401
    """Add ``row`` to ``session`` when it is in none."""
    if row is None:
        return
    current = inspect(row).session
    if current is None:
        session.add(row)
    elif current is not session:
        msg = f"{type(row).__name__} belongs to another session than the row it is related to"
        raise ValueError(msg)


def _placement(rel: Relationship[Any]) -> Placement:
    """Return where ``configure()`` stored ``rel``."""
    return cast("Placement", rel.placement)


def _attr(model: type[Any], column: str) -> str:
    return model.__mapper__.get_property_by_column(model.__table__.c[column]).key


def _pk(row: Any) -> object | None:  # noqa: ANN401
    """Return the single primary-key value of ``row``, or None while it has none."""
    state = inspect(row)
    if state.identity:
        return state.identity[0]
    value = state.mapper.primary_key_from_instance(row)[0]
    return None if value is None else value


def _run(session: Session, *, after_flush: bool) -> None:
    """Apply the queued writes whose rows have ids; keep the rest, and keep each group's order."""
    queue: list[_Write] = session.info.get(_QUEUE, [])
    if not queue:
        return
    waiting: list[_Write] = []
    session.info[_QUEUE] = waiting
    held: set[tuple[str, str]] = set()
    batch: list[_Write] = []
    for write in queue:
        if write.group in held or not write.ready(after_flush=after_flush):
            held.add(write.group)
            waiting.append(write)
            continue
        if write.kind == "fk" and not after_flush:
            _set_column(write.row, write.attr, None if write.key is None else _pk(write.key))
            continue
        if batch and (batch[0].kind, batch[0].group, batch[0].rel) != (write.kind, write.group, write.rel):
            _execute(session, batch)
            batch = []
        batch.append(write)
        if write.kind == "clear":
            _execute(session, batch)
            batch = []
    if batch:
        _execute(session, batch)


def _execute(session: Session, batch: list[_Write]) -> None:
    """Run a batch of writes of one kind on one storage as one statement."""
    first = batch[0]
    conn = session.connection()
    if first.kind == "fk":
        table = first.row.__table__
        column = table.c[next(c.name for c in table.columns if c.key == first.attr)]
        pk = next(iter(table.primary_key.columns))
        statement = update(table).where(pk == bindparam("w_pk")).values({column.name: bindparam("w_val")})
        conn.execute(statement, [{"w_pk": _pk(w.row), "w_val": None if w.key is None else _pk(w.key)} for w in batch])
        for write in batch:
            set_committed_value(write.row, write.attr, None if write.key is None else _pk(write.key))
        return
    placement = _placement(first.rel)
    table, near, far = cast("Table", placement.table), cast("str", placement.near), cast("str", placement.far)
    if first.kind == "clear":
        conn.execute(delete(table).where(table.c[near] == _pk(first.owner)))
    elif first.kind == "add":
        conn.execute(table.insert(), [{near: _pk(w.owner), far: _pk(w.target)} for w in batch])
    else:
        statement = delete(table).where(table.c[near] == bindparam("w_near"), table.c[far] == bindparam("w_far"))
        conn.execute(statement, [{"w_near": _pk(w.owner), "w_far": _pk(w.target)} for w in batch])


def _before_flush(session: Session, _context: object, _instances: object) -> None:
    _run(session, after_flush=False)


def _after_flush_postexec(session: Session, _context: object) -> None:
    _run(session, after_flush=True)


def _before_commit(session: Session) -> None:
    _run(session, after_flush=False)


def _pending_to_persistent(_session: Session, instance: object) -> None:
    """Forget the empty lists a never-flushed row cached for appends: rows may point at it now."""
    loading.drop_empty(inspect(instance))


def _forget(session: Session) -> None:
    """Drop the queued writes once the whole transaction ended.

    ``after_rollback`` also fires when a SAVEPOINT rolls back. Then only the writes made inside that
    SAVEPOINT go, which :func:`_after_soft_rollback` handles, and the writes queued before it stay.
    """
    if not session.in_nested_transaction():
        session.info.pop(_QUEUE, None)


def _after_soft_rollback(session: Session, previous: SessionTransaction) -> None:
    """Drop the queued writes that a rolled back SAVEPOINT made.

    The caches are cleared as well, by ``loading``, because a related list may hold items that were
    appended inside the SAVEPOINT. They reload on the next read.
    """
    if previous.nested:
        queue: list[_Write] = session.info.get(_QUEUE, [])
        session.info[_QUEUE] = [write for write in queue if previous not in write.scopes]


event.listen(Session, "before_flush", _before_flush)
event.listen(Session, "after_flush_postexec", _after_flush_postexec)  # not after_flush: its changes are lost
event.listen(Session, "before_commit", _before_commit)
event.listen(Session, "pending_to_persistent", _pending_to_persistent)
event.listen(Session, "after_commit", _forget)
event.listen(Session, "after_rollback", _forget)
event.listen(Session, "after_soft_rollback", _after_soft_rollback)
