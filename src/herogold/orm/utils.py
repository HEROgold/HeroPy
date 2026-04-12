"""Module with helper methods for the database package."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, Generic, Optional, TypeVar, overload  # noqa: F401

from sqlmodel import SQLModel

from herogold.sentinel import create_sentinel

SELF = create_sentinel()
"""Sentinel value for self-referential relationships in SQLModel classes."""


T = TypeVar("T", bound=SQLModel)


def get_foreign_key[M: SQLModel](table: type[M], column: str = "id") -> str:
    """Return ``<table>.<column>`` for the given model class.

    The generic parameter allows callers such as ``Relationship[T]`` to pass
    ``type[T]`` without a typing error.
    """
    return f"{table.__tablename__}.{column}"


class Relationship[T: SQLModel]:
    """Descriptor for defining a foreign-key relationship.

    ``T`` is the related model type.  ``SELF`` may be given at declaration
    time; in ``__set_name__`` it will be replaced by the actual owner class.
    """

    if TYPE_CHECKING:  # static-only overloads
        @overload
        def __init__(self, related_model: type[T], *, optional: bool = False) -> None: ...
        @overload
        def __init__(self, related_model: Any, *, optional: bool = False) -> None: ...  # noqa: ANN401

        @overload
        def __get__(self, instance: None, owner: type[T]) -> type[T]: ...
        @overload
        def __get__(self, instance: T, owner: type[T]) -> T | None: ...

    def __init__(self, related_model: type[T] | Any = SELF, *, optional: bool = False) -> None:  # noqa: ANN401
        """Initialise the descriptor.

        ``related_model`` may be the special ``SELF`` sentinel or a concrete
        subclass of ``SQLModel``.  ``optional`` indicates whether accessing the
        attribute on an instance may return ``None``.
        """
        self.optional = optional
        # sentinel preserved until set_name
        self.related_model = related_model

    def __set_name__(self, owner: type[T], name: str) -> None:
        """Invoke callback when the descriptor is assigned to a class.

        Binds ``owner`` and ``name`` and resolves a ``SELF`` placeholder if
        present.  Also injects a suitable ``ClassVar`` annotation onto *owner*
        so that pydantic/sqlmodel treats the attribute as a non-field.
        """
        self.owner = owner
        self.name = name
        if self.related_model is SELF:
            # bind sentinel to actual owner class
            self.related_model = owner

        # ---- new behaviour ----
        # automatically add an annotation for the descriptor so that
        # libraries like pydantic/sqlmodel see the correct type without the
        # user having to write ``other: Other`` manually.  we wrap in
        # ClassVar because these are essentially class-level descriptors;
        # the ``optional`` flag is honoured by turning the annotation into a
        # ``Optional``.
        try:
            annotations = owner.__annotations__
        except AttributeError:
            annotations = {}
            owner.__annotations__ = annotations

        if name not in annotations:
            if self.optional:
                annotations[name] = ClassVar[self.related_model | None]
            else:
                annotations[name] = ClassVar[self.related_model]

    def __get__(self, instance: T | None, owner: type[T]) -> type[T] | T | None:
        """Retrieve the class or the related object from an instance.

        If ``instance`` is ``None`` the descriptor is being accessed on the
        class, in which case the related *class* itself is returned.  Otherwise
        the ``{name}_id`` attribute (or object) is looked up on ``instance``.
        """
        if instance is None:
            return self.related_model
        fk_attr = f"{self.name}_id"

        # missing attribute
        if not hasattr(instance, fk_attr):
            if self.optional:
                return None
            msg = f"Relationship '{self.name}' not set on instance"
            raise AttributeError(msg)

        val = getattr(instance, fk_attr)
        if val is None:
            if self.optional:
                return None
            msg = f"Related instance for '{self.name}' is required but None"
            raise AttributeError(msg)

        # if the stored value is already an instance, return it
        if isinstance(val, self.related_model):
            return val

        # otherwise interpret it as a primary key and fetch
        return self.related_model.get(val)  # type: ignore[return-value]

    def __set__(self, instance: T, value: object) -> None:
        """Disallow assignment to the descriptor on instances."""
        msg = f"Cannot set relationship '{self.name}' on instances."
        raise AttributeError(msg)

    def _get_required(self, instance: T, foreign_key: str) -> T:
        """Return related object, raising if the foreign key is absent."""
        if related := self._get_optional(instance, foreign_key):
            return related
        msg = f"Related instance for relationship '{self.name}' not found."
        raise AttributeError(msg)

    def _get_optional(self, instance: T, foreign_key: str) -> T | None:
        """Return value stored in ``foreign_key`` attribute (may be ``None``)."""
        return getattr(instance, foreign_key)

