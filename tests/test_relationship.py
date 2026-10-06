from __future__ import annotations

from sqlmodel import Session, SQLModel

from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import SELF, Relationship, get_foreign_key


# Association tables require real tables, so every model here is table=True.
class Other(BaseModel, table=True):
    name: str = "o"


class HasRel(BaseModel, table=True):
    other = Relationship(Other)


class HasOpt(BaseModel, table=True):
    other = Relationship(Other, optional=True)


class Node(BaseModel, table=True):
    parent = Relationship(SELF, optional=True)


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
