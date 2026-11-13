"""Dependency injection through ``Annotated`` markers.

Mark a parameter with ``Annotated[X, Depends(provider)]``. When the caller leaves
that argument out or passes ``None``, the provider's context manager is entered
around the call and its value is passed in.

Model methods need no decorator. ``ModelMeta`` calls :func:`inject_annotated` on
each attribute of a model class body. ``inject`` stays for plain functions the
ORM does not call, and is not part of the public API.
"""  # noqa: INP001

from __future__ import annotations

import inspect
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from functools import wraps
from types import SimpleNamespace
from typing import TYPE_CHECKING, Annotated, Any, cast, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

__all__ = ["Depends", "inject", "inject_annotated"]


@dataclass(frozen=True, slots=True)
class Depends[T]:
    """Marker that names the provider of an injected argument.

    Attributes:
        provider: Zero-argument callable that returns a context manager yielding the value.

    """

    provider: Callable[[], AbstractContextManager[T]]


def inject[**P, R](fn: Callable[P, R]) -> Callable[P, R]:
    """Fill ``Depends`` parameters that are missing or ``None`` from their providers.

    Args:
        fn: Function or method to wrap. Under ``@classmethod``, put ``@inject`` inside.

    Returns:
        A function with the same signature as ``fn``.

    Raises:
        TypeError: If ``fn`` is a generator, coroutine or async generator function.

    """
    if inspect.isgeneratorfunction(fn) or inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):
        match fn:
            case staticmethod() | classmethod():
                name = fn.__qualname__ or fn.__name__ or str(fn)
            case _:
                name = str(fn)
        msg = f"inject cannot wrap generator or async function {name}"
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


def inject_annotated(attr: object) -> object:
    """Wrap a class attribute with :func:`inject` when it declares a ``Depends`` parameter.

    Handles plain functions, ``classmethod`` and ``staticmethod``. Anything else, and
    functions without a resolvable ``Depends`` annotation, come back unchanged.
    """
    if isinstance(attr, (classmethod, staticmethod)):
        func = attr.__func__
        wrapped = inject_annotated(func)
        if wrapped is func:
            return attr
        return type(attr)(cast("Callable[..., Any]", wrapped))
    if not inspect.isfunction(attr) or inspect.isgeneratorfunction(attr) or inspect.iscoroutinefunction(attr):
        return attr
    if inspect.isasyncgenfunction(attr) or not _find_dependencies(attr, strict=False):
        return attr
    return inject(attr)


def _find_dependencies(fn: Callable[..., Any], *, strict: bool = True) -> dict[str, Depends[Any]]:
    if strict:
        hints = get_type_hints(fn, include_extras=True)
    else:
        hints = {}
        for name, annotation in getattr(fn, "__annotations__", {}).items():
            holder = SimpleNamespace(__annotations__={name: annotation})
            with suppress(Exception):  # unresolvable names cannot be Depends aliases
                hints.update(get_type_hints(holder, globalns=getattr(fn, "__globals__", None), include_extras=True))
    found: dict[str, Depends[Any]] = {}
    for name, hint in hints.items():
        if name == "return" or get_origin(hint) is not Annotated:
            continue
        for meta in get_args(hint)[1:]:
            if isinstance(meta, Depends):
                found[name] = meta
                break
    return found
