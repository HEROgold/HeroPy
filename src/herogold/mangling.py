"""Provides functionality for mangling and unmangling private attribute names in Python classes."""

from __future__ import annotations

import re
from typing import Any

from herogold.errors import HerogoldError

# Matches names that are true dunders: a non-underscore char immediately before
# the trailing ``__`` (e.g. ``__init__``, ``__var__``).  Names like ``___``
# do not match and will be treated as private (mangled) names.
_DUNDER_RE = re.compile(r"^__.*[^_]__$")


class ManglingError(HerogoldError):
    """Custom exception for mangling errors."""


class InvalidNameError(ManglingError):
    """Raised when an invalid name is provided for mangling."""

    def __init__(self, name: str) -> None:
        """Initialize the InvalidNameError with the invalid name."""
        msg = f"Invalid name '{name}' for mangling. Names must be valid Python identifiers and cannot start with a digit."
        super().__init__(msg)


def mangle(cls: type, name: str) -> str:
    """Mangle a private attribute name.

    :param cls: The class containing the private attribute.
    :param name: The original attribute name.
    :return: The mangled attribute name (e.g., '__ClassName__attribute').
    """
    if _DUNDER_RE.match(name):
        # __x__ is a dunder method and is not mangled
        return name
    name = name.removeprefix("__")
    mangled = f"_{cls.__name__}__{name}"
    if not name.isidentifier() or name[0].isdigit():
        raise InvalidNameError(name)
    return mangled


def get_mangled_attribute(cls: type, owner: type, name: str) -> Any:  # noqa: ANN401
    """Get the value of a mangled private attribute.

    Owner is parent of cls or cls itself.
    `cls`: The class from which to get the attribute.
    `owner`: The owner class. This is the class that owns the attribute.
    `name`: The original attribute name.
    `return`: The value found in the class `cls` with the mangled name,
        falling back to the dunder ``__<name>__`` defined on `owner` itself.
    `raises`: `ManglingError` If the name is invalid or if the attribute does not exist in the class.
    """
    mangled_name = mangle(owner, name)
    if hasattr(cls, mangled_name):
        return getattr(cls, mangled_name)
    dunder_name = f"__{name}__"
    if dunder_name in vars(owner):
        return vars(owner)[dunder_name]
    msg = f"type object '{cls.__name__}' has no attribute '{mangled_name}'"
    raise AttributeError(msg)
