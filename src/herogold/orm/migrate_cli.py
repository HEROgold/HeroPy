"""CLI commands for managing database migrations.

Provides command-line interface for creating, running, and rolling back migrations.
"""

import sys
from argparse import ArgumentParser, Namespace

from herogold.argparse import Argument, SubCommand, SubCommandGroup
from herogold.orm.migrations import MigrationManager, create_migration


class MigrateMakeCommand(SubCommand):
    """Create a new migration file."""

    name = "migrate:make"
    help = "Create a new migration file"

    migration_name = Argument(
        "name",
        help="Name of the migration (e.g., create_users_table)",
    )
    migrations_dir = Argument(
        "dir",
        default="migrations",
        help="Directory to store migrations",
    )

    def execute(self, args: Namespace) -> int:
        """Execute the migrate:make command."""
        try:
            create_migration(args.name, args.dir)
            return 0
        except Exception:
            return 1


class MigrateCommand(SubCommand):
    """Run pending migrations."""

    name = "migrate"
    help = "Run pending migrations"

    migrations_dir = Argument(
        "dir",
        default="migrations",
        help="Directory where migrations are stored",
    )
    target = Argument(
        "target",
        default=None,
        help="Run migrations up to this specific migration name",
    )

    def execute(self, args: Namespace) -> int:
        """Execute the migrate command."""
        try:
            manager = MigrationManager(migrations_dir=args.dir)
            manager.run_migrations(target=args.target)
            return 0
        except Exception:
            return 1


class MigrateRollbackCommand(SubCommand):
    """Rollback the last batch of migrations."""

    name = "migrate:rollback"
    help = "Rollback the last batch of migrations"

    migrations_dir = Argument(
        "dir",
        default="migrations",
        help="Directory where migrations are stored",
    )
    steps = Argument(
        "steps",
        type_=int,
        default=1,
        help="Number of batches to rollback",
    )

    def execute(self, args: Namespace) -> int:
        """Execute the migrate:rollback command."""
        try:
            manager = MigrationManager(migrations_dir=args.dir)
            manager.rollback(steps=args.steps)
            return 0
        except Exception:
            return 1


class MigrateStatusCommand(SubCommand):
    """Show migration status."""

    name = "migrate:status"
    help = "Show migration status"

    migrations_dir = Argument(
        "dir",
        default="migrations",
        help="Directory where migrations are stored",
    )

    def execute(self, args: Namespace) -> int:
        """Execute the migrate:status command."""
        try:
            manager = MigrationManager(migrations_dir=args.dir)
            manager.status()
            return 0
        except Exception:
            return 1


class MigrateResetCommand(SubCommand):
    """Rollback all migrations."""

    name = "migrate:reset"
    help = "Rollback all migrations"

    migrations_dir = Argument(
        "dir",
        default="migrations",
        help="Directory where migrations are stored",
    )

    def execute(self, args: Namespace) -> int:
        """Execute the migrate:reset command."""
        try:
            manager = MigrationManager(migrations_dir=args.dir)
            applied = manager.get_applied_migrations()
            if applied:
                max_batch = max(record.batch for record in applied)
                manager.rollback(steps=max_batch)
            return 0
        except Exception:
            return 1


def main() -> int:
    """Main entry point for the migration CLI."""
    parser = ArgumentParser(prog="herogold-migrate", description="Database migration management tool")
    
    commands = SubCommandGroup(parser)
    commands.add_commands(
        MigrateMakeCommand,
        MigrateCommand,
        MigrateRollbackCommand,
        MigrateStatusCommand,
        MigrateResetCommand,
    )
    
    args = parser.parse_args()
    return commands.execute(args)


if __name__ == "__main__":
    sys.exit(main())
