from __future__ import annotations

from herogold.argparse import Actions, Argument, Namespace, entrypoint


class CliOptions(Namespace):
    """Root CLI options, shared across every subcommand."""

    dry_run = Argument(
        "dry_run",
        action=Actions.STORE_BOOL,
        default=False,
        help="Enable/disable dry-run mode (supports --dry-run/--no-dry-run)",
    )


class Deploy(CliOptions, subcommand="deploy"):
    """Deploy the application to an environment."""

    environment = Argument(
        "environment",
        help="Target environment name",
        default="dev",
    )
    retries = Argument(
        "retries",
        type_=int,
        default=2,
        help="Number of retry attempts",
    )


class Build(CliOptions, subcommand="build"):
    """Build the application."""

    target = Argument(
        "target",
        help="Build target name",
        default="all",
    )

@entrypoint(CliOptions)
def main(options: CliOptions) -> None:
    if isinstance(options, Deploy):
        print(
            "Preparing deployment:",
            f"env={options.environment}",
            f"retries={options.retries}",
            f"dry_run={options.dry_run}",
        )
    elif isinstance(options, Build):
        print("Building target:", f"target={options.target}", f"dry_run={options.dry_run}")


if __name__ == "__main__":
    main()
