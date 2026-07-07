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
    from .logger import Logger

    logger = Logger("root")
    getLogger = logger.getChild  # noqa: N816
    debug = logger.debug
    info = logger.info
    warning = logger.warning
    error = logger.error
    exception = logger.exception
    critical = logger.critical
    fatal = logger.fatal

from .formats import BASIC_FORMAT, formatter, message, prefix
from .handlers import stream_handler
from .logger_mixin import LoggerMixin

basicConfig(
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
    "Formatter",
    "Formatter",
    "Handler",
    "LogRecord",
    "Logger",
    "LoggerAdapter",
    "LoggerMixin",
    "NullHandler",
    "RootLogger",
    "StreamHandler",
    "StreamHandler",
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
