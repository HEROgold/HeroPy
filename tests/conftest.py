from __future__ import annotations

import sys
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING
from weakref import WeakKeyDictionary

import pytest
from sqlalchemy import BigInteger, StaticPool, create_engine, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateTable
from sqlmodel import Session, SQLModel

# Ensure src/ is importable during tests without needing installation.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from herogold.orm.core.binding import bound  # noqa: E402
from herogold.orm.core.model import BaseModel  # noqa: E402,F401

# t-strings are a syntax error before 3.14, so the module cannot even be collected.
collect_ignore = [] if sys.version_info >= (3, 14) else ["test_314_loggers.py"]

if TYPE_CHECKING:
    from collections.abc import Iterator


_COUNTERS: WeakKeyDictionary[object, dict[str, count[int]]] = WeakKeyDictionary()


def _assign_composite_pk_ids(session: Session, _flush_context: object, _instances: object) -> None:
    """Assign ``id`` for composite-PK rows before insert.

    Real databases (Postgres/MSSQL) auto-generate the ``id`` half of a composite
    primary key via SERIAL/IDENTITY. SQLite has no equivalent for multi-column
    primary keys (see ``_no_autoincrement_on_composite_pk`` below), so the
    in-memory test engine never populates ``id`` on its own. This mirrors that
    behavior for tests only, with a per-table counter local to each test.
    """
    # Owned sessions come and go, so the counters live on the engine, not the session.
    counters: dict[str, count[int]] = _COUNTERS.setdefault(session.get_bind(), {})
    for obj in session.new:
        table = getattr(obj, "__table__", None)
        if table is None or len(table.primary_key.columns) <= 1:
            continue
        if getattr(obj, "id", None) is not None:
            continue
        counter = counters.setdefault(table.name, count(1))
        obj.id = next(counter)


# Listening on the Session class covers explicit sessions and owned ones alike.
event.listen(Session, "before_flush", _assign_composite_pk_ids)


@pytest.fixture
def session() -> Iterator[Session]:
    # StaticPool keeps a single shared connection so create_all and the Session
    # target the same in-memory database (a fresh connection would start empty).
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    sess = Session(engine)
    try:
        with bound(engine):
            yield sess
    finally:
        sess.close()
        engine.dispose()


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
