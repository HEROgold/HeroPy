from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import APIRouter

from herogold.orm.core.api_model import APIModel, Operator, QueryFilter, QueryRequest
from herogold.orm.core.model import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlmodel import Session


class Item(BaseModel, table=True):
    name: str
    price: int


@pytest.fixture
def api(session: Session) -> Iterator[APIModel[Item]]:
    try:
        for name, price in [("small box", 5), ("big box", 20), ("crate", 50), ("gone", 99)]:
            Item(name=name, price=price).add()
        # soft-delete one row so it must be excluded from query results
        Item.get_all(session)[-1].delete()
        yield APIModel(Item, APIRouter())
    finally:
        pass


def test_operator_gt(api: APIModel[Item]) -> None:
    rows = api.query(QueryRequest(filters=[QueryFilter(field="price", op=Operator.gt, value=10)]))
    assert {r.name for r in rows} == {"big box", "crate"}


def test_operator_like(api: APIModel[Item]) -> None:
    rows = api.query(QueryRequest(filters=[QueryFilter(field="name", op=Operator.like, value="%box%")]))
    assert {r.name for r in rows} == {"small box", "big box"}


def test_operator_in(api: APIModel[Item]) -> None:
    rows = api.query(QueryRequest(filters=[QueryFilter(field="name", op=Operator.in_, value=["crate", "small box"])]))
    assert {r.name for r in rows} == {"crate", "small box"}


def test_sort_and_order(api: APIModel[Item]) -> None:
    rows = api.query(QueryRequest(sort="price", order="desc"))
    assert [r.price for r in rows] == [50, 20, 5]


def test_pagination(api: APIModel[Item]) -> None:
    page1 = api.query(QueryRequest(sort="price", order="asc", page=1, limit=2))
    page2 = api.query(QueryRequest(sort="price", order="asc", page=2, limit=2))
    assert [r.price for r in page1] == [5, 20]
    assert [r.price for r in page2] == [50]


def test_unknown_field_ignored(api: APIModel[Item]) -> None:
    # a filter on a non-existent column is skipped, not an error
    rows = api.query(QueryRequest(filters=[QueryFilter(field="nope", op=Operator.eq, value=1)]))
    assert len(rows) == 3


def test_soft_deleted_excluded(api: APIModel[Item]) -> None:
    rows = api.query(QueryRequest())
    assert "gone" not in {r.name for r in rows}
    assert len(rows) == 3
