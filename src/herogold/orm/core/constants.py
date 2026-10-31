"""Module for containing constants and configuration for the database package."""

from __future__ import annotations

from configparser import ConfigParser
from typing import TYPE_CHECKING

from sqlalchemy import URL

if TYPE_CHECKING:
    from pathlib import Path


CASCADE = "CASCADE"

_DEFAULTS = {
    "driver": "postgresql",
    "username": "postgres",
    "password": "SECURE_PASSWORD",
    "host": "postgres",
    "port": "5432",
    "database": "postgres_db",
}


def url_from_config(path: Path) -> URL:
    """Build the database URL from the ini file at ``path``.

    Only reads the file. Keys missing from the ``DbUrl`` section use defaults.

    Raises:
        FileNotFoundError: If ``path`` does not exist.

    """
    if not path.is_file():
        msg = f"Database config file not found: {path}"
        raise FileNotFoundError(msg)
    parser = ConfigParser()
    parser.read(path, encoding="utf-8")
    section = parser["DbUrl"] if parser.has_section("DbUrl") else {}
    return URL.create(
        section.get("driver", _DEFAULTS["driver"]),
        username=section.get("username", _DEFAULTS["username"]),
        password=section.get("password", _DEFAULTS["password"]),
        host=section.get("host", _DEFAULTS["host"]),
        port=int(section.get("port", _DEFAULTS["port"])),
        database=section.get("database", _DEFAULTS["database"]),
    )
