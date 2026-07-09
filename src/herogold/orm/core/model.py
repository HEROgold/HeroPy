"""Module for extending SQLModel with custom methods.

This module should make the SQLModel classes more like a `Repository` pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum, auto
from functools import partial
from types import NoneType
from typing import TYPE_CHECKING, Any, ClassVar, Unpack, override

from sqlalchemy import BigInteger, ScalarResult, func
from sqlmodel import Field, Session, col, select
from sqlmodel import SQLModel as BaseSQLModel

from herogold.log import LoggerMixin
from herogold.orm.core.utils import SELF, Relationship
from herogold.typing.check import contains_sub_type

from .constants import session as db_session
from .errors import AlreadyExistsError, NotFoundError

if TYPE_CHECKING:
    import logging
    from collections.abc import Sequence

    from pydantic import ConfigDict
    from sqlalchemy.orm import Mapped

models: set[type[_BaseModel]] = set()
def _current_utc() -> datetime:
    return datetime.now(UTC)


class ModelLogger(LoggerMixin):
    """Polymorphic logger for model, on cls level methods.

    Avoids the issue of cls.logger raising AttributeError, property has no attribute `xxx`
    """

class _BaseModel(BaseSQLModel, ABC):
    """Base model class for all models."""

    id: int | None = Field(
        default=None,
        sa_type=BigInteger,
        primary_key=True,
        unique=True,
        nullable=False,
        sa_column_kwargs={"autoincrement": True},
    )

    session: ClassVar[Session] = db_session
    logger: ClassVar[logging.Logger] = ModelLogger().logger
    __count: ClassVar[int | None] = None
    """Cached count of records. avoiding excessive queries."""

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]) -> None:
        """Register subclass in models set."""
        super().__init_subclass__(**kwargs)
        models.add(cls)

    @classmethod
    def _get_session(cls, session: Session | None = None) -> Session:
        """Get the usable session, either the provided one or the default."""
        cls.logger.debug("Getting session: %s", session, extra={"session": session})
        return session or cls.session

    @classmethod
    def count(cls) -> int:
        """Return the total count of records in the model."""
        if not cls.__count or cls.session.identity_map.check_modified():
            cls.__count = cls.session.exec(
                select(func.count(col(cls.id))),
            ).one()
        return cls.__count

    @property
    def relations(self) -> dict[str, type[_BaseModel]]:
        """Return a dict of related models and their values."""
        return {
            name: getattr(self, name)
            for name, info in self.__class__.model_fields.items()
            if info.annotation and issubclass(info.annotation, _BaseModel)
        }

    @classmethod
    def get(cls, id_: int, session: Session | None = None, *, with_for_update: bool = False) -> SELF:
        """Get a record from Database."""
        cls.logger.debug("Getting record: %s", id_, extra={"id": id_})
        session = cls._get_session(session)

        query = select(cls).where(cls.id == id_)
        if with_for_update:
            query = query.with_for_update()

        if known := session.exec(query).first():
            return known
        msg = f"Record with {cls.__name__}.id={id_} not found."
        raise NotFoundError(msg)

    @classmethod
    def get_all(cls: type[SELF], session: Session | None = None) -> Sequence[SELF]:
        """Get all records from Database."""
        cls.logger.debug("Getting all records: %s", cls.__name__, extra={"class": cls.__name__})
        session = cls._get_session(session)
        return session.exec(select(cls)).all()

    def add(self: SELF, session: Session | None = None) -> None:
        """Add a record to Database."""
        self.logger.debug("Adding record: %s", self, extra={"record": self})
        if self.id is not None:
            msg = f"Record with {self.__class__.__name__}.id={self.id} already exists."
            raise AlreadyExistsError(msg)
        self._create_record(session)

    def update(self: SELF, session: Session | None = None) -> None:
        """Create or update a record in Database.

        If the record already exists (has an id), it will be updated.
        If the record does not exist (no id), it will be created.
        """
        self.logger.debug("Record update requested: %s", self, extra={"record": self})
        session = self._get_session(session)
        if known := session.exec(
            select(self.__class__).where(self.__class__.id == self.id).with_for_update(),
        ).first():
            return self._update_record(session, known)
        return self._create_record(session)

    def delete(self, session: Session | None = None) -> None:
        """Delete a record from Database."""
        self.logger.debug("Deleting record: %s", self, extra={"record": self})
        self._delete_record(self._get_session(session))
        msg = f"Record with {self.__class__.__name__}.id={self.id} not found for deletion."
        raise NotFoundError(msg)

    @classmethod
    def from_[T](cls, column: Mapped[T], value: T, session: Session | None = None) -> ScalarResult[SELF]:
        """Get a record from Database by field and value."""
        cls.logger.debug(
            "Getting record from field: %s, %s == %s",
            cls,
            column,
            value,
            extra={"class": cls.__name__, "column": column, "value": value},
        )
        session = cls._get_session(session)
        return session.exec(select(cls).where(column == value))

    @abstractmethod
    def _update_record(self, session: Session, entry: SELF) -> None:
        """Update the record in the database with the current instance's values.

        entry contains the current record in the database, and self contains the new values.
        """
    @abstractmethod
    def _create_record(self, session: Session) -> None:
        """Create the record in the database with the current instance's values."""
    @abstractmethod
    def _delete_record(self, session: Session) -> None:
        """Delete the record in the database with the current instance's values."""

