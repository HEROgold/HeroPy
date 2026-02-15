# Subcommands Example ([`subcommands.py`](https://github.com/HEROgold/HeroPy/blob/master/examples/subcommands.py))

## Purpose

Showcases OOP-style subcommand management:

- Defining subcommands as classes
- Using [`Argument`](pdoc:herogold.argparse.Argument) descriptors in subcommands
- Command execution pattern
- Organizing complex CLIs

## Running

```bash
python examples/subcommands.py --help
python examples/subcommands.py start --port 9000 --reload
python examples/subcommands.py stop --force
python examples/subcommands.py status --verbose
```

## Code Summary

Defines three [`SubCommand`](pdoc:herogold.argparse.SubCommand) classes:

1. **StartCommand** - Start application with port, host, and reload options
2. **StopCommand** - Stop application with optional force flag
3. **StatusCommand** - Show status with verbose option

Each command:
- Has a `name` and `help` class attribute
- Declares arguments as class attributes using [`Argument`](pdoc:herogold.argparse.Argument)
- Implements an `execute()` method with command logic

## Example Output

```text
$ python examples/subcommands.py start --port 9000 --reload
Starting server on localhost:9000
Hot reload: enabled

$ python examples/subcommands.py status --verbose
Application status: running
  - Uptime: 5 hours
  - Active connections: 42
  - Memory usage: 256MB
```

## Design Pattern

```python
class MyCommand(SubCommand):
    name = "mycommand"
    help = "Description of command"
    
    # Declare arguments
    arg1 = Argument("arg1", type_=int, default=0)
    
    def execute(self, args: Namespace) -> int:
        # Command logic here
        print(f"Executing with {args.arg1}")
        return 0  # Exit code

# In main:
commands = SubCommandGroup(parser)
commands.add_commands(MyCommand, OtherCommand)
args = parser.parse_args()
return commands.execute(args)
```

## Try Variations

- Add a new command for restart or logs
- Add required positional arguments
- Implement shared base command class for common options
- Add validation in `execute()` method

## Key Takeaways

- Each command is self-contained in its own class
- Arguments are declared as class attributes
- Easy to test individual commands in isolation
- Clean separation between command definitions and routing logic
