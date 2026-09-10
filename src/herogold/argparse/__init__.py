"""Argument parsing utilities."""

from __future__ import annotations

import sys
from functools import wraps
from typing import TYPE_CHECKING, cast

from .argument import Actions, Argument, Namespace, parser

if TYPE_CHECKING:
    from argparse import Namespace as ArgparseNamespace
    from collections.abc import Callable


def _resolve_subcommand(cls: type[Namespace], raw: ArgparseNamespace) -> type[Namespace]:
    """Walk the subcommand registry to find the class matching the parsed subcommand chain."""
    current = cls
    while current._subparsers is not None:  # noqa: SLF001
        dest = current._subparsers_dest  # noqa: SLF001
        assert dest is not None  # noqa: S101
        chosen = getattr(raw, dest, None)
        if chosen is None:
            break
        current = current._subcommand_registry[chosen]  # noqa: SLF001
    return current


def entrypoint[N: Namespace](namespace: N | type[N]) -> Callable[[Callable[[N], None]], Callable[[], None]]:
    """Define the entrypoint of your application, injecting command-line arguments into the given namespace."""
    root_cls: type[N] = cast("type[N]", namespace if isinstance(namespace, type) else type(namespace))

    def wrapper(func: Callable[[N], None]) -> Callable[[], None]:
        """Inject the arguments into the function."""
        @wraps(func)
        def inner() -> None:
            raw = root_cls._parser.parse_args(sys.argv[1:])  # noqa: SLF001
            leaf_cls = cast("type[N]", _resolve_subcommand(root_cls, raw))
            options = leaf_cls.__new__(leaf_cls)
            for key, value in vars(raw).items():
                setattr(options, key, value)
            func(options)

        return inner

    return wrapper

__all__ = [
    "Actions",
    "Argument",
    "Namespace",
    "entrypoint",
    "parser",
]
