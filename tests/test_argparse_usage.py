from __future__ import annotations

import re

import pytest

from herogold.argparse.argument import ColorArgumentParser

_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    return _ANSI.sub("", text)


def _parser() -> ColorArgumentParser:
    parser = ColorArgumentParser(prog="tool")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--check", action="store_true")
    return parser


def test_error_usage_matches_help_usage(capsys: pytest.CaptureFixture[str]) -> None:
    parser = _parser()
    help_usage = _plain(parser.format_help()).splitlines()[0]

    with pytest.raises(SystemExit):
        parser.parse_args([])
    error_usage = _plain(capsys.readouterr().err).splitlines()[0]

    assert error_usage == help_usage
    assert help_usage.startswith("usage: tool")
    assert "usage: usage:" not in help_usage


def test_store_bool_rejects_non_bool_default_factory() -> None:
    """STORE_BOOL must reject factories that do not return a bool, or are not callable."""
    import pytest

    from herogold.argparse import Actions, Argument

    with pytest.raises(ValueError, match="default_factory"):
        Argument("flag", action=Actions.STORE_BOOL, default_factory=lambda: "x")
    with pytest.raises(ValueError, match="default_factory"):
        Argument("flag", action=Actions.STORE_BOOL, default_factory="x")  # type: ignore[arg-type]
    Argument("flag", action=Actions.STORE_BOOL, default_factory=lambda: True)
