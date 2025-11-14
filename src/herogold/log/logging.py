"""Pass-through of logging module, with custom Logger patches."""

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
    getLevelName,
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

from .formats import message, prefix

# Patch logging for Python 3.14+
if sys.version_info >= (3, 14):  # noqa: UP036
    from .logger import Logger
    logger = Logger("root")
    debug = logger.debug
    info = logger.info
    warning = logger.warning
    error = logger.error
    exception = logger.exception
    critical = logger.critical
    fatal = logger.fatal

BASIC_FORMAT = f"{prefix} {message}"

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
    "raiseExceptions",
    "setLogRecordFactory",
    "setLoggerClass",
    "shutdown",
    "warning",
]
