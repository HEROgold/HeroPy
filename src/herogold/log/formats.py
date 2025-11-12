"""Module that contains some formatting presets."""
from logging import Formatter

# https://docs.python.org/2/library/logging.html#logrecord-attributes

prefix = "< %(asctime)s > %(name)s"
message = "[ %(levelname)s ]: %(message)s"
date_format = "%Y-%m-%d %H:%M:%S.%(msecs)03d"
formatter = Formatter(f"{prefix} {message}", datefmt=date_format)
