"""Module for extending SQLModel with custom methods.

This module should make the SQLModel classes more like a `Repository` pattern.
"""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime
from enum import Enum, auto
from functools import partial
from typing import TYPE_CHECKING, Any, Self, override

from sqlalchemy import JSON, BigInteger, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declared_attr
from sqlalchemy.schema import Index
from sqlmodel import Field, Session, col, select

from herogold.orm.core.base_model import _BaseModel
from herogold.orm.core.binding import OwnedSession  # noqa: TC001  # inject resolves annotations at runtime
from herogold.orm.core.custom_data import CustomData
from herogold.orm.core.utils import Relationship
from herogold.typing.classproperty import classproperty
from herogold.typing.inject import inject

from .errors import AlreadyExistsError, NotFoundError

if TYPE_CHECKING:

    from sqlmodel.sql.expression import SelectOfScalar


def _current_utc() -> datetime:
    return datetime.now(UTC)



# Attach the shared ``custom_data`` relationship to the base now that its target
# (CustomData) exists. Placed here rather than in the _BaseModel body because it
# points at a subclass; CustomData was built above, so it never gains its own
# ``custom_data`` link table (it stays a leaf).
_custom_data = Relationship(CustomData)
_custom_data.__set_name__(_BaseModel, "custom_data")
_BaseModel.custom_data = _custom_data


class BaseModel(_BaseModel):
    """Base model class with custom methods."""

    # ignore Relationship descriptor values so they don't have to be annotated.
    model_config = {"ignored_types": (Relationship,)}  # ty:ignore[invalid-assignment]  # noqa: RUF012

    id: int | None = Field(
        default=None,
        sa_type=BigInteger,
        primary_key=True,
        index=True,
        unique=True,
        nullable=False,
        sa_column_kwargs={"autoincrement": True},
    )

    __cur_utc = partial(datetime.now, UTC)

    created_at: datetime = Field(default_factory=__cur_utc)
    updated_at: datetime = Field(default_factory=__cur_utc, sa_column_kwargs={"onupdate": __cur_utc})
    deleted_at: datetime | None = Field(default=None)

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple[Index, ...]:
        """Specify partial indexes for deleted_at to optimize queries for alive records."""
        return (
            Index(
                f"idx_{cls.__tablename__}_alive_only",
                "id",
                postgresql_where=cls.deleted_at == None,  # noqa: E711
                mssql_where=cls.deleted_at == None,  # noqa: E711
                sqlite_where=cls.deleted_at == None,  # noqa: E711
                # MySQL automatically ignores these and falls back to a normal index on "id"
            ),
        )

    @classproperty
    def query(cls: type[Self]) -> SelectOfScalar[Self]:  # noqa: N805  # ty: ignore[invalid-type-form]
        """Return a default query for the model."""
        return super().query.where(cls.deleted_at == None)  # noqa: E711

    @override
    @classmethod
    @inject
    def count(cls, session: OwnedSession = None) -> int:
        """Return the total count of records in the model."""
        return session.exec(
            select(func.count(col(cls.id))).where(cls.deleted_at == None),  # noqa: E711
        ).one()

    @override
    def _create_record(self, session: Session) -> None:
        self.logger.debug("Creating record: %s", self, extra={"record": self})
        session.add(self)
        session.commit()

    @override
    def _update_record(self, session: Session, entry: Self) -> None:
        self.logger.debug("Updating record: %s", self, extra={"record": self})
        for name, value in self._assignable_fields():
            setattr(entry, name, value)
        entry.updated_at = _current_utc()
        session.add(entry)
        session.commit()

    @override
    def _delete_record(self, session: Session) -> None:
        if known := session.exec(
            select(self.__class__)
            .where(self.__class__.id == self.id)
            .with_for_update(),
        ).first():
            known.deleted_at = _current_utc()
            session.commit()
            return

class Actions(Enum):
    """Enum for actions performed on a record."""

    CREATE = auto()
    UPDATE = auto()
    DELETE = auto()
    QUERY = auto()

class DataModel(_BaseModel):
    """Base model for models that require a history of changes."""

    # ignore Relationship descriptor values so they don't have to be annotated.
    model_config = {"ignored_types": (Relationship,)}  # ty:ignore[invalid-assignment]  # noqa: RUF012

    # Composite primary key of id and timestamp
    # Allows for multiple records with the same id but different timestamps, enabling a history of changes.
    id: int | None = Field(
        default=None,
        sa_type=BigInteger,
        primary_key=True,
        nullable=False,
        sa_column_kwargs={"autoincrement": True},
    )
    timestamp: datetime = Field(
        default_factory=partial(datetime.now, UTC),
        primary_key=True,
    )

    action: Actions = Field()
    """Each implementation of _ACTION_record() must handle setting the action type."""
    # JSONB on PostgreSQL, plain JSON elsewhere (e.g. the sqlite test engine).
    # Uses ``sa_type`` (not ``sa_column``): a bare ``Column`` instance is shared
    # by every subclass's class-attribute FieldInfo, and SQLAlchemy refuses to
    # attach the same Column object to more than one Table. ``sa_type`` instead
    # gets a fresh Column built per subclass, while the TypeEngine instance
    # itself is safe to share.
    changes: dict[str, Any] = Field(
        default_factory=dict,
        sa_type=JSON().with_variant(JSONB(), "postgresql"),
    )

    @override
    def _validate_existing_record(self, session: Session) -> None:
        """Check if a record with the same id and timestamp already exists."""
        with contextlib.suppress(NotFoundError):
            if self.id and self.get(self.id, session=session):
                msg = f"Record with {self.__class__.__name__}.id={self.id} already exists."
                raise AlreadyExistsError(msg)

    @override
    def _create_record(self, session: Session) -> None:
        self.logger.debug("Creating record: %s", self, extra={"record": self})
        self.action = Actions.CREATE
        session.add(self)
        session.commit()

    @override
    def _update_record(self, session: Session, entry: Self) -> None:
        self.logger.debug("Updating record: %s", self, extra={"record": self})
        self.action = Actions.UPDATE
        for name, value in self._assignable_fields():
            setattr(entry, name, value)
        session.add(self)
        session.commit()

    @override
    def _delete_record(self, session: Session) -> None:
        self.action = Actions.DELETE
        if _entry := session.exec(
            select(self.__class__)
            .where(self.__class__.id == self.id),
        ).first():
            self.action = Actions.DELETE
            session.add(self)
            session.commit()
            return
