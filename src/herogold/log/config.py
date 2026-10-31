"""Opt-in logging setup. Importing this module has no side effects on the logging state."""

from __future__ import annotations

from logging import DEBUG, INFO, Formatter, Handler, StreamHandler, getLogger
from pathlib import Path
from typing import Any

from .formats import formatter as default_formatter
from .handlers import LazyFileHandler, PerNameFileHandler

__all__ = [
    "log_directory",
    "register_class_logger",
    "set_directory",
    "set_formatter",
    "setup",
    "teardown",
]

DEFAULT_DIRECTORY = Path("logs")


_installed: list[Handler] = []
_class_loggers: set[str] = set()
_original_level: int | None = None
_directory: Path | None = None
_last_directory: Path | None = None
_last_options: dict[str, Any] = {}
_formatter: Formatter = default_formatter


def _remove_installed() -> None:
    root = getLogger()
    for handler in _installed:
        root.removeHandler(handler)
        handler.close()
    _installed.clear()


def setup(
    directory: str | Path | None = None,
    level: int = DEBUG,
    *,
    global_file: bool = True,
    per_class_files: bool = True,
    stream: bool = True,
) -> None:
    """Install the herogold log handlers on the root logger. Creates no files until a record is written."""
    global _original_level, _directory, _last_directory, _last_options  # noqa: PLW0603
    root = getLogger()
    _remove_installed()
    if _original_level is None:
        _original_level = root.level

    path = Path(directory) if directory is not None else (_last_directory or DEFAULT_DIRECTORY)
    _last_directory = path
    _directory = path
    _last_options = {
        "level": level,
        "global_file": global_file,
        "per_class_files": per_class_files,
        "stream": stream,
    }
    root.setLevel(level)

    if global_file:
        file_handler = LazyFileHandler(path / "_global.log")
        file_handler.setLevel(INFO)
        _installed.append(file_handler)
    if per_class_files:
        _installed.append(PerNameFileHandler(path, _class_loggers))
    if stream:
        stream_handler = StreamHandler()
        stream_handler.setLevel(INFO)
        _installed.append(stream_handler)

    for handler in _installed:
        handler.setFormatter(_formatter)
        root.addHandler(handler)


def teardown() -> None:
    """Remove the handlers installed by setup() and restore the root level."""
    global _original_level, _directory  # noqa: PLW0603
    _remove_installed()
    if _original_level is not None:
        getLogger().setLevel(_original_level)
        _original_level = None
    _directory = None


def log_directory() -> Path | None:
    """Return the active log directory, or None when setup() is not active."""
    return _directory


def set_formatter(formatter: Formatter) -> None:
    """Set the formatter for the installed handlers and for later setup() calls."""
    global _formatter  # noqa: PLW0603
    _formatter = formatter
    for handler in _installed:
        handler.setFormatter(formatter)


def set_directory(directory: str | Path) -> None:
    """Set the log directory. Moves the output when setup() is active."""
    global _last_directory  # noqa: PLW0603
    _last_directory = Path(directory)
    if _directory is not None:
        setup(_last_directory, **_last_options)


def register_class_logger(name: str) -> None:
    """Give the named logger its own file once setup() runs with per_class_files."""
    _class_loggers.add(name)
