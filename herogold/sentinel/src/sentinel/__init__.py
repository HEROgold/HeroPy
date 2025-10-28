"""Backward-compat shim: re-export from herogold.sentinel.

Older code may import the top-level `sentinel` package. Keep a
lightweight shim so both `import sentinel` and `import herogold.sentinel`
work.
"""

from herogold.sentinel import MISSING

__all__ = ["MISSING"]
