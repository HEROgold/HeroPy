"""A module that contains a mixing class, that provides the subclasses with a logging.Logger instance."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .formats import formatter


def ensure_log_directory(directory: str = "logs") -> str:
    """Ensure that the log directory exists and return its path."""
    log_dir = Path(directory)
    log_dir.mkdir(exist_ok=True)
    return str(log_dir)

# In python 3.14 > Use t''

class LoggerMixin:
    """A mixin class to provide a logger for subclasses."""

    __logger: logging.Logger
    __furthest_child_name = None  # Track the name of the furthest child class
    __global_logger: logging.Logger | None = None
    __log_directory: str = ensure_log_directory()
    __formatter = formatter

    def __init_subclass__(cls, **kwargs: Any) -> None:  # noqa: ANN401
        """Initialize any subclass, setting up the logger. Uses a hierarchical naming convention."""
        super().__init_subclass__(**kwargs)
        # Update the furthest child name with the current subclass name
        LoggerMixin.__furthest_child_name = cls.__name__
        # Update the logger for all classes in the hierarchy to reflect the furthest child
        cls.update_logger_for_hierarchy()

    @classmethod
    def update_logger_for_hierarchy(cls) -> None:
        """Update the logger for all classes in the hierarchy."""
        # Ensure global logger is set up
        if LoggerMixin.__global_logger is None:
            LoggerMixin.__setup_global_logger()

        # Traverse the MRO (Method Resolution Order) in reverse to update logger from base to the furthest child
        for base in reversed(cls.mro()):
            if issubclass(base, LoggerMixin) and hasattr(base, "__furthest_child_name"):
                logger_name = f"{base.__module__}.{LoggerMixin.__furthest_child_name}"
                logger = logging.getLogger(logger_name)

                # If the logger doesn't have handlers, set up class-specific file handler
                if not logger.handlers:
                    cls.__setup_class_logger(logger, base.__name__)

                base.logger = logger

    @classmethod
    def __setup_global_logger(cls) -> None:
        """Set up the global logger that captures all logs."""
        global_logger = logging.getLogger()
        global_logger.setLevel(logging.DEBUG)

        # Create global file handler
        global_log_file = Path(cls.__log_directory) / "global.log"
        file_handler = logging.FileHandler(global_log_file)
        file_handler.setFormatter(cls.__formatter)
        file_handler.setLevel(logging.INFO)

        # Add handler to root logger
        global_logger.addHandler(file_handler)

        # Store reference
        LoggerMixin.__global_logger = global_logger

    @classmethod
    def __setup_class_logger(cls, logger: logging.Logger, class_name: str) -> None:
        """Set up a logger specific to a class."""
        logger.setLevel(logging.DEBUG)

        # Create class-specific file handler
        class_log_file = Path(cls.__log_directory) / f"{class_name}.log"
        file_handler = logging.FileHandler(class_log_file)
        file_handler.setFormatter(cls.__formatter)
        file_handler.setLevel(logging.DEBUG)

        # Add handler to logger
        logger.addHandler(file_handler)
        logger.addHandler(logging.StreamHandler())

    @property
    def logger(self) -> logging.Logger:
        """Return the logger instance for the class."""
        if LoggerMixin.__global_logger is None:
            LoggerMixin.__setup_global_logger()

        if not hasattr(self, "_LoggerMixin__logger"):
            class_name = type(self).__name__
            logger_name = f"{type(self).__module__}.{class_name}"
            logger = logging.getLogger(logger_name)

            # Attach a file handler if one matching this class hasn't been added.
            # (Avoid duplicating handlers on repeated lazy initializations.)
            expected_log_filename = f"{class_name}.log"
            has_handler = any(
                isinstance(h, logging.FileHandler) and h.baseFilename.endswith(expected_log_filename)
                for h in logger.handlers
            )
            if not has_handler:
                self.__setup_class_logger(logger, class_name)
            self.__logger = logger
        return self.__logger

    @logger.setter
    def logger(self, value: logging.Logger) -> None:
        """Set the logger instance for the class."""
        if not isinstance(value, logging.Logger): # type: ignore[reportUnnecessaryIsInstance] # ensure robustness.
            msg = "Logger must be an instance of logging.Logger"
            raise TypeError(msg)
        self.__logger = value

    @classmethod
    def set_log_directory(cls, directory: str) -> None:
        """Change the log directory."""
        cls.__log_directory = ensure_log_directory(directory)

    @classmethod
    def set_log_format(cls, formatter: logging.Formatter) -> None:
        """Change the log format."""
        cls.__formatter = formatter
