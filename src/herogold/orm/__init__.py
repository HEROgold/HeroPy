"""The ORM package."""

from __future__ import annotations

try:
    import confkit
    import sqlmodel
except ImportError as e:
    msg = (
        "Failed to import required dependencies for the database package. "
        "Please ensure that 'orm' extra is installed. "
        "You can install them using 'herogold[orm]'."
    )
    raise ImportError(msg) from e

__all__ = [
    "confkit",
    "sqlmodel",
]
