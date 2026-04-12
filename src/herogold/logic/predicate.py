"""Predicate logic for combining boolean conditions."""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable


class Predicate[**P]:
    """A predicate that evaluates to True or False."""

    __slots__ = ("args", "func", "kwargs")

    def __init__(self, func: Callable[P, bool], *args: P.args, **kwargs: P.kwargs) -> None:
        """Initialize the predicate with a callable function."""
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self) -> bool:
        """Evaluate the predicate with the given arguments."""
        return self.func(*self.args, **self.kwargs)

    def __and__(self, other: Predicate[P]) -> Predicate[P]:
        """Combine two predicates with logical AND."""

        def and_func() -> bool:
            return self.func(*self.args, **self.kwargs) and other.func(*other.args, **other.kwargs)

        return _CombinedPredicate("AND", self, other, func=and_func)

    def __or__(self, other: Predicate[P]) -> Predicate[P]:
        """Combine two predicates with logical OR."""

        def or_func() -> bool:
            return self.func(*self.args, **self.kwargs) or other.func(*other.args, **other.kwargs)

        return _CombinedPredicate("OR", self, other, func=or_func)

    def __invert__(self) -> Predicate[P]:
        """Negate the predicate with logical NOT."""

        def not_func() -> bool:
            return not self.func(*self.args, **self.kwargs)

        return _CombinedPredicate("NOT", self, func=not_func)

    def __repr__(self) -> str:
        """Return a string representation of the predicate."""
        return f"Predicate({self.func!r}, args={self.args!r}, kwargs={self.kwargs!r})"


class _CombinedPredicate[**P](Predicate[P]):
    """A predicate wrapper that combines two predicates with a logical operator.

    Used internally for AND, OR, and NOT repr.
    """

    operand: Literal["AND", "OR", "NOT"]

    def __init__(
        self,
        operand: Literal["AND", "OR", "NOT"],
        left: Predicate[P],
        right: Predicate[P] | None = None,
        *,
        func: Callable[[], bool],
    ) -> None:
        super().__init__(func)
        if right is None and operand != "NOT":
            msg = "Right predicate is required for AND/OR"
            raise ValueError(msg)
        self.operand = operand
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        """Return a string representation of the combined predicate."""
        if self.operand == "NOT":
            return f"(NOT {self.left!r})"
        return f"({self.left!r} {self.operand} {self.right!r})"


def predicate[**P](*args1: P.args, **kwargs1: P.kwargs) -> Callable[[Callable[P, bool]], Callable[P, Predicate[P]]]:
    """Decorate a method to create a Predicate instance from it.

    All arguments provided to the decorator are merged with those provided
    when the resulting factory is called.

    Example:
    ```python
        @predicate(2)
        def greater_than(x: int, y: int = 0) -> bool:
            return x > y

        p = greater_than(1)  # Creates Predicate with args (2, 1)
        assert p() is True
    ```

    """

    def wrapper(func: Callable[P, bool]) -> Callable[P, Predicate[P]]:
        @wraps(func)
        def inner(*args2: P.args, **kwargs2: P.kwargs) -> Predicate[P]:
            return Predicate(func, *args1, *args2, **kwargs1, **kwargs2)  # pyright: ignore[reportCallIssue]

        return inner

    return wrapper
