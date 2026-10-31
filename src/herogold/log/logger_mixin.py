"""A module that contains a mixing class, that provides the subclasses with a Logger instance."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from . import Logger, config, getLogger

if TYPE_CHECKING:
    from logging import Formatter
    from pathlib import Path

__all__ = ["LoggerMixin"]


class LoggerMixin:
    """A mixin class to provide a logger for subclasses."""

    __logger: Logger

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        """Give each subclass a logger named ``module.Class``. Adds no handlers."""
        super().__init_subclass__(**kwargs)
        name = f"{cls.__module__}.{cls.__name__}"
        config.register_class_logger(name)
        cls.__logger = getLogger(name)

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
        return self.__logger

    @logger.setter
    def logger(self, value: Logger) -> None:
        """Set the logger instance for the class."""
        if not isinstance(value, Logger):  # pyright: ignore[reportUnnecessaryIsInstance] # ensure robustness.
            msg = "Logger must be an instance of Logger"
            raise TypeError(msg)
        self.__logger = value
