"""Module with custom exceptions for the database package."""

from __future__ import annotations

from herogold.errors import HerogoldError


class NotFoundError(HerogoldError, ValueError):
    """Custom exception for records not found in the database."""


class AlreadyExistsError(HerogoldError, ValueError):
    """Custom exception for already existing records in the database."""


class PermissionDeniedError(HerogoldError):
    """Raised when a user lacks a required permission."""


class RelationshipConfigurationError(HerogoldError):
    """Raised by ``configure()`` when relationships cannot be paired or stored unambiguously."""

    def __init__(self, errors: dict[str, str]) -> None:
        """Keep every message, keyed by ``Owner.attribute``, and join them into the exception text."""
        super().__init__("\n".join(errors.values()))
        self.errors = errors
        """Message per failing relationship, keyed by ``Owner.attribute``."""
