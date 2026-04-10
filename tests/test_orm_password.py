from __future__ import annotations

import sys
from configparser import ConfigParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORM_SRC = ROOT / "herogold" / "src"
if str(ORM_SRC) not in sys.path:
    sys.path.insert(0, str(ORM_SRC))

from orm.core.config import DbConfig  # noqa: E402

PARSER = ConfigParser()
PARSER.read(ROOT / "db_config.ini", encoding="utf-8")
DbConfig.set_parser(PARSER)

from orm.models.password import Password  # noqa: E402


def test_password_create_for_user_hashes_with_salt() -> None:
    password = Password.create_for_user(42, "example-pass")

    assert password.user_id == 42
    assert password.algorithm == Password.DEFAULT_ALGORITHM
    assert password.salt
    assert password.password_hash
    assert password.verify_password("example-pass")


def test_password_salt_changes_hash_for_same_plaintext() -> None:
    first = Password.create_for_user(7, "repeatable")
    second = Password.create_for_user(7, "repeatable")

    assert first.salt != second.salt
    assert first.password_hash != second.password_hash


def test_password_verification_rejects_incorrect_plaintext() -> None:
    password = Password.create_for_user(99, "secret-value")

    assert not password.verify_password("wrong-value")


def test_password_rejects_empty_plaintext() -> None:
    with pytest.raises(ValueError, match="Password cannot be empty"):
        Password.create_for_user(1, "")
