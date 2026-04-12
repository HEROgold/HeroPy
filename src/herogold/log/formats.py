"""Module that contains some formatting presets."""

from __future__ import annotations

from logging import Formatter

# https://docs.python.org/2/library/logging.html#logrecord-attributes

prefix = "< %(asctime)s.%(msecs)03d > %(name)s"
message = "[ %(levelname)s ]: %(message)s"
BASIC_FORMAT = f"{prefix} {message}"
date_format = "%Y-%m-%d %H:%M:%S"
formatter = Formatter(BASIC_FORMAT, datefmt=date_format)
