"""Dependency injection through ``Annotated`` markers.

Mark a parameter with ``Annotated[X, Depends(provider)]`` and wrap the function
with ``@inject``. When the caller leaves that argument out or passes ``None``,
``inject`` enters ``provider()`` and passes the yielded value.
"""  # noqa: INP001

from __future__ import annotations

import inspect
from contextlib import ExitStack
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Annotated, Any, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

__all__ = ["Depends", "inject"]


@dataclass(frozen=True, slots=True)
class Depends[T]:
    """Marker that names the provider of an injected argument.

    Attributes:
        provider: Zero-argument callable that returns a context manager yielding the value.

    """

    provider: Callable[[], AbstractContextManager[T]]


def _find_dependencies(fn: Callable[..., Any]) -> dict[str, Depends[Any]]:
    hints = get_type_hints(fn, include_extras=True)
    found: dict[str, Depends[Any]] = {}
    for name, hint in hints.items():
        if name == "return" or get_origin(hint) is not Annotated:
            continue
        for meta in get_args(hint)[1:]:
            if isinstance(meta, Depends):
                found[name] = meta
                break
    return found


def inject[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """Fill ``Depends`` parameters that are missing or ``None`` from their providers.

    Args:
        fn: Function or method to wrap. Under ``@classmethod``, put ``@inject`` inside.

    Returns:
        A function with the same signature as ``fn``.

    Raises:
        TypeError: If ``fn`` is a generator, coroutine or async generator function.

    """
    if (
        inspect.isgeneratorfunction(fn)
        or inspect.iscoroutinefunction(fn)
        or inspect.isasyncgenfunction(fn)
    ):
        msg = f"inject cannot wrap generator or async function {fn.__qualname__}"
        raise TypeError(msg)
    signature = inspect.signature(fn)
    dependencies: dict[str, Depends[Any]] | None = None

    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        nonlocal dependencies
        if dependencies is None:
            dependencies = _find_dependencies(fn)
        arguments = signature.bind_partial(*args, **kwargs)
        with ExitStack() as stack:
            for name, dep in dependencies.items():
                if arguments.arguments.get(name) is None:
                    arguments.arguments[name] = stack.enter_context(dep.provider())
            return fn(*arguments.args, **arguments.kwargs)

    return wrapper
