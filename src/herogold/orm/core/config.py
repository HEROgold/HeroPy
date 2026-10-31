"""Module for configuration for the database package."""

from __future__ import annotations

from confkit import Config


class DbConfig[T](Config[T]):
    """Configuration namespace for database configuration."""
