"""Module that helps setting up logging configurations."""

from logging import (
    DEBUG,
    INFO,
    FileHandler,
    StreamHandler,
    getLogger,
)

from .formats import formatter

logger = getLogger()

stream_handler = StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(INFO)

file_handler = FileHandler(__name__, mode="w")
file_handler.setFormatter(formatter)
file_handler.setLevel(DEBUG)
