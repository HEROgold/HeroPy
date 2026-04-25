"""Provides helpers for running different loops."""

from __future__ import annotations

from herogold.asynchronous import get_async_loop

__lazy_modules__: list[str] = ["asyncio"]

import asyncio
import os
from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator, Callable, Iterable, Iterator

cpu_count = os.cpu_count() or 1


def _square(value: int) -> int:
    return value * value


def parallel[T, **P](action: Callable[P, T], data: Iterable[T]) -> Iterator[T]:
    """Run a function in parallel across multiple CPU cores."""
    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        yield from executor.map(action, data, chunksize=10)


async def a_parallel[T, **P](action: Callable[P, T], data: AsyncIterable[T]) -> AsyncIterator[T]:
    """Run a function in parallel across multiple CPU cores from async code."""
    loop = get_async_loop()

    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        async for item in data:
            yield await loop.run_in_executor(executor, action, item)

async def _async_range(count: int):
    for value in range(count):
        yield value


async def _run_async_parallel_test() -> None:
    result = [value async for value in a_parallel(_square, _async_range(4))]
    assert result == [0, 1, 4, 9]
    print("a_parallel async test passed:", result)


if __name__ == "__main__":
    output = parallel(_square, range(100_000_000))
    asyncio.run(_run_async_parallel_test())
