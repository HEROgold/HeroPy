from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from herogold.orm.api_model import APIModel
from herogold.orm.model import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterator


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001, ANN202, ARG001
    # SQLite only autoincrements a rowid-aliased INTEGER PRIMARY KEY, not BIGINT,
    # so render BaseModel's BigInteger id as INTEGER for the in-memory test engine.
    return "INTEGER"


class Item(BaseModel, table=True):
    name: str
    price: int


@pytest.fixture
def client() -> Iterator[TestClient]:
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

        router = APIRouter()
        APIModel(Item, router)
        app = FastAPI()
        app.include_router(router)
        yield TestClient(app)
    finally:
        BaseModel.session.close()
        BaseModel.session = original


def _query(client: TestClient, body: dict) -> list[dict]:
    resp = client.request("QUERY", "/", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_operator_gt(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "gt", "value": 10}]})
    assert {r["name"] for r in rows} == {"big box", "crate"}


def test_operator_like(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "name", "op": "like", "value": "%box%"}]})
    assert {r["name"] for r in rows} == {"small box", "big box"}


def test_operator_in(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "name", "op": "in", "value": ["crate", "small box"]}]})
    assert {r["name"] for r in rows} == {"crate", "small box"}


def test_sort_and_order(client: TestClient) -> None:
    rows = _query(client, {"sort": "price", "order": "desc"})
    assert [r["price"] for r in rows] == [50, 20, 5]


def test_pagination(client: TestClient) -> None:
    page1 = _query(client, {"sort": "price", "order": "asc", "page": 1, "limit": 2})
    page2 = _query(client, {"sort": "price", "order": "asc", "page": 2, "limit": 2})
    assert [r["price"] for r in page1] == [5, 20]
    assert [r["price"] for r in page2] == [50]


def test_soft_deleted_excluded(client: TestClient) -> None:
    rows = _query(client, {})
    assert "gone" not in {r["name"] for r in rows}
    assert len(rows) == 3
