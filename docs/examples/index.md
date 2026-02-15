# Examples Overview

This section provides runnable examples demonstrating how to use **HeroPy** in different scenarios. Each example page includes:

- Purpose & concepts demonstrated
- Required setup (if any)
- How to run the example
- Code walkthrough
- Notes & variations you can try

---

## Quick Start: Running Examples

All examples assume you are in the project root:

```bash
# Run an example
python examples/arguments.py --help

# Or with subcommands
python examples/subcommands.py start --port 8080

# Migration CLI
python -m herogold.orm.migrate_cli migrate:make create_users
```

---

## Example Categories

| Category | Example | Concepts |
|----------|---------|----------|
| Argument Parsing | [Arguments](arguments.md) | Descriptor-based CLI arguments, type conversion |
| Subcommands | [Subcommands](subcommands.md) | OOP subcommand pattern, command classes |
| Database | [Migrations](migrations.md) | Schema migrations, up/down methods |
| Logic | [Logic System](logic.md) | Predicates, actions, triggers, composition |

---

## Running Examples Locally

The examples directory contains all runnable code:

```
examples/
├── arguments.py       # Argument descriptor usage
├── subcommands.py     # Subcommand pattern demo
├── descriptor.py      # Custom descriptors
└── wrappers.py        # Decorator patterns
```

Simply execute them:

```bash
python examples/arguments.py
python examples/subcommands.py start --help
```

---

## What to Try

Start with:

1. **[Arguments](arguments.md)** - If you're building CLIs
2. **[Subcommands](subcommands.md)** - For complex multi-command tools
3. **[Migrations](migrations.md)** - If you're working with databases
4. **[Logic](logic.md)** - For composable business logic

Each page has a "Try Variations" section with suggestions for experimentation.

---

## Contributing Examples

Have a use case that would make a great example? Please:

1. Create a file in `examples/`
2. Add a corresponding markdown file in `docs/examples/`
3. Update this index page
4. Submit a PR

We especially welcome examples showing real-world integration patterns!
