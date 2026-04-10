from __future__ import annotations

from typing import TYPE_CHECKING

from herogold.errors import as_group, with_exception

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


def test_as_group_returns_values_for_successful_iterable() -> None:
    @as_group
    def values() -> Iterable[int | Exception]:
        return (value for value in (1, 2, 3))

    result = values()

    assert list(result) == [1, 2, 3]


def test_as_group_returns_exception_group_when_any_exception_occurs() -> None:
    @with_exception
    def divide(value: int) -> float:
        return 10 / value

    @as_group
    def mixed() -> Iterable[float | Exception]:
        return (divide(value) for value in (-2, -1, 0, 1, 2))

    result = mixed()

    assert isinstance(result, ExceptionGroup)
    assert len(result.exceptions) == 1
    assert isinstance(result.exceptions[0], ZeroDivisionError)
