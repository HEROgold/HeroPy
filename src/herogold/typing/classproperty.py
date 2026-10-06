"""Class-level property descriptor."""  # noqa: INP001

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class classproperty[O, R]:  # noqa: N801
    """Like `property`, but resolved on the class rather than an instance.

    Stacking `@property` on top of `@classmethod` does not produce a working
    class-level property, so a dedicated descriptor is needed. This also
    supports `super().attr` lookups from subclass getters.
    """

    def __init__(self, fget: Callable[[type[O]], R]) -> None:
        """Store the getter, called with the owner class."""
        self.fget = fget

    def __get__(self, obj: O | None, owner: type[O]) -> R:
        """Call the getter with the owner class (always passed by the descriptor protocol)."""
        return self.fget(owner)
