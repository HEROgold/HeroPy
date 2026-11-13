"""Pair typed relationships and generate the columns and link tables they are stored in.

Call :func:`configure` once every model is imported, and before ``create_all`` or Alembic read the
metadata. Nothing in ``herogold.orm`` calls it for you, and ``herogold.orm`` has no ``create_all``
helper of its own, so ``SQLModel.metadata.create_all`` and Alembic's ``env.py`` must follow
:func:`configure`. Until it has run, the generated ``<name>_id`` columns do not exist, and the ORM
warns where a missing column would otherwise go unnoticed.
"""

from __future__ import annotations

import functools
import logging
import sys
import types
import warnings
from dataclasses import dataclass
from enum import StrEnum
from inspect import get_annotations
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Index, Table, event, inspect
from sqlalchemy.orm import Mapper
from sqlalchemy.orm.attributes import NO_VALUE, set_attribute
from sqlalchemy.orm.util import identity_key
from sqlmodel import SQLModel

from herogold.orm.core.errors import RelationshipConfigurationError
from herogold.orm.core.loading import FkLoader, LinkLoader, Loader, forget_cached_name, is_internal_write, register_loader
from herogold.orm.core.utils import AUTO, LinkInfo, Relationship

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from sqlalchemy.orm import InstanceState, Session

logger = logging.getLogger(__name__)

GENERATED = "herogold_generated"
"""Key in ``Column.info`` that marks a column made by :func:`configure`; its value is ``Owner.attribute``."""

_REGISTRY: list[Relationship[Any]] = []
_GENERATED_KWARGS: dict[type, set[str]] = {}


class Storage(StrEnum):
    """Where a relationship is stored."""

    OWNER_COLUMN = "column on owner"
    TARGET_COLUMN = "column on target"
    LINK = "link table"


@dataclass(frozen=True)
class Placement:
    """The storage :func:`configure` chose for one relationship."""

    storage: Storage
    reason: str
    column: str | None = None
    """Foreign-key column name, on the owner or on the target depending on ``storage``."""
    table: Table | None = None
    """Link table, for ``Storage.LINK``."""
    near: str | None = None
    """Link-table column that holds the owner's key."""
    far: str | None = None
    """Link-table column that holds the target's key."""


@dataclass(eq=False)
class _Node:
    """Working state of one relationship during a :func:`configure` run."""

    rel: Relationship[Any]
    owner: type[Any]
    target: type[Any]
    pair: _Node | None = None
    error: str | None = None
    placement: Placement | None = None

    @property
    def label(self) -> str:
        return label(self.rel)

    @property
    def many(self) -> bool:
        return self.rel.shape.many

    @property
    def name(self) -> str:
        return self.rel.name

    def fail(self, message: str) -> None:
        """Record why this relationship cannot be configured; the first message wins."""
        self.error = self.error or message


def register(rel: Relationship[Any]) -> None:
    """Remember a typed relationship so :func:`configure` can find it."""
    if rel not in _REGISTRY:
        _REGISTRY.append(rel)


def label(rel: Relationship[Any]) -> str:
    """Return ``Owner.attribute`` for ``rel``."""
    owner = rel.owner
    return f"{owner.__name__ if owner else '?'}.{rel.name}"


def _pending() -> list[Relationship[Any]]:
    """Return typed relationships that neither configured nor failed."""
    return [rel for rel in _REGISTRY if not rel.configured and rel.error is None]


def _warn_unconfigured(where: str) -> None:
    names = ", ".join(label(rel) for rel in _pending()[:5])
    warnings.warn(
        f"herogold.orm: configure() has not run ({where}). Relationships ({names}) and the columns they generate "
        "do not exist yet. Call configure() after the last model is imported, and from Alembic's env.py.",
        UserWarning,
        stacklevel=3,
    )


def check_readable(rel: Relationship[Any]) -> None:
    """Raise when ``rel`` is read before :func:`configure` placed it, or after it refused it."""
    if rel.error is not None:
        raise LookupError(rel.error)
    if not rel.configured:
        _warn_unconfigured(f"{label(rel)} was read")
        msg = f"{label(rel)} is not configured: call herogold.orm.configure() after the models are imported"
        raise RuntimeError(msg)


