from __future__ import annotations

import sys
from argparse import Namespace
from functools import wraps
from typing import TYPE_CHECKING

from herogold.argparse import Actions, Argument, parser

if TYPE_CHECKING:
    from collections.abc import Callable


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

def entrypoint[N: Namespace](namespace: N | type[N]) -> Callable[[Callable[[N], None]], Callable[[], None]]:
    """Define the entrypoint of your application, injecting command-line arguments into the given namespace."""
    if isinstance(namespace, type):
        namespace = namespace()

    def wrapper(func: Callable[[N], None]) -> Callable[[], None]:
        """Wrapper function that will inject the arguments into the function."""
        @wraps(func)
        def inner() -> None:
            options = parser.parse_args(sys.argv, namespace=namespace)
            func(options)

        return inner

    return wrapper

__all__ = ["DeployOptions", "entrypoint"]

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
