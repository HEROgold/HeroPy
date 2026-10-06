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