def declared_annotation_names(cls: type) -> set[str]:
    """Return the names ``cls`` itself annotates, without resolving the annotations.

    Python 3.14 and later defer annotations, so an unquoted forward reference such as ``team: Team | None`` would
    raise ``NameError`` when evaluated. The ``FORWARDREF`` format keeps those names. Earlier versions store the
    annotations on the class, where the names are always readable. ``typing.get_type_hints`` is not used because it
    raises on any unresolved forward reference.
    """
    if sys.version_info >= (3, 14):
        import annotationlib  # noqa: PLC0415  # exists from 3.14 only

        return set(get_annotations(cls, format=annotationlib.Format.FORWARDREF))
    return set(get_annotations(cls))  # the class's own annotations, not evaluated


def missing_column_hint(cls: type, name: str) -> None:
    """Raise a hinted ``AttributeError`` when ``name`` is a column :func:`configure` would generate on ``cls``."""
    if not name.endswith("_id") or name in declared_annotation_names(cls):
        return
    for rel in _pending():
        expected = rel.column if isinstance(rel.column, str) else f"{rel.name}_id"
        if rel.owner is cls and expected == name and not rel.shape.many:
            msg = f"{cls.__name__}.{name} is generated by the relationship {label(rel)}, but configure() has not run yet"
            raise AttributeError(msg)


@event.listens_for(Mapper, "before_configured")
def _check_on_first_use() -> None:
    if _pending():
        _warn_unconfigured("first query or instance")


@event.listens_for(SQLModel.metadata, "before_create")
def _check_on_create(target: object, connection: object, **kw: object) -> None:  # noqa: ARG001
    if _pending():
        _warn_unconfigured("create_all")


def configure(models: Iterable[type] | None = None) -> None:
    """Resolve, pair and store every typed relationship, generating the columns and link tables they need.

    Call it after the last model is imported and before ``create_all`` or Alembic read the metadata;
    it is never run implicitly. It needs no database and is safe to call again after more models
    load. It only adds what is missing, skips relationships it already placed, and leaves a
    relationship whose forward reference does not resolve yet for a later call.

    ``models`` limits the run to relationships declared on those classes, plus the relationships that
    point back at them, so a pair is never judged from one side. Without it, every typed relationship
    is considered.

    Pairs follow the rules in the relationship design: ``inverse=<relationship>`` pins a pair,
    ``inverse=None`` opts out, and otherwise two relationships pair when each is the only automatic
    one from its model to the other. Every member of an ambiguous group fails. A single-valued
    relationship stores a foreign-key column, a declared one if the model has it, else a generated
    ``<name>_id``, or the one named by ``column=``. Pinning ``column=`` on an existing plain column
    attaches the foreign key to it, which Alembic reports as a new constraint, so that change needs a
    migration note. A many-to-many pair, and a list nothing points back to, get a link table.

    Raises:
        RelationshipConfigurationError: Carries every failing relationship's message in ``errors``.
            Relationships that did not fail are configured before it is raised.

    """
    scope = None if models is None else set(models)
    nodes: dict[Relationship[Any], _Node] = {}

    def node_for(rel: Relationship[Any]) -> _Node | None:
        if rel in nodes:
            return nodes[rel]
        if rel.configured or rel.owner is None:
            return None
        try:
            target = rel.resolve()
        except NameError:
            return None  # the target model is not imported yet; a later call places it
        rel.error = None
        node = nodes[rel] = _Node(rel, rel.owner, target)
        _check_models(node)
        return node

    for rel in _REGISTRY.copy():
        if scope is None or rel.owner in scope:
            node_for(rel)
    if scope is not None:
        _add_partners(nodes, node_for)

    _pin_pairs(nodes, node_for)
    _pair_automatically(nodes)
    _check_one_to_one(nodes)
    _place(nodes)
    _report(nodes)


