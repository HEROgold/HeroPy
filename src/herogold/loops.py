"""Provides helpers for running different loops."""

from __future__ import annotations

from herogold.asynchronous import get_async_loop

__lazy_modules__: list[str] = ["asyncio"]

import os
from concurrent.futures import ProcessPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable, Iterable, Iterator

cpu_count = os.cpu_count() or 1


def parallel[T](action: Callable[[T], T], data: Iterable[T]) -> Iterator[T]:
    """Run a function in parallel across multiple CPU cores."""
    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        yield from executor.map(action, data, chunksize=10)


async def a_parallel[T](action: Callable[[T], Awaitable[T]], data: AsyncIterable[T]) -> AsyncIterator[T]:
    """Run a function in parallel across multiple CPU cores."""
    loop = get_async_loop()

    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        async for item in data:
            yield await loop.run_in_executor(executor, action, item)


if __name__ == "__main__":
    output = parallel(lambda x: x * x, range(100_000_000))
