"""The enforce_types wrapper is supposed to enforce any args to match its annotated type.
The overhead is quite big, with simple functions, can ~double the runtime, at 100_000 iterations.

TODO: add support for things like Sequence[int | str], list[int] etc.
"""
from __future__ import annotations

import asyncio
import inspect
from asyncio import iscoroutinefunction
from typing import TYPE_CHECKING, Any, Callable, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence


def args_check[F, **P](func: Callable[P, F]) -> Literal[True]:
    """Check if all arguments are type hinted and return True, if it isn't raises TypeError.

    Args:
        func (FunctionType): The function to check

    Raises:
        TypeError: Error that gets raised when annotations are missing

    Returns:
        bool: True

    """
    spec = inspect.getfullargspec(func)
    for arg in [*spec.args, "return"]:
        if arg not in spec.annotations:
            msg = f"Missing type annotation for {arg}"
            raise TypeError(msg)
    return True


def check_annotation(arg: Any, annotation: type) -> None:
    """Check if a argument is of a given type.

    Args:
        arg: The argument to check
        annotation: The type to check for

    Raises:
        TypeError: If the type doesn't match, telling which type to expect

    """
    if annotation in [Any]:
        return
    if not inspect.isclass(annotation):
        msg = f"Expected a class but got {type(annotation)}"
        raise TypeError(msg)
    if not isinstance(arg, annotation):
        msg = f"Expected {annotation} but got {type(arg)} for argument: {arg}"
        raise TypeError(msg)


def type_check[T](args: Sequence[T] | dict[str, T], annotations: dict[str, type]) -> Literal[True]:
    """Check if arguments are of a annotated type.

    Args:
        args: The argument to check
        annotations: The type to check for

    Raises:
        TypeError: If the type doesn't match, telling which type to expect

    Returns:
        bool: True

    """
    if isinstance(args, dict):
        for arg in args:
            annotation = annotations.get(arg)
            check_annotation(arg, annotation) # type: ignore . Ignore None type, it'll raise a TypeError when and we want that.
    else:
        for arg, annotation in zip(args, annotations.values()):
            check_annotation(arg, annotation)
    return True


def enforce_types[F, **P](func: Callable[P, F]) -> Callable[P, F]:
    """Enforce type checking for a function, this makes sure that the decorated function needs type hinting,
    and forces passed arguments to be of that type.

    Uses a cache to store the results of the function, to avoid rechecking the same arguments.

    Raises:
        TypeError: If the type doesn't match, telling which type to expect, or when type hinting is not present

    Args:
        func (FunctionType): The function to check

    """
    # async_cache: dict[tuple[*tuple[Any, ...], tuple[tuple[str, Any], ...]], Any] = {}
    # cache: dict[tuple[*tuple[Any, ...], tuple[tuple[str, Any], ...]], Any] = {}

    async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
        # key = (*args, tuple(sorted(kwargs.items())))
        # if key in async_cache:
        #     return async_cache[key]

        if (
            args_check(func) and
            type_check(args, func.__annotations__) and
            type_check(kwargs, func.__annotations__)
        ):
            return await func(*args, **kwargs)
        return None
            # async_cache[key] = result # type: ignore

    def wrapper(*args: P.args, **kwargs: P.kwargs):
        # key = (*args, tuple(sorted(kwargs.items())))
        # if key in cache:
        #     return cache[key]

        if (
            args_check(func) and
            type_check(args, func.__annotations__) and
            type_check(kwargs, func.__annotations__)
        ):
            return func(*args, **kwargs)
        return None
            # cache[key] = result

    if iscoroutinefunction(func):
        return async_wrapper # type: ignore[reportReturnType]
    return wrapper # type: ignore[reportReturnType]


def test_collections() -> None:
    @enforce_types
    def collections(a: list[int]) -> bool:
        return True
    def collections_nowrap(a: list[int]) -> bool:
        return True

    time.time()
    for _ in range(100_000):
        assert collections([1, 2, 3]) is True
    time.time()

    time.time()
    for _ in range(100_000):
        assert collections_nowrap([1, 2, 3]) is True
    time.time()



def test_simple() -> None:
    @enforce_types
    def test(a: int, b: str) -> bool:
        return True

    def test_nowrap(a: Any, b: Any) -> bool:
        return True

    time.time()
    for _ in range(test_count):
        assert test(random.randint(0, 10), b=random.choice(letters)) is True
    time.time()

    time.time()
    for _ in range(test_count):
        assert test_nowrap(random.randint(0, 10), b=random.choice(letters)) is True
    time.time()



async def test_simple_async() -> None:
    @enforce_types
    async def async_test(a: int, b: str) -> bool:
        return True

    async def async_test_nowrap(a: Any, b: Any) -> bool:
        return True

    time.time()
    for _ in range(test_count):
        assert await async_test(random.randint(0, 10), b=random.choice(letters)) is True
    time.time()

    time.time()
    for _ in range(test_count):
        assert await async_test_nowrap(random.randint(0, 10), b=random.choice(letters)) is True
    time.time()

    time.time()
    for _ in range(test_count):
        assert await async_test(0, b="a") is True
    time.time()


async def async_test_collections() -> None:
    @enforce_types
    def collections(a: list[int]) -> bool:
        return True
    def collections_nowrap(a: list[int]) -> bool:
        return True

    time.time()
    for _ in range(100_000):
        assert collections([1, 2, 3]) is True
    time.time()

    time.time()
    for _ in range(100_000):
        assert collections_nowrap([1, 2, 3]) is True
    time.time()



def main() -> None:
    test_simple()
    # test_collections()


async def main_async() -> None:
    await test_simple_async()
    # await async_test_collections()


if __name__ == "__main__":
    import random
    import time

    test_count = 100_000
    letters = "abcdefghijklmnopqrstuvwxyz"

    test_simple()
    asyncio.run(main_async())
