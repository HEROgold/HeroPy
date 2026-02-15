"""Subparser support for OOP-style argument definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from .argument import Argument

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction  # pyright: ignore[reportPrivateUsage]


class SubCommand:
    """Base class for defining subcommands with OOP semantics.

    Each subclass represents a subcommand and can define arguments using the Argument descriptor.
    """

    name: ClassVar[str]
    """The name of the subcommand (e.g., 'migrate', 'rollback')."""

    help: ClassVar[str] = ""
    """Help text for the subcommand."""

    _parser: ClassVar[ArgumentParser | None] = None
    """The ArgumentParser for this subcommand."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Register the subcommand class."""
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "name"):
            cls.name = cls.__name__.lower()

    @classmethod
    def setup_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Set up the argument parser for this subcommand.

        Args:
            subparsers: The subparsers action from the parent parser.

        Returns:
            The created ArgumentParser for this subcommand.

        """
        cls._parser = subparsers.add_parser(cls.name, help=cls.help)

        # Add all Argument descriptors to this parser
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, Argument):
                cls._add_argument(attr, attr_name)

        return cls._parser

    @classmethod
    def _add_argument(cls, arg: Argument, name: str) -> None:
        """Add an argument to the subcommand's parser.

        Args:
            arg: The Argument descriptor.
            name: The attribute name.

        """
        if cls._parser is None:
            msg = "Parser not initialized. Call setup_parser first."
            raise RuntimeError(msg)

        type_name = getattr(arg.type, "__name__", str(arg.type))
        help_text = f"{arg.help} - {type_name}" if arg.help else type_name

        # Handle positional vs optional arguments
        if arg.names and not any(n.startswith("-") for n in arg.names):
            # Positional argument
            cls._parser.add_argument(
                arg.names[0],
                type=arg.type if not isinstance(arg.type, type) else arg.type,
                help=help_text,
            )
        else:
            # Optional argument
            for arg_name in arg.names:
                flag = f"--{arg_name.replace('_', '-')}"

                if arg.action.value == "store_bool":
                    cls._parser.add_argument(
                        flag,
                        action="store_true",
                        dest=name,
                        help=help_text,
                    )
                    cls._parser.add_argument(
                        f"--no-{arg_name.replace('_', '-')}",
                        action="store_false",
                        dest=name,
                        help="",
                    )
                else:
                    cls._parser.add_argument(
                        flag,
                        type=arg.type if not isinstance(arg.type, type) else arg.type,
                        action=arg.action.value,
                        default=arg.default,
                        dest=name,
                        help=help_text,
                    )

    def execute(self, args: Namespace) -> int:
        """Execute the subcommand.

        Args:
            args: Parsed command-line arguments.

        Returns:
            Exit code (0 for success, non-zero for error).

        """
        msg = f"{self.__class__.__name__} must implement execute()"
        raise NotImplementedError(msg)


class SubCommandGroup:
    """Group of subcommands with a shared parser."""

    def __init__(self, parser: ArgumentParser, dest: str = "command") -> None:
        """Initialize the subcommand group.

        Args:
            parser: The parent ArgumentParser.
            dest: The attribute name where the subcommand name will be stored.

        """
        self.parser = parser
        self.dest = dest
        self.subparsers = parser.add_subparsers(dest=dest, help="Available commands")
        self.commands: dict[str, type[SubCommand]] = {}

    def add_command(self, command_cls: type[SubCommand]) -> None:
        """Add a subcommand to the group.

        Args:
            command_cls: The SubCommand class to add.

        """
        command_cls.setup_parser(self.subparsers)
        self.commands[command_cls.name] = command_cls

    def add_commands(self, *command_classes: type[SubCommand]) -> None:
        """Add multiple subcommands to the group.

        Args:
            command_classes: SubCommand classes to add.

        """
        for cmd_cls in command_classes:
            self.add_command(cmd_cls)

    def execute(self, args: Namespace) -> int:
        """Execute the appropriate subcommand based on parsed arguments.

        Args:
            args: Parsed command-line arguments.

        Returns:
            Exit code (0 for success, non-zero for error).

        """
        command_name = getattr(args, self.dest, None)
        if not command_name or command_name not in self.commands:
            self.parser.print_help()
            return 1

        command_cls = self.commands[command_name]
        command = command_cls()
        return command.execute(args)
