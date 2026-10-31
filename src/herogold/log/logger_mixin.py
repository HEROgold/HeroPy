"""A module that contains a mixing class, that provides the subclasses with a Logger instance."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from . import Logger, config, getLogger

if TYPE_CHECKING:
    from logging import Formatter
    from pathlib import Path

__all__ = ["LoggerMixin"]


def _class_logger(cls: type) -> Logger:
    """Return the logger for a class and register it for a per-class log file."""
    name = f"{cls.__module__}.{cls.__name__}"
    config.register_class_logger(name)
    return getLogger(name)


class LoggerMixin:
    """A mixin class to provide a logger for subclasses."""

    __logger: Logger

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize any subclass, creating its logger. Adds no handlers."""
        super().__init_subclass__(**kwargs)
        cls.__logger = _class_logger(cls)

    @classmethod
    def set_log_directory(cls, directory: str | Path) -> None:
        """Change the log directory."""
        config.set_directory(directory)

    @classmethod
    def set_log_format(cls, formatter: Formatter) -> None:
        """Change the log format."""
        config.set_formatter(formatter)

    @property
    def logger(self) -> Logger:
        """Return the logger instance for the class."""
        if not hasattr(self, "_LoggerMixin__logger"):
            self.__logger = _class_logger(type(self))
        return self.__logger

    @logger.setter
    def logger(self, value: Logger) -> None:
        """Set the logger instance for the class."""
        if not isinstance(value, Logger):  # pyright: ignore[reportUnnecessaryIsInstance] # ensure robustness.
            msg = "Logger must be an instance of Logger"
            raise TypeError(msg)
        self.__logger = value