def _check_models(node: _Node) -> None:
    """Fail ``node`` when its owner or target is not a table model with a single-column primary key."""
    for cls, role in ((node.owner, "owner"), (node.target, "target")):
        if getattr(cls, "__table__", None) is None:
            node.fail(f"{node.label}: the {role} {cls.__name__} is not a table model")
    if node.error:
        return
    if len(node.target.__table__.primary_key.columns) != 1:
        node.fail(f"{node.label}: {node.target.__name__} has a composite primary key, which a relationship cannot target")
    elif len(node.owner.__table__.primary_key.columns) != 1:
        node.fail(f"{node.label}: {node.owner.__name__} has a composite primary key, which a relationship cannot own")


def _add_partners(nodes: dict[Relationship[Any], _Node], node_for: Callable[[Relationship[Any]], _Node | None]) -> None:
    """Add the relationships that point back at an in-scope one, so a pair is never judged from one side.

    Without them, an in-scope relationship whose partner lies outside ``models`` would look unpaired and get
    a link table or a column of its own, which a later call could not undo.
    """
    for node in list(nodes.values()):
        for rel in _REGISTRY.copy():
            if rel in nodes or rel.owner is not node.target or rel.configured:
                continue
            try:
                back = rel.resolve()
            except NameError:
                continue
            if back is node.owner:
                node_for(rel)


def _place(nodes: dict[Relationship[Any], _Node]) -> None:
    """Choose the storage of every node: columns first, then the lists and link tables that follow them."""
    _spread_errors(nodes)
    claimed = {
        (rel.owner, rel.placement.column)
        for rel in _REGISTRY
        if rel.placement and rel.placement.storage is Storage.OWNER_COLUMN
    }
    for node in nodes.values():
        if not node.many and node.error is None and node.placement is None:
            _store_in_column(node, claimed)
    _spread_errors(nodes)
    for node in nodes.values():
        if node.error is None:
            _follow_or_link(node, claimed)


def _report(nodes: dict[Relationship[Any], _Node]) -> None:
    """Write each node's outcome to its relationship and raise one error for all that failed."""
    errors: dict[str, str] = {}
    for rel, node in nodes.items():
        if node.error is not None:
            rel.error, rel.configured = node.error, False
            errors[node.label] = node.error
        else:
            rel.placement, rel.configured = node.placement, True
            rel.pair = node.pair.rel if node.pair else None
            if node.placement is not None:
                register_loader(node.owner, node.name, _loader_for(node, node.placement))
                _watch_column(node, node.placement)
    if errors:
        raise RelationshipConfigurationError(errors)


_WATCHED: set[tuple[type, str, str]] = set()


def _watch_column(node: _Node, placement: Placement) -> None:
    """Drop cached values of ``node`` when the foreign-key column it reads is written directly.

    Writing `book.author_id = x` bypasses the relationship, so a cached `book.author` (and the
    cached `author.books` on both the old and the new author) would go stale. Link tables are not
    watched; their rows change through the related list or `QuerySet` statements.
    """
    if placement.storage is Storage.LINK or placement.column is None:
        return
    on_owner = placement.storage is Storage.OWNER_COLUMN
    holder = node.owner if on_owner else node.target
    attr = holder.__mapper__.get_property_by_column(holder.__table__.c[placement.column]).key
    if (holder, attr, node.label) in _WATCHED:
        return
    _WATCHED.add((holder, attr, node.label))

    def on_set(target: object, value: object, old: object, _initiator: object) -> None:
        if is_internal_write():
            return
        state = inspect(target)
        if on_owner:
            forget_cached_name(state, node.name)
            return
        if state.session is not None:
            _forget_readers(state.session, state, node, (value, old))

    event.listen(getattr(holder, attr), "set", on_set, propagate=True)


