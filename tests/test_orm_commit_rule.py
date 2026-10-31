"""The ORM commits only sessions it opened itself (ADR 0001).

Visibility is checked through a second, independent session on a file-backed
SQLite database, so an uncommitted write cannot be seen from outside.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from herogold.orm.core.binding import bound
from herogold.orm.core.model import BaseModel, DataModel

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from sqlalchemy import Engine


class CommitRuleWidget(BaseModel, table=True):
    name: str


class CommitRuleHistory(DataModel, table=True):
    label: str


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    SQLModel.metadata.create_all(engine)
    try:
        with bound(engine):
            yield engine
    finally:
        engine.dispose()  # release the sqlite file lock on Windows


def _widget_name(engine: Engine, widget_id: int) -> str | None:
    """Read a widget's name through a fresh, independent session."""
    with Session(engine) as other:
        row = other.get(CommitRuleWidget, widget_id)
        return row.name if row else None


def _widget_deleted_at(engine: Engine, widget_id: int) -> object:
    with Session(engine) as other:
        row = other.get(CommitRuleWidget, widget_id)
        assert row is not None
        return row.deleted_at


def _widget_count(engine: Engine) -> int:
    with Session(engine) as other:
        return len(other.exec(select(CommitRuleWidget)).all())


def _history_count(engine: Engine) -> int:
    with Session(engine) as other:
        return len(other.exec(select(CommitRuleHistory)).all())


# --- add ---------------------------------------------------------------------


def test_add_with_session_assigns_id_but_stays_invisible_until_commit(engine: Engine) -> None:
    widget = CommitRuleWidget(name="draft")
    with Session(engine) as s:
        widget.add(session=s)
        assert widget.id is not None  # flushed, so the id exists
        assert _widget_count(engine) == 0  # not committed yet
        s.commit()
        assert _widget_name(engine, widget.id) == "draft"


def test_add_with_session_is_gone_after_rollback(engine: Engine) -> None:
    with Session(engine) as s:
        CommitRuleWidget(name="draft").add(session=s)
        s.rollback()
    assert _widget_count(engine) == 0


def test_add_without_session_is_visible_immediately(engine: Engine) -> None:
    widget = CommitRuleWidget(name="owned")
    widget.add()
    assert _widget_name(engine, widget.id) == "owned"


# --- update ------------------------------------------------------------------


def test_update_with_session_stays_invisible_until_commit(engine: Engine) -> None:
    widget = CommitRuleWidget(name="before")
    widget.add()
    assert widget.id is not None

    with Session(engine) as s:
        widget.name = "after"
        widget.update(session=s)
        assert _widget_name(engine, widget.id) == "before"
        s.commit()
        assert _widget_name(engine, widget.id) == "after"


def test_update_without_session_is_visible_immediately(engine: Engine) -> None:
    widget = CommitRuleWidget(name="before")
    widget.add()
    assert widget.id is not None

    widget.name = "after"
    widget.update()
    assert _widget_name(engine, widget.id) == "after"


# --- delete (soft delete on BaseModel) ---------------------------------------


def test_delete_with_session_soft_delete_stays_invisible_until_commit(engine: Engine) -> None:
    widget = CommitRuleWidget(name="doomed")
    widget.add()
    assert widget.id is not None

    with Session(engine) as s:
        widget.delete(session=s)
        assert _widget_deleted_at(engine, widget.id) is None
        s.commit()
        assert _widget_deleted_at(engine, widget.id) is not None


def test_delete_without_session_is_visible_immediately(engine: Engine) -> None:
    widget = CommitRuleWidget(name="doomed")
    widget.add()
    assert widget.id is not None

    widget.delete()
    assert _widget_deleted_at(engine, widget.id) is not None


# --- DataModel history rows --------------------------------------------------


def test_datamodel_add_with_session_stays_invisible_until_commit(engine: Engine) -> None:
    row = CommitRuleHistory(label="entry")
    with Session(engine) as s:
        row.add(session=s)
        assert _history_count(engine) == 0
        s.commit()
        assert _history_count(engine) == 1
