"""Module with helper methods for the database package."""

from __future__ import annotations

import ast
import sys
import types
from typing import TYPE_CHECKING, Any, ForwardRef, NamedTuple, Self, TypeVar, Union, cast, get_args, get_origin, overload

from sqlalchemy import Column, ForeignKey, Index, Table, UniqueConstraint, and_
from sqlmodel import SQLModel, select

from herogold.log import LoggerMixin
from herogold.sentinel import create_sentinel

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement

    # Imported for typing only: ``_BaseModel`` appears solely in (stringized)
    # annotations.
    # Importing it at runtime creates a circular import (model -> utils -> model).
    from herogold.orm.core.model import _BaseModel

SELF = create_sentinel()
"""Sentinel value for self-referential relationships in SQLModel classes."""


T = TypeVar("T", bound=SQLModel)



class LinkInfo[T: _BaseModel](NamedTuple):
    """Resolved association table for a single (owner, relationship) pair."""

    table: Table
    owner_pk: list[str]
    """Owner primary-key attribute names (e.g. ``["id"]`` or ``["id", "timestamp"]``)."""
    owner_cols: list[str]
    """Link-table column names referencing the owner PK."""
    target_pk: list[str]
    """Target primary-key attribute names."""
    target_cols: list[str]
    """Link-table column names referencing the target PK."""
    target: type[T]

    def owner_values(self, owner: _BaseModel) -> dict[str, object]:
        """Map the link-table owner columns to ``owner``'s primary-key values."""
        return {col: getattr(owner, pk) for col, pk in zip(self.owner_cols, self.owner_pk, strict=True)}

    def target_values(self, target: _BaseModel) -> dict[str, object]:
        """Map the link-table target columns to ``target``'s primary-key values."""
        return {col: getattr(target, pk) for col, pk in zip(self.target_cols, self.target_pk, strict=True)}

    def owner_filter(self, owner: _BaseModel) -> ColumnElement[bool]:
        """Match the link row(s) belonging to ``owner``."""
        return and_(*(self.table.c[col] == value for col, value in self.owner_values(owner).items()))

    def target_join(self) -> ColumnElement[bool]:
        """Join condition between the link table and the target table."""
        return and_(*(
            self.table.c[col] == self.target.__table__.c[pk]
            for col, pk in zip(self.target_cols, self.target_pk, strict=True)
        ))


class Shape(NamedTuple):
    """Whether a relationship holds one object or many, and whether it may be empty."""

    many: bool
    """True for ``list[Target]``, False for ``Target`` and ``Target | None``."""
    optional: bool
    """True when the declared type allows ``None``."""


