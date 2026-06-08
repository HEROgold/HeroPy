"""Connectors for auto-updates."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Self, override

from httpxyz import Client

from herogold.log import LoggerMixin

if TYPE_CHECKING:
    from types import TracebackType

    from herogold.auto_update.sources import Source

class Connector(ABC, LoggerMixin):
    """ABC for tracking different connectors for auto-updates."""

    def __init__(self, source: Source) -> None:
        """Initialize the connector with the given source."""
        self.source: Source = source

    def __enter__(self) -> _Connected[Self]:
        """Enter the connection context."""
        return _Connected(self)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> _Disconnected[Self]:
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
        return _Disconnected(self)

    @abstractmethod
    @property
    def has_update(self) -> bool:
        """Check if there is an update available from the source."""

    @abstractmethod
    def download(self) -> None:
        """Download the update from the source."""

    @abstractmethod
    def install(self) -> None:
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

    def download(self) -> None:
        """Download the update from the source."""
        return self.connector.download()

    def install(self) -> None:
        """Install the downloaded update."""
        return self.connector.install()


## Concrete connector implementations


class HTTP(Connector):
    """HTTP(s) based connector for auto-updates."""

    def __init__(self, source: Source) -> None:
        """Initialize the HTTP connector with the given source."""
        super().__init__(source)
        self.client = Client(http2=True)

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
    def download(self) -> None:
        """Download the update from the source."""
        self.client.get(self.source.url)
        # Put on disk

    @override
    def install(self) -> None:
        """Install the downloaded update."""
        # Install the update
