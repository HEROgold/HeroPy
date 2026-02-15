# Database Migrations Example

## Purpose

Demonstrates Django/Laravel-style database migrations:

- Creating migration files with timestamps
- Implementing `up()` and `down()` methods
- Running and rolling back migrations
- Tracking migration status
- Batch management

## Setup

Install with ORM support:

```bash
pip install herogold[orm]
```

## Creating a Migration

```bash
python -m herogold.orm.migrate_cli migrate:make create_users_table
```

Creates `migrations/YYYYMMDD_create_users_table.py`:

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

## Running Migrations

```bash
# Run all pending migrations
python -m herogold.orm.migrate_cli migrate

# Run up to specific migration
python -m herogold.orm.migrate_cli migrate --target 20260215_create_users

# Check status
python -m herogold.orm.migrate_cli migrate:status

# Rollback last batch
python -m herogold.orm.migrate_cli migrate:rollback

# Rollback multiple batches
python -m herogold.orm.migrate_cli migrate:rollback --steps 2

# Reset all
python -m herogold.orm.migrate_cli migrate:reset
```

## Migration File Format

Files are named: `YYYYMMDD_description.py`

- `YYYYMMDD`: Date when created
- Multiple migrations same day: `YYYYMMDD_02_description.py`
- Migrations run in alphabetical (chronological) order

## Programmatic Usage

```python
from herogold.orm.migrations import MigrationManager, create_migration

# Create migration
migration_path = create_migration("add_user_email_index")

# Initialize manager
manager = MigrationManager(migrations_dir="migrations")

# Check status
status = manager.status()
print(f"Applied: {status['applied']}")
print(f"Pending: {status['pending']}")

# Run migrations
applied = manager.run_migrations()
for name in applied:
    print(f"Applied: {name}")

# Rollback
rolled_back = manager.rollback(steps=1)
```

## Complete Example

```python
from sqlalchemy import text
from sqlmodel import Session
from herogold.orm.migrations import Migration

class AddUserRoles(Migration):
    """Add user roles table and relationship."""

    def up(self, session: Session) -> None:
        # Create roles table
        session.exec(text("""
            CREATE TABLE roles (
                id SERIAL PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL
            )
        """))
        
        # Add role_id to users
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
        session.exec(text("ALTER TABLE users DROP COLUMN role_id"))
        session.exec(text("DROP TABLE roles"))
        session.commit()
```

## Try Variations

- Create multiple migrations and run them
- Test rollback functionality
- Implement data migrations (not just schema)
- Add indexes or constraints

## Key Takeaways

- Migrations are tracked in a database table
- Batch system allows safe rollbacks
- Always implement `down()` for reversibility
- Use descriptive names for clarity
- Test migrations on development data first
