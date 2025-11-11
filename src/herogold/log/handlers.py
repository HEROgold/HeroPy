"""Module that helps setting up logging configurations."""

import logging
from logging import (
    DEBUG,
    INFO,
    FileHandler,
    StreamHandler,
)

from .formats import formatter

stream_handler = StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(INFO)

file_handler = FileHandler(__name__, mode="w")
file_handler.setFormatter(formatter)
file_handler.setLevel(DEBUG)

logging.basicConfig(
    level=INFO,
    handlers=[stream_handler, file_handler],
)
