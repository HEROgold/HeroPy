"""Handle auto-updates."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from herogold.auto_update.connectors import Connector
    from herogold.auto_update.sources import Source


class AutoUpdater:
    """The main class for handling auto-updates."""

    def __init__(self, source: Source, connector: type[Connector]) -> None:
        """Initialize the AutoUpdater with a source and a connector."""
        self.source: Source = source
        self.connector = connector(source)

    def check_for_updates(self) -> bool:
        """Check for updates from the source using the connector."""
        with self.connector as connection:
            if connection.has_update:
                return True
        return False

    def update(self) -> None:
        """Perform the update process."""
        with self.connector as connection:
            if connection.has_update:
                connection.download()
                connection.install()
