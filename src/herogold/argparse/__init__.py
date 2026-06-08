"""Argument parsing utilities."""

from __future__ import annotations

import sys
from argparse import Namespace
from functools import wraps
from typing import TYPE_CHECKING

from .argument import Actions, Argument, parser

if TYPE_CHECKING:
    from collections.abc import Callable


def entrypoint[N: Namespace](namespace: N | type[N]) -> Callable[[Callable[[N], None]], Callable[[], None]]:
    """Define the entrypoint of your application, injecting command-line arguments into the given namespace."""
    if isinstance(namespace, type):
        namespace = namespace()

    def wrapper(func: Callable[[N], None]) -> Callable[[], None]:
        """Inject the arguments into the function."""
        @wraps(func)
        def inner() -> None:
            options = parser.parse_args(sys.argv, namespace=namespace)
            func(options)

        return inner

    return wrapper

__all__ = [
    "Actions",
    "Argument",
    "entrypoint",
    "parser",
]
