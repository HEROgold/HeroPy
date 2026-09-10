"""Argument descriptor for argparse integration."""

from __future__ import annotations

import re
import sys
from argparse import SUPPRESS, Action, ArgumentParser
from argparse import Namespace as ArgparseNamespace
from collections.abc import Callable, Iterator, Sequence
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


# Metavar given to every subparsers action, purely so `ColorArgumentParser.format_help` can
# find and drop its standalone header row by exact match (see `format_help`); never shown to a
# user, since its choices are already listed individually right underneath it.
_SUBCOMMANDS_METAVAR = "<command>"


class ColorArgumentParser(ArgumentParser):
    """ArgumentParser with colored help and error output."""

    def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        """Initialize the ColorArgumentParser."""
        super().__init__(*args, **kwargs)
        # A prefix to detect argparse's own usage line by, not `self.usage` (an ArgumentParser
        # constructor attribute): setting that one instead makes argparse treat "usage: " as the
        # entire usage string, still prefixed by argparse's own hardcoded "usage: ", printing it twice.
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
        """Override to colorize usage text.

        Keeps the real program name (including any subcommand chain it's nested under), but
        collapses the `[--flag VALUE]` options into a single generic placeholder (they're already
        listed individually in the options section below) and drops the subcommand metavar: an
        `Argument`-declared parser's only positional is ever the auto-generated subparsers action,
        and its choices are already listed individually under "positional arguments" too.
        """
        if self.usage_marker is None:
            return line
        rest = line[len(self.usage_marker) :]
        remainder = rest.removeprefix(self.prog)
        has_options = re.search(r"\[[^\]]*\]", remainder) is not None
        tail = f" {self.format_command('[--argument OPTION]')}" if has_options else ""
        return self.format_heading(self.usage_marker) + self.format_program(self.prog) + tail

    def format_help(self) -> str:
        """Override to colorize help text and simplify usage line."""
        if self.usage_marker is None:
            return super().format_help()

        help_text = super().format_help()
        lines = help_text.splitlines()

        # argparse wraps a long usage line onto multiple physical lines (indented continuations,
        # ending at the blank line before the next section). Merge them into one logical line
        # before collapsing it, otherwise leftover option text survives on the wrapped lines.
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

        # Drop the subcommand metavar's own standalone row: its choices are already listed,
        # by name and help text, directly underneath it.
        lines = [line for line in lines if line.strip() != _SUBCOMMANDS_METAVAR]
        return "\n".join(lines)


parser = ColorArgumentParser()


def _iter_namespace_tree(cls: type[Namespace], path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], type[Namespace]]]:
    """Depth-first walk of a `Namespace` and every subcommand nested under it."""
    yield path, cls
    for name, child in cls._subcommand_registry.items():
        yield from _iter_namespace_tree(child, (*path, name))


_HELP_FULL_HIDDEN_OPTIONS = frozenset({"-h", "--help", "--help-full"})


def _format_help_hiding_help_actions(target: ColorArgumentParser) -> str:
    """Render `target`'s help with `-h`/`--help`/`--help-full` omitted.

    Every level in the tree carries these, so repeating them at each level is just noise.
    """
    hidden = [
        action
        for action in target._actions  # noqa: SLF001
        if not _HELP_FULL_HIDDEN_OPTIONS.isdisjoint(action.option_strings)
    ]
    originals = [action.help for action in hidden]
    try:
        for action in hidden:
            action.help = SUPPRESS
        return target.format_help()
    finally:
        for action, original in zip(hidden, originals, strict=True):
            action.help = original


def _format_full_help(cls: type[Namespace]) -> str:
    """Render `cls`'s help and every nested subcommand's help as an indented tree.

    Each subparser's own usage line already spells out the full command path (argparse builds
    `prog` up as it descends into subparsers), so sections don't need a separate heading for it.
    """
    sections: list[str] = []
    for path, node in _iter_namespace_tree(cls):
        indent = "  " * len(path)
        body = "\n".join(f"{indent}{line}" for line in _format_help_hiding_help_actions(node._parser).splitlines())  # noqa: SLF001
        sections.append(body)
    return "\n\n".join(sections)


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
        print(_format_full_help(self.namespace_cls))  # noqa: T201
        parser.exit()


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
        # Each class needs its own subparsers state: unset, these would otherwise resolve
        # through the MRO to whatever the nearest Namespace ancestor already set.
        cls._subcommand_registry = {}
        cls._subparsers = None
        cls._subparsers_dest = None
        parent = cls._find_parent()

        if subcommand is None:
            if parent is None:
                cls._parser = parser
                # A root class attaches to the shared global `parser`, which has no description
                # of its own; without this, a root with no Arguments shows a bare usage line.
                cls._parser.description = cls.__doc__
            else:
                cls._parser = parent._parser  # noqa: SLF001
        else:
            if parent is None:
                msg = (
                    f"{cls.__qualname__} declares subcommand={subcommand!r} "
                    "but has no Namespace parent to attach to."
                )
                raise TypeError(msg)

            if parent._subparsers is None:  # noqa: SLF001
                parent._subparsers_dest = f"_subcommand__{parent.__qualname__}"  # noqa: SLF001
                parent._subparsers = parent._parser.add_subparsers(  # noqa: SLF001
                    dest=parent._subparsers_dest,  # noqa: SLF001
                    required=True,
                    metavar=_SUBCOMMANDS_METAVAR,
                )

            # `help=` is what the parent's own listing shows next to `subcommand`; `description=`
            # is what this subcommand's own --help prints, which matters most for leaves that
            # declare no Arguments of their own and would otherwise show a bare usage line.
            cls._parser = parent._subparsers.add_parser(subcommand, help=cls.__doc__, description=cls.__doc__)  # noqa: SLF001
            parent._subcommand_registry[subcommand] = cls  # noqa: SLF001

        cls._parser.add_argument(
            "--help-full",
            action=_HelpFullAction,
            namespace_cls=cls,
            help="Show this command's help and every nested subcommand's help, as a tree.",
        )

        for attr_name, value in cls.__dict__.items():
            if isinstance(value, Argument):
                value._setup_parser_argument(cls, attr_name)  # noqa: SLF001

    @classmethod
    def _find_parent(cls) -> type[Namespace] | None:
        """Return the nearest base class that is itself a `Namespace` subclass, if any."""
        for base in cls.__bases__:
            if issubclass(base, Namespace) and base is not Namespace:
                return base
        return None


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
        for i in self.names:
            if self.action is Actions.STORE_BOOL:
                target.add_argument(
                    f"--{i.replace('_', '-')}",
                    action="store_true",
                    dest=name,
                    help=help_,
                )
                target.add_argument(
                    f"--no-{i.replace('_', '-')}",
                    action="store_false",
                    dest=name,
                    help="",
                )
            else:
                target.add_argument(
                    f"--{i.replace('_', '-')}",
                    type=self.type,
                    action=self.action.value,
                    default=self.default,
                    help=help_,
                )
