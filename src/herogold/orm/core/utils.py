"""Module with helper methods for the database package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple, TypeVar, cast, overload

from sqlalchemy import Column, ForeignKey, Index, Table, UniqueConstraint, and_
from sqlmodel import SQLModel, select

from herogold.log import LoggerMixin
from herogold.sentinel import create_sentinel

if TYPE_CHECKING:
    import sys

    from sqlalchemy import ColumnElement

    if sys.version_info >= (3, 13):
        from typing import TypeIs
    else:
        from typing_extensions import TypeIs

    # Imported for typing only: ``_BaseModel`` appears solely in (stringized)
    # annotations and the lazily-evaluated PEP 695 bound ``Relationship[T: _BaseModel]``.
    # Importing it at runtime creates a circular import (model -> utils -> model).
    from herogold.orm.core.model import _BaseModel

SELF = create_sentinel()
"""Sentinel value for self-referential relationships in SQLModel classes."""


T = TypeVar("T", bound=SQLModel)


def get_foreign_key[M: SQLModel](table: type[M], column: str = "id") -> str:
    """Return ``<table>.<column>`` for the given model class.

    The generic parameter allows callers such as ``Relationship[T]`` to pass
    ``type[T]`` without a typing error.
    """
    return f"{table.__tablename__}.{column}"



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


class Relationship[T: _BaseModel](LoggerMixin):
    """Descriptor for a single-valued relationship backed by an association table.

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

    def __init__(self, related_model: type[T] = SELF, *, optional: bool = True) -> None:
        """Initialise the descriptor.

        ``related_model`` may be the ``SELF`` sentinel (self-referential) or a
        concrete ``table=True`` model. ``optional`` is accepted for API symmetry;
        access always returns ``None`` when there is no link.
        """
        self.optional = optional
        self.related_model = related_model
        # Per-owner registry: a single inherited descriptor serves many subclasses.
        self._links: dict[type, LinkInfo[_BaseModel]] = {}

    def __set_name__(self, owner: type[_BaseModel], name: str) -> None:
        """Record the attribute name (link tables are built later, per subclass)."""
        self.name = name

    def __set__(self, instance: _BaseModel, value: T) -> None:
        """Persist ``value`` if needed and replace the owner's single link row."""
        instance.logger.debug("Setting relationship '%s' to %s", self.name, value, extra={"record": instance})
        info = self._links[type(instance)]
        if instance.id is None:
            msg = f"Owner must be persisted before setting relationship '{self.name}'."
            raise ValueError(msg)
        if value.id is None:
            value.add()
        session = type(instance).session
        session.exec(info.table.delete().where(info.owner_filter(instance)))
        session.exec(info.table.insert().values(**info.owner_values(instance), **info.target_values(value)))
        session.commit()

    def __delete__(self, instance: _BaseModel) -> None:
        """Remove the owner's link row(s)."""
        info = self._links.get(type(instance))
        if info is None:
            return
        session = type(instance).session
        session.exec(info.table.delete().where(info.owner_filter(instance)))
        session.commit()

    @overload
    def __get__(self, instance: None, owner: type[_BaseModel]) -> type[T]: ...
    @overload
    def __get__(self, instance: _BaseModel, owner: type[_BaseModel]) -> T | None: ...

    def __get__(self, instance: _BaseModel | None, owner: type[_BaseModel]) -> type[T] | T | None:
        """Class access returns the target class; instance access joins the link table."""
        if instance is None:
            return self._resolve_target(owner)
        info = self._links.get(type(instance))
        if info is None:
            return None
        # pyrefly: ignore [missing-attribute]
        session = type(instance).session
        query = select(info.target).join(info.table, info.target_join()).where(info.owner_filter(instance))
        return cast("T | None", session.exec(query).first())

    def build_link_for(self, owner: type[_BaseModel]) -> None:
        """Build (once) the association table joining ``owner`` to the target.

        Called from :class:`ModelMeta` for each concrete ``table=True`` subclass.
        Idempotent per owner and guarded against duplicate metadata registration.
        """
        if owner in self._links:
            return
        target = self._resolve_target(owner)
        # Prefixes (owner tablename / attribute name) keep the self-referential case from colliding.
        owner_pk, owner_cols = _pk_columns(owner, prefix=str(owner.__tablename__))
        target_pk, target_cols = _pk_columns(target, prefix=self.name)
        link_name = f"{owner.__tablename__}_{self.name}"
        table = owner.metadata.tables.get(link_name)
        if table is None:
            table = _create_link_table(link_name, owner, owner_cols, target, target_cols)
        self._links[owner] = LinkInfo(table, owner_pk, owner_cols, target_pk, target_cols, target)

    def _resolve_target(self, owner: type[_BaseModel]) -> type[T]:
        """Resolve ``SELF`` to the owner; otherwise return the declared target."""
        if self._is_self_referential(owner):
            return owner
        return self.related_model

    def _is_self_referential(self, owner: type[_BaseModel]) -> TypeIs[type[T]]:
        """Return True if the relationship is self-referential for the given owner."""
        return self.related_model is SELF or owner is self.related_model


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
        def __get__(self, instance: _BaseModel | None, owner: type[_BaseModel]) -> Any:
            """Typing-only signature; the runtime ``__get__`` is inherited from :class:`Relationship`."""



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
                    attr.build_link_for(cls)
