"""Module with custom exceptions for the database package."""

from __future__ import annotations

from herogold.errors import HerogoldError


class NotFoundError(HerogoldError, ValueError):
    """Custom exception for records not found in the database."""


class AlreadyExistsError(HerogoldError, ValueError):
    """Custom exception for already existing records in the database."""
