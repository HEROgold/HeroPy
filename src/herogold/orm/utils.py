"""Module with helper methods for the database package."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple, TypeVar, overload

from sqlalchemy import Column, ForeignKey, Index, Table, UniqueConstraint, and_
from sqlmodel import SQLModel, select

from herogold.log import LoggerMixin
from herogold.sentinel import create_sentinel

if TYPE_CHECKING:
    # Imported for typing only: ``_BaseModel`` appears solely in (stringized)
    # annotations and the lazily-evaluated PEP 695 bound ``Relationship[T: _BaseModel]``.
    # Importing it at runtime creates a circular import (model -> utils -> model).
    from herogold.orm.model import _BaseModel

SELF = create_sentinel()
"""Sentinel value for self-referential relationships in SQLModel classes."""


T = TypeVar("T", bound=SQLModel)


def get_foreign_key[M: SQLModel](table: type[M], column: str = "id") -> str:
    """Return ``<table>.<column>`` for the given model class.

    The generic parameter allows callers such as ``Relationship[T]`` to pass
    ``type[T]`` without a typing error.
    """
    return f"{table.__tablename__}.{column}"


class LinkInfo(NamedTuple):
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
    target: type[SQLModel]


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
        self._links: dict[type, LinkInfo] = {}

    def __set_name__(self, owner: type[T], name: str) -> None:
        """Record the attribute name (link tables are built later, per subclass)."""
        self.name = name

    def _resolve_target(self, owner: type) -> type[SQLModel]:
        """Resolve ``SELF`` to the owner; otherwise return the declared target."""
        return owner if self.related_model is SELF else self.related_model

    def build_link_for(self, owner: type[SQLModel]) -> None:
        """Build (once) the association table joining ``owner`` to the target.

        Called from :class:`ModelMeta` for each concrete ``table=True`` subclass.
        Idempotent per owner and guarded against duplicate metadata registration.
        """
        if owner in self._links:
            return
        target = self._resolve_target(owner)
        link_name = f"{owner.__tablename__}_{self.name}"
        metadata = owner.metadata

        owner_pk = [c.name for c in owner.__table__.primary_key.columns]
        target_pk = [c.name for c in target.__table__.primary_key.columns]
        # Column names are prefixed by the owner tablename / the attribute name so
        # the self-referential case (owner is target) does not collide.
        owner_cols = [f"{owner.__tablename__}_{pk}" for pk in owner_pk]
        target_cols = [f"{self.name}_{pk}" for pk in target_pk]

        if link_name in metadata.tables:
            table = metadata.tables[link_name]
        else:
            columns = [
                Column(col, pk_col.type, ForeignKey(f"{owner.__tablename__}.{pk}"), primary_key=True)
                for col, pk, pk_col in zip(owner_cols, owner_pk, owner.__table__.primary_key.columns, strict=True)
            ]
            columns += [
                Column(col, pk_col.type, ForeignKey(f"{target.__tablename__}.{pk}"), primary_key=True)
                for col, pk, pk_col in zip(target_cols, target_pk, target.__table__.primary_key.columns, strict=True)
            ]
            table = Table(
                link_name,
                metadata,
                *columns,
                # single-valued: at most one link per owner row
                UniqueConstraint(*owner_cols, name=f"uq_{link_name}"),
                # secondary index for reverse (target -> owners) lookups
                Index(f"ix_{link_name}_tgt", *target_cols),
            )

        self._links[owner] = LinkInfo(table, owner_pk, owner_cols, target_pk, target_cols, target)

    @overload
    def __get__(self, instance: None, owner: type[T]) -> type[T]: ...
    @overload
    def __get__(self, instance: T, owner: type[T]) -> T | None: ...
    def __get__(self, instance: T | None, owner: type[T]) -> type[T] | T | None:
        """Class access returns the target class; instance access joins the link table."""
        if instance is None:
            return self._resolve_target(owner)
        info = self._links.get(type(instance))
        if info is None:
            return None
        session = type(instance).session
        join_cond = and_(*(
            info.table.c[tc] == info.target.__table__.c[tp]
            for tc, tp in zip(info.target_cols, info.target_pk, strict=True)
        ))
        where_cond = and_(*(
            info.table.c[oc] == getattr(instance, op)
            for oc, op in zip(info.owner_cols, info.owner_pk, strict=True)
        ))
        return session.exec(select(info.target).join(info.table, join_cond).where(where_cond)).first()

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
        owner_vals = {oc: getattr(instance, op) for oc, op in zip(info.owner_cols, info.owner_pk, strict=True)}
        target_vals = {tc: getattr(value, tp) for tc, tp in zip(info.target_cols, info.target_pk, strict=True)}
        session.execute(
            info.table.delete().where(and_(*(info.table.c[oc] == v for oc, v in owner_vals.items()))),
        )
        session.execute(info.table.insert().values(**owner_vals, **target_vals))
        session.commit()

    def __delete__(self, instance: _BaseModel) -> None:
        """Remove the owner's link row(s)."""
        info = self._links.get(type(instance))
        if info is None:
            return
        session = type(instance).session
        owner_vals = {oc: getattr(instance, op) for oc, op in zip(info.owner_cols, info.owner_pk, strict=True)}
        session.execute(
            info.table.delete().where(and_(*(info.table.c[oc] == v for oc, v in owner_vals.items()))),
        )
        session.commit()


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
        for klass in cls.__mro__:
            for attr_name, attr in vars(klass).items():
                if attr_name in seen:
                    continue
                seen.add(attr_name)
                if isinstance(attr, Relationship):
                    attr.build_link_for(cls)
