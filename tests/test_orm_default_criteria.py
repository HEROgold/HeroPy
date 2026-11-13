from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from herogold.orm.core.model import BaseModel, _BaseModel

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlmodel import Session


class CriteriaPlain(BaseModel, table=True):
    name: str


class CriteriaTenant(BaseModel, table=True):
    name: str
    tenant: int

    @classmethod
    def default_criteria(cls) -> list[ColumnElement[bool]]:
        return [*super().default_criteria(), cls.tenant == 1]


def test_base_model_default_is_empty() -> None:
    assert _BaseModel.default_criteria() == []


def test_query_and_count_skip_soft_deleted(session: Session) -> None:
    session.add(CriteriaPlain(name="alive"))
    session.add(CriteriaPlain(name="gone", deleted_at=datetime.now(UTC)))
    session.commit()

    assert [row.name for row in session.exec(CriteriaPlain.query)] == ["alive"]
    assert CriteriaPlain.count() == 1


def test_override_filters_query_and_count(session: Session) -> None:
    session.add(CriteriaTenant(name="mine", tenant=1))
    session.add(CriteriaTenant(name="other", tenant=2))
    session.add(CriteriaTenant(name="deleted", tenant=1, deleted_at=datetime.now(UTC)))
    session.commit()

    assert [row.name for row in session.exec(CriteriaTenant.query)] == ["mine"]
    assert CriteriaTenant.count() == 1


class CriteriaGhost(BaseModel, table=True):
    name: str

    @classmethod
    def soft_delete_criteria(cls) -> ColumnElement[bool]:
        return cls.name != "ghost"


def test_default_criteria_includes_soft_delete_criteria() -> None:
    criteria = CriteriaPlain.default_criteria()
    assert len(criteria) == 1
    assert criteria[0].compare(CriteriaPlain.soft_delete_criteria())


def test_overridden_soft_delete_criteria_filters_query(session: Session) -> None:
    session.add(CriteriaGhost(name="visible"))
    session.add(CriteriaGhost(name="ghost"))
    session.commit()

    assert [row.name for row in session.exec(CriteriaGhost.query)] == ["visible"]
    assert CriteriaGhost.count() == 1
