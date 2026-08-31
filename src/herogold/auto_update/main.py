"""Handle auto-updates."""
from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import overload

from herogold.auto_update.connectors import Connector, GitHub
from herogold.auto_update.sources import Github, Source


class AutoUpdater:
    """The main class for handling auto-updates.

    *args and **kwargs are passed to the Connector's __init__.
    Alternatively, you can pass a partial(Connector, *args, **kwargs) as the connector argument.
    """

    @overload
    def __init__[**P](
        self,
        source: Source,
        connector: type[Connector],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None: ...

    @overload
    def __init__[**P](
        self,
        source: Source,
        connector: partial[Connector],
    ) -> None: ...

    def __init__[**P](
        self,
        source: Source,
        connector: type[Connector] | partial[Connector],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """Initialize the AutoUpdater with a source and a connector."""
        self.source: Source = source
        self.connector = connector(source, *args, **kwargs)

    def check_for_updates(self) -> bool:
        """Check for updates from the source using the connector."""
        with self.connector as connection:
            return connection.has_update

    def update(self) -> None:
        """Perform the update process."""
        with self.connector as connection:
            result = connection.download()
            if isinstance(result, Exception):
                raise result
            result.install()

def main() -> None:
    """Auto-update workflow is as follows.

    1. Check + Download using a Source and subclasses.
    2. Install using a Connector and subclasses.
    """
    src = Github("https://github.com/HEROgold/funcsort/releases")
    connector = partial(GitHub, root_directory=Path(__file__).parent.parent.parent.parent)
    updater = AutoUpdater(
        source=src,
        connector=connector,
    )
    if updater.check_for_updates():
        updater.update()


if __name__ == "__main__":
    main()
