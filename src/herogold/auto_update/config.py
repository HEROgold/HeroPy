"""Configuration management for the auto-update system."""

from __future__ import annotations

from confkit import Config as OGConfig


class Config[T](OGConfig[T]):  # noqa: D101
    pass
