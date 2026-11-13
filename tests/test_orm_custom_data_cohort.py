from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import BigInteger, StaticPool, insert
from sqlalchemy.ext.compiler import compiles
from sqlmodel import Session, SQLModel, create_engine, select

from herogold.orm.core.custom_data import CustomData
from herogold.orm.core.model import BaseModel, _BaseModel
from herogold.orm.testing import assert_statements

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine


class CdItem(BaseModel, table=True):
    __tablename__ = "cd_item"

    name: str = ""


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_: object, compiler: object, **kw: object) -> str:
    return "INTEGER"


@pytest.fixture
def engine() -> Iterator[Engine]:
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    sess = Session(engine)
    original = _BaseModel.__dict__.get("session")
    _BaseModel.session = sess
    try:
        yield sess
    finally:
        sess.close()
        if original is None:
            delattr(_BaseModel, "session")
        else:
            _BaseModel.session = original


def _seed(session: Session, count: int) -> None:
    items = [CdItem(name=f"item{i}") for i in range(count)]
    session.add_all(items)
    session.flush()
    link = SQLModel.metadata.tables["cd_item_custom_data"]
    for item in items:
        data = CustomData(data={"n": item.id})
        session.add(data)
        session.flush()
        session.execute(insert(link).values(cd_item_id=item.id, custom_data_id=data.id))
    session.commit()
    session.expunge_all()


def _read_all(session: Session, limit: int) -> list[CustomData | None]:
    rows = session.exec(select(CdItem).order_by(CdItem.id).limit(limit)).all()
    return [row.custom_data for row in rows]


def test_reading_costs_the_same_for_one_row_and_fifty(engine: Engine, session: Session) -> None:
    _seed(session, 50)
    with assert_statements(engine, 2):  # the row query and one query for every custom_data
        one = _read_all(session, 1)
    session.expunge_all()
    with assert_statements(engine, 2):
        many = _read_all(session, 50)
    assert len(one) == 1
    assert [cd.data["n"] for cd in many if cd is not None] == list(range(1, 51))


def test_write_joins_the_callers_transaction_and_does_not_commit(session: Session) -> None:
    item = CdItem(name="w")
    session.add(item)
    session.commit()
    item.custom_data = CustomData(data={"a": 1})
    assert session.in_transaction()
    assert item.custom_data is not None
    assert item.custom_data.data == {"a": 1}
    session.rollback()
    session.expunge_all()
    again = session.exec(select(CdItem).where(CdItem.name == "w")).one()
    assert again.custom_data is None


def test_write_is_visible_after_commit(session: Session) -> None:
    item = CdItem(name="c")
    session.add(item)
    session.commit()
    item.custom_data = CustomData(data={"b": 2})
    session.commit()
    session.expunge_all()
    again = session.exec(select(CdItem).where(CdItem.name == "c")).one()
    assert again.custom_data is not None
    assert again.custom_data.data == {"b": 2}


def test_replace_and_delete(session: Session) -> None:
    item = CdItem(name="r")
    session.add(item)
    session.commit()
    item.custom_data = CustomData(data={"v": 1})
    item.custom_data = CustomData(data={"v": 2})
    session.commit()
    link = SQLModel.metadata.tables["cd_item_custom_data"]
    assert len(session.execute(select(link)).all()) == 1
    assert item.custom_data is not None
    assert item.custom_data.data == {"v": 2}
    del item.custom_data
    assert item.custom_data is None
    session.commit()
    assert session.execute(select(link)).all() == []


def test_existing_link_table_keeps_its_name_and_columns() -> None:
    link = SQLModel.metadata.tables["cd_item_custom_data"]
    assert {c.name for c in link.columns} == {"cd_item_id", "custom_data_id"}
    assert {c.name for c in link.primary_key.columns} == {"cd_item_id", "custom_data_id"}


def test_custom_data_stays_a_leaf() -> None:
    assert "custom_data_custom_data" not in SQLModel.metadata.tables


def test_private_links_path_still_works() -> None:
    descriptor = _BaseModel.__dict__["custom_data"]
    assert descriptor._links[CdItem].table.name == "cd_item_custom_data"
