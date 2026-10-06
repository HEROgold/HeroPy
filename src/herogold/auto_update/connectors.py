"""Connectors for auto-updates.

A connector checks a :class:`Source` for an update, downloads it and installs it:

- :class:`HTTP` downloads a single file to a destination path.
- :class:`GitCheckout` fast-forwards a git checkout to its upstream branch.
- :class:`GitHubRelease` replaces an installed copy with the latest GitHub release.
"""

from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Self, override
from zipfile import ZipFile

from httpxyz import Client, HTTPStatusError

from herogold.command import CommandError
from herogold.errors import HerogoldError, with_known_exception
from herogold.log import LoggerMixin

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from herogold.auto_update.sources import Github as GitHubSource
    from herogold.auto_update.sources import Source


class UpdateError(HerogoldError):
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
    """Download the file at the source URL to ``destination``."""

    def __init__(self, source: Source, destination: Path, client: Client | None = None) -> None:
        """Initialize the HTTP connector with the given source and destination file."""
        super().__init__(source)
        self.destination = destination
        self.client = client or Client(http2=True, follow_redirects=True)

    @override
    def __enter__(self) -> _Connected[Self]:
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
        response = self.client.get(self.source.url)
        response.raise_for_status()
        return _Downloaded(self.install, response.content)

    @override
    def install(self, data: bytes) -> _Installed:
        """Write the downloaded file to ``destination``."""
        self.destination.write_bytes(data)
        return _Installed(success=True)


class GitCheckout(Connector):
    """Update a git checkout by fast-forwarding it to its upstream branch.

    Git runs as an argument list (no shell), so ``root_directory`` is never
    interpreted as shell syntax.
    """

    def __init__(self, source: Source, root_directory: Path) -> None:
        """Initialize the connector for the checkout at ``root_directory``."""
        super().__init__(source)
        self.root_directory = root_directory

    @property
    @override
    def has_update(self) -> bool:
        """Fetch, then report whether the upstream branch is ahead of ``HEAD``."""
        self._git("fetch", "--quiet")
        return self._git("rev-parse", "HEAD") != self._git("rev-parse", "@{u}")

    @override
    @with_known_exception(CommandError)
    def download(self) -> _Downloaded:
        """Fetch the upstream changes; ``install`` applies them."""
        self._git("fetch", "--quiet")
        return _Downloaded(self.install, b"")

    @override
    def install(self, data: bytes) -> _Installed:
        """Fast-forward to the fetched upstream commit."""
        self._git("pull", "--ff-only", "--quiet")
        return _Installed(success=True)

    def _git(self, *args: str) -> str:
        """Run ``git <args>`` in the checkout and return its stripped stdout."""
        git = shutil.which("git")
        if git is None:
            msg = "git is not installed."
            raise CommandError(msg)
        result = subprocess.run(  # noqa: S603
            [git, *args],
            cwd=self.root_directory,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            msg = f"git {' '.join(args)} failed: {result.stderr.strip()}"
            raise CommandError(msg)
        return result.stdout.strip()


class GitHubRelease(Connector):
    """Replace an installed copy at ``root_directory`` with the latest GitHub release.

    ``current_version`` is the installed version (e.g. ``importlib.metadata.version(...)``);
    an update is available when the latest release tag differs from it (a leading ``v``
    is ignored on both).
    """

    def __init__(
        self,
        source: GitHubSource,
        root_directory: Path,
        current_version: str,
        client: Client | None = None,
    ) -> None:
        """Initialize the connector for the installation at ``root_directory``."""
        super().__init__(source)
        self.github: GitHubSource = source
        self.root_directory = root_directory
        self.current_version = current_version
        self.client = client or Client(follow_redirects=True, headers={"Accept": "application/vnd.github+json"})
        self._release: dict[str, object] | None = None

    @property
    @override
    def has_update(self) -> bool:
        """Return whether the latest release tag differs from ``current_version``."""
        tag = str(self._latest_release()["tag_name"])
        return tag.removeprefix("v") != self.current_version.removeprefix("v")

    @override
    @with_known_exception(HTTPStatusError)
    def download(self) -> _Downloaded:
        """Download the latest release's source archive."""
        response = self.client.get(str(self._latest_release()["zipball_url"]))
        response.raise_for_status()
        return _Downloaded(self.install, response.content)

    @override
    def install(self, data: bytes) -> _Installed:
        """Extract the archive and copy its contents over ``root_directory``.

        GitHub archives wrap everything in a single ``<owner>-<repo>-<sha>/`` folder;
        its contents (not the folder itself) are copied.
        """
        with TemporaryDirectory() as tmp, ZipFile(BytesIO(data)) as archive:
            archive.extractall(tmp)
            entries = list(Path(tmp).iterdir())
            top = entries[0] if len(entries) == 1 and entries[0].is_dir() else Path(tmp)
            shutil.copytree(top, self.root_directory, dirs_exist_ok=True)
        return _Installed(success=True)

    def _latest_release(self) -> dict[str, object]:
        """Fetch (once) the latest release metadata from the GitHub API."""
        if self._release is None:
            response = self.client.get(self.github.api_latest_release)
            response.raise_for_status()
            self._release = response.json()
        return self._release
