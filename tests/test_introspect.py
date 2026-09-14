from __future__ import annotations

import inspect

from herogold.introspect import signature_of


def test_signature_of_includes_name() -> None:
    def foo(a: int, b: str = "x") -> bool:
        return bool(a) and bool(b)

    assert signature_of(foo).startswith("foo")


def test_signature_of_stable_across_calls() -> None:
    def foo(a: int, b: str = "x") -> bool:
        return bool(a) and bool(b)

    assert signature_of(foo) == signature_of(foo)


def test_signature_of_differs_when_parameter_added() -> None:
    def foo(a: int) -> bool:
        return bool(a)

    def foo_with_extra(a: int, b: str = "x") -> bool:
        return bool(a) and bool(b)

    assert signature_of(foo) != signature_of(foo_with_extra)


def test_signature_of_differs_when_default_changes() -> None:
    def foo(a: int = 1) -> int:
        return a

    def foo_other_default(a: int = 2) -> int:
        return a

    assert signature_of(foo) != signature_of(foo_other_default)


def test_signature_of_differs_when_annotation_changes() -> None:
    def foo(a: int) -> int:
        return a

    def foo_other_annotation(a: str) -> int:
        return len(a)

    assert signature_of(foo) != signature_of(foo_other_annotation)


def test_signature_of_same_shape_different_names_match_after_name() -> None:
    def foo(a: int) -> int:
        return a

    def bar(a: int) -> int:
        return a

    assert signature_of(foo) != signature_of(bar)
    assert signature_of(foo).removeprefix("foo") == signature_of(bar).removeprefix("bar")


def test_signature_of_works_on_async_functions() -> None:
    async def foo(a: int, b: str = "x") -> bool:
        return bool(a) and bool(b)

    assert inspect.iscoroutinefunction(foo)
    assert signature_of(foo).startswith("foo")


def test_signature_of_works_on_lambda() -> None:
    result = signature_of(lambda a, b=1: a + b)

    assert "<lambda>" in result


def test_signature_of_works_on_callable_object() -> None:
    class CallableThing:
        def __call__(self, a: int) -> int:
            return a

    result = signature_of(CallableThing())

    assert result.startswith("CallableThing")
    assert "a" in result