class Relationship[T](LoggerMixin):
    """Descriptor for a single-valued relationship backed by an association table.

    Two call forms exist. ``Relationship(Target)`` is the original form and keeps its
    link-table behaviour. ``Relationship[Optional["Target"]]()`` and
    ``Relationship[list["Target"]]()`` are the typed form: the type argument declares the
    :class:`Shape` and the target, and the target is resolved by :meth:`resolve` once every
    model exists. Declare the typed form without an annotation, because SQLModel turns an
    annotated class attribute into a column.

    Instead of adding a foreign-key column to the owner, each concrete
    ``table=True`` owner gets its own association (join) table linking the owner's
    primary key to the target's. The owner's own table is left unchanged.

    Semantics are single-valued: a ``UNIQUE`` constraint on the owner columns means
    at most one link per owner row, so ``instance.rel`` returns one object or
    ``None`` and ``instance.rel = target`` replaces that single link.

    Link tables are built per concrete subclass by :class:`ModelMeta` (after
    SQLModel has built the owner's ``__table__``), so a single inherited descriptor
    on ``_BaseModel`` yields a distinct link table for every model.
    """

    if TYPE_CHECKING:
        # Typing only: the call form picks the typing. ``Relationship(Target)`` is checked as
        # ``_LegacyRelationship[Target]`` (instances ``Target | None``, class access ``type[Target]``).
        # ``Relationship[T]()`` keeps ``Relationship[T]`` (instances ``T``, class access the descriptor).
        @overload
        def __new__[M: _BaseModel](cls, related_model: type[M], *, optional: bool = ...) -> _LegacyRelationship[M]: ...
        @overload
        def __new__(cls, *, optional: bool = ...) -> Self: ...
        def __new__(cls, *args: object, **kwargs: object) -> Any:
            """Typing-only signature; the runtime class is built by ``__init__``."""

    def __init__(self, related_model: type[_BaseModel] = SELF, *, optional: bool = True) -> None:
        """Initialise the descriptor.

        ``related_model`` may be the ``SELF`` sentinel (self-referential) or a
        concrete ``table=True`` model. ``optional`` is accepted for API symmetry;
        access always returns ``None`` when there is no link.
        """
        self.optional = optional
        self.related_model = related_model
        self._declared: bool = False
        self._type_arg: object = None
        self._declared_shape: Shape | None = None
        self._owner: type | None = None
        self._resolved: type | None = None
        # Per-owner registry: a single inherited descriptor serves many subclasses.
        self._links: dict[type, LinkInfo[_BaseModel]] = {}

    def __set_name__(self, owner: type[_BaseModel], name: str) -> None:
        """Record the attribute name and, for the typed form, the shape and owner.

        Link tables are built later, per subclass. ``__orig_class__`` exists by now
        because Python sets it right after ``Relationship[...]()`` returns, which is
        before the class body finishes.
        """
        self.name = name
        orig = getattr(self, "__orig_class__", None)
        if orig is not None:
            (arg,) = get_args(orig)
            self._declared = True
            self._type_arg = arg
            self._declared_shape = _shape_of(arg)
            self._owner = owner

    @property
    def shape(self) -> Shape:
        """Return whether this relationship is single or many valued, and optional or not."""
        if self._declared_shape is not None:
            return self._declared_shape
        return Shape(many=False, optional=self.optional)

    def resolve(self) -> type:
        """Return the target class of the typed form, evaluating forward references.

        Call this after every model exists. Raises ``NameError`` while the target is
        still undefined, and ``TypeError`` for the original call form.
        """
        if not self._declared or self._owner is None:
            msg = f"Relationship '{self.name}' was not declared with a type argument."
            raise TypeError(msg)
        if self._resolved is None:
            self._resolved = _target_of(self._type_arg, self._owner)
        return self._resolved

    def __set__(self, instance: Any, value: T) -> None:  # noqa: ANN401
        """Persist ``value`` if needed and replace the owner's single link row."""
        if self._declared:
            msg = f"Assigning to the typed relationship '{self.name}' is not implemented yet."
            raise NotImplementedError(msg)
        target = cast("_BaseModel", value)
        instance.logger.debug("Setting relationship '%s' to %s", self.name, value, extra={"record": instance})
        info = self._links[type(instance)]
        if instance.id is None:
            msg = f"Owner must be persisted before setting relationship '{self.name}'."
            raise ValueError(msg)
        if target.id is None:
            target.add()
        session = type(instance).session
        session.exec(info.table.delete().where(info.owner_filter(instance)))
        session.exec(info.table.insert().values(**info.owner_values(instance), **info.target_values(target)))
        session.commit()

    def __delete__(self, instance: Any) -> None:  # noqa: ANN401
        """Remove the owner's link row(s).

        For the typed form, `del owner.rel` on a single-valued relationship is the same as
        `owner.rel = None`. On a many-valued one it raises `TypeError`, because there is no single
        value to clear; mutate the list instead.
        """
        if self._declared:
            if self.shape.many:
                msg = f"Cannot delete the many-valued relationship '{self.name}'; remove items from it instead."
                raise TypeError(msg)
            self.__set__(instance, cast("T", None))
            return
        info = self._links.get(type(instance))
        if info is None:
            return
        session = type(instance).session
        session.exec(info.table.delete().where(info.owner_filter(instance)))
        session.commit()

    @overload
    def __get__(self, instance: None, owner: type) -> Self: ...
    @overload
    def __get__(self, instance: object, owner: type) -> T: ...

    def __get__(self, instance: Any, owner: type) -> Any:
        """Class access returns the target class; instance access joins the link table."""
        if instance is None:
            return self if self._declared else self._resolve_target(cast("type[_BaseModel]", owner))
        if self._declared:
            return loading.load_typed(self, instance)
        info = self._links.get(type(instance))
        if info is None:
            return None
        session = type(instance).session
        query = select(info.target).join(info.table, info.target_join()).where(info.owner_filter(instance))
        return cast("T | None", session.exec(query).first())

    def build_link_for(self, owner: type[_BaseModel]) -> None:
        """Build (once) the association table joining ``owner`` to the target.

        Called from :class:`ModelMeta` for each concrete ``table=True`` subclass.
        Idempotent per owner and guarded against duplicate metadata registration.
        """
        if self._declared or owner in self._links:
            return  # the typed form builds its storage in a later step
        target = self._resolve_target(owner)
        # Prefixes (owner tablename / attribute name) keep the self-referential case from colliding.
        owner_pk, owner_cols = _pk_columns(owner, prefix=str(owner.__tablename__))
        target_pk, target_cols = _pk_columns(target, prefix=self.name)
        link_name = f"{owner.__tablename__}_{self.name}"
        table = owner.metadata.tables.get(link_name)
        if table is None:
            table = _create_link_table(link_name, owner, owner_cols, target, target_cols)
        self._links[owner] = LinkInfo(table, owner_pk, owner_cols, target_pk, target_cols, target)

    def _resolve_target(self, owner: type[_BaseModel]) -> type[_BaseModel]:
        """Resolve ``SELF`` to the owner; otherwise return the declared target."""
        if self._is_self_referential(owner):
            return owner
        return self.related_model

    def _is_self_referential(self, owner: type[_BaseModel]) -> bool:
        """Return True if the relationship is self-referential for the given owner."""
        return self.related_model is SELF or owner is self.related_model


