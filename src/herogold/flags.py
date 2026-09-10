"""Improvements often used on flags."""
from __future__ import annotations

from enum import IntFlag as IntFlagBase


class IntFlag(IntFlagBase):
    """A subclass of IntFlag that adds some convenience methods."""

    def has_flag(self, flag: IntFlag) -> bool:
        """Check if the flag is set."""
        return (self & flag) == flag

    def add(self, flag: IntFlag) -> IntFlag:
        """Return a new IntFlag with the given flag added."""
        return self | flag

    def remove(self, flag: IntFlag) -> IntFlag:
        """Return a new IntFlag with the given flag removed."""
        return self & ~flag

    @classmethod
    def none(cls) -> IntFlag:
        """Check if no flags are set."""
        return cls(0)

    @classmethod
    def all(cls) -> IntFlag:
        """Check if all flags are set."""
        return ~cls.none()
