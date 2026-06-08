from __future__ import annotations

from argparse import Namespace

from herogold.argparse import Actions, Argument, entrypoint


class DeployOptions(Namespace):
    """Describe CLI arguments with Argument descriptors."""

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
    dry_run = Argument(
        "dry_run",
        action=Actions.STORE_BOOL,
        default=False,
        help="Enable/disable dry-run mode (supports --dry-run/--no-dry-run)",
    )

@entrypoint(DeployOptions)
def main(options: DeployOptions) -> None:
    print(
        "Preparing deployment:",
        f"env={options.environment}",
        f"retries={options.retries}",
        f"dry_run={options.dry_run}",
    )


if __name__ == "__main__":
    main()
