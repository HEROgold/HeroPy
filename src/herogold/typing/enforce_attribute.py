"""Enforce strict attribute definitions on classes."""  # noqa: INP001
from __future__ import annotations

from typing import Self


class StrictAttributesMeta(type):
    """Metaclass that requires attributes to be defined before __init__.

    Any attempt to assign a new attribute after __init__ completes will raise
    an AttributeError.
    """

    def __new__[**P](mcs, name: str, bases: tuple[type, ...], namespace: dict[str, P]) -> type:
        """Create a new class with strict attribute enforcement."""
        cls = super().__new__(mcs, name, bases, namespace)
        original_init = cls.__init__

        def new_init(self: type[Self], *args: P.args, **kwargs: P.kwargs) -> None:
            """Allow attributes during init, then lock after completion."""
            original_init(self, *args, **kwargs)
            object.__setattr__(self, "_locked", True)

        cls.__init__ = new_init  # ty: ignore[invalid-assignment] Explicit override of init

        return cls

class StrictAttributes(metaclass=StrictAttributesMeta):
    """Base class that enforces strict attribute definitions."""

    def __setattr__(self, name: str, value: object) -> None:
        """Prevent setting attributes after initialization completes."""
        if getattr(self, "_locked", False):
            msg = (
                f"Cannot add new attribute '{name}' to {self.__class__.__name__}. "
                "All attributes must be defined before __init__."
            )
            raise AttributeError(msg)
        object.__setattr__(self, name, value)

def strict_attributes(cls: type) -> type:
    """Apply strict attribute enforcement to a class.

    Wraps the class with StrictAttributesMeta and ensures it inherits from
    StrictAttributes to get the __setattr__ protection.
    """
    # Add StrictAttributes to bases if not already present
    bases = cls.__bases__
    if not issubclass(cls, StrictAttributes):
        bases = (StrictAttributes, *bases)
    return StrictAttributesMeta(cls.__name__, bases, dict(cls.__dict__))
