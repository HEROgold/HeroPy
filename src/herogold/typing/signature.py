"""Signature utilities for decorators."""
from collections.abc import Callable


def copy_signature[**P, R](_signature: Callable[P, R], /) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Copy the signature of a function to a decorator."""
    return lambda f: f
