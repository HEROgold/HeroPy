import sys
from argparse import ArgumentParser
from collections.abc import Callable
from enum import Enum
from typing import Generic, TypeVar

from herogold.src.herogold.sentinel import MISSING

# Prefer to use later versions. For typevar support defaults.
# Better yet, switch to 3.14+
if sys.version_info > (3, 13):
    T = TypeVar("T", default=str)
else:
    T = TypeVar("T")

parser = ArgumentParser()

class Actions(Enum):
    """Possible argument actions."""

    STORE = "store"
    STORE_TRUE = "store_true"
    STORE_FALSE = "store_false"
    STORE_BOOL = "store_bool" # Custom action to store bools
    STORE_CONST = "store_const"
    APPEND = "append"
    APPEND_CONST = "append_const"
    EXTEND = "extend"
    COUNT = "count"
    HELP = "help"
    VERSION = "version"

# Type alias for argparse type
ArgumentType = Callable[[str], T]


class Argument(Generic[T]):
    """Helper to define arguments with argparse."""
    internal_prefix = "_ARGUMENT_"

    def __init__(
        self,
        *names: str,
        type_: ArgumentType[T] = MISSING,
        action: Actions = Actions.STORE,
        default: T | None = None,
        default_factory: Callable[[], T] | None = None,
        help: str = "",
    ) -> None:
        """Initialize argument."""
        default = self.resolve_default(default, default_factory)
        type_ = self.resolve_type(type_, action)

        self.names = names
        self.action = action
        self.type = type_
        self.default = default
        self.help = help

        if self.action is Actions.STORE_BOOL:
            self.type = bool 

    def resolve_default(self, default: T | None, default_factory: Callable[[], T] | None) -> T:
        if default is None and default_factory is not None:
            return default_factory()
        if default is not None:
            return default
        raise ValueError("Either default or default_factory must be provided.")

    def resolve_type(self, type_: ArgumentType[T], action: Actions) -> ArgumentType[T] | type:
        if action in (
            Actions.STORE_TRUE,
            Actions.STORE_FALSE,
            Actions.STORE_BOOL
        ):
            return bool
        if type_ is MISSING:
            return str
        return type_

    def __set_name__(self, owner: type, name: str) -> None:
        """Set the name of the attribute to the name of the descriptor."""
        self.setup_parser_argument(name)
        self.name = name
        self.private_name = f"{self.internal_prefix}{name}"

    def __get__(self, obj: object, obj_type: object) -> T:
        """Get the value of the attribute."""
        return getattr(obj, self.private_name)

    def __set__(self, obj: object, value: T) -> None:
        """Set the value of the attribute."""
        setattr(obj, self.private_name, value)

    def setup_parser_argument(self, name: str) -> None:
        """Set up the argument in the parser."""
        help_ = f"{self.help} - {self.type.__name__}" if self.help else f"{self.type.__name__}"  # ty:ignore[possibly-missing-attribute]  # noqa: E501
        for i in self.names:
            if self.action is Actions.STORE_BOOL:
                parser.add_argument(
                    f"--{i.replace('_', '-')}",
                    action="store_true",
                    dest=name,
                    help=help_,
                )
                parser.add_argument(
                    f"--no-{i.replace('_', '-')}",
                    action="store_false",
                    dest=name,
                    help="",
                )
            else:
                parser.add_argument(
                    f"--{i.replace('_', '-')}",
                    type=self.type,
                    action=self.action.value,
                    default=self.default,
                    help=help_,
                )
