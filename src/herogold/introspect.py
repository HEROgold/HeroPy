"""Utilities for introspecting callables.

signature_of() returns a stable string form of a callable's signature, useful for
detecting when a callable's definition changed (e.g. to skip re-syncing unchanged
commands or plugin ABIs).
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def signature_of(func: Callable[..., object]) -> str:
    """Return a stable string form of `func`'s signature.

    :param func: The callable to inspect.
    :return: The callable's name followed by its `inspect.signature()` string form.
    """
    name = getattr(func, "__name__", type(func).__name__)
    return f"{name}{inspect.signature(func)}"
