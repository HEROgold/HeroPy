"""Package for logging utilities."""

from .formats import Formatter, formatter, message, prefix
from .handlers import FileHandler, StreamHandler, file_handler, stream_handler
from .logger_mixin import LoggerMixin
from .logging import INFO, basicConfig

basicConfig(
    level=INFO,
    handlers=[stream_handler, file_handler],
)

__all__ = [
    "FileHandler",
    "Formatter",
    "LoggerMixin",
    "StreamHandler",
    "file_handler",
    "formatter",
    "message",
    "prefix",
    "stream_handler",
]
