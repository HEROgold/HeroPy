from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import APIRouter
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from herogold.orm.api_model import APIModel, Operator, QueryFilter, QueryRequest
from herogold.orm.model import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterator


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):
    # SQLite only autoincrements a rowid-aliased INTEGER PRIMARY KEY, not BIGINT,
    # so render BaseModel's BigInteger id as INTEGER for the in-memory test engine.
    return "INTEGER"


class Item(BaseModel, table=True):
    name: str
    price: int


@pytest.fixture
def api() -> Iterator[APIModel[Item]]:
    # StaticPool keeps a single shared connection so create_all and the Session
    # target the same in-memory database (a fresh connection would start empty).
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    original = BaseModel.session
    BaseModel.session = Session(engine)
    try:
        for name, price in [("small box", 5), ("big box", 20), ("crate", 50), ("gone", 99)]:
            Item(name=name, price=price).add()
        # soft-delete one row so it must be excluded from query results
        Item.get_all()[-1].delete()
        yield APIModel(Item, APIRouter())
    finally:
        BaseModel.session.close()
        BaseModel.session = original


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
