"""Module that contains some formatting presets."""
from logging import Formatter

stream_format = "[ %(levelname)s ]: %(message)s"
file_prefix = "< %(asctime)s > %(name)s"
formatter = Formatter(f"{file_prefix} {stream_format}")
