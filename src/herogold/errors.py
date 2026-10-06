"""Module for enhancing python's error handling capabilities.

Decorators with_exception(), with_group()
to wrap functions and handle exceptions in a more structured way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, overload

from herogold.asynchronous import dual_wraps

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable


def call_returning_exception[**P, T](func: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T | Exception:
    """Call func and return any exception it raises, instead of letting it propagate."""
    try:
        return func(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        return e


async def a_call_returning_exception[**P, T](
    func: Callable[P, Awaitable[T]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T | Exception:
    """Await func and return any exception it raises, instead of letting it propagate."""
    try:
        return await func(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        return e


@overload
def with_exception[**P, T](func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T | Exception]]: ...
@overload
def with_exception[**P, T](func: Callable[P, T]) -> Callable[P, T | Exception]: ...
def with_exception[**P, T](func: Callable[P, T]) -> Callable[P, T | Exception]:
    """Wrap a function and returns any thrown exception.

    Supports both sync and async functions.
    """

    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T | Exception:
        return call_returning_exception(func, *args, **kwargs)

    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T | Exception:
        a_func = cast("Callable[P, Awaitable[T]]", func)
        return await a_call_returning_exception(a_func, *args, **kwargs)

    return dual_wraps(func, sync_wrapper, async_wrapper)


def with_known_exception[**P, F, E: Exception](*exceptions: type[E]) -> Callable[[Callable[P, F | E]], Callable[P, F | E]]:
    """Wrap a function and returns any thrown exception if it's any instance of the provided exception types.

    Supports both sync and async functions.
    """
    exception_types = tuple(exceptions)

    def classify[T](result: T | Exception) -> T | E:
        if isinstance(result, exception_types):
            return result
        if isinstance(result, Exception):
            raise result
        return result

    @overload
    def with_exception[T](func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T | E]]: ...
    @overload
    def with_exception[T](func: Callable[P, T]) -> Callable[P, T | E]: ...
    def with_exception[T](func: Callable[P, T]) -> Callable[P, T | E]:
        """Wrap a function and returns any thrown exception."""

        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T | E:
            return classify(call_returning_exception(func, *args, **kwargs))

        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T | E:
            a_func = cast("Callable[P, Awaitable[T]]", func)
            return classify(await a_call_returning_exception(a_func, *args, **kwargs))

        return dual_wraps(func, sync_wrapper, async_wrapper)

    return with_exception


def with_group[**P, T](func: Callable[P, Iterable[T | Exception]]) -> Callable[P, Iterable[T] | ExceptionGroup]:
    """Collect exceptions from an iterable of results and raise them as an ExceptionGroup."""

    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Iterable[T] | ExceptionGroup:
        results: Iterable[T | Exception] = func(*args, **kwargs)
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
