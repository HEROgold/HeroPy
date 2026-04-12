"""Provides helpers for asynchronous code."""

from __future__ import annotations

import asyncio
from asyncio import AbstractEventLoop


def get_async_loop() -> AbstractEventLoop:
    """Get the current event loop, or create one if it doesn't exist."""
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop()
