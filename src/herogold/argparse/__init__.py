"""Argument parsing utilities."""

from __future__ import annotations

import sys
from functools import wraps
from typing import TYPE_CHECKING, cast

from .argument import Actions, Argument, Namespace, parser

if TYPE_CHECKING:
    from collections.abc import Callable


def entrypoint[N: Namespace](namespace: N | type[N]) -> Callable[[Callable[[N], None]], Callable[[], None]]:
    """Define the entrypoint of your application, injecting command-line arguments into the given namespace."""
    root_cls: type[N] = cast("type[N]", namespace if isinstance(namespace, type) else type(namespace))

    def wrapper(func: Callable[[N], None]) -> Callable[[], None]:
        """Inject the arguments into the function."""

        @wraps(func)
        def inner() -> None:
            raw = root_cls._parser.parse_args(sys.argv[1:])  # noqa: SLF001
            leaf_cls = cast("type[N]", root_cls._resolve_subcommand(raw))  # noqa: SLF001
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