def _forget_readers(session: Session, state: InstanceState[Any], node: _Node, keys: tuple[object, ...]) -> None:
    """Drop `node`'s cached value on the loaded owners whose primary key is in `keys`."""
    for key in keys:
        if key is None:
            continue
        if key is NO_VALUE:  # the old value was not loaded: any owner of this session may hold it
            if state.key is None:  # a row not in the database yet had no old key, so no owner reads it
                continue
            for instance in list(session.identity_map.values()):
                if isinstance(instance, node.owner):
                    forget_cached_name(inspect(instance), node.name)
            continue
        reader = session.identity_map.get(identity_key(node.owner, key))
        if reader is not None:
            forget_cached_name(inspect(reader), node.name)


def _loader_for(node: _Node, placement: Placement) -> Loader:
    """Return the loader that reads ``node`` from where ``placement`` stores it."""
    if placement.storage is Storage.LINK:
        table = cast("Table", placement.table)
        owner_pk = [c.key for c in node.owner.__table__.primary_key.columns]
        target_pk = [c.key for c in node.target.__table__.primary_key.columns]
        near, far = cast("str", placement.near), cast("str", placement.far)
        return LinkLoader(LinkInfo(table, owner_pk, [near], target_pk, [far], node.target))
    on_owner = placement.storage is Storage.OWNER_COLUMN
    return FkLoader(node.owner, node.target, cast("str", placement.column), on_owner=on_owner)


def _evaluate(value: object) -> object:
    """Call a lambda given for ``inverse=`` or ``column=``; return anything else as is."""
    return value() if isinstance(value, types.FunctionType) else value


def _pin_pairs(nodes: dict[Relationship[Any], _Node], node_for: Callable[[Relationship[Any]], _Node | None]) -> None:
    """Pair relationships whose ``inverse=`` names the other side."""
    for node in list(nodes.values()):
        inverse = node.rel.inverse
        if inverse is AUTO or inverse is None or node.error:
            continue
        try:
            other = _evaluate(inverse)
        except Exception as exc:  # noqa: BLE001  # the user's lambda can raise anything
            node.fail(f"{node.label}: inverse could not be evaluated ({exc!r})")
            continue
        if not isinstance(other, Relationship):
            node.fail(f"{node.label}: inverse must be a relationship, got {other!r}")
            continue
        partner = node_for(other)
        if partner is None:
            node.fail(
                f"{node.label}: inverse {label(other)} cannot be resolved yet; import its models and call configure() again",
            )
            continue
        if partner.owner is not node.target or partner.target is not node.owner:
            node.fail(f"{node.label}: inverse must be a relationship from {node.target.__name__} to {node.owner.__name__}")
            continue
        try:
            partner_inverse = _evaluate(partner.rel.inverse) if partner.rel.inverse is not AUTO else AUTO
        except Exception as exc:  # noqa: BLE001  # the user's lambda can raise anything
            node.fail(f"{node.label}: the inverse of {partner.label} could not be evaluated ({exc!r})")
            partner.fail(f"{partner.label}: inverse could not be evaluated ({exc!r})")
            continue
        if (partner_inverse is not AUTO and partner_inverse is not node.rel) or partner.pair not in (None, node):
            message = (f"{node.label} and {partner.label} are pinned to different pairs, or {partner.label} opts out; "
            "fix inverse=")
            node.fail(message)
            partner.fail(message)
            continue
        node.pair, partner.pair = partner, node


def _pair_automatically(nodes: dict[Relationship[Any], _Node]) -> None:
    """Pair the automatic relationships between two models, or fail all of them when they are not one against one."""
    free = [n for n in nodes.values() if n.rel.inverse is AUTO and n.pair is None and n.error is None]
    seen: set[frozenset[type]] = set()
    for node in free:
        group = frozenset({node.owner, node.target})
        if group in seen:
            continue
        seen.add(group)
        if node.owner is node.target:
            same = [n for n in free if n.owner is node.owner and n.target is node.owner]
            first, second = [n for n in same if not n.many], [n for n in same if n.many]
        else:
            same = [n for n in free if frozenset({n.owner, n.target}) == group]
            first = [n for n in same if n.owner is node.owner]
            second = [n for n in same if n.owner is node.target]
        if len(first) == 1 == len(second):
            first[0].pair, second[0].pair = second[0], first[0]
        elif first and second:
            names = ", ".join(n.label for n in same)
            for member in same:
                member.fail(
                    f"{member.label}: {names} could pair in several ways; "
                    "pin one with inverse=<relationship>, or opt out with inverse=None",
                )


