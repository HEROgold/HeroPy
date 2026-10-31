"""Session-aware relationships: link, unlink and get follow the commit rule (ADR 0001).

Visibility is checked through a second, independent session on a file-backed
SQLite database, so an uncommitted write cannot be seen from outside.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from herogold.orm.core.binding import bound
from herogold.orm.core.model import BaseModel
from herogold.orm.core.utils import SELF, Relationship

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from sqlalchemy import Engine


class SessTarget(BaseModel, table=True):
    name: str = "t"


class SessOwner(BaseModel, table=True):
    target = Relationship(SessTarget)


class SessNode(BaseModel, table=True):
    parent = Relationship(SELF)


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    SQLModel.metadata.create_all(engine)
    try:
        with bound(engine):
            yield engine
    finally:
        engine.dispose()


def _links(engine: Engine, rel: Relationship, owner_cls: type) -> int:
    """Count link rows visible to a fresh, independent session."""
    table = rel._links[owner_cls].table
    with Session(engine) as other:
        return len(other.exec(select(table)).all())


def _rows(engine: Engine, model: type[BaseModel]) -> int:
    with Session(engine) as other:
        return len(other.exec(select(model)).all())


def _committed_target_id(engine: Engine, owner: SessOwner) -> int | None:
    """Read the owner's target through a fresh session, committed state only."""
    with Session(engine) as other:
        found = SessOwner.target.get(owner, session=other)
        return found.id if found else None


def test_class_access_returns_descriptor() -> None:
    assert isinstance(SessOwner.target, Relationship)
    assert isinstance(SessNode.parent, Relationship)


def test_target_resolves_target_class() -> None:
    assert SessOwner.target.target(SessOwner) is SessTarget
    assert SessNode.parent.target(SessNode) is SessNode


def test_atomic_signup_visible_after_commit(engine: Engine) -> None:
    with Session(engine) as s:
        owner = SessOwner()
        target = SessTarget(name="new")
        owner.add(session=s)
        SessOwner.target.link(owner, target, session=s)
        assert target.id is not None
        assert _rows(engine, SessOwner) == 0
        assert _rows(engine, SessTarget) == 0
        assert _links(engine, SessOwner.target, SessOwner) == 0
        s.commit()
        assert (owner.id, target.id) != (None, None)  # reload expired attributes before the session closes
    assert _rows(engine, SessOwner) == 1
    assert _rows(engine, SessTarget) == 1
    assert _links(engine, SessOwner.target, SessOwner) == 1
    assert _committed_target_id(engine, owner) == target.id


def test_atomic_signup_gone_after_rollback(engine: Engine) -> None:
    with Session(engine) as s:
        owner = SessOwner()
        owner.add(session=s)
        SessOwner.target.link(owner, SessTarget(), session=s)
        s.rollback()
    assert _rows(engine, SessOwner) == 0
    assert _rows(engine, SessTarget) == 0
    assert _links(engine, SessOwner.target, SessOwner) == 0


def test_flushed_uncommitted_owner_can_be_linked(engine: Engine) -> None:
    with Session(engine) as s:
        owner = SessOwner()
        target = SessTarget()
        target.add(session=s)
        owner.add(session=s)  # flushed, not committed
        SessOwner.target.link(owner, target, session=s)
        assert SessOwner.target.get(owner, session=s) is target
        s.commit()
        assert (owner.id, target.id) != (None, None)  # reload expired attributes before the session closes
    assert _committed_target_id(engine, owner) == target.id


def test_link_unsaved_owner_raises(engine: Engine) -> None:
    with Session(engine) as s, pytest.raises(ValueError, match="persisted"):
        SessOwner.target.link(SessOwner(), SessTarget(), session=s)


def test_link_without_session_commits(engine: Engine) -> None:
    owner, target = SessOwner(), SessTarget()
    owner.add()
    SessOwner.target.link(owner, target)
    assert _committed_target_id(engine, owner) == target.id


def test_attribute_syntax_on_caller_session_instance_does_not_commit(engine: Engine) -> None:
    with Session(engine) as s:
        owner = SessOwner()
        owner.add(session=s)
        s.commit()
        target = SessTarget()
        owner.target = target
        assert target.id is not None
        assert owner.target is target
        assert _links(engine, SessOwner.target, SessOwner) == 0
        s.commit()
        assert (owner.id, target.id) != (None, None)  # reload expired attributes before the session closes
    assert _committed_target_id(engine, owner) == target.id


def test_attribute_syntax_on_caller_session_rolls_back(engine: Engine) -> None:
    with Session(engine) as s:
        owner = SessOwner()
        owner.add(session=s)
        s.commit()
        owner.target = SessTarget()
        s.rollback()
    assert _links(engine, SessOwner.target, SessOwner) == 0
    assert _rows(engine, SessTarget) == 0


def test_attribute_syntax_on_detached_instance_commits(engine: Engine) -> None:
    owner = SessOwner()
    owner.add()
    target = SessTarget()
    owner.target = target
    assert _committed_target_id(engine, owner) == target.id
    assert owner.target is not None
    assert owner.target.id == target.id


def test_relink_replaces_single_link(engine: Engine) -> None:
    with Session(engine) as s:
        owner, first, second = SessOwner(), SessTarget(), SessTarget()
        owner.add(session=s)
        SessOwner.target.link(owner, first, session=s)
        SessOwner.target.link(owner, second, session=s)
        assert SessOwner.target.get(owner, session=s) is second
        s.commit()
    assert _links(engine, SessOwner.target, SessOwner) == 1
    assert _rows(engine, SessTarget) == 2


@pytest.mark.parametrize("how", ["unlink", "none", "del"])
def test_unlink_keeps_owner_and_target(engine: Engine, how: str) -> None:
    with Session(engine) as s:
        owner, target = SessOwner(), SessTarget()
        owner.add(session=s)
        SessOwner.target.link(owner, target, session=s)
        s.commit()
        if how == "unlink":
            SessOwner.target.unlink(owner, session=s)
        elif how == "none":
            owner.target = None
        else:
            del owner.target
        assert owner.target is None
        s.commit()
    assert _links(engine, SessOwner.target, SessOwner) == 0
    assert _rows(engine, SessOwner) == 1
    assert _rows(engine, SessTarget) == 1


def test_unlink_detached_commits(engine: Engine) -> None:
    owner = SessOwner()
    owner.add()
    owner.target = SessTarget()
    owner.target = None
    assert _links(engine, SessOwner.target, SessOwner) == 0
    assert _rows(engine, SessTarget) == 1


def test_get_returns_none_without_link(engine: Engine) -> None:
    with Session(engine) as s:
        owner = SessOwner()
        owner.add(session=s)
        assert SessOwner.target.get(owner, session=s) is None


def test_self_relationship(engine: Engine) -> None:
    with Session(engine) as s:
        parent, child = SessNode(), SessNode()
        parent.add(session=s)
        child.add(session=s)
        s.commit()
        child.parent = parent
        assert child.parent is parent
        assert _links(engine, SessNode.parent, SessNode) == 0
        s.commit()
        child.parent = None
        assert child.parent is None
        s.commit()
    assert _links(engine, SessNode.parent, SessNode) == 0
    assert _rows(engine, SessNode) == 2
