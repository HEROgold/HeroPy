"""Connectors for auto-updates."""
from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent
from tkinter import filedialog
from typing import TYPE_CHECKING, LiteralString, Self, override
from zipfile import ZipFile

from httpxyz import Client, HTTPStatusError

from herogold.errors import with_group, with_known_exception
from herogold.log import LoggerMixin

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable
    from types import TracebackType

    from herogold.auto_update.sources import Github as GitHubSource
    from herogold.auto_update.sources import Source

class UpdateError(Exception):
    """Custom exception for update errors."""

class CommandError(UpdateError):
    """Custom exception for command execution errors."""

class _State:
    """State for tracking an update."""

    __slots__ = ()

class _Downloaded(_State):
    """Represents a downloaded update."""

    def __init__(self, installer: Callable[[bytes], _Installed], data: bytes) -> None:
        """Initialize the downloaded update with the given data."""
        self.installer = installer
        self.data = data

    def install(self) -> _Installed:
        """Install the downloaded update."""
        return self.installer(self.data)

class _Installed(_State):
    """Represents an installed update."""

    def __init__(self, *, success: bool) -> None:
        """Initialize the installed update with the given success status."""
        self.success: bool = success

class Connector(ABC, LoggerMixin):
    """ABC for tracking different connectors for auto-updates."""

    def __init__(self, source: Source) -> None:
        """Initialize the connector with the given source."""
        self.source: Source = source

    def __str__(self) -> str:
        """Return a string representation of the connector."""
        return str(self.source)

    def __enter__(self) -> _Connected[Self]:
        """Enter the connection context."""
        return _Connected(self)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the connection context."""
        if not exc_type or not exc_val or not exc_tb:
            self.logger.debug("Connection to %s closed successfully.", self.source.url)
        else:
            self.logger.error(
                "Connection to %s closed with an error: %s",
                self.source.url,
                exc_val,
                exc_info=(exc_type, exc_val, exc_tb),
            )

    @property
    @abstractmethod
    def has_update(self) -> bool:
        """Check if there is an update available from the source."""

    @with_known_exception(Exception)
    @abstractmethod
    def download(self) -> _Downloaded:
        """Download the update from the source."""

    @abstractmethod
    def install(self, data: bytes) -> _Installed:
        """Install the downloaded update."""

class _Disconnected[T: Connector]:
    """A disconnected state for a connector, providing connection handling."""

    def __init__(self, connector: T) -> None:
        self.connector: T = connector

    def connect(self) -> _Connected[T]:
        """Connect to the source and return a connected state."""
        return _Connected(self.connector)

class _Connected[T: Connector]:
    """A connected state for a connector, providing update checking and installation."""

    def __init__(self, connector: T) -> None:
        self.connector: T = connector

    def disconnect(self) -> _Disconnected[T]:
        """Disconnect from the source and return a disconnected state."""
        return _Disconnected(self.connector)

    @property
    def has_update(self) -> bool:
        """Check if there is an update available from the source."""
        return self.connector.has_update

    def download(self) -> _Downloaded | Exception:
        """Download the update from the source."""
        return self.connector.download()

## Concrete connector implementations


class HTTP(Connector):
    """HTTP(s) based connector for auto-updates."""

    def __init__(self, source: Source) -> None:
        """Initialize the HTTP connector with the given source."""
        super().__init__(source)
        self.client = Client(http2=False) # TEMP FALSE
        # self.client.headers.update({"Accept": "application/json"})

    @override
    def __enter__(self) -> _Connected[Self]:  # ty:ignore[invalid-method-override]
        """Enter the connection context."""
        self.result = self.client.options(self.source.url)
        return _Connected(self)

    @property
    @override
    def has_update(self) -> bool:
        """Check if there is an update available from the source."""
        return self.result.status_code == 200  # noqa: PLR2004

    @override
    @with_known_exception(HTTPStatusError)
    def download(self) -> _Downloaded:
        """Download the update from the source."""
        result = self.client.get(self.source.url)
        return _Downloaded(self.install, result.content)

    @override
    def install(self, data: bytes) -> _Installed:
        """Install the downloaded update."""
        loc = Path(filedialog.askopenfilename())
        with loc.open("wb") as f:
            f.write(data)
        return _Installed(success=True)

@dataclass
class CLI:
    """Run a command line interface command and define a callback for when the command is complete."""

    command: LiteralString | str
    success = False

# TODO: make commandrunner into a full heropy library.
class CommandRunner:
    """Run a series of command line interface commands."""

    def __init__(self, commands: Iterable[CLI] | None = None) -> None:
        """Initialize the command runner with a list of commands."""
        self.process = subprocess.Popen(  # noqa: S603
            "/bin/bash" if os.name != "nt" else "cmd.exe",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        if self.process.stdin is None or self.process.stdout is None or self.process.stderr is None:
            msg = "Failed to initialize subprocess for command runner."
            raise UpdateError(msg)
        self.stdin = self.process.stdin
        self.stdout = self.process.stdout
        self.stderr = self.process.stderr
        self._read_output() # Clear any initial output
        self.commands = deque[CLI]()
        if commands is not None:
            for i in commands:
                self.commands.append(i)

    def add(self, command: CLI) -> None:
        """Add a command to the list of commands to run."""
        self.commands.append(command)

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
                    command.success = True
                    return output_lines
                case CLI(), _:
                    command.success = False
                    output_lines.append(line)
                case None, _:
                    output_lines.append(line)
                case _:
                    msg = "Unexpected case in _read_output."
                    raise UpdateError(msg)

    @with_known_exception(UpdateError)
    def _check_success(self, command: CLI, output: list[bytes]) -> list[bytes]:
        if command.success:
            return output
        error_msg = dedent(f"""
            Failed to run command: {command.command}.
            {self.stderr.read().decode() if self.stderr else 'No error message available.'}""",
        )
        raise UpdateError(error_msg)

    @with_group
    def run(self) -> Generator[list[bytes] | UpdateError, None, None]:
        """Run the commands in a subprocess and check for success.

        Removes commands from the list after successful execution.
        """
        while self.commands:
            command = self.commands.popleft()
            self._send(command)
            output = self._read_output(command)
            yield self._check_success(command, output)

class GitHub(HTTP):
    """GitHub based connector for auto-updates."""

    def __init__(self, source: GitHubSource, root_directory: Path) -> None:
        """Initialize the Git connector with the given source."""
        super().__init__(source)
        # due to source: GithubSource, we know that source is a subclass of Source, so this is valid
        # However, using self.source in this class, assumes source is of type Source
        # Even though, super().__init__(source) could be narrowed to GitHubSource.
        self.root_directory = root_directory
        self.cmd = CommandRunner([CLI(f"cd {self.root_directory}")])

    @property
    @override
    def has_update(self) -> bool:
        """Check if there is an update available from the source."""
        is_git = self._is_git_repo()
        same_hash = self._has_same_commit_hash()
        if isinstance(same_hash, Exception):
            return False
        return is_git and not same_hash

    @override
    @with_known_exception(HTTPStatusError)
    def download(self) -> _Downloaded:
        """Download the update from the source."""
        if self._is_git_repo():
            self.cmd.add(CLI("git fetch --all"))
            results = self.cmd.run()
            if isinstance(results, ExceptionGroup):
                msg = "Failed to fetch latest changes from git repository."
                raise CommandError(msg)
            return _Downloaded(self.install, b"")

        # FIXME: actually get the latest release .zip file.
        response = self.client.get(self.source.url)
        response.raise_for_status()
        return _Downloaded(self.install, response.content)

    def _git_pull(self) -> _Installed:
        """Pull the latest changes from the git repository."""
        self.cmd.add(CLI("git pull"))
        results = self.cmd.run()
        if isinstance(results, ExceptionGroup):
            msg = "Failed to pull latest changes from git repository."
            raise CommandError(msg)
        return _Installed(success=True)

    def _extract_zip(self, data: bytes) -> _Installed:
        """Extract the downloaded zip file to the root directory."""
        with NamedTemporaryFile(delete=False, suffix=".zip") as _zip:
            _zip.write(data)
            _zip.flush()
            _zip.seek(0)
            z = ZipFile(_zip.name)
            z.extractall(self.root_directory)
        return _Installed(success=True)

    @override
    def install(self, data: bytes) -> _Installed:
        """Install the downloaded zip."""
        match self._is_git_repo(), data:
            case True, b"":
                return self._git_pull()
            case False, b"":
                msg = "No data to install and not a git repository."
                raise UpdateError(msg)
            case False, _:
                return self._extract_zip(data)
            case True, _:
                msg = "Unexpected data received for git repository."
                raise UpdateError(msg)
            case _, _:
                msg = "Unexpected state in install method."
                raise UpdateError(msg)

    def apply_git_update(self) -> None:
        """Apply the update from a git repository."""

    def apply_zip_update(self) -> None:
        """Apply the update from a zip file."""
        _zip = self.download()
        if isinstance(_zip, HTTPStatusError):
            raise _zip
        _zip.install()

    def apply_update(self) -> None:
        """Apply the update from the Github source."""
        # We know that self.source is of type GitHubSource.
        # Pyrefly seems to have trouble inferring that.
        self.source: GitHubSource # type: ignore[assignment]
        match self._is_git_repo(), self.source.is_zip:
            case True, False:
                self.apply_git_update()
            case False, True:
                self.apply_zip_update()
            case _, _:
                msg = "Invalid combination of git repo and zip installation."
                raise ValueError(msg)

    def _is_git_repo(self) -> bool:
        """Check if the root directory contains a .git directory."""
        git_directory = self.root_directory / ".git"
        return git_directory.is_dir()

    @with_known_exception(CommandError)
    def _has_same_commit_hash(self) -> bool:
        """Check if the local git repository has the same commit hash as the remote."""
        self.cmd.add(CLI("git fetch --all"))
        local_commit_hash = self._get_local_commit_hash()
        source_commit_hash = self._get_remote_commit_hash()
        if isinstance(local_commit_hash, Exception) or isinstance(source_commit_hash, Exception):
            msg = "Failed to get commit hashes for comparison."
            raise CommandError(msg)
        return source_commit_hash == local_commit_hash

    @with_known_exception(CommandError)
    def _get_remote_commit_hash(self) -> str:
        """Get the latest commit hash from the remote repository."""
        self.cmd.add(CLI("git rev-parse @{u}"))
        results = self.cmd.run()
        if isinstance(results, ExceptionGroup):
            msg = "Failed to get remote commit hash."
            raise CommandError(msg)

        results = list(results)
        last = results[-1]
        return last[-1].decode()

    @with_known_exception(CommandError)
    def _get_local_commit_hash(self) -> str:
        """Get the latest commit hash from the local repository."""
        self.cmd.add(CLI("git rev-parse HEAD"))
        results = self.cmd.run()
        if isinstance(results, ExceptionGroup):
            msg = "Failed to get local commit hash."
            raise CommandError(msg)

        results = list(results)
        last = results[-1]
        return last[-1].decode()
