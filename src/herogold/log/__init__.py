"""Pass-through of logging module, with custom Logger patches."""

from __future__ import annotations

import sys
from logging import (
    CRITICAL,
    DEBUG,
    ERROR,
    FATAL,
    INFO,
    NOTSET,
    WARNING,
    BufferingFormatter,
    FileHandler,
    Filter,
    Formatter,
    Handler,
    Logger,
    LoggerAdapter,
    LogRecord,
    NullHandler,
    RootLogger,
    StreamHandler,
    addLevelName,
    basicConfig,
    captureWarnings,
    critical,
    debug,
    disable,
    error,
    exception,
    fatal,
    getHandlerByName,
    getHandlerNames,
    getLevelName,  # pyright: ignore[reportDeprecated]
    getLevelNamesMapping,
    getLogger,
    getLoggerClass,
    getLogRecordFactory,
    info,
    lastResort,
    log,
    makeLogRecord,
    raiseExceptions,
    setLoggerClass,
    setLogRecordFactory,
    shutdown,
    warning,
)

# Patch logging for Python 3.14+
if sys.version_info >= (3, 14):
    import logging as _logging

    from .logger import Logger

    def getLogger(name: str | None = None) -> Logger:  # noqa: N802
        """Return a logger registered with the stdlib manager, using the custom Logger class."""
        manager = _logging.Logger.manager
        # The manager only uses loggerClass for new loggers, so existing ones come back unchanged.
        with _logging._lock:  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            previous, manager.loggerClass = manager.loggerClass, Logger
            try:
                return _logging.getLogger(name)
            finally:
                manager.loggerClass = previous

    logger = getLogger("herogold")
    debug = logger.debug
    info = logger.info
    warning = logger.warning
    error = logger.error
    exception = logger.exception
    critical = logger.critical
    fatal = logger.fatal

from .config import log_directory, setup, teardown
from .formats import BASIC_FORMAT, formatter, message, prefix
from .handlers import stream_handler
from .logger_mixin import LoggerMixin

# Library convention: stay silent unless the application configures logging.
getLogger("herogold").addHandler(NullHandler())

__all__ = [
    "BASIC_FORMAT",
    "CRITICAL",
    "DEBUG",
    "ERROR",
    "FATAL",
    "INFO",
    "NOTSET",
    "WARNING",
    "BufferingFormatter",
    "FileHandler",
    "Filter",
    "Formatter",
    "Handler",
    "LogRecord",
    "Logger",
    "LoggerAdapter",
    "LoggerMixin",
    "NullHandler",
    "RootLogger",
    "StreamHandler",
    "addLevelName",
    "basicConfig",
    "captureWarnings",
    "critical",
    "debug",
    "disable",
    "error",
    "exception",
    "fatal",
    "formatter",
    "getHandlerByName",
    "getHandlerNames",
    "getLevelName",
    "getLevelNamesMapping",
    "getLogRecordFactory",
    "getLogger",
    "getLoggerClass",
    "info",
    "lastResort",
    "log",
    "log_directory",
    "makeLogRecord",
    "message",
    "prefix",
    "raiseExceptions",
    "setLogRecordFactory",
    "setLoggerClass",
    "setup",
    "shutdown",
    "stream_handler",
    "teardown",
    "warning",
]
