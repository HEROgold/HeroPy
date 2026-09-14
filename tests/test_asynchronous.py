from __future__ import annotations

import asyncio

from herogold.asynchronous import dual_wraps


def test_dual_wraps_uses_sync_wrapper_for_sync_func() -> None:
    def add_one(value: int) -> int:
        return value + 1

    def sync_wrapper(value: int) -> int:
        return add_one(value) * 10

    async def async_wrapper(value: int) -> int:
        return add_one(value) * 100

    wrapped = dual_wraps(add_one, sync_wrapper, async_wrapper)

    assert wrapped(2) == 30
    assert wrapped.__name__ == "add_one"


def test_dual_wraps_uses_async_wrapper_for_async_func() -> None:
    async def add_one(value: int) -> int:
        return value + 1

    def sync_wrapper(value: int) -> int:
        return value * 10

    async def async_wrapper(value: int) -> int:
        return await add_one(value) * 100

    wrapped = dual_wraps(add_one, sync_wrapper, async_wrapper)

    result = asyncio.run(wrapped(2))

    assert result == 300
    assert wrapped.__name__ == "add_one"