if TYPE_CHECKING:

    class _LegacyRelationship[M: _BaseModel](Relationship[M]):
        """Typing-only result of ``Relationship(Target)``; the runtime class is :class:`Relationship`."""

        @overload
        def __get__(self, instance: None, owner: type) -> type[M]: ...
        @overload
        def __get__(self, instance: object, owner: type) -> M | None: ...
        def __get__(self, instance: Any, owner: type) -> Any:  # ty: ignore[incompatible-method-override]
            """Typing-only signature; the runtime ``__get__`` is inherited from :class:`Relationship`."""


class SelfRelationship(Relationship[Any]):
    """A :class:`Relationship` from a model to itself, typed as the owning model.

    ``Relationship(SELF)`` cannot know its owner when it is created, so its target
    type is unknown. This descriptor's ``__get__`` is generic over the owner instead:
    ``parent = SelfRelationship()`` on ``Node`` makes ``node.parent`` a ``Node | None``.
    """

    def __init__(self, *, optional: bool = True) -> None:
        """Initialise a relationship that targets the owning model."""
        super().__init__(SELF, optional=optional)

    if TYPE_CHECKING:

        @overload
        def __get__[O: _BaseModel](self, instance: None, owner: type[O]) -> type[O]: ...
        @overload
        def __get__[O: _BaseModel](self, instance: O, owner: type[O]) -> O | None: ...
        def __get__(self, instance: _BaseModel | None, owner: type[_BaseModel]) -> Any:  # ty: ignore[incompatible-method-override]
            """Typing-only signature; the runtime ``__get__`` is inherited from :class:`Relationship`."""


class ModelMeta(type(SQLModel)):
    """Metaclass that builds association tables for each concrete model.

    SQLModel builds a class's ``__table__`` in the metaclass ``__init__`` (after
    ``__new__``), so this is the earliest hook where a subclass's table exists.
    For every concrete ``table=True`` subclass it scans the MRO for
    :class:`Relationship` descriptors and asks each to build its link table.
    """

    def __init__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, object], **kwargs: object) -> None:
        """Build link tables once the owner's ``__table__`` has been created."""
        super().__init__(name, bases, namespace, **kwargs)
        if getattr(cls, "__table__", None) is None:
            return  # abstract base (no table) -> nothing to link
        seen: set[str] = set()
        for cls2 in cls.__mro__:
            for attr_name, attr in vars(cls2).items():
                if attr_name in seen:
                    continue
                seen.add(attr_name)
                if isinstance(attr, Relationship):
                    # pyrefly: ignore [bad-argument-type]
                    attr.build_link_for(cls)


