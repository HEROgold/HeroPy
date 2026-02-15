# Reference Overview

This section provides detailed API documentation for all major components of HeroPy.

---

## Main Modules

### [Argparse](argparse.md)
Type-safe argument parsing with descriptors and subcommands.

**Key Classes:**
- [`Argument`](pdoc:herogold.argparse.Argument) - Descriptor for CLI arguments
- [`SubCommand`](pdoc:herogold.argparse.SubCommand) - Base class for subcommands
- [`SubCommandGroup`](pdoc:herogold.argparse.SubCommandGroup) - Subcommand manager
- [`Actions`](pdoc:herogold.argparse.Actions) - Argument action types

### [ORM](orm.md)
Database models and Django/Laravel-style migrations.

**Key Classes:**
- [`Migration`](pdoc:herogold.orm.Migration) - Base migration class
- [`MigrationManager`](pdoc:herogold.orm.MigrationManager) - Migration orchestrator
- [`MigrationRecord`](pdoc:herogold.orm.MigrationRecord) - Migration tracking model
- [`BaseModel`](pdoc:herogold.orm.BaseModel) - Base database model

### [Logic](logic.md)
Composable predicates, actions, and triggers.

**Key Classes:**
- [`Predicate`](pdoc:herogold.logic.Predicate) - Boolean condition wrapper
- [`Action`](pdoc:herogold.logic.Action) - Side-effect function wrapper
- [`Trigger`](pdoc:herogold.logic.Trigger) - Predicate-action pair

### [Utilities](utilities.md)
Helper functions and common tools.

**Key Exports:**
- [`MISSING`](pdoc:herogold.sentinel.MISSING) - Sentinel value
- [`RAINBOW`](pdoc:herogold.rainbow.RAINBOW) - Color constants
- [`LoggerMixin`](pdoc:herogold.log.LoggerMixin) - Logging helper

---

## Quick Links

**By Use Case:**
- Building CLIs → [Argparse](argparse.md)
- Database work → [ORM](orm.md)
- Business logic → [Logic](logic.md)
- Common helpers → [Utilities](utilities.md)

**Full API Index:**
- [Complete Symbol Index (pdoc)](pdoc:herogold)

---

## Using This Reference

Each reference page includes:

1. **Overview** - Purpose and main concepts
2. **Key Classes** - Main types with links to detailed docs
3. **Common Patterns** - Typical usage examples
4. **API Links** - Deep links to full API documentation

For in-depth API details, click the `(pdoc:...)` links which take you to the auto-generated API documentation.
