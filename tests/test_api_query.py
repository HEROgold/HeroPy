from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from herogold.orm.core.api_model import APIModel, Operator, PaginatedResponse, QueryFilter, QueryRequest
from herogold.orm.core.model import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterator


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


def test_client_operator_eq(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "eq", "value": 20}]})
    assert {r["name"] for r in rows} == {"big box"}


def test_client_operator_ne(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "ne", "value": 20}]})
    assert {r["name"] for r in rows} == {"small box", "crate"}


def test_client_operator_gt(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "gt", "value": 10}]})
    assert {r["name"] for r in rows} == {"big box", "crate"}


def test_client_operator_like(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "name", "op": "like", "value": "%box%"}]})
    assert {r["name"] for r in rows} == {"small box", "big box"}


def test_client_operator_ge(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "ge", "value": 20}]})
    assert {r["name"] for r in rows} == {"big box", "crate"}


def test_client_operator_lt(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "lt", "value": 20}]})
    assert {r["name"] for r in rows} == {"small box"}


def test_client_operator_le(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "price", "op": "le", "value": 20}]})
    assert {r["name"] for r in rows} == {"small box", "big box"}


def test_client_operator_like_http(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "name", "op": "like", "value": "%box%"}]})
    assert {r["name"] for r in rows} == {"small box", "big box"}


def test_client_operator_ilike(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "name", "op": "ilike", "value": "%BOX%"}]})
    assert {r["name"] for r in rows} == {"small box", "big box"}


def test_client_operator_in(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "name", "op": "in", "value": ["crate", "small box"]}]})
    assert {r["name"] for r in rows} == {"crate", "small box"}


def test_client_operator_in_http(client: TestClient) -> None:
    rows = _query(client, {"filters": [{"field": "name", "op": "in", "value": ["crate", "small box"]}]})
    assert {r["name"] for r in rows} == {"crate", "small box"}


def test_client_sort_and_order(client: TestClient) -> None:
    rows = _query(client, {"sort": "price", "order": "desc"})
    assert [r["price"] for r in rows] == [50, 20, 5]


def test_client_pagination(client: TestClient) -> None:
    page1 = client.request("QUERY", "/", json={"sort": "price", "order": "asc", "page": 1, "limit": 2})
    page2 = client.request("QUERY", "/", json={"sort": "price", "order": "asc", "page": 2, "limit": 2})
    assert [r["price"] for r in page1.json()["items"]] == [5, 20]
    assert [r["price"] for r in page2.json()["items"]] == [50]


def test_client_unknown_field_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"filters": [{"field": "nope", "op": "eq", "value": 1}]})
    assert resp.status_code == 422, resp.text


def test_client_soft_deleted_excluded(client: TestClient) -> None:
    rows = _query(client, {})
    assert "gone" not in {r["name"] for r in rows}
    assert len(rows) == 3


def test_client_pagination_metadata(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"sort": "price", "order": "asc", "page": 1, "limit": 2})
    body = resp.json()
    assert body["page"] == 1
    assert body["size"] == 2
    assert body["total_items"] == 3
    assert body["total_pages"] == 2
    assert body["next"] is not None


def test_client_unknown_filter_field_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"filters": [{"field": "session", "op": "eq", "value": 1}]})
    assert resp.status_code == 422, resp.text


def test_client_unknown_sort_field_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"sort": "logger"})
    assert resp.status_code == 422, resp.text


def test_client_invalid_page_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"page": 0})
    assert resp.status_code == 422, resp.text


def test_client_invalid_limit_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"limit": 0})
    assert resp.status_code == 422, resp.text


def test_client_in_operator_with_non_iterable_value_rejected(client: TestClient) -> None:
    resp = client.request("QUERY", "/", json={"filters": [{"field": "price", "op": "in", "value": 42}]})
    assert resp.status_code == 422, resp.text


def test_client_query_advertised_in_allow_header(client: TestClient) -> None:
    resp = client.options("/")
    allow = resp.headers.get("allow", "")
    assert "QUERY" in allow
    rows = _query(client, {})
    assert len(list(rows)) == 3

def test_api_operator_eq(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="price", op=Operator.eq, value=20)]))["items"]
    assert len(items) == 0
    assert item.name == "big box"
    assert item.price == 20
    assert item.deleted_at is None

def test_api_operator_ne(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="price", op=Operator.ne, value=20)]))["items"]
    assert len(items) == 1
    assert item.name == "small box"
    assert item.price == 5
    assert item.deleted_at is None

def test_api_operator_gt(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="price", op=Operator.gt, value=10)]))["items"]
    assert len(items) == 1
    assert item.name == "big box"
    assert item.price == 20
    assert item.deleted_at is None

def test_api_operator_like(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="name", op=Operator.like, value="%box%")]))["items"]
    assert len(items) == 1
    assert item.name == "small box"
    assert item.price == 5
    assert item.deleted_at is None

