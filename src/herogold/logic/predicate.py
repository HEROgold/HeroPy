"""Predicate logic for combining boolean conditions."""
from collections.abc import Callable
from functools import wraps
from typing import Generic, ParamSpec

P = ParamSpec("P")


class Predicate(Generic[P]):
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

    def __and__(self, other: "Predicate") -> "Predicate":
        """Combine two predicates with logical AND."""
        return Predicate(lambda: self() and other())

    def __or__(self, other: "Predicate") -> "Predicate":
        """Combine two predicates with logical OR."""
        return Predicate(lambda: self() or other())

    def __invert__(self) -> "Predicate[P]":
        """Negate the predicate with logical NOT."""
        return Predicate(lambda: not self())

    def __repr__(self) -> str:
        """Return a string representation of the predicate."""
        return f"Predicate({self.func!r}, args={self.args!r}, kwargs={self.kwargs!r})"

def predicate(*args1: P.args, **kwargs1: P.kwargs) -> Callable[[Callable[P, bool]], Callable[P, Predicate[P]]]:
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
            return Predicate(func, *args1, *args2, **{**kwargs1, **kwargs2})
        return inner
    return wrapper
