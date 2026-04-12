"""Module that helps setting up logging configurations."""

from __future__ import annotations

from logging import (
    INFO,
    StreamHandler,
)

from .formats import formatter

stream_handler = StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(INFO)
