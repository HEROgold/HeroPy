from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING, Annotated, ClassVar

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from herogold.orm.api import APIModel, request_session
from herogold.orm.core.binding import bound, orm_session
from herogold.orm.core.custom_data import CustomData
from herogold.orm.core.model import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterator


class Crate(BaseModel, table=True):
    name: str
    custom_data_size_limit: ClassVar[int] = 64


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):
    return "INTEGER"


@pytest.fixture
def router() -> APIRouter:
    return APIRouter()


@pytest.fixture
def client(router: APIRouter) -> Iterator[TestClient]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    APIModel(Crate, router)

    @router.post("/boom")
    def boom(name: str, session: Annotated[Session, Depends(request_session)]) -> None:
        Crate(name=name).add(session=session)
        msg = "handler failed after add"
        raise RuntimeError(msg)

    app = FastAPI()
    app.include_router(router)
    try:
        with bound(engine):
            yield TestClient(app, raise_server_exceptions=False)
    finally:
        engine.dispose()


def _names() -> list[str]:
    with orm_session() as s:
        return [c.name for c in s.exec(select(Crate)).all()]


def test_oversize_custom_data_returns_413_and_stores_nothing(client: TestClient) -> None:
    resp = client.post("/", json={"item": {"name": "big"}, "custom_data": {f"k{i}": i for i in range(50)}})
    assert resp.status_code == 413, resp.text
    assert _names() == []
    with orm_session() as s:
        assert s.exec(select(CustomData)).all() == []


def test_valid_custom_data_stores_item_and_data(client: TestClient) -> None:
    resp = client.post("/", json={"item": {"name": "ok"}, "custom_data": {"a": 1}})
    assert resp.status_code == 200, resp.text
    assert _names() == ["ok"]
    with orm_session() as s:
        assert [c.data for c in s.exec(select(CustomData)).all()] == [{"a": 1}]


def test_failing_route_rolls_back(client: TestClient) -> None:
    resp = client.post("/boom", params={"name": "ghost"})
    assert resp.status_code == 500
    assert _names() == []


def test_core_import_does_not_load_fastapi() -> None:
    code = "import sys, herogold.orm, herogold.orm.core.model; sys.exit('fastapi' in sys.modules)"
    assert subprocess.run([sys.executable, "-I", "-c", code], check=False).returncode == 0  # noqa: S603
