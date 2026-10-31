"""Tests for the Depends marker and the inject decorator."""

from __future__ import annotations

import inspect
from contextlib import contextmanager
from typing import TYPE_CHECKING, Annotated

import pytest

from herogold.typing.inject import Depends, inject

if TYPE_CHECKING:
    from collections.abc import Iterator


class FakeProvider:
    """Context manager provider that records how it was used."""

    def __init__(self, value: str = "provided") -> None:
        self.value = value
        self.entered = 0
        self.exited = 0
        self.exit_exception: BaseException | None = None

    @contextmanager
    def __call__(self) -> Iterator[str]:
        self.entered += 1
        try:
            yield self.value
        except BaseException as exc:
            self.exit_exception = exc
            raise
        finally:
            self.exited += 1


provider = FakeProvider()


@pytest.fixture(autouse=True)
def _reset_provider() -> None:
    provider.entered = 0
    provider.exited = 0
    provider.exit_exception = None


def test_missing_argument_is_provided() -> None:

    @inject
    def func(x: int, res: Annotated[str | None, Depends(provider)] = None) -> tuple[int, str | None]:
        return x, res

    assert func(1) == (1, "provided")
    assert provider.entered == 1


def test_none_argument_is_provided() -> None:

    @inject
    def func(res: Annotated[str | None, Depends(provider)] = None) -> str | None:
        return res

    assert func(None) == "provided"
    assert func(res=None) == "provided"
    assert provider.entered == 2


def test_supplied_value_passes_through_without_entering_provider() -> None:
    sentinel = object()

    @inject
    def func(res: Annotated[object | None, Depends(provider)] = None) -> object:
        return res

    assert func(sentinel) is sentinel
    assert func(res=sentinel) is sentinel
    assert provider.entered == 0


def test_provider_exits_after_normal_return() -> None:

    @inject
    def func(res: Annotated[str | None, Depends(provider)] = None) -> str:
        assert provider.exited == 0
        return res

    func()
    assert provider.exited == 1
    assert provider.exit_exception is None


def test_provider_exit_sees_exception_from_function() -> None:
    error = ValueError("boom")

    @inject
    def func(res: Annotated[str | None, Depends(provider)] = None) -> None:
        raise error

    with pytest.raises(ValueError, match="boom"):
        func()
    assert provider.exited == 1
    assert provider.exit_exception is error


def test_works_on_methods() -> None:

    class Service:
        prefix = "svc"

        @inject
        def run(self, res: Annotated[str | None, Depends(provider)] = None) -> str:
            return f"{self.prefix}:{res}"

    assert Service().run() == "svc:provided"


def test_works_on_classmethods() -> None:

    class Service:
        prefix = "cls"

        @classmethod
        @inject
        def run(cls, res: Annotated[str | None, Depends(provider)] = None) -> str:
            return f"{cls.prefix}:{res}"

    assert Service.run() == "cls:provided"
    assert Service.run("given") == "cls:given"
    assert provider.entered == 1


def test_signature_shows_original_parameters() -> None:

    def original(x: int, res: Annotated[str | None, Depends(provider)] = None) -> str:
        """Doc."""
        return f"{x}{res}"

    wrapped = inject(original)

    assert inspect.signature(wrapped) == inspect.signature(original)
    assert wrapped.__name__ == "original"
    assert wrapped.__doc__ == "Doc."


def test_unmarked_parameters_are_untouched() -> None:

    @inject
    def func(x: int | None = None, res: Annotated[str | None, Depends(provider)] = None) -> tuple[int | None, str | None]:
        return x, res

    assert func() == (None, "provided")
    assert provider.entered == 1


def test_inject_rejects_generator_and_async_functions() -> None:
    def gen(x: Annotated[str | None, Depends(provider)] = None) -> Iterator[str]:  # type: ignore[assignment]
        yield x

    async def coro(x: Annotated[str | None, Depends(provider)] = None) -> str:  # type: ignore[assignment]
        return x

    async def agen(x: Annotated[str | None, Depends(provider)] = None):
        yield x

    for fn in (gen, coro, agen):
        with pytest.raises(TypeError):
            inject(fn)
