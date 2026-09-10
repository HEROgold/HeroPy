"""Argument descriptor for argparse integration."""

from __future__ import annotations

import re
import sys
from argparse import SUPPRESS, Action, ArgumentParser
from argparse import Namespace as ArgparseNamespace
from collections.abc import Callable, Sequence
from enum import Enum
from typing import TYPE_CHECKING, ClassVar, NoReturn, Self, TypeVar, override

if TYPE_CHECKING:
    from argparse import _SubParsersAction

from herogold.colors import Bold, colorize
from herogold.sentinel import MISSING

# Prefer to use later versions. For typevar support defaults.
# Better yet, switch to 3.14+
if sys.version_info >= (3, 14):
    T = TypeVar("T", default=str)
else:
    T = TypeVar("T")

# Metavar every subparsers action gets, so its standalone header row can be found and dropped
# from help output by exact match: its choices are already listed individually right below it.
_SUBCOMMANDS_METAVAR = "<command>"
# Repeated at every level of a --help-full tree, so hidden there in favor of the top-level entry.
_HIDDEN_HELP_OPTIONS = frozenset({"-h", "--help", "--help-full"})
_HELP_FULL_TEXT = "Show this command's help and every nested subcommand's help, as a tree."


class ColorArgumentParser(ArgumentParser):
    """ArgumentParser with colored help and error output."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Initialize the ColorArgumentParser."""
        super().__init__(*args, **kwargs)
        # Not `self.usage` (an ArgumentParser constructor attribute): setting that instead makes
        # argparse treat "usage: " as the whole usage string, doubling argparse's own hardcoded
        # "usage: " prefix into "usage: usage: ".
        self.usage_marker: str = "usage: "

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
        """Colorize the usage line, keeping the real program name but collapsing its options.

        Options are already listed individually below, so `[--flag VALUE]` tokens collapse to one
        generic placeholder; the subcommand metavar is dropped for the same reason.
        """
        if self.usage_marker is None:
            return line
        remainder = line[len(self.usage_marker) :].removeprefix(self.prog)
        has_options = re.search(r"\[[^\]]*\]", remainder) is not None
        tail = f" {self.format_command('[--argument OPTION]')}" if has_options else ""
        return self.format_heading(self.usage_marker) + self.format_program(self.prog) + tail

    def format_help(self) -> str:
        """Override to colorize help text and simplify usage line."""
        if self.usage_marker is None:
            return super().format_help()

        lines = super().format_help().splitlines()

        # A long usage line wraps onto indented continuation lines; merge them before collapsing,
        # otherwise leftover option text survives on the wrapped lines untouched.
        if lines and lines[0].casefold().startswith(self.usage_marker):
            end = 1
            while end < len(lines) and lines[end].strip():
                end += 1
            merged = " ".join(line.strip() for line in lines[:end])
            lines[:end] = [self.format_usage_line(merged)]

        for i, line in enumerate(lines):
            comparable = line.casefold()
            stripped = line.strip()
            if comparable.startswith(self.usage_marker):
                lines[i] = self.format_usage_line(line)
            elif stripped.endswith(":"):
                lines[i] = self.format_heading(stripped)
            else:
                self.regex_formatter(lines, i)

        lines = [line for line in lines if line.strip() != _SUBCOMMANDS_METAVAR]
        return "\n".join(lines)


parser = ColorArgumentParser()