def _declared_fks(owner: type[Any], target: type[Any]) -> list[str]:
    """Return the foreign keys from ``owner`` to ``target`` the user wrote, not the generated ones."""
    prefix = target.__table__.fullname
    return [
        c.name
        for c in owner.__table__.columns
        if GENERATED not in c.info and any(fk.target_fullname.rpartition(".")[0] == prefix for fk in c.foreign_keys)
    ]


def _owns_column(node: _Node) -> bool:
    """Return True when the user already chose a column for this single-valued side."""
    return node.rel.column is not None or bool(_declared_fks(node.owner, node.target))


def _check_one_to_one(nodes: dict[Relationship[Any], _Node]) -> None:
    """Pick which side of a one-to-one stores the column; the other side gets ``None`` for ``_store_in_column``."""
    done: set[_Node] = set()
    for node in nodes.values():
        other = node.pair
        if node.many or other is None or other.many or node in done or node.error or other.error:
            continue
        done.update((node, other))
        if _owns_column(node) and _owns_column(other):
            message = f"{node.label} <-> {other.label}: both sides already have a column; a one-to-one stores it on one side"
            node.fail(message)
            other.fail(message)
        elif not _owns_column(node) and not _owns_column(other):
            message = (f"{node.label} <-> {other.label}: one-to-one with no column chosen; "
            "pin column= on the side that stores it")
            node.fail(message)
            other.fail(message)
        else:
            reader = other if _owns_column(node) else node
            reader.placement = Placement(
                Storage.TARGET_COLUMN,
                "reads the pair's column",
                column=None,
            )


def _spread_errors(nodes: dict[Relationship[Any], _Node]) -> None:
    """Fail a relationship whose pair failed, because it would follow a column that does not exist."""
    changed = True
    while changed:
        changed = False
        for node in nodes.values():
            if node.error is None and node.pair is not None and node.pair.error is not None:
                node.fail(f"{node.label}: its pair {node.pair.label} failed: {node.pair.error}")
                changed = True


def _column_name(node: _Node) -> str:
    """Return the column ``column=`` pins, or ``<name>_id``."""
    pinned = _evaluate(node.rel.column)
    if pinned is None:
        return f"{node.name}_id"
    return pinned if isinstance(pinned, str) else str(cast("Any", pinned).key)


def _store_in_column(node: _Node, claimed: set[tuple[type | None, str | None]]) -> None:
    """Choose, attach or generate the foreign-key column that a single-valued relationship stores."""
    if node.placement is not None:  # the reading side of a one-to-one
        return
    try:
        name = _column_name(node)
    except Exception as exc:  # noqa: BLE001  # the user's lambda can raise anything
        node.fail(f"{node.label}: column could not be evaluated ({exc!r})")
        return
    pinned = node.rel.column is not None
    table: Table = node.owner.__table__
    pk = next(iter(node.target.__table__.primary_key.columns))
    declared = _declared_fks(node.owner, node.target)
    existing = table.columns.get(name)
    reason: str
    if existing is not None and name in declared:
        reason = "declared column"
    elif existing is not None and existing.info.get(GENERATED) == node.label:
        reason = "generated"
    elif existing is not None and pinned and GENERATED not in existing.info:
        table.append_constraint(ForeignKeyConstraint([name], [pk]))
        reason = f"pinned: foreign key attached to existing {name}"
        logger.info("%s: attached a foreign key to the existing column %s; add a migration note", node.label, name)
    elif existing is not None:
        node.fail(
            f"{node.label}: {node.owner.__name__}.{name} exists but is not a foreign key to {node.target.__name__}; "
            f"pin a different name with column=, or column={name!r} to make it one",
        )
        return
    elif not pinned and len(declared) == 1:
        name, reason = declared[0], "the only declared foreign key"
    elif not pinned and len(declared) > 1:
        node.fail(
            f"{node.label}: {len(declared)} foreign keys to {node.target.__name__} ({', '.join(declared)}), "
            f"none named {name}; pin with column=",
        )
        return
    else:
        _generate_column(node, name, pk)
        reason = "generated"
    node.placement = Placement(Storage.OWNER_COLUMN, reason, column=name)
    claimed.add((node.owner, name))


