"""Run a series of command line interface commands."""
from __future__ import annotations

import os
import shutil
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from subprocess import PIPE, Popen
from textwrap import dedent
from typing import TYPE_CHECKING, LiteralString, override

from herogold.errors import with_group, with_known_exception

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable


class CommandError(Exception):
    """Raised when a command fails to execute successfully."""

class CommandState(Enum):
    """State of the command line interface."""

    WAITING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILURE = auto()

@dataclass
class CLI:
    """Run a command line interface command and define a callback for when the command is complete."""

    command: LiteralString | str
    """Where possible, prefer LiteralString for safety. *Never* use user input for this value."""
    state = CommandState.WAITING
    """State of the command."""

class CommandRunner:
    """Run a series of command line interface commands."""

    def __init__(self, commands: Iterable[CLI] | None = None) -> None:
        """Initialize the command runner with a list of commands."""
        self._setup_process()
        self.commands = deque[CLI]()
        if commands is not None:
            for i in commands:
                self.commands.append(i)

    def add(self, command: CLI) -> None:
        """Add a command to the list of commands to run."""
        self.commands.append(command)

    @with_group
    def run(self) -> Generator[list[bytes] | CommandError, None, None]:
        """Run the commands in a subprocess and check for success.

        Removes commands from the list after successful execution.
        """
        while self.commands:
            command = self.commands.popleft()
            self._send(command)
            output = self._read_output(command)
            yield self._check_success(command, output)

    def _setup_process(self) -> None:
        self.process = Popen(  # noqa: S603
            "/bin/bash" if os.name != "nt" else _windows_shell(),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            shell=False,
        )
        if self.process.stdin is None or self.process.stdout is None or self.process.stderr is None:
            msg = "Failed to initialize subprocess for command runner."
            raise CommandError(msg)
        self.stdin = self.process.stdin
        self.stdout = self.process.stdout
        self.stderr = self.process.stderr
        self._read_output() # Clear any initial output

    def _send(self, command: CLI) -> None:
        """Send a command to the subprocess."""
        self.stdin.write(f"{command.command}\n".encode())
        self.stdin.flush()

    def _read_output(self, command: CLI | None = None) -> list[bytes]:
        """Read the output of the command and check for success."""
        # line == b"\r\n" works for windows cmd.
        output_lines: list[bytes] = []
        while True:
            line = self.stdout.readline()

            match command, line:
                case None, b"\r\n":
                    return output_lines
                case CLI(), b"\r\n":
                    command.state = CommandState.SUCCESS
                    return output_lines
                case CLI(), _:
                    command.state = CommandState.FAILURE
                    output_lines.append(line)
                case None, _:
                    output_lines.append(line)
                case _:
                    msg = "Unexpected case in _read_output."
                    raise CommandError(msg)

    @with_known_exception(CommandError)
    def _check_success(self, command: CLI, output: list[bytes]) -> list[bytes]:
        if command.state == CommandState.SUCCESS:
            return output
        error_msg = dedent(f"""
            Failed to run command: {command.command}.
            {self.stderr.read().decode() if self.stderr else 'No error message available.'}""",
        )
        raise CommandError(error_msg)

class SingleRunner(CommandRunner):
    """Run a single command line interface command."""

    def __init__(self, commands: list[CLI]) -> None:
        """Initialize the single command runner with a list of commands."""
        if len(commands) != 1:
            msg = "expected a single command to execute."
            raise ValueError(msg)
        super().__init__(commands)

class MultipleRunner(CommandRunner):
    """Run multiple commands, each in a new process."""

    def __init__(self, commands: Iterable[CLI] | None = None) -> None:
        """Initialize the command runner with a list of commands."""
        self.commands = deque[CLI]()
        if commands is not None:
            for i in commands:
                self.commands.append(i)

    @override
    @with_group
    def run(self) -> Generator[CommandError | list[bytes], None, None]:
        """Run the commands in a subprocess and check for success.

        Removes commands from the list after successful execution.
        """
        while self.commands:
            command = self.commands.popleft()
            self._setup_process()
            self._send(command)
            output = self._read_output(command)
            yield self._check_success(command, output)

def _windows_shell() -> str:
    """Get either powershell of cmd for windows."""
    has_powershell = shutil.which("powershell")
    return "powershell" if has_powershell else "cmd.exe"

def command(*command: LiteralString | str, location: Path | None = None) -> Iterable[list[bytes]] | ExceptionGroup[Exception]:
    """Run a single or multiple commands in sequence."""
    location = location or Path.cwd()
    cd_loc = CLI(f"cd {location}\n")
    return CommandRunner([cd_loc, *[CLI(cmd) for cmd in command]]).run()


__all__ = [
    "CLI",
    "CommandError",
    "CommandRunner",
    "CommandState",
    "MultipleRunner",
    "SingleRunner",
    "command",
]
