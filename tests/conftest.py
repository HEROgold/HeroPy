from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import BigInteger, StaticPool, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateTable
from sqlmodel import Session, SQLModel

# Ensure src/ is importable during tests without needing installation.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from herogold.orm.core.model import BaseModel, _BaseModel  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Iterator


@compiles(CreateTable, "sqlite")
def _no_autoincrement_on_composite_pk(element: CreateTable, compiler, **kw):
    cols = list(element.element.columns)
    pks = [c for c in cols if c.primary_key]
    if len(pks) > 1:  # only composite PKs can't autoincrement on SQLite
        for c in pks:
            if c.autoincrement is True:
                c.autoincrement = False
    return compiler.visit_create_table(element, **kw)


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):
    # SQLite only autoincrements a rowid-aliased INTEGER PRIMARY KEY, not BIGINT,
    # so render BaseModel's BigInteger id as INTEGER for the in-memory test engine.
    return "INTEGER"


@pytest.fixture
def session() -> Iterator[Session]:
    # StaticPool keeps a single shared connection so create_all and the Session
    # target the same in-memory database (a fresh connection would start empty).
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    original = BaseModel.session
    sess = Session(engine)

    originals = {cls: cls.__dict__.get("session") for cls in (_BaseModel, BaseModel)}
    for cls in (_BaseModel, BaseModel):
        cls.session = sess
    try:
        yield sess
    finally:
        sess.close()
        for cls, original in originals.items():
            if original is None:
                delattr(cls, "session")
            else:
                cls.session = original
        engine.dispose()