def _shape_of(arg: object) -> Shape:
    """Return the :class:`Shape` that the type argument ``arg`` declares."""
    if isinstance(arg, ForwardRef):
        arg = arg.__forward_arg__
    if isinstance(arg, str):
        return _shape_of_node(ast.parse(arg, mode="eval").body)
    origin = get_origin(arg)
    if origin is Union or origin is types.UnionType:
        inner = [a for a in get_args(arg) if a is not type(None)]
        if len(inner) != 1:
            msg = f"A relationship type argument must be one type or None, got {arg!r}."
            raise TypeError(msg)
        return Shape(many=_shape_of(inner[0]).many, optional=len(inner) != len(get_args(arg)))
    return Shape(many=origin is list, optional=False)


def _shape_of_node(node: ast.expr) -> Shape:
    """Return the :class:`Shape` of a quoted type argument such as ``"Team | None"``."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        sides = [node.left, node.right]
        inner = [s for s in sides if not (isinstance(s, ast.Constant) and s.value is None)]
        if len(inner) != 1 or len(inner) == len(sides):
            msg = "A quoted relationship type argument must be one type or None."
            raise TypeError(msg)
        return Shape(many=_shape_of_node(inner[0]).many, optional=True)
    if isinstance(node, ast.Subscript):
        name = _node_name(node.value)
        if name == "Optional":
            return Shape(many=_shape_of_node(node.slice).many, optional=True)
        if name == "Union":
            members = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
            inner = [m for m in members if not (isinstance(m, ast.Constant) and m.value is None)]
            if len(inner) != 1:
                msg = "A quoted relationship type argument must be one type or None."
                raise TypeError(msg)
            return Shape(many=_shape_of_node(inner[0]).many, optional=len(inner) != len(members))
        return Shape(many=name in {"list", "List"}, optional=False)
    return Shape(many=False, optional=False)


def _node_name(node: ast.expr) -> str | None:
    """Return the last name of ``Name`` or ``module.Name`` (such as ``typing.Optional``), else None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _target_of(arg: object, owner: type) -> type:
    """Evaluate forward references in ``arg`` and unwrap ``list[...]`` and ``... | None`` to the target class."""
    namespace = dict(vars(sys.modules[owner.__module__]))
    namespace.update(vars(owner))
    while True:
        if isinstance(arg, ForwardRef):
            arg = arg.__forward_arg__
        if isinstance(arg, str):
            arg = eval(arg, namespace)  # noqa: S307  # quoted type argument written by the model author
            continue
        origin = get_origin(arg)
        if origin is Union or origin is types.UnionType:
            arg = next(a for a in get_args(arg) if a is not type(None))
        elif origin is list:
            (arg,) = get_args(arg)
        else:
            return cast("type", arg)


def get_foreign_key[M: SQLModel](table: type[M], column: str = "id") -> str:
    """Return ``<table>.<column>`` for the given model class.

    The generic parameter allows callers such as ``Relationship[T]`` to pass
    ``type[T]`` without a typing error.
    """
    return f"{table.__tablename__}.{column}"



def _pk_columns(model: type[_BaseModel], prefix: str) -> tuple[list[str], list[str]]:
    """Return ``model``'s primary-key attribute names and the matching ``<prefix>_<pk>`` link-table column names."""
    pk = [c.name for c in model.__table__.primary_key.columns]
    return pk, [f"{prefix}_{name}" for name in pk]


def _fk_columns(model: type[_BaseModel], link_cols: list[str]) -> list[Column]:
    """Build link-table columns ``link_cols`` that reference ``model``'s primary key."""
    return [
        Column(col, pk_col.type, ForeignKey(f"{model.__tablename__}.{pk_col.name}"), primary_key=True)
        for col, pk_col in zip(link_cols, model.__table__.primary_key.columns, strict=True)
    ]


def _create_link_table(
    name: str,
    owner: type[_BaseModel],
    owner_cols: list[str],
    target: type[_BaseModel],
    target_cols: list[str],
) -> Table:
    """Create the association table linking ``owner`` rows to ``target`` rows."""
    return Table(
        name,
        owner.metadata,
        *_fk_columns(owner, owner_cols),
        *_fk_columns(target, target_cols),
        # single-valued: at most one link per owner row
        UniqueConstraint(*owner_cols, name=f"uq_{name}"),
        # secondary index for reverse (target -> owners) lookups
        Index(f"ix_{name}_tgt", *target_cols),
    )


# Imported last: loading imports this module, and importing it registers the cohort ``load`` listener.
from herogold.orm.core import loading  # noqa: E402
