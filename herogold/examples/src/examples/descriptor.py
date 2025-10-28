from __future__ import annotations

from typing import cast


class Descriptor[VT]:
    """A descriptor for config values, preserving type information."""

    def __init__(self, default: VT | None = None) -> None:
        """Initialize the descriptor with a default value."""
        self._default = default

    def __set_name__(self, owner: type, name: str) -> None:
        """Set the name of the attribute to the name of the descriptor."""
        self.name = name
        self.private = f"_{self.name}"

    def __get__(self, obj: object, obj_type: object) -> VT:
        """Get the value of the attribute."""
        return cast("VT", getattr(obj, self.private, self._default))

    def __set__(self, obj: object, value: VT) -> None:
        """Set the value of the attribute."""
        setattr(obj, self.private, value)