class Namespace(ArgparseNamespace):
    """Base for classes that declare `Argument` descriptors.

    Tracks which `ArgumentParser` a class's `Argument` descriptors register onto. Subclass
    without `subcommand=` to keep using the shared root `parser`, or with `subcommand=` to
    attach to a (lazily created) subparser of the nearest `Namespace` base.
    """

    _parser: ClassVar[ColorArgumentParser]
    _subparsers: ClassVar[_SubParsersAction[ColorArgumentParser] | None] = None
    _subparsers_dest: ClassVar[str | None] = None
    _subcommand_registry: ClassVar[dict[str, type[Namespace]]]

    def __init_subclass__(cls, *, subcommand: str | None = None, **kwargs) -> None:  # noqa: ANN003
        """Attach the subclass to its target parser, creating a subparser if requested.

        `__set_name__` runs on a class's own descriptors before `__init_subclass__` does, so
        `Argument`s declared directly in this class body couldn't yet resolve `cls._parser` when
        their `__set_name__` fired. They register themselves here instead, once `_parser` exists.
        """
        super().__init_subclass__(**kwargs)
        cls._subcommand_registry = {}
        cls._subparsers = None
        cls._subparsers_dest = None

        cls._parser = cls._resolve_parser(cls._find_parent(), subcommand)
        cls._parser.add_argument("--help-full", action=_HelpFullAction, namespace_cls=cls, help=_HELP_FULL_TEXT)

        for attr_name, value in cls.__dict__.items():
            if isinstance(value, Argument):
                value._setup_parser_argument(cls, attr_name)  # noqa: SLF001

    @classmethod
    def _resolve_parser(cls, parent: type[Namespace] | None, subcommand: str | None) -> ColorArgumentParser:
        """Return the parser this class's `Argument`s should register onto."""
        if subcommand is None:
            if parent is None:
                parser.description = cls.__doc__
                return parser
            return parent._parser  # noqa: SLF001

        if parent is None:
            msg = f"{cls.__qualname__} declares subcommand={subcommand!r} but has no Namespace parent to attach to."
            raise TypeError(msg)
        return parent._attach_subcommand(subcommand, cls)  # noqa: SLF001

    @classmethod
    def _attach_subcommand(cls, subcommand: str, child: type[Namespace]) -> ColorArgumentParser:
        """Lazily create this node's subparsers group and register `child` under `subcommand`."""
        if cls._subparsers is None:
            cls._subparsers_dest = f"_subcommand__{cls.__qualname__}"
            cls._subparsers = cls._parser.add_subparsers(
                dest=cls._subparsers_dest,
                required=True,
                metavar=_SUBCOMMANDS_METAVAR,
            )
        cls._subcommand_registry[subcommand] = child
        return cls._subparsers.add_parser(subcommand, help=child.__doc__, description=child.__doc__)

    @classmethod
    def _find_parent(cls) -> type[Namespace] | None:
        """Return the nearest base class that is itself a `Namespace` subclass, if any."""
        for base in cls.__bases__:
            if issubclass(base, Namespace) and base is not Namespace:
                return base
        return None

    @classmethod
    def _resolve_subcommand(cls, raw: ArgparseNamespace) -> type[Namespace]:
        """Walk the subcommand registry to find the class matching the parsed subcommand chain."""
        current = cls
        while current._subparsers is not None:  # noqa: SLF001
            # pyrefly: ignore [no-matching-overload]
            chosen = getattr(raw, current._subparsers_dest, None)  # noqa: SLF001  # ty: ignore[no-matching-overload]
            if chosen is None:
                break
            current = current._subcommand_registry[chosen]  # noqa: SLF001
        return current

    @classmethod
    def _format_own_help(cls) -> str:
        """Render this node's own --help text, with `-h`/`--help`/`--help-full` hidden."""
        hidden = [
            action
            for action in cls._parser._actions  # noqa: SLF001
            if not _HIDDEN_HELP_OPTIONS.isdisjoint(action.option_strings)
        ]
        originals = [action.help for action in hidden]
        try:
            for action in hidden:
                action.help = SUPPRESS
            return cls._parser.format_help()
        finally:
            for action, original in zip(hidden, originals, strict=True):
                action.help = original

    @classmethod
    def _render_help_tree(cls, depth: int = 0) -> str:
        """Render this node's help and every nested subcommand's help as an indented tree.

        Each subparser's own usage line already spells out the full command path (argparse builds
        `prog` up as it descends), so sections don't need a separate heading for it.
        """
        indent = "  " * depth
        own = "\n".join(f"{indent}{line}" for line in cls._format_own_help().splitlines())
        children = (child._render_help_tree(depth + 1) for child in cls._subcommand_registry.values())  # noqa: SLF001
        return "\n\n".join([own, *children])


class _HelpFullAction(Action):
    """Print help for a command and every nested subcommand beneath it, then exit."""

    def __init__(
        self,
        option_strings: list[str],
        dest: str = SUPPRESS,
        default: str = SUPPRESS,
        help: str | None = None,  # noqa: A002
        *,
        namespace_cls: type[Namespace],
    ) -> None:
        """Initialize the action, remembering which Namespace's tree to print."""
        super().__init__(option_strings=option_strings, dest=dest, default=default, nargs=0, help=help)
        self.namespace_cls = namespace_cls

    @override
    def __call__(
        self,
        parser: ArgumentParser,
        namespace: ArgparseNamespace,
        values: str | Sequence[object] | None,
        option_string: str | None = None,
    ) -> None:
        """Print the full help tree and exit."""
        print(self.namespace_cls._render_help_tree())  # noqa: SLF001, T201
        parser.exit()


class Actions(Enum):
    """Possible argument actions."""

    STORE = "store"
    STORE_TRUE = "store_true"
    STORE_FALSE = "store_false"
    STORE_BOOL = "store_bool"  # Custom action to store bools
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
        """Set the name of the attribute to the name of the descriptor.

        `Namespace` subclasses aren't set up here: `owner._parser` doesn't exist yet at this
        point (`__set_name__` runs before `__init_subclass__`), so `Namespace.__init_subclass__`
        does it once the owner's target parser is known.
        """
        self.name = name
        self.private_name = f"{self.internal_prefix}{name}"
        if not issubclass(owner, Namespace):
            self._setup_parser_argument(owner, name)

    def __get__(self, obj: object, obj_type: object) -> T:
        """Get the value of the attribute."""
        return getattr(obj, self.private_name)

    def __set__(self, obj: object, value: T) -> None:
        """Set the value of the attribute."""
        setattr(obj, self.private_name, value)

    def _setup_parser_argument(self, owner: type, name: str) -> None:
        """Set up the argument in the owner's target parser.

        `owner` is used to find the parser to register onto: a `Namespace` subclass's own
        `_parser` (the root parser, or a subparser if it declared `subcommand=`), falling back
        to the shared root `parser` for classes that don't opt into the `Namespace` system.
        """
        if not isinstance(self.type, type):
            self.type = type(self.type)

        target = owner._parser if issubclass(owner, Namespace) else parser  # noqa: SLF001

        type_name = self.type.__name__
        help_ = f"{self.help} - {type_name}" if self.help else f"{type_name}"
        # TD: Handle groups
        for flag_name in self.names:
            if self.action is Actions.STORE_BOOL:
                target.add_argument(
                    f"--{flag_name.replace('_', '-')}",
                    action="store_true",
                    dest=name,
                    help=help_,
                )
                target.add_argument(
                    f"--no-{flag_name.replace('_', '-')}",
                    action="store_false",
                    dest=name,
                    help="",
                )
            else:
                target.add_argument(
                    f"--{flag_name.replace('_', '-')}",
                    type=self.type,
                    action=self.action.value,
                    default=self.default,
                    help=help_,
                )
