"""Provides helpers for asynchronous code."""

from __future__ import annotations

import asyncio
from asyncio import AbstractEventLoop
from functools import wraps
from inspect import iscoroutinefunction
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


def get_async_loop() -> AbstractEventLoop:
    """Get the current event loop, or create one if it doesn't exist."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop()

@overload
def dual_wraps[**P, R](
    func: Callable[P, Awaitable[object]],
    sync_wrapper: Callable[P, R],
    async_wrapper: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]: ...
@overload
def dual_wraps[**P, R](
    func: Callable[P, object],
    sync_wrapper: Callable[P, R],
    async_wrapper: Callable[P, Awaitable[R]],
) -> Callable[P, R]: ...
def dual_wraps[**P, R](
    func: Callable[P, object],
    sync_wrapper: Callable[P, R],
    async_wrapper: Callable[P, Awaitable[R]],
) -> Callable[P, R] | Callable[P, Awaitable[R]]:
    """Pick sync_wrapper or async_wrapper to match func's sync/async-ness, and apply functools.wraps(func) to it.

    Lets decorators that need an async-aware wrapper build both variants and hand
    them here, instead of each repeating the `iscoroutinefunction(func)` branch and
    the matching `@wraps(func)` on both sides themselves.
    """
    if iscoroutinefunction(func):
        return wraps(func)(async_wrapper)

    return wraps(func)(sync_wrapper)
