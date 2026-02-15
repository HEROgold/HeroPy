# Usage Guide

This page explains common patterns and best practices when using HeroPy.

---

## Argument Parsing

### Basic Descriptor Usage

```python
from argparse import ArgumentParser, Namespace
from herogold.argparse import Argument, Actions

class Config(Namespace):
    port = Argument("port", type_=int, default=8000, help="Server port")
    debug = Argument("debug", action=Actions.STORE_BOOL, default=False, help="Debug mode")
    host = Argument("host", default="localhost", help="Host address")

parser = ArgumentParser()
args = parser.parse_args(namespace=Config())

print(f"Server: {args.host}:{args.port}")
print(f"Debug: {args.debug}")
```

### Subcommand Pattern

```python
from herogold.argparse import SubCommand, SubCommandGroup

class MigrateCommand(SubCommand):
    name = "migrate"
    help = "Run database migrations"
    
    target = Argument("target", default=None, help="Target migration")
    
    def execute(self, args):
        print(f"Running migrations to {args.target or 'latest'}")
        return 0

# In your main function
parser = ArgumentParser(prog="myapp")
commands = SubCommandGroup(parser)
commands.add_commands(MigrateCommand)

args = parser.parse_args()
return commands.execute(args)
```

---

## Database Migrations

### Creating Migrations

```python
from herogold.orm.migrations import create_migration

# Create a new migration file
migration_path = create_migration("add_user_email_column")
# Creates: migrations/YYYYMMDD_add_user_email_column.py
```

### Writing Migration Logic

```python
from sqlmodel import Session
from sqlalchemy import text
from herogold.orm.migrations import Migration

class AddUserEmailColumn(Migration):
    """Add email column to users table."""
    
    def up(self, session: Session) -> None:
        """Apply the migration."""
        session.exec(text("""
            ALTER TABLE users 
            ADD COLUMN email VARCHAR(255) UNIQUE
        """))
        session.commit()
    
    def down(self, session: Session) -> None:
        """Rollback the migration."""
        session.exec(text("ALTER TABLE users DROP COLUMN email"))
        session.commit()
```

### Running Migrations

```bash
# Run all pending migrations
python -m herogold.orm.migrate_cli migrate

# Run migrations up to a specific migration
python -m herogold.orm.migrate_cli migrate --target 20260215_add_email

# Check migration status
python -m herogold.orm.migrate_cli migrate:status

# Rollback last batch
python -m herogold.orm.migrate_cli migrate:rollback

# Rollback multiple batches
python -m herogold.orm.migrate_cli migrate:rollback --steps 3

# Reset all migrations
python -m herogold.orm.migrate_cli migrate:reset
```

### Programmatic Migration Control

```python
from herogold.orm.migrations import MigrationManager

# Initialize manager
manager = MigrationManager(migrations_dir="migrations")

# Check status
status = manager.status()
print(f"Applied: {status['applied']}")
print(f"Pending: {status['pending']}")

# Run migrations
applied = manager.run_migrations()
for migration in applied:
    print(f"Applied: {migration}")

# Rollback
rolled_back = manager.rollback(steps=1)
```

---

## Logic System

### Predicates

Predicates are callable wrappers for boolean functions:

```python
from herogold.logic import Predicate, predicate

# Direct creation
is_positive = Predicate(lambda x: x > 0)

# Using decorator
@predicate
def is_even(x: int) -> bool:
    return x % 2 == 0

# Combine predicates
is_positive_even = is_positive & is_even
is_positive_or_even = is_positive | is_even
is_negative = ~is_positive

# Use them
if is_positive_even(4):
    print("Positive and even!")
```

### Partial Application

```python
@predicate
def greater_than(x: int, threshold: int) -> bool:
    return x > threshold

# Create partial predicate
gt_10 = greater_than(threshold=10)

# Use it
if gt_10(15):
    print("Greater than 10!")
```

### Actions

Actions are callable wrappers for side-effect functions:

```python
from herogold.logic import Action, action

@action
def log_message(message: str) -> None:
    print(f"[LOG] {message}")

@action
def send_email(to: str, subject: str) -> None:
    print(f"Sending email to {to}: {subject}")

# Execute actions
log_message("System started")
send_email("admin@example.com", "Alert")
```

### Triggers

Triggers combine predicates and actions:

```python
from herogold.logic import Trigger

# Define trigger
error_trigger = Trigger(
    predicate=is_error,
    action=send_alert,
)

# Execute trigger
result = error_trigger(error_code)
# Returns: (predicate_result, action_result)
```

---

## Utilities

### Sentinel Values

```python
from herogold.sentinel import MISSING

def function(value=MISSING):
    if value is MISSING:
        print("No value provided")
    else:
        print(f"Value: {value}")
```

### Rainbow Colors

```python
from herogold.rainbow import RAINBOW

for color in RAINBOW:
    print(f"Color: {color}")
```

### Logger Mixin

```python
from herogold.log import LoggerMixin

class MyClass(LoggerMixin):
    def do_something(self):
        self.logger.info("Doing something")
        self.logger.error("An error occurred")
```

---

## Best Practices

### Migrations

1. **One change per migration** - Keep migrations focused on a single schema change
2. **Always implement `down()`** - Ensure rollbacks work correctly
3. **Test migrations** - Test both up and down on development data
4. **Never modify applied migrations** - Create a new migration instead
5. **Use descriptive names** - `add_email_to_users` not `update_users`

### Argument Parsing

1. **Group related arguments** - Use subcommands for logical grouping
2. **Provide help text** - Always add helpful descriptions
3. **Use type hints** - Specify `type_=int`, etc. for validation
4. **Set sensible defaults** - Make CLIs user-friendly

### Logic System

1. **Keep predicates pure** - No side effects in predicates
2. **Name predicates clearly** - Use `is_*` or `has_*` patterns
3. **Compose complex logic** - Build complex predicates from simple ones
4. **Test edge cases** - Especially with combined predicates

---

## Regenerating API Docs

The documentation uses both `mkdocstrings` and `mkdocs-pdoc-plugin` for API references:

```bash
# Regenerate API docs
uv run pdoc herogold -o docs/api --force

# Build the site
uv run mkdocs build

# Serve for live preview
uv run mkdocs serve
```

The `--force` flag overwrites existing output. The pdoc plugin enables `(pdoc:herogold.module.Class)` links in Markdown.

---

## Next Steps

- Explore [Examples](examples/index.md) for practical use cases
- Check [Reference](reference/index.md) for detailed API documentation
- Visit the [GitHub repository](https://github.com/HEROgold/HeroPy) to contribute
