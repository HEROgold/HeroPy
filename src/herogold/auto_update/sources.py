"""Module that helps with tracking and automatically updating your project from production servers."""
# TODO: run this code to see if it works.
# TODO: sort classes and functions in this file by their purpose and functionality.
from __future__ import annotations

import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, LiteralString, override
from zipfile import ZipFile

from httpxyz import HTTPStatusError, get

from herogold.errors import with_known_exception

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from httpxyz import URL

class UpdateError(Exception):
    """Custom exception for update errors."""

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


class Source(meta=ABC):
    """ABC for tracking different sources for auto-updates."""

    def __init__(self, url: URL) -> None:
        """Initialize the source with the given URL."""
        self.url: URL = url

    @abstractmethod
    def apply_update(self) -> None:
        """Install the update from the source."""

@dataclass
class CLI:
    """Run a command line interface command and define a callback for when the command is complete."""

    command: LiteralString
    success = False

class Github(Source):
    """Github source for auto-updates."""

    def __init__(self, url: URL, root: Path, *, is_zip: bool = False) -> None:
        """Initialize the Github source with the given URL.

        The root directory is used to determine where to install the update.
        """
        super().__init__(url)
        self.root_directory = root
        self.is_zip = is_zip

    @with_known_exception(HTTPStatusError)
    def download(self) -> _Downloaded:
        """Download the update from the Github source."""
        response = get(self.url)
        response.raise_for_status()
        return _Downloaded(self.install, response.content)

    def install(self, data: bytes) -> _Installed:
        """Install the downloaded zip."""
        with NamedTemporaryFile(delete=True) as _zip:
            _zip.write(data)
            _zip.flush()
            _zip.seek(0)
            ZipFile(_zip).extractall(self.root_directory)
        return _Installed(success=True)

    def apply_git_update(self) -> None:
        """Apply the update from a git repository."""
        fetch = CLI("git fetch --all")
        pull = CLI("git pull")

        # Setup the subprocess to run the commands
        process = subprocess.Popen(  # noqa: S603
            "/bin/bash" if os.name != "nt" else "cmd.exe",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            shell=False,
        )
        # Run the commands in the subprocess and check for success
        for command in (fetch, pull):
            if process.stdin is not None:
                process.stdin.write(f"{command.command}\n".encode())
                process.stdin.flush()
            if process.stdout is not None:
                output = process.stdout.readline().decode()
                print(output)  # noqa: T201
            command.success = process.wait() == 0

        if not fetch.success:
            error_msg = f"Failed to fetch updates from {self.url}. Cannot apply update."
            raise UpdateError(error_msg)

        if not pull.success:
            error_msg = f"Failed to pull updates from {self.url}. Cannot apply update."
            raise UpdateError(error_msg)

    def apply_zip_update(self) -> None:
        """Apply the update from a zip file."""
        _zip = self.download()
        if isinstance(_zip, HTTPStatusError):
            raise _zip
        _zip.install()

    @override
    def apply_update(self) -> None:
        """Apply the update from the Github source."""
        match self._is_git_repo(), self.is_zip:
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
