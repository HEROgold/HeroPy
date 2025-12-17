from configparser import ConfigParser
from pathlib import Path
from types import SimpleNamespace
from typing import Sequence
from unittest.mock import MagicMock

import pytest

from herogold.config.argparse_config import ArgConfig, ConfigError


class DummyParser:
    def __init__(self, responses: Sequence[object]) -> None:
        self.added_args: list[tuple[tuple[str, ...], dict[str, object]]] = []
        self.parse_args = MagicMock(side_effect=list(responses))

    def add_argument(self, *args: str, **kwargs: object) -> None:
        self.added_args.append((tuple(args), dict(kwargs)))


def _argument_flags(parser: DummyParser) -> list[tuple[str, ...]]:
    return [entry[0] for entry in parser.added_args]


def test_arg_config_with_conflicting_sources_raises(tmp_path: Path) -> None:
    parser = DummyParser([SimpleNamespace(config="cli.ini")])
    config = ConfigParser()
    file_path = tmp_path / "settings.ini"
    file_path.write_text("[section]\nkey = value\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        ArgConfig(parser, config, file_path)


def test_arg_config_reads_file_and_adds_arguments(tmp_path: Path) -> None:
    parser = DummyParser([
        SimpleNamespace(config=None),
        SimpleNamespace(config=None),
    ])
    config = ConfigParser()
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    config_path = config_dir / "settings.ini"
    config_path.write_text("[general]\nflag = value\nthreshold = 3\n", encoding="utf-8")

    ArgConfig(parser, config, config_path)

    assert parser.parse_args.call_count == 2
    assert ("-c", "--config") in _argument_flags(parser)
    assert ("--flag",) in _argument_flags(parser)
    assert config.get("general", "flag") == "value"


def test_arg_config_respects_cli_config_path(tmp_path: Path) -> None:
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()
    config_path = config_dir / "settings.ini"
    config_path.write_text("[general]\nmode = auto\n", encoding="utf-8")

    parser = DummyParser([
        SimpleNamespace(config=str(config_path)),
        SimpleNamespace(config=str(config_path)),
    ])

    config = ConfigParser()

    ArgConfig(parser, config, None)

    assert parser.parse_args.call_count == 2
    assert ("--mode",) in _argument_flags(parser)
    assert config.get("general", "mode") == "auto"
