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
    LoggerAdapter,
    LogRecord,
    NullHandler,
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
    import logging
    from typing import cast

    from .logger import Logger, RootLogger

    # Register the class so the manager builds, caches and parents our Logger.
    setLoggerClass(Logger)
    # Give the existing root logger t-string support without replacing it.
    # The module-level debug, info, ... helpers log through it, so they accept t-strings too.
    logging.root.__class__ = RootLogger

    def getLogger(name: str | None = None) -> Logger:  # noqa: N802
        """Return the logger with this name, typed as herogold's Logger."""
        # Loggers created before herogold.log was imported are still stdlib Loggers.
        return cast("Logger", logging.getLogger(name))
else:
    from logging import Logger, RootLogger, getLogger


from .formats import BASIC_FORMAT, formatter, message, prefix
from .handlers import stream_handler
from .logger_mixin import LoggerMixin

basicConfig(
    format=BASIC_FORMAT,
    level=INFO,
    handlers=[stream_handler],
)

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
    "makeLogRecord",
    "message",
    "prefix",
    "raiseExceptions",
    "setLogRecordFactory",
    "setLoggerClass",
    "shutdown",
    "stream_handler",
    "warning",
]
