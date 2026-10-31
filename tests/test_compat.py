from __future__ import annotations

import sys

import pytest

from herogold.compat import UnsupportedPythonVersionError, require_python, requires_python


def test_require_python_ok() -> None:
    require_python((3, 0), module="x")


def test_require_python_too_old() -> None:
    with pytest.raises(UnsupportedPythonVersionError, match=r"x requires Python >= 99\.0"):
        require_python((99, 0), module="x")


def test_error_is_import_error() -> None:
    assert issubclass(UnsupportedPythonVersionError, ImportError)


def test_decorator_passes_through() -> None:
    @requires_python((3, 0))
    def add(a: int, b: int) -> int:
        return a + b

    assert add(1, 2) == 3
    assert add.__name__ == "add"


def test_decorator_raises_on_call_not_definition() -> None:
    @requires_python((99, 0))
    def nope() -> None: ...

    with pytest.raises(UnsupportedPythonVersionError, match="nope"):
        nope()


def test_monkeypatched_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "version_info", (3, 12, 4, "final", 0))
    with pytest.raises(UnsupportedPythonVersionError, match=r"3\.14.*running 3\.12\.4"):
        require_python((3, 14), module="m")
