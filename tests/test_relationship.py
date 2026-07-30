from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlmodel import Session, SQLModel, create_engine

from herogold.orm.core.model import BaseModel, _BaseModel
from herogold.orm.core.utils import SELF, Relationship, get_foreign_key

if TYPE_CHECKING:
    from collections.abc import Iterator

DB_PATH = Path(__file__).with_name("_relationship.sqlite")


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):
    return "INTEGER"


# Association tables require real tables, so every model here is table=True.
class Other(BaseModel, table=True):
    name: str = "o"


class HasRel(BaseModel, table=True):
    other = Relationship(Other)


class HasOpt(BaseModel, table=True):
    other = Relationship(Other, optional=True)


class Node(BaseModel, table=True):
    parent = Relationship(SELF, optional=True)


@pytest.fixture
def session() -> Iterator[Session]:
    DB_PATH.unlink(missing_ok=True)
    engine = create_engine(f"sqlite:///{DB_PATH}")
    SQLModel.metadata.create_all(engine)
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


def test_class_access_returns_target() -> None:
    assert HasRel.other is Other
    assert HasOpt.other is Other
    assert Node.parent is Node  # SELF resolves to the owner


def test_link_tables_registered() -> None:
    assert "hasrel_other" in SQLModel.metadata.tables
    assert "node_parent" in SQLModel.metadata.tables
    # the owner table gains no relationship column
    assert "other" not in {c.name for c in HasRel.__table__.columns}


def test_set_and_get(session: Session) -> None:
    o = Other(name="target")
    o.add()
    h = HasRel()
    h.add()
    h.other = o
    assert h.other is not None
    assert h.other.id == o.id


def test_reassign_replaces_single_link(session: Session) -> None:
    o1, o2 = Other(name="one"), Other(name="two")
    o1.add()
    o2.add()
    h = HasRel()
    h.add()
    h.other = o1
    h.other = o2  # UNIQUE(owner) means the single link is replaced
    assert h.other is not None
    assert h.other.id == o2.id


def test_optional_returns_none_when_unset(session: Session) -> None:
    h = HasOpt()
    h.add()
    assert h.other is None


def test_self_referential(session: Session) -> None:
    parent = Node()
    parent.add()
    child = Node()
    child.add()
    assert child.parent is None
    child.parent = parent
    assert child.parent is not None
    assert child.parent.id == parent.id


def test_foreign_key_helper_accepts_generic() -> None:
    assert get_foreign_key(Other, "id") == "other.id"