class BaseModel(_BaseModel):
    """Base model class with custom methods."""

    # ignore Relationship descriptor values so they don't have to be
    # annotated at all; the class object is available at import time, so we
    # can configure this statically rather than in __init_subclass__.
    model_config = {"ignored_types": (Relationship,)}  # ty:ignore[invalid-assignment]

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
    updated_at: datetime = Field(default_factory=__cur_utc)
    deleted_at: datetime | None = Field(default=None)
    extra = Relationship["ExtraData"](optional=True)

    @override
    @classmethod
    def count(cls) -> int:
        """Return the total count of records in the model."""
        if not cls.__count or cls.session.identity_map.check_modified():
            cls.__count = cls.session.exec(
                select(func.count(col(cls.id))).where(cls.deleted_at == None),  # noqa: E711
            ).one()
        return cls.__count

    @override
    def _create_record(self, session: Session) -> None:
        self.logger.debug("Creating record: %s", self, extra={"record": self})
        session = self._get_session(session)
        session.add(self)
        session.commit()

    @override
    def _update_record(self, session: Session, entry: SELF) -> None:
        self.logger.debug("Updating record: %s", self, extra={"record": self})
        session = self._get_session(session)
        for name, info in self.__class__.model_fields.items():
            if name == "id":
                continue
            value = getattr(self, name)
            value_type: type[Any] = type(value)
            if info.annotation is None or value_type is NoneType:
                # Filter out fields without type annotations. Filters out optional fields too.
                continue
            self.logger.debug(
                "%s: %s, %s",
                value_type,
                value_type is info.annotation,
                self,
                extra={"record": self},
            )
            if value_type is not info.annotation:
                self.logger.debug("Contains sub type: %s", contains_sub_type(info, info.annotation), extra={"record": self})
            if value_type is info.annotation or contains_sub_type(info, info.annotation):
                # Set the actual value from the instance, not from field info
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

    # ignore Relationship descriptor values so they don't have to be
    # annotated at all; the class object is available at import time, so we
    # can configure this statically rather than in __init_subclass__.
    model_config = {"ignored_types": (Relationship,)}  # ty:ignore[invalid-assignment]

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
        default_factory=datetime.now,
        primary_key=True,
    )

    action: Actions = Field()
    """Each implementation of _ACTION_record() must handle setting the action type."""
    changes: dict[str, Any] = Field(default_factory=dict, sa_column_kwargs={"type_": "JSONB"})
    extra = Relationship["ExtraData"](optional=True)

    @override
    def _create_record(self, session: Session) -> None:
        self.logger.debug("Creating record: %s", self, extra={"record": self})
        self.action = Actions.CREATE
        session.add(self)
        session.commit()

    @override
    def _update_record(self, session: Session, entry: SELF) -> None:
        self.logger.debug("Updating record: %s", self, extra={"record": self})
        self.action = Actions.UPDATE
        for name, info in self.__class__.model_fields.items():
            if name == "id":
                continue
            value = getattr(self, name)
            value_type: type[Any] = type(value)
            if info.annotation is None or value_type is NoneType:
                # Filter out fields without type annotations. Filters out optional fields too.
                continue
            self.logger.debug(
                "%s: %s, %s",
                value_type,
                value_type is info.annotation,
                self,
                extra={"record": self},
            )
            if value_type is not info.annotation:
                self.logger.debug("Contains sub type: %s", contains_sub_type(info, info.annotation), extra={"record": self})
            if value_type is info.annotation or contains_sub_type(info, info.annotation):
                # Set the actual value from the instance, not from field info
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


class ExtraData(_BaseModel):
    """Model for storing extra data in JSONB format."""

    data: dict[str, Any] = Field(default_factory=dict, sa_column_kwargs={"type_": "JSONB"})
