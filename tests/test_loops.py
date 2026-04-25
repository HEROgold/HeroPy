from __future__ import annotations

import asyncio

import herogold.loops as loops


def _square(value: int) -> int:
    return value * value


def test_a_parallel_runs_sync_action_in_async_context() -> None:
    async def run() -> None:
        results: list[int] = [i async for i in loops.a_parallel(_square, range(5))]
        assert results == [0, 1, 4, 9, 16]

    asyncio.run(run())
