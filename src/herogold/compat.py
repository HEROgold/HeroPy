"""Tell importers when a module or callable needs a newer Python.

Companion to :mod:`herogold.imports`, which reports missing *extras*;
this reports a too-old *interpreter*.

Module-level guard (place it before anything version-specific)::

    from herogold.compat import require_python

    require_python((3, 14), module=__name__)

Decorator for a single function or class::

    @requires_python((3, 14))
    def new_api() -> None: ...

Both raise :class:`UnsupportedPythonVersionError` (an ``ImportError``).
The guard raises on import, the decorator raises on call.

.. note::
    Modules containing syntax that is new in the required version fail with
    ``SyntaxError`` on older interpreters *before* any guard can run. Put the
    guard in a thin package ``__init__`` and import the real module afterwards.
"""

from __future__ import annotations

import sys
from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

type Version = tuple[int, int]


class UnsupportedPythonVersionError(ImportError):
    """Raised when the running Python is older than a feature requires."""


def _format(version: tuple[int, ...]) -> str:
    return ".".join(str(part) for part in version)


def _check(minimum: Version, name: str) -> None:
    if tuple(sys.version_info[:2]) < minimum:
        msg = (
            f"{name} requires Python >= {_format(minimum)} "
            f"(running {_format(tuple(sys.version_info[:3]))})."
        )
        raise UnsupportedPythonVersionError(msg)


def require_python(minimum: Version, *, module: str) -> None:
    """Raise UnsupportedPythonVersionError if Python is older than ``minimum``."""
    _check(minimum, module)


def requires_python[**P, R](minimum: Version) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate a callable so calling it on an older Python raises a clear error."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            _check(minimum, f"{func.__module__}.{func.__qualname__}")
            return func(*args, **kwargs)

        return wrapper

    return decorator
