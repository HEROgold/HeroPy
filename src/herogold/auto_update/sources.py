"""Module that helps with tracking and automatically updating your project from production servers."""
from __future__ import annotations

from typing import override

from httpxyz import URL


class Source:
    """ABC for tracking different sources for auto-updates."""

    __slots__ = ("url",)

    def __init__(self, url: URL | str) -> None:
        """Initialize the source with the given URL."""
        self.url: URL = URL(url) if isinstance(url, str) else url

    def __str__(self) -> str:
        """Return a string representation of the source."""
        return str(self.url)

class Github(Source):
    """Github source for auto-updates."""

    @override
    def __str__(self) -> str:
        """Return a string representation of the Github source."""
        host = self.url.host
        path_parts = self.url.path.split("/")
        owner = path_parts[1]
        repo = path_parts[2]
        return f"{self.url.scheme}://{host}/{owner}/{repo}"

    @property
    def base_url(self) -> str:
        """Return the base URL for the Github source."""
        if not hasattr(self, "_base_url"):
            self._base_url = str(self)
        return self._base_url

    @property
    def releases(self) -> str:
        """Return the releases URL for the Github source."""
        return f"{self.base_url}/releases"

    @property
    def latest(self) -> str:
        """Return the latest release URL for the Github source."""
        return f"{self.releases}/latest"

    @property
    def is_zip(self) -> bool:
        """Check if the source is a zip file.

        I.E: https://github.com/<OWNER>/<REPO>/archive/refs/tags/v1.0.0.zip
        """
        return self.url.path.endswith(".zip")
