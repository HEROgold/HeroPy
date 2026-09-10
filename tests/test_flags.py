
from __future__ import annotations

from enum import auto

from herogold.flags import IntFlag


def test_flags_none_are_0():
    """Test that the none() method returns 0."""
    class TestFlag(IntFlag):
        A = auto()
        B = auto()
        C = auto()

    assert TestFlag.none() == 0

def test_flags_all_are_set():
    """Test that the all() method returns a flag with all bits set."""
    class TestFlag(IntFlag):
        A = auto()
        B = auto()
        C = auto()
        D = C | B
        # pyrefly: ignore [unsupported-operation]
        E = C & ~B
        # pyrefly: ignore [unsupported-operation]
        F = ~C & B

    assert TestFlag.all() == (TestFlag.A | TestFlag.B | TestFlag.C | TestFlag.D | TestFlag.E | TestFlag.F)
