"""Tests for herogold.syntax.generic_class_values."""

from __future__ import annotations

from typing import Literal, get_args, get_origin

import pytest

from herogold.syntax.generic_class_values import GenericClass, TypeArg


class One[T](GenericClass[T]):
    def __init__(self) -> None:
        self.seen = dict(self.__stored_types__)


class Two[T, J](GenericClass[T, J]):
    def __init__(self) -> None:
        self.seen = dict(self.__stored_types__)


class Three[T, J, K](GenericClass[T, J, K]):
    def __init__(self) -> None:
        self.seen = dict(self.__stored_types__)


class Other[T](GenericClass[T]):
    pass


def test_one_param_visible_at_init() -> None:
    assert One[int]().seen == {"T": int}


def test_two_params_visible_at_init() -> None:
    assert Two[int, str]().seen == {"T": int, "J": str}


def test_three_params_visible_at_init() -> None:
    assert Three[int, str, bytes]().seen == {"T": int, "J": str, "K": bytes}


def test_unsubscripted_is_empty() -> None:
    assert One().seen == {}
    assert One.__stored_types__.get("T") is None


def test_non_class_arguments_are_stored() -> None:
    assert One[int | None]().seen == {"T": int | None}
    assert One[Literal["a"]]().seen == {"T": Literal["a"]}
    assert One[list[int]]().seen == {"T": list[int]}


def test_specialization_is_cached_subclass() -> None:
    assert One[int] is One[int]
    assert One[int] is not One[str]
    assert issubclass(One[int], One)
    assert isinstance(One[int](), One)
    assert One[int].__name__ == "One[int]"
    assert Two[int, str].__name__ == "Two[int, str]"


def test_registry_is_per_class() -> None:
    assert Other[int] is not One[int]
    assert issubclass(Other[int], Other)
    assert not issubclass(Other[int], One)


def test_stored_types_is_read_only() -> None:
    with pytest.raises(TypeError):
        One[int].__stored_types__["T"] = str  # pyrefly: ignore [unsupported-operation]  # ty: ignore[invalid-assignment]


def test_wrong_arity_raises() -> None:
    with pytest.raises(TypeError, match="Too many arguments for One; actual 2, expected 1"):
        One[int, str]  # pyrefly: ignore [bad-specialization]  # ty: ignore[invalid-type-arguments]
    with pytest.raises(TypeError, match="Too few arguments for Three; actual 2, expected 3"):
        Three[int, str]  # pyrefly: ignore [bad-specialization]  # ty: ignore[invalid-type-arguments]


def test_specialized_class_cannot_be_subscripted_again() -> None:
    with pytest.raises(TypeError, match="actual 1, expected 0"):
        One[int][str]  # pyrefly: ignore [unsupported-operation]  # ty: ignore[not-subscriptable]


def test_concrete_subclass_inherits_stored_types() -> None:
    class IntOne(One[int]):
        pass

    assert IntOne().seen == {"T": int}


def test_partial_specialization_only_stores_own_params() -> None:
    class Pair[J](Two[int, J]):
        pass

    assert Pair[str]().seen == {"J": str}


def test_typevar_arguments_return_generic_alias() -> None:
    def make[U]() -> object:
        return One[list[U]]

    alias = make()
    assert get_origin(alias) is One
    assert get_origin(get_args(alias)[0]) is list


class Typed[T, J](GenericClass[T, J]):
    t = TypeArg[T]()
    j = TypeArg[J]()

    def __init__(self) -> None:
        self.seen = (self.t, self.j)


def test_type_arg_visible_at_init() -> None:
    assert Typed[int, str]().seen == (int, str)


def test_type_arg_unsubscripted_is_none() -> None:
    assert Typed().seen == (None, None)


def test_type_arg_non_class_is_none() -> None:
    assert Typed[int | None, bytes]().seen == (None, bytes)


def test_type_arg_inherited_by_concrete_subclass() -> None:
    class IntTyped(Typed[int, str]):
        pass

    assert IntTyped().seen == (int, str)


def test_type_arg_rejects_missing_parameter() -> None:
    with pytest.raises(TypeError, match=r"Bad\.x must be TypeArg\[P\]\(\)"):

        class Bad[T](GenericClass[T]):
            x = TypeArg()


def test_type_arg_rejects_concrete_type() -> None:
    with pytest.raises(TypeError, match=r"Bad\.x must be TypeArg\[P\]\(\)"):

        class Bad[T](GenericClass[T]):
            x = TypeArg[int]()


def test_type_arg_rejects_non_generic_class_owner() -> None:
    with pytest.raises(TypeError, match=r"Plain\.x: TypeArg can only be used on GenericClass subclasses"):

        class Plain[T]:
            x = TypeArg[T]()
