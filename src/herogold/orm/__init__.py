"""The database package for the Winter Dragon project."""

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

from .migrations import Migration, MigrationManager, MigrationRecord, create_migration

__all__ = [
    "Migration",
    "MigrationManager",
    "MigrationRecord",
    "confkit",
    "create_migration",
    "sqlmodel",
]
