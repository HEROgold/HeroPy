"""Provides functionality for mangling and unmangling private attribute names in Python classes."""
from __future__ import annotations

from typing import Any


class ManglingError(Exception):
    """Custom exception for mangling errors."""

class InvalidNameError(ManglingError):
    """Raised when an invalid name is provided for mangling."""

    def __init__(self, name: str) -> None:
        """Initialize the InvalidNameError with the invalid name."""
        super().__init__(f"Invalid name '{name}' for mangling. Names must be valid Python identifiers and cannot start with a digit.")

def mangle(cls: type, name: str) -> str:
    """Mangle a private attribute name.

    :param cls: The class containing the private attribute.
    :param name: The original attribute name.
    :return: The mangled attribute name (e.g., '__ClassName__attribute__').
    """
    mangled = f"_{cls.__name__}__{name}__"
    if not name.isidentifier() or name[0].isdigit():
        raise InvalidNameError(name)
    return mangled

def get_mangled_attribute(cls: type, owner: type, name: str) -> Any:  # noqa: ANN401
    """Get the value of a mangled private attribute.

    `cls`: The class from which to get the attribute.
    `owner`: The owner class. This is the class that owns the attribute.
    `name`: The original attribute name.
    `return`: The value found in the class `cls` with the mangled name.
    `raises`: `ManglingError` If the name is invalid or if the attribute does not exist in the class.
    """
    mangled_name = mangle(owner, name)
    return getattr(cls, mangled_name)
