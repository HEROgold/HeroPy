"""Custom data descriptor for storing semi-persistent data in models."""
from __future__ import annotations

from collections.abc import Mapping
from sys import getsizeof
from typing import override

from herogold.errors import with_known_exception
from herogold.orm.model import _BaseModel
from herogold.protocols import DataDescriptor


class OutOfSpaceError(ValueError):
    """Raised when the custom data exceeds the size limit."""

    def __init__(self, size: int, limit: int) -> None:
        """Initialize the OutOfSpaceError with the size and limit."""
        super().__init__(f"Custom data of size {size} exceeds limit of {limit} bytes.")

# TODO: Currently the owner of type BaseModel has not effect on typing  # noqa: TD002, TD003
# meaning this descriptor is still able to be used on any other class/owner :(
class CustomData[Key, Value](DataDescriptor[Mapping[Key, Value], _BaseModel]):
    """Enables custom data to be stored in the model, without being a field.

    Useful for storing related models or other data that should not be persisted.
    """

    def __init__(self, *, size_limit: int = 1024*10) -> None:
        """Initialize the CustomData with an empty dictionary."""
        self._data: dict[Key, Value] = {}
        self.size_limit = size_limit

    @with_known_exception(AttributeError)
    def __get__(self, instance: _BaseModel, owner: type[_BaseModel]) -> Mapping[Key, Value]:
        """Return the value of the custom data for the instance."""
        return self._data

    @override
    def __set__(self, instance: _BaseModel, value: Mapping[Key, Value]) -> None:
        """Update the custom data.

        This will persisting existing data
        Add or overwrite data
        """
        self._data.update(value.items())

    @staticmethod
    @with_known_exception(OutOfSpaceError)
    def validate_size(item: Mapping[Key, Value], size_limit: int) -> None:
        """Validate that the size of the custom data does not exceed the limit."""
        if getsizeof(item) > size_limit:
            raise OutOfSpaceError(getsizeof(item), size_limit)
