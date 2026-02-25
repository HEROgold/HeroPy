
from typing import Protocol, Self, SupportsAbs, runtime_checkable

# Protocols for comparison operations

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

# Protocols for arithmetic operations

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
class SupportsMin(Protocol):
    def __min__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsMax(Protocol):
    def __max__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsNumeric[T](
    SupportsAddition, SupportsMultiplication, SupportsComparison,
    SupportsSubtraction, SupportsAbs[T], SupportsMin, SupportsMax,
    Protocol):
    """A protocol for numeric types that support all operations."""

# Protocol for bitwise operations

@runtime_checkable
class SupportsAnd(Protocol):
    def __and__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsOr(Protocol):
    def __or__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsXor(Protocol):
    def __xor__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsLShift(Protocol):
    def __lshift__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsRShift(Protocol):
    def __rshift__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsRLShift(Protocol):
    def __rlshift__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsRRShift(Protocol):
    def __rrshift__[T](self, other: T, /) -> T: ...

@runtime_checkable
class SupportsInvert(Protocol):
    def __invert__(self) -> Self: ...

@runtime_checkable
class SupportsBitwise(
    SupportsAnd, SupportsOr, SupportsXor, SupportsLShift, SupportsRShift, SupportsInvert,
    SupportsRLShift, SupportsRRShift,
    Protocol,
):
    """A protocol for bitwise operations."""

@runtime_checkable
class SupportsBitNumeric[T](SupportsNumeric[T], SupportsBitwise, Protocol):
    """A protocol for types that support both numeric and bitwise operations."""

@runtime_checkable
class SupportsBitComparison(SupportsComparison, SupportsBitwise, Protocol):
    """A protocol for types that support both comparison and bitwise operations."""

# Protocols for container operations

@runtime_checkable
class SupportsLen(Protocol):
    def __len__(self) -> int: ...
