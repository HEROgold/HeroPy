"""A module that provides a sentinel object which is falsy with all other objects."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable


class _Sentinel:
    __slots__ = ()

    def __init__(self) -> None:
        return

    def __eq__(self, other: object) -> bool:
        return False

    def __ne__(self, value: object, /) -> bool:
        return False

    def __bool__(self) -> bool:
        return False

    def __hash__(self) -> int:
        return 0

    def __repr__(self) -> str:
        return "MISSING"

    def __str__(self) -> str:
        return self.__repr__()

    def __setattr__(self, name: str, value: Any, /) -> None:  # noqa: ANN401
        return None

    def __delattr__(self, name: str, /) -> None:
        return None

    def __getattribute__(self, name: str, /) -> Any:  # noqa: ANN401
        return None

    def __dir__(self) -> Iterable[str]:
        return [""]

    def __init_subclass__(cls) -> None:
        return None

    @classmethod
    def __subclasshook__(cls, subclass: type, /) -> bool:
        return False


MISSING: Any = _Sentinel()

def create_sentinel() -> Any:  # noqa: ANN401
    """Create a new sentinel object which is falsy with all other objects."""
    return _Sentinel()
