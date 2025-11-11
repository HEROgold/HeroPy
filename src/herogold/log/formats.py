"""Module that contains some formatting presets."""
from logging import Formatter

prefix = "< %(asctime)s > %(name)s"
message = "[ %(levelname)s ]: %(message)s"
date_format = "%Y-%m-%d %H:%M:%S:%f"
formatter = Formatter(f"{prefix} {message}", datefmt=date_format)
