"""Module for enhancing python's error handling capabilities.

Decorators with_exception(), with_group()
to wrap functions and handle exceptions in a more structured way.
"""

from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable


def with_exception[**P, T](func: Callable[P, T]) -> Callable[P, T | Exception]:
    """Wrap a function and returns any thrown exception."""
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T | Exception:
        try:
            return func(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            return e

    return wrapper


def with_group[**P, T](func: Callable[P, Iterable[T | Exception]]) -> Callable[P, Iterable[T] | ExceptionGroup]:
    """Collect exceptions from an iterable of results and raise them as an ExceptionGroup."""
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Iterable[T] | ExceptionGroup:
        results = func(*args, **kwargs)
        exceptions: list[Exception] = []
        values: list[T] = []

        for i in results:
            if isinstance(i, Exception):
                exceptions.append(i)
            else:
                values.append(i)

        if exceptions:
            msg = "Multiple exceptions occurred"
            return ExceptionGroup(msg, exceptions)

        return values

    return wrapper


if __name__ == "__main__":

    @with_exception
    def test(i: int) -> float:  # noqa: D103
        return 10 / i

    @with_group
    def test_group() -> Generator[float | Exception]:  # noqa: D103
        return (test(i) for i in range(-2, 3))

    def test_generator() -> Generator[float | Exception]:  # noqa: D103
        return (test(i) for i in range(-2, 3))

    r1 = test(0)
    r2 = test_group()
    r3 = test_generator()

    print(r1)  # noqa: T201
    print(r2)  # noqa: T201
    print(list(r3))  # noqa: T201
