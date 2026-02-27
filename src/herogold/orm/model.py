"""Module for extending SQLModel with custom methods.

This module should make the SQLModel classes more like a `Repository` pattern.
"""
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from functools import partial
from types import NoneType
from typing import Any, ClassVar, Self, Unpack

from pydantic import ConfigDict
from sqlalchemy import BigInteger, ScalarResult
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Session, select
from sqlmodel import SQLModel as BaseSQLModel

from herogold.log import LoggerMixin
from herogold.typing.check import contains_sub_type

from .constants import session as db_session
from .errors import AlreadyExistsError, NotFoundError

models: set[type["BaseModel"]] = set()


class ModelLogger(LoggerMixin):
    """Polymorphic logger for model, on cls level methods.

    Avoids the issue of cls.logger raising AttributeError, property has no attribute `xxx`
    """


class BaseModel(BaseSQLModel):
    """Base model class with custom methods."""

    __cur_utc = partial(datetime.now, UTC)

    id: int | None = Field(
        default=None,
        sa_type=BigInteger,
        primary_key=True,
        index=True,
        unique=True,
        nullable=False,
        sa_column_kwargs={"autoincrement": True},
    )
    created_at: datetime = Field(default_factory=__cur_utc)
    updated_at: datetime = Field(default_factory=__cur_utc)

    session: ClassVar[Session] = db_session
    logger: ClassVar[logging.Logger] = ModelLogger().logger

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]) -> None:
        """Register subclass in models set."""
        super().__init_subclass__(**kwargs)
        models.add(cls)

    def add(self: Self, session: Session | None = None) -> None:
        """Add a record to Database."""
        self.logger.debug("Adding record: %s", self, extra={"record": self})
        if self.id is not None:
            msg = f"Record with {self.__class__.__name__}.id={self.id} already exists."
            raise AlreadyExistsError(msg)
        self._create_record(session)

    def update(self: Self, session: Session | None = None) -> None:
        """Create or update a record in Database."""
        self.logger.debug("Record update requested: %s", self, extra={"record": self})
        session = self._get_session(session)
        if known := session.exec(
            select(self.__class__).where(self.__class__.id == self.id).with_for_update(),
        ).first():
            return self._update_record(known, session)
        return self._create_record(session)

    @classmethod
    def get(cls, id_: int, session: Session | None = None, *, with_for_update: bool = False) -> Self:
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
    def get_all(cls: type[Self], session: Session | None = None) -> Sequence[Self]:
        """Get all records from Database."""
        cls.logger.debug("Getting all records: %s", cls.__name__, extra={"class": cls.__name__})
        session = cls._get_session(session)
        return session.exec(select(cls)).all()

    @classmethod
    def _get_session(cls, session: Session | None = None) -> Session:
        """Get the usable session, either the provided one or the default."""
        cls.logger.debug("Getting session: %s", session, extra={"session": session})
        return session or cls.session

    def delete(self, session: Session | None = None) -> None:
        """Delete a record from Database."""
        self.logger.debug("Deleting record: %s", self, extra={"record": self})
        session = self._get_session(session)
        if known := session.exec(
            select(self.__class__).where(self.__class__.id == self.id).with_for_update(),
        ).first():
            session.delete(known)
            session.commit()
            return
        msg = f"Record with {self.__class__.__name__}.id={self.id} not found for deletion."
        raise NotFoundError(msg)

    def _create_record(self, session: Session | None = None) -> None:
        self.logger.debug("Creating record: %s", self, extra={"record": self})
        session = self._get_session(session)
        session.add(self)
        session.commit()

    def _update_record(self, known: Self, session: Session | None = None) -> None:
        """Update known, with the values from self."""
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
                setattr(known, name, value)
        known.updated_at = self.__cur_utc()
        session.add(known)
        session.commit()

    @classmethod
    def from_[T](cls, column: Mapped[T], value: T, session: Session | None = None) -> ScalarResult[Self]:
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

