"""Module that helps setting up logging configurations."""

from __future__ import annotations

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

file_handler = FileHandler("logs.log", mode="w")
file_handler.setFormatter(formatter)
file_handler.setLevel(DEBUG)
