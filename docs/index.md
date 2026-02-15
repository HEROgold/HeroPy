# HeroPy

Personal utilities package providing type-safe configuration, ORM helpers, and development tools.

This landing page will help you navigate the documentation:

| Topic | Where to Go |
|-------|-------------|
| Run examples | [Examples section](examples/index.md) |
| Argument parsing with descriptors | [Argparse Reference](reference/argparse.md) |
| Database migrations | [ORM Reference](reference/orm.md) |
| Logic system (predicates, actions, triggers) | [Logic Reference](reference/logic.md) |
| API by symbol | [Generated API (pdoc)](pdoc:herogold) |
| Contribute / issues | [GitHub: HEROgold/HeroPy](https://github.com/HEROgold/HeroPy) |

---

## Quick Start

Install the package:

```bash
pip install herogold
```

For optional features:

```bash
# ORM and database features
pip install herogold[orm]

# API integration (FastAPI)
pip install herogold[api]

# Combined ORM + API
pip install herogold[orm-api]

# Documentation tools
pip install herogold[docs]

# Everything
pip install herogold[all]
```

---

## Features

### 🎯 Argument Parsing

OOP-style argument parsing with descriptors and subcommands:

```python
from herogold.argparse import Argument, SubCommand, Actions

class StartCommand(SubCommand):
    name = "start"
    port = Argument("port", type_=int, default=8000, help="Server port")
    debug = Argument("debug", action=Actions.STORE_BOOL, default=False)
    
    def execute(self, args):
        print(f"Starting on port {args.port}")
        return 0
```

See [Argparse Reference](reference/argparse.md) for details.

### 🗄️ ORM Migrations

Django/Laravel-style database migrations:

```python
from herogold.orm.migrations import Migration, create_migration

# Create a migration
create_migration("create_users_table")

# Run migrations
python -m herogold.orm.migrate_cli migrate
```

See [ORM Reference](reference/orm.md) for details.

### 🧠 Logic System

Composable predicates, actions, and triggers:

```python
from herogold.logic import Predicate, Action, Trigger

# Define predicates
is_valid = Predicate(lambda x: x > 0)
is_even = Predicate(lambda x: x % 2 == 0)

# Combine them
is_valid_even = is_valid & is_even

# Use in conditions
if is_valid_even(4):
    print("Valid and even!")
```

See [Logic Reference](reference/logic.md) for details.

---

## Examples

Explore focused example pages:

- [Argument Parsing](examples/arguments.md) - Descriptor-based CLI arguments
- [Subcommands](examples/subcommands.md) - OOP subcommand pattern
- [Migrations](examples/migrations.md) - Database schema management
- [Logic System](examples/logic.md) - Predicates, actions, and triggers

---

## Contributing

We welcome contributions! To contribute:

1. Fork the repository and clone locally
2. Install dependencies: `uv sync --group test`
3. Run tests: `pytest .`
4. Run linting: `ruff check .`
5. Make changes following existing patterns
6. Add tests for new functionality
7. Submit a pull request

### Building Documentation

```bash
# Install documentation dependencies
uv sync --group docs

# Generate API documentation with pdoc
uv run pdoc herogold -o docs/api

# Build documentation site
uv run mkdocs build

# Or serve locally for live preview
uv run mkdocs serve
```

Documentation is automatically built and deployed to GitHub Pages when changes are pushed to the `master` branch.

---

## Supported Python Versions

HeroPy follows the [Python version support policy](https://devguide.python.org/versions/):

- We support Python 3.12 and above
- End-of-life (EOL) Python versions are **not** supported
- We aim to support Python release candidates

This ensures compatibility with current Python versions while leveraging modern language features.

---

## API Reference

Two ways to explore the API:

### Curated Reference Pages

- [Argparse](reference/argparse.md) - Argument descriptors and subcommands
- [ORM](reference/orm.md) - Database models and migrations
- [Logic](reference/logic.md) - Predicates, actions, and triggers
- [Utilities](reference/utilities.md) - Helper functions and tools

### Full Symbol Index (pdoc)

[herogold API](pdoc:herogold)

Use `(pdoc:qual.name)` style links inside docs for deep, stable symbol links.

---

## Next Steps

Head to the [Usage Guide](usage.md) for patterns and best practices, or jump straight into an [Example](examples/index.md).
