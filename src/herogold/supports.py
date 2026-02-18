
from typing import Protocol, SupportsAbs, runtime_checkable


@runtime_checkable
class SupportsGT(Protocol):
    def __gt__(self, other: object, /) -> bool: ...

@runtime_checkable
class SupportsLT(Protocol):
    def __lt__(self, other: object, /) -> bool: ...

@runtime_checkable
class SupportsGE(Protocol):
    def __ge__(self, other: object, /) -> bool: ...

@runtime_checkable
class SupportsLE(Protocol):
    def __le__(self, other: object, /) -> bool: ...

@runtime_checkable
class SupportsEq(Protocol):  # noqa: PLW1641
    def __eq__(self, other: object, /) -> bool: ...

@runtime_checkable
class SupportsNe(Protocol):
    def __ne__(self, other: object, /) -> bool: ...

@runtime_checkable
class SupportsComparison(Protocol):  # noqa: PLW1641
    """A protocol for rich comparison methods."""

    def __gt__(self, other: object, /) -> bool: ...
    def __lt__(self, other: object, /) -> bool: ...
    def __ge__(self, other: object, /) -> bool: ...
    def __le__(self, other: object, /) -> bool: ...
    def __eq__(self, other: object, /) -> bool: ...
    def __ne__(self, other: object, /) -> bool: ...

@runtime_checkable
class SupportsAddition(Protocol):
    def __add__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsMultiplication(Protocol):
    def __mul__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsSubtraction(Protocol):
    def __sub__[T](self, other: T, /) -> T: ...


@runtime_checkable
class SupportsNumericComparison(SupportsAddition, SupportsMultiplication, SupportsComparison, SupportsSubtraction, SupportsAbs, Protocol):
    """A protocol for numeric types that support comparison and subtraction."""
