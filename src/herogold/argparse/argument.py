"""Argument descriptor for argparse integration."""
from __future__ import annotations

import re
import sys
from argparse import ArgumentParser
from collections.abc import Callable
from enum import Enum
from typing import ClassVar, NoReturn, Self, TypeVar, override

from herogold.colors import Bold, colorize
from herogold.sentinel import MISSING

# Prefer to use later versions. For typevar support defaults.
# Better yet, switch to 3.14+
if sys.version_info >= (3, 14):
    T = TypeVar("T", default=str)
else:
    T = TypeVar("T")


class ColorArgumentParser(ArgumentParser):
    """ArgumentParser with colored help and error output."""

    usage: ClassVar[str] = "usage: "

    @property
    def cls(self) -> type[Self]:
        """Return the class of the parser.

        Used when trying to get ClassVars
        """
        return type(self)

    @override
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        msg = colorize(Bold.Red, f"error: {message}\n")
        self.exit(2, msg)

    def regex_flag(self, string: str) -> str:
        """Format an option flag (e.g. -h, --help) for regex replacement."""
        def repl_flag(match: re.Match) -> str:
            return self.format_argument(match.group(0))
        return re.sub(r"(?<![\w-])(-{1,2}[\w-]+)(?![\w-])", repl_flag, string)

    def regex_option(self, string: str) -> str:
        """Format an option name (e.g. ENVIRONMENT) for regex replacement."""
        def repl_value(match: re.Match) -> str:
            return self.format_option(match.group(0))
        return re.sub(r"\b([A-Z_][A-Z0-9_\-]*)\b", repl_value, string)

    def regex_type(self, string: str) -> str:
        """Format a type name (e.g. str, int) for regex replacement at end of line, only color the type name."""
        def repl_type(match: re.Match) -> str:
            return f" - {self.format_type(match.group(1))}"
        # Match ' - <letters>' at end of line only, only color the type name
        return re.sub(r" - ([a-zA-Z]+)$", repl_type, string, flags=re.MULTILINE)

    def regex_formatter(self, lines: list[str], index: int) -> None:
        """Apply regex-based formatting to a line of help text."""
        lines[index] = self.regex_flag(lines[index])
        lines[index] = self.regex_option(lines[index])
        lines[index] = self.regex_type(lines[index])

    def format_argument(self, argument: str) -> str:
        """Format an argument."""
        return colorize(Bold.Blue, argument)

    def format_option(self, option: str) -> str:
        """Format an option (e.g. ENVIRONMENT, RETRIES)."""
        return colorize(Bold.Purple, option)

    def format_type(self, type_name: str) -> str:
        """Format type names in help text."""
        return colorize(Bold.Red, type_name)

    def format_program(self, program: str) -> str:
        """Format the program name in usage."""
        return program

    def format_value(self, value: str) -> str:
        """Format argument values in help text."""
        return colorize(Bold.Yellow, value)

    def format_heading(self, heading: str) -> str:
        """Override to colorize section headings."""
        return colorize(Bold.Green, heading)

    def format_command(self, command: str) -> str:
        """Format the command part after usage, coloring flags and values precisely."""
        return self.regex_option(self.regex_flag(command))

    def format_usage_line(self, line: str) -> str:
        """Override to colorize usage text."""
        # Only show script name, -h/--help, and a generic abstraction
        script = self.format_program(line[len(self.cls.usage):].split(maxsplit=1)[0])
        usage_line = f"{self.cls.usage}{script} [-h] [--argument OPTION]"
        rest = usage_line[len(self.cls.usage):]
        return self.format_heading(self.cls.usage) + self.format_command(rest)

    def format_help(self) -> str:
        """Override to colorize help text and simplify usage line."""
        help_text = super().format_help()
        lines = help_text.splitlines()
        for i, line in enumerate(lines):
            comparable = line.casefold()
            stripped = line.strip()
            if comparable.startswith(self.cls.usage):
                lines[i] = self.format_usage_line(line)
            elif stripped.endswith(":"):
                lines[i] = self.format_heading(stripped)
            else:
                self.regex_formatter(lines, i)
        return "\n".join(lines)

parser = ColorArgumentParser()

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


class Argument[T]:
    """Helper to define arguments with argparse."""

    internal_prefix = "_ARGUMENT_"

    def __init__(
        self,
        *names: str,
        type_: ArgumentType[T] = MISSING,
        action: Actions = Actions.STORE,
        default: T | None = None,
        default_factory: Callable[[], T] | None = None,
        help: str = "",  # noqa: A002
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
        """Resolve the default value for the argument.

        Given either a default value or a default factory, return the appropriate default value.
        If both are provided, the default value takes precedence.
        """
        if default is None and default_factory is not None:
            return default_factory()
        if default is not None:
            return default
        msg = "Either default or default_factory must be provided."
        raise ValueError(msg)

    def resolve_type(self, type_: ArgumentType[T], action: Actions) -> ArgumentType[T] | type:
        """Resolve the type for the argument.

        If the action is STORE_TRUE, STORE_FALSE, or STORE_BOOL, the type is bool.
        If the type is MISSING, the type is str. Otherwise, return the provided type.
        """
        if action in (
            Actions.STORE_TRUE,
            Actions.STORE_FALSE,
            Actions.STORE_BOOL,
        ):
            return bool
        if type_ is MISSING:
            return str
        return type_

    def __set_name__(self, owner: type, name: str) -> None:
        """Set the name of the attribute to the name of the descriptor."""
        self._setup_parser_argument(name)
        self.name = name
        self.private_name = f"{self.internal_prefix}{name}"

    def __get__(self, obj: object, obj_type: object) -> T:
        """Get the value of the attribute."""
        return getattr(obj, self.private_name)

    def __set__(self, obj: object, value: T) -> None:
        """Set the value of the attribute."""
        setattr(obj, self.private_name, value)

    def _setup_parser_argument(self, name: str) -> None:
        """Set up the argument in the parser."""
        if not isinstance(self.type, type):
            self.type = type(self.type)

        type_name = self.type.__name__
        help_ = f"{self.help} - {type_name}" if self.help else f"{type_name}"
        # TD: Handle subparsers and groups
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
