"""Module that helps setting up logging configurations."""

from __future__ import annotations

import re
from logging import (
    DEBUG,
    INFO,
    FileHandler,
    Formatter,
    Handler,
    LogRecord,
    StreamHandler,
)
from pathlib import Path
from typing import TYPE_CHECKING, override

from .formats import formatter

if TYPE_CHECKING:
    from collections.abc import Container
    from io import TextIOWrapper

stream_handler = StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(INFO)

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


def _windows_safe_name(name: str) -> str:
    """Replace characters that are invalid in Windows file names."""
    return _INVALID_FILENAME_CHARS.sub("_", name)


class LazyFileHandler(FileHandler):
    """A FileHandler that creates its directory and file on the first write."""

    def __init__(self, filename: str | Path) -> None:
        """Create the handler without touching the filesystem."""
        super().__init__(filename, delay=True)

    @override
    def _open(self) -> TextIOWrapper:
        Path(self.baseFilename).parent.mkdir(parents=True, exist_ok=True)
        return super()._open()


class PerNameFileHandler(Handler):
    """Write records of the given loggers to ``<directory>/<logger name>.log``, opened on first use."""

    def __init__(self, directory: str | Path, names: Container[str]) -> None:
        """Remember the directory and logger names without touching the filesystem."""
        super().__init__(DEBUG)
        self.directory = Path(directory)
        self.names = names
        self._children: dict[str, LazyFileHandler] = {}

    @override
    def emit(self, record: LogRecord) -> None:
        if record.name not in self.names:
            return
        child = self._children.get(record.name)
        if child is None:
            child = LazyFileHandler(self.directory / f"{_windows_safe_name(record.name)}.log")
            child.setFormatter(self.formatter)
            self._children[record.name] = child
        child.emit(record)

    @override
    def setFormatter(self, fmt: Formatter | None) -> None:
        super().setFormatter(fmt)
        for child in self._children.values():
            child.setFormatter(fmt)

    @override
    def flush(self) -> None:
        for child in list(self._children.values()):
            child.flush()

    @override
    def close(self) -> None:
        for child in self._children.values():
            child.close()
        self._children.clear()
        super().close()
