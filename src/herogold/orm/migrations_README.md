# Database Migrations

A Django and Laravel-inspired migration system for managing database schema changes.

## Features

- **Version Control for Database**: Track schema changes over time
- **Up/Down Migrations**: Apply and rollback changes safely
- **Batch Tracking**: Group migrations and rollback in batches
- **Timestamped Migrations**: Files named with `YYYYMMDD_name.py` format
- **CLI Tools**: Simple commands to create and manage migrations

## Installation

The migration system is included with the ORM package:

```bash
pip install herogold[orm]
```

## Quick Start

### 1. Create a Migration

```bash
python -m herogold.orm.migrate_cli migrate:make create_users_table
```

This creates a migration file like `migrations/20260215_create_users_table.py`:

```python
from sqlmodel import Session
from herogold.orm.migrations import Migration

class CreateUsersTable(Migration):
    """Migration for create users table."""

    def up(self, session: Session) -> None:
        """Apply the migration."""
        session.exec(text("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        session.commit()

    def down(self, session: Session) -> None:
        """Rollback the migration."""
        session.exec(text("DROP TABLE IF EXISTS users"))
        session.commit()
```

### 2. Run Migrations

```bash
python -m herogold.orm.migrate_cli migrate
```

### 3. Check Status

```bash
python -m herogold.orm.migrate_cli migrate:status
```

### 4. Rollback

```bash
python -m herogold.orm.migrate_cli migrate:rollback
```

## CLI Commands

### Create a Migration

```bash
python -m herogold.orm.migrate_cli migrate:make <name> [--dir migrations]
```

- `name`: Descriptive name for the migration (e.g., `create_users_table`)
- `--dir`: Directory to store migrations (default: `migrations`)

### Run Migrations

```bash
python -m herogold.orm.migrate_cli migrate [--dir migrations] [--target <migration_name>]
```

- `--dir`: Directory where migrations are stored
- `--target`: Run migrations up to a specific migration name

### Rollback Migrations

```bash
python -m herogold.orm.migrate_cli migrate:rollback [--dir migrations] [--steps 1]
```

- `--dir`: Directory where migrations are stored
- `--steps`: Number of batches to rollback (default: 1)

### Show Migration Status

```bash
python -m herogold.orm.migrate_cli migrate:status [--dir migrations]
```

Shows applied and pending migrations.

### Reset All Migrations

```bash
python -m herogold.orm.migrate_cli migrate:reset [--dir migrations]
```

Rolls back all migrations.

## Programmatic Usage

You can also use the migration system programmatically:

```python
from herogold.orm.migrations import MigrationManager, create_migration

# Create a new migration
migration_path = create_migration("add_users_age_column")

# Initialize the manager
manager = MigrationManager(migrations_dir="migrations")

# Run pending migrations
applied = manager.run_migrations()

# Check status
status = manager.status()
print(f"Applied: {status['applied']}")
print(f"Pending: {status['pending']}")

# Rollback last batch
rolled_back = manager.rollback(steps=1)
```

## Migration File Format

Migration files are named: `YYYYMMDD_description.py`

- `YYYYMMDD`: Date when the migration was created
- If multiple migrations are created on the same day, a sequence number is added: `YYYYMMDD_02_description.py`

## How It Works

1. **Migrations Table**: The system creates a `migrations` table to track which migrations have been applied
2. **Batch System**: Migrations run together are grouped in batches, making rollbacks safer
3. **Up/Down Methods**: Each migration has `up()` for applying changes and `down()` for reverting them
4. **Sequential Execution**: Migrations run in filename order (sorted alphabetically/chronologically)

## Best Practices

1. **One Change Per Migration**: Keep migrations focused on a single schema change
2. **Always Test Down**: Make sure your `down()` method properly reverts the `up()` changes
3. **Don't Modify Applied Migrations**: Once a migration is applied, create a new migration for changes
4. **Use Descriptive Names**: Name migrations clearly (e.g., `add_email_index_to_users`)
5. **Test on Dev First**: Always test migrations on development before production

## Example: Complete Migration

```python
"""Migration: add_user_roles

Created at: 2026-02-15T12:00:00Z
"""

from sqlalchemy import text
from sqlmodel import Session

from herogold.orm.migrations import Migration


class AddUserRoles(Migration):
    """Migration for adding user roles table and relationship."""

    def up(self, session: Session) -> None:
        """Apply the migration."""
        # Create roles table
        session.exec(text("""
            CREATE TABLE roles (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Add role_id to users table
        session.exec(text("""
            ALTER TABLE users 
            ADD COLUMN role_id INTEGER REFERENCES roles(id)
        """))
        
        # Insert default roles
        session.exec(text("""
            INSERT INTO roles (name) VALUES 
            ('admin'), ('user'), ('guest')
        """))
        
        session.commit()

    def down(self, session: Session) -> None:
        """Rollback the migration."""
        # Remove role_id column
        session.exec(text("ALTER TABLE users DROP COLUMN IF EXISTS role_id"))
        
        # Drop roles table
        session.exec(text("DROP TABLE IF EXISTS roles"))
        
        session.commit()
```

## Troubleshooting

### Migration Fails Partway Through

If a migration fails, it will be rolled back automatically. Fix the issue in the migration file and run again.

### Migration File Missing

If you deleted a migration file that was applied, the system will warn you and remove it from the tracking table during rollback.

### Out of Sync

If your database and migration tracking get out of sync, you can:

1. Use `migrate:reset` to rollback everything
2. Manually fix the `migrations` table in the database
3. Re-run migrations from a clean state

## Integration with Models

The migration system works alongside your SQLModel models:

```python
from herogold.orm.model import BaseModel
from sqlmodel import Field

class User(BaseModel, table=True):
    """User model."""
    
    name: str
    email: str = Field(unique=True)
    role_id: int | None = None
```

Use migrations to create the actual database tables for your models.
