"""Example demonstrating SubCommand and SubCommandGroup usage."""

from argparse import ArgumentParser, Namespace

from herogold.argparse import Actions, Argument, SubCommand, SubCommandGroup


class StartCommand(SubCommand):
    """Start the application."""

    name = "start"
    help = "Start the application server"

    port = Argument(
        "port",
        type_=int,
        default=8000,
        help="Port to bind the server to",
    )
    host = Argument(
        "host",
        default="localhost",
        help="Host to bind the server to",
    )
    reload = Argument(
        "reload",
        action=Actions.STORE_BOOL,
        default=False,
        help="Enable hot reload",
    )

    def execute(self, args: Namespace) -> int:
        """Execute the start command."""
        print(f"Starting server on {args.host}:{args.port}")
        print(f"Hot reload: {'enabled' if args.reload else 'disabled'}")
        return 0


class StopCommand(SubCommand):
    """Stop the application."""

    name = "stop"
    help = "Stop the application server"

    force = Argument(
        "force",
        action=Actions.STORE_BOOL,
        default=False,
        help="Force stop without graceful shutdown",
    )

    def execute(self, args: Namespace) -> int:
        """Execute the stop command."""
        method = "force" if args.force else "graceful"
        print(f"Stopping server ({method} shutdown)")
        return 0


class StatusCommand(SubCommand):
    """Show application status."""

    name = "status"
    help = "Show application status"

    verbose = Argument(
        "verbose",
        action=Actions.STORE_BOOL,
        default=False,
        help="Show detailed status information",
    )

    def execute(self, args: Namespace) -> int:
        """Execute the status command."""
        print("Application status: running")
        if args.verbose:
            print("  - Uptime: 5 hours")
            print("  - Active connections: 42")
            print("  - Memory usage: 256MB")
        return 0


def main() -> int:
    """Main entry point."""
    parser = ArgumentParser(
        prog="myapp",
        description="Application management tool",
    )

    commands = SubCommandGroup(parser)
    commands.add_commands(
        StartCommand,
        StopCommand,
        StatusCommand,
    )

    args = parser.parse_args()
    return commands.execute(args)


if __name__ == "__main__":
    import sys
    sys.exit(main())