def test_api_operator_ge(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="price", op=Operator.ge, value=20)]))["items"]
    assert len(items) == 1
    assert item.name == "big box"
    assert item.price == 20
    assert item.deleted_at is None

def test_api_operator_lt(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="price", op=Operator.lt, value=20)]))["items"]
    assert len(items) == 0
    assert item.name == "small box"
    assert item.price == 5
    assert item.deleted_at is None

def test_api_operator_le(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="price", op=Operator.le, value=20)]))["items"]
    assert len(items) == 1
    assert item.name == "small box"
    assert item.price == 5
    assert item.deleted_at is None

def test_api_operator_like_http(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="name", op=Operator.like, value="%box%")]))["items"]
    assert len(items) == 1
    assert item.name == "small box"
    assert item.price == 5
    assert item.deleted_at is None

def test_api_operator_ilike(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="name", op=Operator.ilike, value="%BOX%")]))["items"]
    assert len(items) == 1
    assert item.name == "small box"
    assert item.price == 5
    assert item.deleted_at is None

def test_api_operator_in(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="name", op=Operator.in_, value=["crate", "small box"])]))["items"]
    assert len(items) == 1
    assert item.name == "small box"
    assert item.price == 5
    assert item.deleted_at is None

def test_api_operator_in_http(api: APIModel[Item]) -> None:
    [item, *items] = api.query(QueryRequest(filters=[QueryFilter(field="name", op=Operator.in_, value=["crate", "small box"])]))["items"]
    assert len(items) == 1
    assert item.name == "small box"
    assert item.price == 5
    assert item.deleted_at is None

def test_api_sort_and_order(api: APIModel[Item]) -> None:
    rows = api.query(QueryRequest(sort="price", order="desc"))["items"]
    assert [r.price for r in rows] == [50, 20, 5]

def test_api_pagination(api: APIModel[Item]) -> None:
    page1 = api.query(QueryRequest(sort="price", order="asc", page=1, limit=2))["items"]
    page2 = api.query(QueryRequest(sort="price", order="asc", page=2, limit=2))["items"]
    assert [r.price for r in page1] == [5, 20]
    assert [r.price for r in page2] == [50]

def test_api_unknown_field_rejected(api: APIModel[Item]) -> None:
    with pytest.raises(HTTPException) as exc_info:
        api.query(QueryRequest(filters=[QueryFilter(field="nope", op=Operator.eq, value=1)]))["items"]
    assert exc_info.value.status_code == 422

def test_api_soft_deleted_excluded(api: APIModel[Item]) -> None:
    rows = api.query(QueryRequest())["items"]
    assert "gone" not in {r.name for r in rows}
    assert len(rows) == 3

def test_api_pagination_metadata(api: APIModel[Item]) -> None:
    request = QueryRequest(sort="price", order="asc", page=1, limit=2)
    response = PaginatedResponse(Item, request.page, request.limit)
    assert response.meta["page"] == 1
    assert response.meta["size"] == 2
    assert response.meta["total_items"] == 3
    assert response.meta["total_pages"] == 2
    assert response.meta["next"] is not None

def test_api_unknown_filter_field_rejected(api: APIModel[Item]) -> None:
    with pytest.raises(HTTPException) as exc_info:
        api.query(QueryRequest(filters=[QueryFilter(field="session", op=Operator.eq, value=1)]))["items"]
    assert exc_info.value.status_code == 422

def test_api_unknown_sort_field_rejected(api: APIModel[Item]) -> None:
    with pytest.raises(HTTPException) as exc_info:
        api.query(QueryRequest(sort="logger"))["items"]
    assert exc_info.value.status_code == 422

def test_api_invalid_page_rejected(api: APIModel[Item]) -> None:
    with pytest.raises(ValidationError):
        QueryRequest(page=0)

def test_api_invalid_limit_rejected(api: APIModel[Item]) -> None:
    with pytest.raises(ValidationError):
        QueryRequest(limit=0)

def test_api_in_operator_with_non_iterable_value_rejected(api: APIModel[Item]) -> None:
    with pytest.raises(HTTPException) as exc_info:
        api.query(QueryRequest(filters=[QueryFilter(field="price", op=Operator.in_, value=42)]))["items"]
    assert exc_info.value.status_code == 422

def test_api_query_advertised_in_allow_header(api: APIModel[Item]) -> None:
    resp = api.options()
    assert "QUERY" in resp.headers.get("allow", "")
    rows = api.query(QueryRequest())["items"]
    assert len(rows) == 3


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):
    # SQLite only autoincrements a rowid-aliased INTEGER PRIMARY KEY, not BIGINT,
    # so render BaseModel's BigInteger id as INTEGER for the in-memory test engine.
    return "INTEGER"


def _query(client: TestClient, body: dict) -> list[dict]:
    resp = client.request("QUERY", "/", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()["items"]
