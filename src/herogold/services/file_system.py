"""File system watcher using watchdog to monitor file system events."""

from __future__ import annotations

from pathlib import Path
from typing import override

from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileClosedEvent,
    FileClosedNoWriteEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileOpenedEvent,
    FileSystemEvent,
    FileSystemEventHandler,
)

from herogold.log import LoggerMixin, log_directory


class BaseFileSystemWatcher(FileSystemEventHandler, LoggerMixin):
    """Handle file system events."""

    def log(self, msg: str, event: FileSystemEvent) -> None:
        """Log a message using the logger."""
        directory = log_directory()
        if directory is not None and Path(str(event.src_path)).resolve().is_relative_to(directory):
            return  # Skip logging events from the log directory
        self.logger.debug(msg, event)

    @override
    def on_any_event(self, event: FileSystemEvent) -> None:
        self.log("File system event: %s", event)

    @override
    def on_moved(self, event: DirMovedEvent | FileMovedEvent) -> None:
        self.log("File moved event: %s", event)

    @override
    def on_created(self, event: DirCreatedEvent | FileCreatedEvent) -> None:
        self.log("File created event: %s", event)

    @override
    def on_deleted(self, event: DirDeletedEvent | FileDeletedEvent) -> None:
        self.log("File deleted event: %s", event)

    @override
    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        self.log("File modified event: %s", event)

    @override
    def on_closed(self, event: FileClosedEvent) -> None:
        self.log("File closed event: %s", event)

    @override
    def on_closed_no_write(self, event: FileClosedNoWriteEvent) -> None:
        self.log("File closed no write event: %s", event)

    @override
    def on_opened(self, event: FileOpenedEvent) -> None:
        self.log("File opened event: %s", event)


if __name__ == "__main__":
    from watchdog.observers import Observer

    path = "."
    event_handler = BaseFileSystemWatcher()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            pass
    except Exception:
        event_handler.logger.exception("An error occurred while monitoring the file system.")
        observer.stop()
    observer.join()
