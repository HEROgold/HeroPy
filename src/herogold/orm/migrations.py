"""Migration system for database schema changes.

Provides tools to create, track, and execute database migrations similar to Django and Laravel.
"""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from sqlmodel import Field, Session, col, select

from herogold.log import LoggerMixin

from .constants import engine
from .constants import session as db_session
from .model import BaseModel


class Migration(ABC, LoggerMixin):
    """Base class for database migrations.

    Each migration should inherit from this class and implement the up() and down() methods.
    """

    name: str
    """The name of the migration (derived from filename)."""

    def __init__(self) -> None:
        """Initialize the migration."""
        super().__init__()

    @abstractmethod
    def up(self, session: Session) -> None:
        """Apply the migration.

        Args:
            session: Database session to use for executing SQL commands.

        """
        ...

    @abstractmethod
    def down(self, session: Session) -> None:
        """Rollback the migration.

        Args:
            session: Database session to use for executing SQL commands.

        """
        ...


class MigrationRecord(BaseModel, table=True):
    """Model for tracking applied migrations in the database."""

    name: str = Field(unique=True, index=True, nullable=False)
    """The name of the migration file."""

    batch: int = Field(default=1)
    """The batch number when the migration was run."""

    applied_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """Timestamp when the migration was applied."""

    session: ClassVar[Session] = db_session


class MigrationManager(LoggerMixin):
    """Manages database migrations including running, rolling back, and tracking."""

    def __init__(
        self,
        migrations_dir: Path | str = "migrations",
        session: Session | None = None,
    ) -> None:
        """Initialize the migration manager.

        Args:
            migrations_dir: Directory where migration files are stored.
            session: Database session to use. If None, uses the default session.

        """
        super().__init__()
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(exist_ok=True)
        self.session = session or db_session
        self._ensure_migrations_table()

    def _ensure_migrations_table(self) -> None:
        """Ensure the migrations tracking table exists."""
        from sqlmodel import SQLModel  # noqa: PLC0415

        SQLModel.metadata.create_all(engine, tables=[MigrationRecord.__table__])  # type: ignore[attr-defined]

    def get_applied_migrations(self) -> list[MigrationRecord]:
        """Get all applied migrations from the database, ordered by batch and name."""
        statement = select(MigrationRecord).order_by(col(MigrationRecord.batch), col(MigrationRecord.name))
        return list(self.session.exec(statement).all())

    def get_pending_migrations(self) -> list[Path]:
        """Get list of migration files that haven't been applied yet."""
        applied = {record.name for record in self.get_applied_migrations()}
        return [
            path for path in sorted(self.migrations_dir.glob("*.py"))
            if path.stem != "__init__" and path.stem not in applied
        ]

    def get_last_batch(self) -> int:
        """Get the last batch number, or 0 if no migrations have been applied."""
        return max((record.batch for record in self.get_applied_migrations()), default=0)

    def run_migrations(self, *, target: str | None = None) -> list[str]:
        """Run pending migrations, optionally up to a specific target."""
        pending = self.get_pending_migrations()
        if not pending:
            return []

        batch = self.get_last_batch() + 1
        applied_migrations: list[str] = []

        for migration_path in pending:
            migration_name = migration_path.stem
            try:
                migration_instance = self._load_migration(migration_path)
                migration_instance.up(self.session)

                record = MigrationRecord(name=migration_name, batch=batch)
                self.session.add(record)
                self.session.commit()

                applied_migrations.append(migration_name)
                self.logger.info("Applied migration: %s", migration_name)

                if target == migration_name:
                    break
            except Exception:
                self.logger.exception("Failed to run migration %s", migration_name)
                self.session.rollback()
                raise

        return applied_migrations

    def rollback(self, *, steps: int = 1) -> list[str]:
        """Rollback the last N batch(es) of migrations."""
        applied = self.get_applied_migrations()
        if not applied:
            return []

        batches_to_rollback = sorted({record.batch for record in applied}, reverse=True)[:steps]
        migrations_to_rollback = [r for r in reversed(applied) if r.batch in batches_to_rollback]
        rolled_back: list[str] = []

        for record in migrations_to_rollback:
            migration_path = self.migrations_dir / f"{record.name}.py"

            if not migration_path.exists():
                self.logger.warning("Migration file not found: %s", record.name)
                self.session.delete(record)
                self.session.commit()
                continue

            try:
                migration_instance = self._load_migration(migration_path)
                migration_instance.down(self.session)

                self.session.delete(record)
                self.session.commit()

                rolled_back.append(record.name)
                self.logger.info("Rolled back migration: %s", record.name)
            except Exception:
                self.logger.exception("Failed to rollback migration %s", record.name)
                self.session.rollback()
                raise

        return rolled_back

    def _load_migration(self, migration_path: Path) -> Migration:
        """Load a migration class from a file."""
        import importlib.util  # noqa: PLC0415
        import sys  # noqa: PLC0415

        spec = importlib.util.spec_from_file_location(migration_path.stem, migration_path)
        if not spec or not spec.loader:
            msg = f"Cannot load migration from {migration_path}"
            raise ImportError(msg)

        module = importlib.util.module_from_spec(spec)
        sys.modules[migration_path.stem] = module
        spec.loader.exec_module(module)

        for attr in (getattr(module, name) for name in dir(module)):
            if isinstance(attr, type) and issubclass(attr, Migration) and attr is not Migration:
                instance = attr()
                instance.name = migration_path.stem
                return instance

        msg = f"No Migration subclass found in {migration_path}"
        raise ValueError(msg)

    def status(self) -> dict[str, list[str]]:
        """Get the current migration status with 'applied' and 'pending' lists."""
        return {
            "applied": [r.name for r in self.get_applied_migrations()],
            "pending": [p.stem for p in self.get_pending_migrations()],
        }


def create_migration(name: str, migrations_dir: Path | str = "migrations") -> Path:
    """Create a new migration file with timestamp format: YYYYMMDD_name.py."""
    migrations_path = Path(migrations_dir)
    migrations_path.mkdir(exist_ok=True)

    init_file = migrations_path / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Database migrations."""\n')

    timestamp = datetime.now(UTC).strftime("%Y%m%d")
    existing = list(migrations_path.glob(f"{timestamp}_*.py"))
    sequence = len(existing) + 1

    filename = f"{timestamp}_{sequence:02d}_{name}.py" if sequence > 1 else f"{timestamp}_{name}.py"
    migration_path = migrations_path / filename

    template = f'''"""Migration: {name}

Created: {datetime.now(UTC).isoformat()}
"""
from sqlmodel import Session
from herogold.orm.migrations import Migration


class {_to_class_name(name)}(Migration):
    """Migration for {name.replace('_', ' ')}."""

    def up(self, session: Session) -> None:
        """Apply the migration."""
        # Example: session.exec(text("CREATE TABLE ..."))
        # session.commit()
        pass

    def down(self, session: Session) -> None:
        """Rollback the migration."""
        # Example: session.exec(text("DROP TABLE IF EXISTS ..."))
        # session.commit()
        pass
'''
    migration_path.write_text(template)

    return migration_path


def _to_class_name(name: str) -> str:
    """Convert snake_case to PascalCase (e.g., 'create_users' -> 'CreateUsers')."""
    return "".join(word.capitalize() for word in name.split("_"))
