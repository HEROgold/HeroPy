"""Module that helps with tracking and automatically updating your project from production servers."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from httpxyz import URL


class Source:
    """ABC for tracking different sources for auto-updates."""

    def __init__(self, url: URL) -> None:
        """Initialize the source with the given URL."""
        self.url: URL = url


class Github(Source):
    """Github source for auto-updates."""
