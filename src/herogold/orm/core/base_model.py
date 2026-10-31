"""Base model class for all models."""
from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Self, Unpack, override

from sqlalchemy import BigInteger, ScalarResult, func
from sqlmodel import Field, Session, Table, col, select
from sqlmodel import SQLModel as BaseSQLModel

from herogold.log import LoggerMixin
from herogold.orm.core.utils import ModelMeta, Relationship
from herogold.typing.check import contains_sub_type
from herogold.typing.classproperty import classproperty

from .constants import session as db_session
from .errors import AlreadyExistsError, NotFoundError

if TYPE_CHECKING:
    import logging
    from collections.abc import Iterator, Sequence

    from pydantic import ConfigDict
    from sqlalchemy.orm import Mapped
    from sqlmodel.sql.expression import SelectOfScalar

    from herogold.orm.core.custom_data import CustomData


models: set[type[_BaseModel]] = set()

class ModelLogger(LoggerMixin):
    """Polymorphic logger for model, on cls level methods.

    Avoids the issue of cls.logger raising AttributeError, property has no attribute `xxx`
    """

class _BaseModel(BaseSQLModel, ABC, metaclass=ModelMeta):
    """Base model class for all models."""

    # ignore the Relationship descriptors so pydantic/sqlmodel treat them as
    # non-fields (they carry no column annotation).
    model_config = {"ignored_types": (Relationship,)}  # ty:ignore[invalid-assignment]

    id: int | None = Field(
        default=None,
        sa_type=BigInteger,
        primary_key=True,
        unique=True,
        nullable=False,
        sa_column_kwargs={"autoincrement": True},
    )

    if TYPE_CHECKING:
        # pyrefly: ignore [bad-assignment, bad-dataclass-descriptor]
        custom_data: Relationship[CustomData] = None  # ty: ignore[invalid-assignment]
        # ``custom_data`` (a Relationship to the CustomData table) is attached below,
        # after CustomData is defined, because it targets a subclass of this class.
        __table__: ClassVar[Table]
        # __table__ is a normally hidden attribute.
        # For type completeness, we're adding it here.

    query: ClassVar[SelectOfScalar[Self]]
    """Default query for the model, may be overridden by subclasses."""
    session: ClassVar[Session] = db_session
    logger: ClassVar[logging.Logger] = ModelLogger().logger
    __count: ClassVar[int | None] = None
    """Cached count of records. avoiding excessive queries."""

    def __init_subclass__(cls, **kwargs: Unpack[ConfigDict]) -> None:
        """Register subclass in models set."""
        super().__init_subclass__(**kwargs)
        models.add(cls)

    @override
    def __setattr__(self, name: str, value: Any) -> None:
        """Route ``Relationship``-backed attributes to the descriptor's ``__set__``.

        Pydantic's own ``__setattr__`` only special-cases ``property``/``cached_property``
        for non-field attributes; any other descriptor (like ``Relationship``) is rejected
        as an unknown field, so it has to be handled here before delegating.
        """
        descriptor = inspect.getattr_static(type(self), name, None)
        if isinstance(descriptor, Relationship):
            descriptor.__set__(self, value)
            return
        super().__setattr__(name, value)

    @property
    def relations(self) -> dict[str, type[_BaseModel]]:
        """Return a dict of related models and their values."""
        return {
            name: getattr(self, name)
            for name, info in self.__class__.model_fields.items()
            if isinstance(info.annotation, type) and issubclass(info.annotation, _BaseModel)
        }

    def add(self, session: Session | None = None) -> None:
        """Add a record to Database."""
        self.logger.debug("Adding record: %s", self, extra={"record": self})
        self._validate_existing_record()
        self._create_record(self._get_session(session))

    def update(self, session: Session | None = None) -> None:
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
        if self.id is None:
            msg = f"Record with {self.__class__.__name__}.id={self.id} not found for deletion."
            raise NotFoundError(msg)
        self._delete_record(self._get_session(session))

    @classproperty
    def query(cls: type[Self]) -> SelectOfScalar[Self]:  # noqa: N805  # ty: ignore[invalid-type-form]
        """Return a default query for the model."""
        return select(cls)

    @classmethod
    def count(cls) -> int:
        """Return the total count of records in the model."""
        if not cls.__count or cls.session.identity_map.check_modified():
            cls.__count = cls.session.exec(
                select(func.count(col(cls.id))),
            ).one()
        return cls.__count

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
    def get_all(cls, session: Session | None = None) -> Sequence[Self]:
        """Get all records from Database."""
        cls.logger.debug("Getting all records: %s", cls.__name__, extra={"class": cls.__name__})
        session = cls._get_session(session)
        return session.exec(select(cls)).all()

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

    def _validate_existing_record(self) -> None:
        """Check if a record of this item already exists."""
        if self.id is not None:
            msg = f"Record with {self.__class__.__name__}.id={self.id} already exists."
            raise AlreadyExistsError(msg)

    def _assignable_fields(self) -> Iterator[tuple[str, Any]]:
        """Yield ``(name, value)`` for every field whose value may be copied onto the stored record.

        Skips ``id``, fields without an annotation, and ``None`` values (so unset
        optional fields never overwrite stored data).
        """
        for name, info in type(self).model_fields.items():
            if name == "id":
                continue
            value = getattr(self, name)
            if info.annotation is None or value is None:
                continue
            if type(value) is info.annotation or contains_sub_type(info, info.annotation):
                yield name, value

    @abstractmethod
    def _update_record(self, session: Session, entry: Self) -> None:
        """Update the record in the database with the current instance's values.

        entry contains the current record in the database, and self contains the new values.
        """
    @abstractmethod
    def _create_record(self, session: Session) -> None:
        """Create the record in the database with the current instance's values."""
    @abstractmethod
    def _delete_record(self, session: Session) -> None:
        """Delete the record in the database with the current instance's values."""

    @classmethod
    def _get_session(cls, session: Session | None = None) -> Session:
        """Get the usable session, either the provided one or the default."""
        cls.logger.debug("Getting session: %s", session, extra={"session": session})
        return session or cls.session