def _generate_column(node: _Node, name: str, pk: Column[Any]) -> None:
    """Append a foreign-key column to the owner's table and map it."""
    column = Column(name, pk.type, ForeignKey(pk), nullable=node.rel.shape.optional, info={GENERATED: node.label})
    node.owner.__table__.append_column(column)
    node.owner.__mapper__.add_property(name, column)
    _accept_generated_kwarg(node.owner, name)


def _accept_generated_kwarg(cls: type, name: str) -> None:
    """Make ``cls(name=...)`` keep the value, since generated columns are not pydantic fields."""
    names = _GENERATED_KWARGS.setdefault(cls, set())
    names.add(name)
    if len(names) > 1:
        return
    original = cls.__init__

    @functools.wraps(original)
    def init(self: object, *args: object, **kwargs: object) -> None:
        extra = {key: kwargs.pop(key) for key in list(kwargs) if key in names}
        original(self, *args, **kwargs)
        for key, value in extra.items():
            set_attribute(self, key, value)  # pydantic's __setattr__ rejects names that are not fields

    cls.__init__ = init  # ty: ignore[invalid-assignment]


def _follow_or_link(node: _Node, claimed: set[tuple[type | None, str | None]]) -> None:
    """Place what is left: readers of a pair's column, lone lists and many-to-many pairs."""
    pair = node.pair
    if node.placement is not None and node.placement.storage is Storage.TARGET_COLUMN and pair and pair.placement:
        node.placement = Placement(Storage.TARGET_COLUMN, node.placement.reason, column=pair.placement.column)
    elif node.placement is not None:
        return
    elif node.many and pair is not None and not pair.many and pair.placement:
        node.placement = Placement(Storage.TARGET_COLUMN, "follows its pair's column", column=pair.placement.column)
    elif node.many and pair is None:
        candidates = [c for c in _declared_fks(node.target, node.owner) if (node.target, c) not in claimed]
        if len(candidates) == 1:
            node.placement = Placement(Storage.TARGET_COLUMN, "the only unclaimed foreign key", column=candidates[0])
        elif candidates:
            node.fail(
                f"{node.label}: {len(candidates)} unclaimed foreign keys fit ({', '.join(candidates)}); pin with inverse=",
            )
        else:
            _link_table(node, None, "link table (nothing points back)")
    elif node.many and pair is not None and pair.many and pair.placement is None:
        _link_table(node, pair, "many-to-many link table")


def _link_table(node: _Node, pair: _Node | None, reason: str) -> None:
    """Create the link table for ``node`` and, in a many-to-many, for its ``pair``."""
    name = f"{node.owner.__tablename__}_{node.name}"
    metadata = SQLModel.metadata
    if name in metadata.tables:
        node.fail(f"{node.label}: the table {name} already exists; rename the relationship")
        return
    owner_pk = next(iter(node.owner.__table__.primary_key.columns))
    target_pk = next(iter(node.target.__table__.primary_key.columns))
    Table(
        name,
        metadata,
        Column("owner_id", owner_pk.type, ForeignKey(owner_pk), primary_key=True),
        Column("target_id", target_pk.type, ForeignKey(target_pk), primary_key=True),
        Index(f"ix_{name}_tgt", "target_id"),
        info={GENERATED: node.label},
    )
    table = metadata.tables[name]
    node.placement = Placement(Storage.LINK, reason, table=table, near="owner_id", far="target_id")
    if pair is not None:
        pair.placement = Placement(Storage.LINK, reason, table=table, near="target_id", far="owner_id")
