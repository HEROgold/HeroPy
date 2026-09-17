from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from herogold.errors import with_exception, with_group, with_known_exception

if TYPE_CHECKING:
    from collections.abc import Iterable


def test_with_exception_returns_value_when_successful() -> None:
    @with_exception
    def add_one(value: int) -> int:
        return value + 1

    result = add_one(2)

    assert result == 3


def test_with_exception_returns_exception_when_failing() -> None:
    @with_exception
    def divide(value: int) -> float:
        return 10 / value

    result = divide(0)

    assert isinstance(result, Exception)
    assert isinstance(result, ZeroDivisionError)


def test_with_group_returns_values_for_successful_iterable() -> None:
    @with_group
    def values() -> Iterable[int | Exception]:
        return (value for value in (1, 2, 3))

    result = values()

    assert list(result) == [1, 2, 3]


def test_with_exception_returns_value_when_successful_async() -> None:
    @with_exception
    async def add_one(value: int) -> int:
        return value + 1

    result = asyncio.run(add_one(2))

    assert result == 3


def test_with_exception_returns_exception_when_failing_async() -> None:
    @with_exception
    async def divide(value: int) -> float:
        return 10 / value

    result = asyncio.run(divide(0))

    assert isinstance(result, Exception)
    assert isinstance(result, ZeroDivisionError)


def test_with_known_exception_returns_value_when_successful_async() -> None:
    @with_known_exception(ZeroDivisionError)
    async def divide(value: int) -> float:
        return 10 / value

    result = asyncio.run(divide(2))

    assert result == 5


def test_with_known_exception_returns_exception_when_known_async() -> None:
    @with_known_exception(ZeroDivisionError)
    async def divide(value: int) -> float:
        return 10 / value

    result = asyncio.run(divide(0))

    assert isinstance(result, ZeroDivisionError)


def test_with_known_exception_reraises_unknown_exception_async() -> None:
    @with_known_exception(ZeroDivisionError)
    async def raise_value_error() -> None:
        raise ValueError

    async def run() -> None:
        await raise_value_error()

    try:
        asyncio.run(run())
    except ValueError:
        pass
    else:
        msg = "Expected ValueError to be raised"
        raise AssertionError(msg)


def test_with_group_returns_exception_group_when_any_exception_occurs() -> None:
    @with_exception
    def divide(value: int) -> float:
        return 10 / value

    @with_group
    def mixed() -> Iterable[float | Exception]:
        return (divide(value) for value in (-2, -1, 0, 1, 2))

    result = mixed()

    assert isinstance(result, ExceptionGroup)
    assert len(result.exceptions) == 1
    assert isinstance(result.exceptions[0], ZeroDivisionError)
