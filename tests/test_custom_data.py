from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

import pytest
from fastapi import APIRouter, HTTPException
from sqlalchemy import BigInteger
from sqlalchemy.ext.compiler import compiles
from sqlmodel import Session, SQLModel, create_engine, select

from herogold.orm.core.api_model import APIModel
from herogold.orm.core.model import Actions, BaseModel, DataModel, _BaseModel
from herogold.orm.custom_data import OutOfSpaceError, validate_size

if TYPE_CHECKING:
    from collections.abc import Iterator

# The persisted database is written here and deliberately NOT deleted on teardown
# so it can be inspected after the run (e.g. with a sqlite viewer).
DB_PATH = Path(__file__).with_name("_custom_data.sqlite")


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):
    # SQLite only autoincrements a rowid-aliased INTEGER PRIMARY KEY, not BIGINT.
    return "INTEGER"


class Widget(BaseModel, table=True):
    name: str


class Tiny(BaseModel, table=True):
    name: str
    custom_data_size_limit: ClassVar[int] = 64  # a small budget so a modest payload overflows


class History(DataModel, table=True):
    label: str


@pytest.fixture(scope="module", autouse=True)
def _fresh_db() -> None:
    # Start from a clean file ONCE per module, then let rows accumulate across the
    # tests so the final on-disk database holds real, inspectable data.
    DB_PATH.unlink(missing_ok=True)


@pytest.fixture
def session() -> Iterator[Session]:
    # On-disk engine (not in-memory) so the file survives for inspection.
    engine = create_engine(f"sqlite:///{DB_PATH}")
    SQLModel.metadata.create_all(engine)  # idempotent; keeps accumulated rows
    sess = Session(engine)
    # `session` is a ClassVar on _BaseModel; set it on the root (reaches CustomData,
    # which subclasses _BaseModel directly) AND on BaseModel, because other test
    # modules leave a class-level shadow that would otherwise win via the MRO.
    originals = {cls: cls.__dict__.get("session") for cls in (_BaseModel, BaseModel, DataModel)}
    for cls in (_BaseModel, BaseModel, DataModel):
        cls.session = sess
    try:
        yield sess
    finally:
        sess.close()
        for cls, original in originals.items():
            if original is None:
                delattr(cls, "session")
            else:
                cls.session = original
        engine.dispose()  # release the sqlite file lock on Windows; file is kept


@pytest.fixture
def api(session: Session) -> APIModel[Widget]:
    return APIModel(Widget, APIRouter())


# --- size validation helper -------------------------------------------------


def test_validate_size_returns_error() -> None:
    # with_known_exception makes validate_size RETURN the error rather than raise it
    err = validate_size({"x": "y" * 1000}, 8)
    assert isinstance(err, OutOfSpaceError)
    assert validate_size({"x": 1}, 10_000) is None


# --- owner tables carry no custom_data column -------------------------------


def test_owner_table_has_no_custom_data_column() -> None:
    assert "custom_data" not in {c.name for c in Widget.__table__.columns}
    assert "custom_data" not in Widget.model_fields
    # the link table exists instead
    assert "widget_custom_data" in SQLModel.metadata.tables


# --- API round-trip on BaseModel --------------------------------------------


def test_basemodel_create_persists_and_links(api: APIModel[Widget], session: Session) -> None:
    item = Widget(name="thing")
    api.create(item, {"colour": "red", "tags": [1, 2, 3]})

    fetched = api.get(item.id)
    assert isinstance(fetched, Widget)
    assert fetched.custom_data is not None
    assert fetched.custom_data.data == {"colour": "red", "tags": [1, 2, 3]}
    # exactly one CustomData row was created and one link row exists
    link = SQLModel.metadata.tables["widget_custom_data"]
    rows = session.exec(select(link.c.widget_id, link.c.custom_data_id).where(link.c.widget_id == item.id)).all()
    assert len(rows) == 1


def test_basemodel_update_replaces(api: APIModel[Widget]) -> None:
    item = Widget(name="thing2")
    api.create(item, {"a": 1})
    api.update(item, {"b": 2})  # replaces (single link + new CustomData row)

    fetched = api.get(item.id)
    assert isinstance(fetched, Widget)
    assert fetched.custom_data is not None
    assert fetched.custom_data.data == {"b": 2}  # replaced, not merged


def test_no_custom_data_leaves_link_empty(api: APIModel[Widget]) -> None:
    item = Widget(name="bare")
    api.create(item)  # no custom_data
    fetched = api.get(item.id)
    assert isinstance(fetched, Widget)
    assert fetched.custom_data is None


# --- API round-trip on DataModel (composite PK) -----------------------------


def test_datamodel_create_persists_and_links(session: Session) -> None:
    api = APIModel(History, APIRouter())
    item = History(label="v1")
    api.create(item, {"note": "first"})

    fetched = api.get(item.id)
    assert isinstance(fetched, History)
    assert fetched.custom_data is not None
    assert fetched.custom_data.data == {"note": "first"}
    # the composite-PK link table carries both owner PK columns
    link = SQLModel.metadata.tables["history_custom_data"]
    assert {"history_id", "history_timestamp", "custom_data_id"} <= {c.name for c in link.columns}
    assert item.action is Actions.CREATE


# --- overflow -> 413 --------------------------------------------------------


def test_overflow_returns_413(session: Session) -> None:
    tiny_api = APIModel(Tiny, APIRouter())
    item = Tiny(name="big")
    with pytest.raises(HTTPException) as excinfo:
        tiny_api.create(item, {f"k{i}": i for i in range(50)})  # over the 64-byte limit
    assert excinfo.value.status_code == 413
