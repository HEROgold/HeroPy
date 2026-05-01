"""Custom data descriptor for storing semi-persistent data in models."""
from __future__ import annotations

from collections.abc import Mapping
from sys import getsizeof

from herogold.errors import with_known_exception
from herogold.orm.model import BaseModel
from herogold.protocols import DataDescriptor


class OutOfSpaceError(ValueError):
    """Raised when the custom data exceeds the size limit."""

    def __init__(self, size: int, limit: int) -> None:
        """Initialize the OutOfSpaceError with the size and limit."""
        super().__init__(f"Custom data of size {size} exceeds limit of {limit} bytes.")

# TODO: Currently the owner of type BaseModel has not effect on typing
# meaning this descriptor is still able to be used on any other class/owner :(
class CustomData[Key, Value](DataDescriptor[Mapping[Key, Value], BaseModel]):
    """Enables custom data to be stored in the model, without being a field.

    Useful for storing related models or other data that should not be persisted.
    """

    def __init__(self, *, size_limit: int = 1024*10) -> None:
        """Initialize the CustomData with an empty dictionary."""
        self._data: Mapping[Key, Value] = {}
        self.size_limit = size_limit

    @with_known_exception(AttributeError)
    def __get__(self, instance: BaseModel, owner: type[BaseModel]) -> Mapping[Key, Value]:
        """Return the value of the custom data for the instance."""
        return self._data

    def __set__(self, instance: BaseModel, value: Mapping[Key, Value]) -> None:
        """Update the custom data.

        This will persisting existing data
        Add or overwrite data
        """
        data: Mapping[Key, Value] = self._data.copy()
        for k, v in value.items():
            data[k] = v
        self._data = data

    def _validate_size(self) -> None:
        """Validate that the size of the custom data does not exceed the limit."""
        if self.size > self.size_limit:
            raise OutOfSpaceError(self.size, self.size_limit)

    @property
    def size(self) -> int:
        """Return the number of items in the custom data."""
        return getsizeof(self._data)
