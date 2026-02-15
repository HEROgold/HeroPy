# ORM Reference

Database models and Django/Laravel-style migrations.

---

## Overview

The [`herogold.orm`](pdoc:herogold.orm) module provides:

- **Base models** with common fields and methods
- **Migration system** for schema versioning
- **CLI tools** for migration management
- **SQLModel integration** for type-safe queries

For detailed migration guides, see [Migrations Example](../examples/migrations.md).

---

## Key Classes

### Migration

[`Migration`](pdoc:herogold.orm.migrations.Migration) - Base class for database migrations.

**Abstract Methods:**
```python
def up(self, session: Session) -> None:
    """Apply the migration."""
    ...

def down(self, session: Session) -> None:
    """Rollback the migration."""
    ...
```

**Example:**
```python
from sqlalchemy import text
from herogold.orm.migrations import Migration

class CreateUsersTable(Migration):
    def up(self, session):
        session.exec(text("CREATE TABLE users (...)"))
        session.commit()
    
    def down(self, session):
        session.exec(text("DROP TABLE users"))
        session.commit()
```

### MigrationManager

[`MigrationManager`](pdoc:herogold.orm.migrations.MigrationManager) - Orchestrates migration execution.

**Usage:**
```python
from herogold.orm.migrations import MigrationManager

manager = MigrationManager(migrations_dir="migrations")

# Check status
status = manager.status()
print(status['applied'], status['pending'])

# Run migrations
applied = manager.run_migrations()

# Rollback
rolled_back = manager.rollback(steps=1)
```

**Methods:**
- [`run_migrations(target=None)`](pdoc:herogold.orm.migrations.MigrationManager.run_migrations) - Run pending migrations
- [`rollback(steps=1)`](pdoc:herogold.orm.migrations.MigrationManager.rollback) - Rollback N batches
- [`status()`](pdoc:herogold.orm.migrations.MigrationManager.status) - Get migration status
- [`get_applied_migrations()`](pdoc:herogold.orm.migrations.MigrationManager.get_applied_migrations) - List applied
- [`get_pending_migrations()`](pdoc:herogold.orm.migrations.MigrationManager.get_pending_migrations) - List pending

### MigrationRecord

[`MigrationRecord`](pdoc:herogold.orm.migrations.MigrationRecord) - Tracks applied migrations in database.

**Fields:**
- `name`: Migration filename
- `batch`: Batch number when applied
- `applied_at`: Timestamp of application

### BaseModel

[`BaseModel`](pdoc:herogold.orm.model.BaseModel) - Base class for database models.

**Built-in Fields:**
- `id`: Primary key (auto-increment)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Methods:**
- [`add()`](pdoc:herogold.orm.model.BaseModel.add) - Insert record
- [`update()`](pdoc:herogold.orm.model.BaseModel.update) - Update record
- [`delete()`](pdoc:herogold.orm.model.BaseModel.delete) - Delete record
- [`get(id)`](pdoc:herogold.orm.model.BaseModel.get) - Get by ID
- [`get_all()`](pdoc:herogold.orm.model.BaseModel.get_all) - Get all records

---

## CLI Commands

### Create Migration

```bash
python -m herogold.orm.migrate_cli migrate:make <name> [--dir migrations]
```

### Run Migrations

```bash
python -m herogold.orm.migrate_cli migrate [--target <name>] [--dir migrations]
```

### Rollback

```bash
python -m herogold.orm.migrate_cli migrate:rollback [--steps N] [--dir migrations]
```

### Status

```bash
python -m herogold.orm.migrate_cli migrate:status [--dir migrations]
```

### Reset

```bash
python -m herogold.orm.migrate_cli migrate:reset [--dir migrations]
```

---

## Functions

### create_migration

[`create_migration(name, migrations_dir="migrations")`](pdoc:herogold.orm.migrations.create_migration)

Creates a new migration file with timestamp.

**Parameters:**
- `name`: Migration description (e.g., "add_user_email")
- `migrations_dir`: Directory for migration files

**Returns:** Path to created migration file

**Example:**
```python
from herogold.orm.migrations import create_migration

path = create_migration("add_user_status_field")
# Creates: migrations/20260215_add_user_status_field.py
```

---

## Common Patterns

### Model Definition

```python
from herogold.orm.model import BaseModel
from sqlmodel import Field

class User(BaseModel, table=True):
    email: str = Field(unique=True)
    name: str
    is_active: bool = Field(default=True)
```

### Data Migration

```python
class MigrateUserStatus(Migration):
    def up(self, session):
        # Update existing data
        session.exec(text("""
            UPDATE users 
            SET status = 'active' 
            WHERE is_active = true
        """))
        session.commit()
    
    def down(self, session):
        session.exec(text("UPDATE users SET status = NULL"))
        session.commit()
```

### Programmatic Migrations

```python
from pathlib import Path
from herogold.orm.migrations import MigrationManager, create_migration

# Setup
migrations_dir = Path("db/migrations")
manager = MigrationManager(migrations_dir=migrations_dir)

# Create
create_migration("add_indexes", migrations_dir)

# Run
if manager.get_pending_migrations():
    applied = manager.run_migrations()
    print(f"Applied {len(applied)} migrations")
```

---

## See Also

- [Examples: Migrations](../examples/migrations.md)
- [Full API](pdoc:herogold.orm)
