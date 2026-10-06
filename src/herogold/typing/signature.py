"""Signature utilities for decorators."""  # noqa: INP001

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def copy_signature[**P, R](_signature: Callable[P, R], /) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Copy the signature of a function to a decorator."""
    return lambda f: f
