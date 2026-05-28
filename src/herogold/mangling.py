"""Provides functionality for mangling and unmangling private attribute names in Python classes."""

from __future__ import annotations

import re
from typing import Any


class ManglingError(Exception):
    """Custom exception for mangling errors."""


class InvalidNameError(ManglingError):
    """Raised when an invalid name is provided for mangling."""

    def __init__(self, name: str) -> None:
        """Initialize the InvalidNameError with the invalid name."""
        super().__init__(
            f"Invalid name '{name}' for mangling. Names must be valid Python identifiers and cannot start with a digit."
        )


def mangle(cls: type, name: str) -> str:
    """Mangle a private attribute name following Python's name-mangling rules.

    :param cls: The class containing the private attribute.
    :param name: The original attribute name.
    :return: The mangled attribute name (e.g., '_ClassName__attr'), or the
        original name when it is a dunder (``__x__``) or has no ``__`` prefix.
    :raises InvalidNameError: If *name* is not a valid Python identifier or
        starts with a digit.
    """
    if not name.isidentifier() or name[0].isdigit():
        raise InvalidNameError(name)
    # A "dunder" has a non-underscore character immediately before its trailing `__`
    # (e.g. ``__init__``, ``__var__``).  Names like ``___`` do not qualify.
    if name.startswith("__") and re.search(r"[^_]__$", name):
        return name
    if name.startswith("__"):
        return f"_{cls.__name__}{name}"
    return name


def get_mangled_attribute(cls: type, owner: type, name: str) -> Any:  # noqa: ANN401
    """Get the value of a dunder attribute (``__name__``) from *owner*.

    Looks up ``__<name>__`` directly in *owner*'s own ``__dict__`` so that
    attributes defined on a specific class in a hierarchy are returned
    without MRO interference.

    :param cls: The subclass context (used only for error messages).
    :param owner: The class whose ``__dict__`` is searched.
    :param name: The bare attribute name, without surrounding underscores.
    :return: The value of ``owner.__dict__["__<name>__"]``.
    :raises InvalidNameError: If *name* is not a valid Python identifier or
        starts with a digit.
    :raises AttributeError: If the attribute does not exist in *owner*.
    """
    if not name.isidentifier() or name[0].isdigit():
        raise InvalidNameError(name)
    dunder_name = f"__{name}__"
    try:
        return vars(owner)[dunder_name]
    except KeyError as exc:
        msg = f"type object '{cls.__name__}' has no attribute '{dunder_name}'"
        raise AttributeError(msg) from exc
