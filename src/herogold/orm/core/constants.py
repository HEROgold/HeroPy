"""Module for containing constants and configuration for the database package."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import URL

from .config import DbConfig

if TYPE_CHECKING:
    from pathlib import Path


CASCADE = "CASCADE"


def url_from_config(path: Path) -> URL:
    """Build the database URL from the ini file at ``path``.

    Reads the file (creating it with defaults if missing) only when called.
    """
    DbConfig.set_file(path)

    # Config descriptors read the ini when the class body runs, so build them here.
    class DbUrl:
        """Database URL components read from the ini file."""

        driver = DbConfig("postgresql")
        username = DbConfig("postgres")
        password = DbConfig("SECURE_PASSWORD")
        host = DbConfig("postgres")
        port = DbConfig(5432)
        database = DbConfig("postgres_db")

    return URL.create(
        DbUrl.driver,
        username=DbUrl.username,
        password=DbUrl.password,
        host=DbUrl.host,
        port=DbUrl.port,
        database=DbUrl.database,
    )
