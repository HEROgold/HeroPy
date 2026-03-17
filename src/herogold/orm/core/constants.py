"""Module for containing constants and configuration for the database package."""

from sqlalchemy import URL
from sqlmodel import Session, create_engine

from .config import DbConfig


class DbUrl:
    """Class containing database URL components."""

    driver = DbConfig("postgresql")
    username = DbConfig("postgres")
    password = DbConfig("SECURE_PASSWORD")
    host = DbConfig("postgres")
    port = DbConfig(5432)
    database = DbConfig("postgres_db")


CASCADE = "CASCADE"
DATABASE_URL = URL.create(
    DbUrl.driver,
    username=DbUrl.username,
    password=DbUrl.password,
    host=DbUrl.host,
    port=DbUrl.port,
    database=DbUrl.database,
)
engine = create_engine(DATABASE_URL, echo=False)
session = Session(engine)


class SessionMixin:
    """Mixin class to provide a session for database operations."""

    session: Session = session
