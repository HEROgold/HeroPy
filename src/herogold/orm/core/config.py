"""Module for configuration for the database package."""
from pathlib import Path

from confkit import Config


class DbConfig[T](Config[T]):
    """Configuration namespace for database configuration."""

DbConfig.set_file(Path("db_config.ini"))
