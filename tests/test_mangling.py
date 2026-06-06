from __future__ import annotations

import pytest

from herogold.mangling import InvalidNameError, ManglingError, get_mangled_attribute, mangle


def contains_mangle(class_: type, mangled_name: str) -> bool:
    """Helper function to check if a class contains a mangled attribute."""
    return any(attr for attr in dir(class_) if attr == mangled_name)

class TestInvalidNameError:
    def test_exception_message_format(self) -> None:
        """Test InvalidNameError has proper message format."""
        name = "123invalid"
        error = InvalidNameError(name)
        assert str(error) == (
            f"Invalid name '{name}' for mangling. Names must be valid Python "
            "identifiers and cannot start with a digit."
        )

    def test_exception_inheritance(self) -> None:
        """Test InvalidNameError inherits from ManglingError."""
        error = InvalidNameError("test")
        assert isinstance(error, ManglingError)


class TestMangle:
    def test_mangle_dunder_name(self) -> None:
        """Test mangling a dunder name (starts with __)."""
        class TestClass:
            __attr = None

        result = mangle(TestClass, "attr")
        assert contains_mangle(TestClass, result)

    def test_mangle_dunder_with_underscores(self) -> None:
        """Test mangling dunder names with underscores."""
        class TestClass:
            __private_attr = None

        result = mangle(TestClass, "__private_attr")
        assert contains_mangle(TestClass, result)

    def test_mangle_dunder_with_single_trailing_underscore(self) -> None:
        """Test mangling dunder names with single trailing underscore."""
        class TestClass:
            __myAttribute_ = None

        result = mangle(TestClass, "myAttribute_")
        assert contains_mangle(TestClass, result)

    def test_no_mangle_dunder_method(self) -> None:
        """Test that dunder methods (both __ prefix and suffix) are not mangled."""
        class TestClass:
            __init__ = None

        result = mangle(TestClass, "__init__")
        assert contains_mangle(TestClass, result)

    def test_no_mangle_dunder_variable(self) -> None:
        """Test that dunder variables are not mangled."""
        class TestClass:
            __var__ = None

        result = mangle(TestClass, "__var__")
        assert contains_mangle(TestClass, result)

    def test_get_mangled_attribute_with_dunder_method(self) -> None:
        """Test that trying to get a dunder method returns it unmolested."""
        class TestClass:
            def __init__(self) -> None:
                pass

        result = mangle(TestClass, "__init__")
        assert contains_mangle(TestClass, result)

    def test_mangle_invalid_name_starts_with_digit(self) -> None:
        """Test that names starting with digits raise InvalidNameError."""
        class TestClass:
            __123attr = None

        with pytest.raises(InvalidNameError) as exc_info:
            mangle(TestClass, "123attr")
        assert "123attr" in str(exc_info.value)

    def test_mangle_invalid_name_with_special_chars(self) -> None:
        """Test that names with special characters raise InvalidNameError."""
        class TestClass:
            __attr = None

        with pytest.raises(InvalidNameError):
            mangle(TestClass, "attr-name")

    def test_mangle_invalid_name_with_space(self) -> None:
        """Test that names with spaces raise InvalidNameError."""
        class TestClass:
            __attr = None

        with pytest.raises(InvalidNameError):
            mangle(TestClass, "attr name")

    def test_mangle_valid_simple_names_not_mangled(self) -> None:
        """Test that valid simple names without __ prefix are not mangled."""
        class TestClass:
            attr = None

        result = mangle(TestClass, "attr")
        assert not contains_mangle(TestClass, result)


class TestGetMangledAttribute:
    def test_get_mangled_attribute_simple(self) -> None:
        """Test retrieving a mangled attribute from a class."""
        class TestClass:
            __attr = "test_value"

        result = get_mangled_attribute(TestClass, TestClass, "attr")
        assert not contains_mangle(TestClass, result)

    def test_get_mangled_attribute_different_types(self) -> None:
        """Test retrieving various types of mangled attributes."""
        class Container:
            __num = 42
            __lst = [1, 2, 3]
            __dct = {"key": "value"}

        assert get_mangled_attribute(Container, Container, "num") == 42
        assert get_mangled_attribute(Container, Container, "lst") == [1, 2, 3]
        assert get_mangled_attribute(Container, Container, "dct") == {"key": "value"}

    def test_get_mangled_attribute_missing_raises_attribute_error(self) -> None:
        """Test that missing attributes raise AttributeError."""
        class TestClass:
            pass

        with pytest.raises(AttributeError):
            get_mangled_attribute(TestClass, TestClass, "nonexistent")

    def test_get_mangled_attribute_invalid_name_raises(self) -> None:
        """Test that invalid attribute names raise InvalidNameError."""
        class TestClass:
            pass

        with pytest.raises(InvalidNameError):
            get_mangled_attribute(TestClass, TestClass, "123bad")

    def test_get_mangled_attribute_with_different_owner(self) -> None:
        """Test getting an attribute when owner differs from cls."""
        class Parent:
            __value = 100

        class Child(Parent):
            pass

        result = get_mangled_attribute(Child, Parent, "value")
        assert result == 100


class TestMultipleInheritance:
    def test_mangle_with_single_inheritance(self) -> None:
        """Test unmangling in single inheritance hierarchy."""
        class Base:
            __secret = "base_value"

        class Derived(Base):
            pass

        result = get_mangled_attribute(Derived, Base, "secret")
        assert result == "base_value"

    def test_mangle_with_multiple_inheritance(self) -> None:
        """Test unmangling with multiple inheritance (diamond problem)."""
        class A:
            __attr = "from_a"

        class B(A):
            __attr = "from_b"

        class C(A):
            __attr = "from_c"

        class D(B, C):
            pass

        # Each class has its own mangled name
        assert get_mangled_attribute(D, A, "attr") == "from_a"
        assert get_mangled_attribute(D, B, "attr") == "from_b"
        assert get_mangled_attribute(D, C, "attr") == "from_c"

    def test_mro_with_multiple_inheritance(self) -> None:
        """Test MRO is respected when accessing mangled attributes."""
        class Mixin1:
            __data = "mixin1"

        class Mixin2:
            __data = "mixin2"

        class Combined(Mixin1, Mixin2):
            pass

        # Access through explicit owner classes
        assert get_mangled_attribute(Combined, Mixin1, "data") == "mixin1"
        assert get_mangled_attribute(Combined, Mixin2, "data") == "mixin2"

    def test_mangle_consistency_across_hierarchy(self) -> None:
        """Test that mangle produces consistent results across hierarchy."""
        class GrandParent:
            pass

        class Parent(GrandParent):
            pass

        class Child(Parent):
            pass

        # All should produce the same mangled name for the same owner
        assert mangle(Child, "__test") == "_Child__test"
        assert mangle(Parent, "__test") == "_Parent__test"
        assert mangle(GrandParent, "__test") == "_GrandParent__test"
