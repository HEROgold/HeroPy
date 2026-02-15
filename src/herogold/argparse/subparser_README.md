# SubCommand and SubCommandGroup

OOP-style subcommand management for argparse with the `Argument` descriptor.

## Features

- **Class-based subcommands**: Define each subcommand as a separate class
- **Argument descriptors**: Use the `Argument` descriptor to declare arguments
- **Clean separation**: Each command encapsulates its own arguments and logic
- **Type-safe**: Full type checking support with `ty` and similar tools

## Basic Usage

### Define a SubCommand

```python
from argparse import Namespace
from herogold.argparse import Argument, SubCommand, Actions

class StartCommand(SubCommand):
    """Start the application."""
    
    name = "start"  # Command name (optional, defaults to lowercase class name)
    help = "Start the application server"  # Help text for this command
    
    # Define arguments using the Argument descriptor
    port = Argument(
        "port",
        type_=int,
        default=8000,
        help="Port to bind the server to",
    )
    
    verbose = Argument(
        "verbose",
        action=Actions.STORE_BOOL,
        default=False,
        help="Enable verbose output",
    )
    
    def execute(self, args: Namespace) -> int:
        """Execute the command logic."""
        print(f"Starting server on port {args.port}")
        if args.verbose:
            print("Verbose mode enabled")
        return 0  # Return exit code
```

### Create a CLI with Multiple Commands

```python
from argparse import ArgumentParser
from herogold.argparse import SubCommandGroup

def main() -> int:
    parser = ArgumentParser(prog="myapp", description="My application")
    
    # Create a command group
    commands = SubCommandGroup(parser)
    
    # Register commands
    commands.add_commands(
        StartCommand,
        StopCommand,
        StatusCommand,
    )
    
    # Parse arguments and execute the selected command
    args = parser.parse_args()
    return commands.execute(args)

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

## Complete Example

See `examples/subcommands.py` for a full working example with multiple commands.

## Migration CLI Example

The migration CLI has been refactored to use this pattern:

```python
class MigrateMakeCommand(SubCommand):
    """Create a new migration file."""
    
    name = "migrate:make"
    help = "Create a new migration file"
    
    migration_name = Argument("name", help="Name of the migration")
    migrations_dir = Argument("dir", default="migrations", help="Directory to store migrations")
    
    def execute(self, args: Namespace) -> int:
        create_migration(args.name, args.dir)
        return 0
```

## Positional Arguments

To define positional arguments, pass argument names without dashes:

```python
class DeployCommand(SubCommand):
    name = "deploy"
    
    environment = Argument(
        "environment",  # No dashes = positional
        help="Target environment (dev, staging, prod)",
    )
```

Usage: `myapp deploy staging`

## Optional Arguments

For optional (flag-based) arguments, the descriptor automatically converts names to flags:

```python
class BuildCommand(SubCommand):
    name = "build"
    
    output_dir = Argument(
        "output_dir",  # Becomes --output-dir
        default="dist",
        help="Output directory",
    )
```

Usage: `myapp build --output-dir ./build`

## Boolean Flags

Use `Actions.STORE_BOOL` to create boolean flags with `--flag` and `--no-flag`:

```python
dry_run = Argument(
    "dry_run",
    action=Actions.STORE_BOOL,
    default=False,
    help="Enable dry-run mode",
)
```

Usage:
- `myapp start --dry-run` (sets `args.dry_run = True`)
- `myapp start --no-dry-run` (sets `args.dry_run = False`)

## Benefits

1. **Organized code**: Each command is self-contained in its own class
2. **Clear argument definitions**: Arguments are declared as class attributes
3. **Reusability**: Commands can be easily reused or extended
4. **Type safety**: Full IDE autocomplete and type checking support
5. **Testability**: Easy to test individual commands in isolation

## Comparison with Traditional argparse

### Before (procedural):

```python
def add_commands(parser):
    subparsers = parser.add_subparsers(dest="command")
    
    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--port", type=int, default=8000)
    start_parser.add_argument("--verbose", action="store_true")
    
    stop_parser = subparsers.add_parser("stop")
    stop_parser.add_argument("--force", action="store_true")

def handle_commands(args):
    if args.command == "start":
        # logic here
    elif args.command == "stop":
        # logic here
```

### After (OOP):

```python
class StartCommand(SubCommand):
    name = "start"
    port = Argument("port", type_=int, default=8000)
    verbose = Argument("verbose", action=Actions.STORE_BOOL, default=False)
    
    def execute(self, args: Namespace) -> int:
        # logic here
        return 0

class StopCommand(SubCommand):
    name = "stop"
    force = Argument("force", action=Actions.STORE_BOOL, default=False)
    
    def execute(self, args: Namespace) -> int:
        # logic here
        return 0

# In main:
commands = SubCommandGroup(parser)
commands.add_commands(StartCommand, StopCommand)
args = parser.parse_args()
return commands.execute(args)
```

Much cleaner and more maintainable!
