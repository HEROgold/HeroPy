from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from herogold.orm.core.api_model import APIModel
from herogold.orm.core.model import BaseModel

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
    return resp.json()["items"]


def test_operator_eq(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "eq", "value": 20}]})
    assert {r["name"] for r in rows} == {"big box"}


def test_operator_ne(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "ne", "value": 20}]})
    assert {r["name"] for r in rows} == {"small box", "crate"}


def test_operator_gt(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "gt", "value": 10}]})
    assert {r["name"] for r in rows} == {"big box", "crate"}


def test_operator_ge(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "ge", "value": 20}]})
    assert {r["name"] for r in rows} == {"big box", "crate"}


def test_operator_lt(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "lt", "value": 20}]})
    assert {r["name"] for r in rows} == {"small box"}


def test_operator_le(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "le", "value": 20}]})
    assert {r["name"] for r in rows} == {"small box", "big box"}


def test_operator_like(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "name", "op": "like", "value": "%box%"}]})
    assert {r["name"] for r in rows} == {"small box", "big box"}


def test_operator_ilike(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "name", "op": "ilike", "value": "%BOX%"}]})
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


def test_pagination_metadata(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"sort": "price", "order": "asc", "page": 1, "limit": 2})
    body = resp.json()
    assert body["page"] == 1
    assert body["size"] == 2
    assert body["total_items"] == 3
    assert body["total_pages"] == 2
    assert body["next"] is not None


def test_unknown_filter_field_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"filters": [{"field": "session", "op": "eq", "value": 1}]})
    assert resp.status_code == 422, resp.text


def test_unknown_sort_field_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"sort": "logger"})
    assert resp.status_code == 422, resp.text


def test_invalid_page_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"page": 0})
    assert resp.status_code == 422, resp.text


def test_invalid_limit_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"limit": 0})
    assert resp.status_code == 422, resp.text


def test_in_operator_with_non_iterable_value_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"filters": [{"field": "price", "op": "in", "value": 42}]})
    assert resp.status_code == 422, resp.text


def test_query_advertised_in_allow_header(client: TestClient) -> None:
    resp = client.options("/")
    allow = resp.headers.get("allow", "")
    assert "QUERY" in allow
