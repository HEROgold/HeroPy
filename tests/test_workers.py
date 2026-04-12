from __future__ import annotations

import asyncio
import time

from herogold.workers import AsyncWorkerPool, WorkerPool

timeout = 1  # seconds


def no_op() -> None:
    return


def _sort() -> None:
    size = 10
    numbers = list(range(size, 0, -1))
    numbers.sort()
    if numbers[0] != 1 or numbers[-1] != size:
        msg = "Sorting failed: first element is %s, last element is %s"
        raise RuntimeError(msg, numbers[0], numbers[-1])


def _raise_zero_division() -> None:
    _ = 1 / 0


def _sleep_long() -> None:
    time.sleep(5)


def test_workerpool_sort_integers() -> None:
    with WorkerPool() as pool:
        pool.submit(_sort)
        pool.wait()
        assert list(pool.pop_errors()) == []


def test_workerpool_extracts_zero_division_error() -> None:
    with WorkerPool() as pool:
        pool.submit(_raise_zero_division)
        pool.wait()

        errors = list(pool.pop_errors())
        assert len(errors) == 1
        assert isinstance(errors[0], ZeroDivisionError)
        assert list(pool.pop_errors()) == []  # All errors consumed!


def test_workerpool_waits_for_completed_tasks() -> None:
    with WorkerPool() as pool:
        pool.submit(no_op)
        pool.wait()

        assert list(pool.pop_errors()) == []


def test_async_workerpool_sort_integers() -> None:
    async def run() -> None:
        async with AsyncWorkerPool() as pool:
            await pool.submit(_sort)
            await asyncio.wait_for(pool.wait(), timeout=timeout)

            assert [i async for i in pool.pop_errors()] == []

    asyncio.run(run())


def test_async_workerpool_extracts_zero_division_error() -> None:
    async def run() -> None:
        async with AsyncWorkerPool() as pool:
            await pool.submit(_raise_zero_division)
            await asyncio.wait_for(pool.wait(), timeout=timeout)

            errors = [i async for i in pool.pop_errors()]
            assert len(errors) == 1
            assert isinstance(errors[0], ZeroDivisionError)
            assert [i async for i in pool.pop_errors()] == []  # All errors consumed!

    asyncio.run(run())


def test_async_workerpool_waits_for_completed_tasks() -> None:
    async def run() -> None:
        async with AsyncWorkerPool() as pool:
            await pool.submit(no_op)
            await asyncio.wait_for(pool.wait(), timeout=timeout)

            assert [i async for i in pool.pop_errors()] == []

    asyncio.run(run())


def main() -> None:
    test_workerpool_sort_integers()
    test_workerpool_extracts_zero_division_error()
    test_async_workerpool_sort_integers()
    test_async_workerpool_extracts_zero_division_error()


if __name__ == "__main__":
    main()
