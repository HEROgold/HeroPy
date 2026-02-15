# HeroPy

Personal utilities package providing type-safe configuration, ORM helpers, and development tools.

**Full documentation:** [HeroPy docs](https://HEROgold.github.io/HeroPy/)

---

## Features

### 🎯 Argument Parsing
OOP-style argument parsing with descriptors and subcommands

### 🗄️ ORM & Migrations  
Django/Laravel-style database migrations with SQLModel

### 🧠 Logic System
Composable predicates, actions, and triggers for business logic

### 🛠️ Utilities
Common helpers: sentinels, logging mixins, color constants

---

## Installation

```bash
# Basic installation
pip install herogold

# With ORM support
pip install herogold[orm]

# With API support (FastAPI)
pip install herogold[api]

# Combined ORM + API
pip install herogold[orm-api]

# Everything
pip install herogold[all]
```

---

## Quick Examples

### Argument Parsing

```python
from herogold.argparse import Argument, SubCommand, Actions

class StartCommand(SubCommand):
    name = "start"
    port = Argument("port", type_=int, default=8000)
    debug = Argument("debug", action=Actions.STORE_BOOL, default=False)
    
    def execute(self, args):
        print(f"Starting on port {args.port}")
        return 0
```

### Database Migrations

```bash
# Create a migration
python -m herogold.orm.migrate_cli migrate:make create_users_table

# Run migrations
python -m herogold.orm.migrate_cli migrate

# Check status
python -m herogold.orm.migrate_cli migrate:status
```

### Logic System

```python
from herogold.logic import Predicate, predicate

@predicate
def is_even(x: int) -> bool:
    return x % 2 == 0

@predicate
def is_positive(x: int) -> bool:
    return x > 0

# Compose predicates
is_positive_even = is_positive & is_even

if is_positive_even(4):
    print("Positive and even!")
```

---

## Documentation

👉 **[Full Documentation Site](https://HEROgold.github.io/HeroPy/)**

Direct links:
- [Usage Guide](https://HEROgold.github.io/HeroPy/usage) - Patterns and best practices
- [Examples](https://HEROgold.github.io/HeroPy/examples) - Runnable code examples
- [API Reference](https://HEROgold.github.io/HeroPy/reference) - Complete API docs

---

## Supported Python Versions

HeroPy supports Python 3.12 and above, following the [Python version support policy](https://devguide.python.org/versions/):

- ✅ Active and maintenance Python releases
- ❌ End-of-life (EOL) versions not supported
- 🔄 Release candidates supported when available

---

## Contributing

We welcome contributions! To contribute:

1. Fork and clone the repository
2. Install dependencies: `uv sync --group test`
3. Run tests: `pytest .`
4. Run linting: `ruff check .`
5. Make changes following existing patterns
6. Add tests for new functionality
7. Submit a pull request

### Building Documentation

```bash
# Install doc dependencies
uv sync --group docs

# Generate API docs
uv run pdoc herogold -o docs/api

# Build docs site
uv run mkdocs build

# Serve for live preview
uv run mkdocs serve
```

---

## License

MIT License - see LICENSE file for details

---

## Links

- **Documentation:** https://HEROgold.github.io/HeroPy/
- **Repository:** https://github.com/HEROgold/HeroPy
- **Issues:** https://github.com/HEROgold/HeroPy/issues
