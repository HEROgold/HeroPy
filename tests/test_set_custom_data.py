"""set_custom_data writes into the caller's session and measures the serialised JSON size.

Commit visibility is checked through a second, independent session on a file-backed
SQLite database, so an uncommitted write cannot be seen from outside.
"""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING, ClassVar

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

import herogold.orm
from herogold.orm.core.binding import bound
from herogold.orm.core.custom_data import CustomData
from herogold.orm.core.model import BaseModel
from herogold.orm.custom_data import DEFAULT_SIZE_LIMIT, OutOfSpaceError, set_custom_data, validate_size

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine


class SetOwner(BaseModel, table=True):
    name: str


class SetCapped(BaseModel, table=True):
    name: str
    custom_data_size_limit: ClassVar[int] = 64  # below the 10 KB default


class SetRoomy(BaseModel, table=True):
    name: str
    custom_data_size_limit: ClassVar[int] = 100_000  # above the 10 KB default


@pytest.fixture
def engine(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Engine]:
    path = tmp_path_factory.mktemp("set_custom_data") / "db.sqlite"
    engine = create_engine(f"sqlite:///{path}")
    SQLModel.metadata.create_all(engine)
    try:
        with bound(engine):
            yield engine
    finally:
        engine.dispose()  # release the sqlite file lock on Windows


def _payload_of_size(size: int) -> dict[str, str]:
    """Return ``{"k": "vvv..."}`` whose compact JSON is exactly ``size`` bytes (size >= 9)."""
    # '{"k":"' is 6 bytes and '"}' is 2 bytes, so the value needs size - 8 characters.
    return {"k": "v" * (size - 8)}


def _owner_data(engine: Engine, owner_cls: type[BaseModel], owner_id: int) -> dict | None | str:
    """Read an owner's custom data through a fresh session. Returns "missing" if the owner is not visible."""
    with Session(engine) as other:
        owner = other.get(owner_cls, owner_id)
        if owner is None:
            return "missing"
        row = owner_cls.custom_data.get(owner, other)
        return None if row is None else row.data


def _custom_data_rows(engine: Engine) -> int:
    with Session(engine) as other:
        return len(other.exec(select(CustomData)).all())


# --- size measurement ---------------------------------------------------------


def test_size_is_utf8_bytes_of_compact_ascii_escaped_json() -> None:
    # json.dumps escapes e-acute as é (6 ASCII bytes): {"k":"é"} is 14 bytes
    assert validate_size({"k": "é"}, 14) is None
    with pytest.raises(OutOfSpaceError, match="of size 14 exceeds limit of 13 bytes"):
        validate_size({"k": "é"}, 13)


def test_payload_exactly_at_limit_passes() -> None:
    payload = _payload_of_size(64)
    assert validate_size(payload, 64) is None


def test_payload_one_byte_over_limit_raises() -> None:
    payload = _payload_of_size(65)
    with pytest.raises(OutOfSpaceError, match="of size 65 exceeds limit of 64 bytes"):
        validate_size(payload, 64)


def test_nested_payload_with_small_outer_dict_raises() -> None:
    # One top-level key, but the serialised nested value is far over 64 bytes.
    with pytest.raises(OutOfSpaceError):
        validate_size({"outer": {"inner": "x" * 100}}, 64)


# --- per-model budget ---------------------------------------------------------


def test_model_without_override_uses_default_limit(engine: Engine) -> None:
    owner = SetOwner(name="plain")
    owner.add()
    assert owner.id is not None

    set_custom_data(owner, _payload_of_size(DEFAULT_SIZE_LIMIT))
    with pytest.raises(OutOfSpaceError, match=f"exceeds limit of {DEFAULT_SIZE_LIMIT} bytes"):
        set_custom_data(owner, _payload_of_size(DEFAULT_SIZE_LIMIT + 1))


def test_override_lowers_the_limit(engine: Engine) -> None:
    # 65 bytes would fit the 10 KB default, but SetCapped only allows 64.
    owner = SetCapped(name="capped")
    owner.add()
    assert owner.id is not None

    with pytest.raises(OutOfSpaceError, match="exceeds limit of 64 bytes"):
        set_custom_data(owner, _payload_of_size(65))
    assert _owner_data(engine, SetCapped, owner.id) is None  # nothing was linked


def test_override_raises_the_limit(engine: Engine) -> None:
    # 20_000 bytes is over the 10 KB default but within SetRoomy's 100_000 budget.
    owner = SetRoomy(name="roomy")
    owner.add()
    assert owner.id is not None

    row = set_custom_data(owner, _payload_of_size(20_000))
    assert isinstance(row, CustomData)
    assert _owner_data(engine, SetRoomy, owner.id) == _payload_of_size(20_000)


# --- caller session: commit and rollback as one unit --------------------------


def test_owner_and_custom_data_commit_together(engine: Engine) -> None:
    owner = SetOwner(name="committed")
    with Session(engine) as s:
        owner.add(session=s)
        owner_id = owner.id
        assert owner_id is not None
        set_custom_data(owner, {"colour": "red"}, session=s)
        assert _owner_data(engine, SetOwner, owner_id) == "missing"  # not committed yet
        s.commit()

    assert _owner_data(engine, SetOwner, owner_id) == {"colour": "red"}


def test_owner_and_custom_data_roll_back_together(engine: Engine) -> None:
    owner = SetOwner(name="rolled back")
    with Session(engine) as s:
        owner.add(session=s)
        owner_id = owner.id
        assert owner_id is not None
        set_custom_data(owner, {"colour": "red"}, session=s)
        s.rollback()

    assert _owner_data(engine, SetOwner, owner_id) == "missing"
    assert _custom_data_rows(engine) == 0


def test_oversize_in_caller_session_writes_nothing(engine: Engine) -> None:
    owner = SetCapped(name="too big")
    with Session(engine) as s:
        owner.add(session=s)
        owner_id = owner.id
        assert owner_id is not None
        with pytest.raises(OutOfSpaceError):
            set_custom_data(owner, {"outer": {"inner": "x" * 100}}, session=s)
        s.commit()

    assert _owner_data(engine, SetCapped, owner_id) is None
    assert _custom_data_rows(engine) == 0


def test_second_call_replaces_the_link(engine: Engine) -> None:
    owner = SetOwner(name="replaced")
    owner.add()
    assert owner.id is not None

    set_custom_data(owner, {"a": 1})
    set_custom_data(owner, {"b": 2})

    assert _owner_data(engine, SetOwner, owner.id) == {"b": 2}  # replaced, not merged
    with Session(engine) as other:
        link = SQLModel.metadata.tables["setowner_custom_data"]
        rows = other.exec(select(link.c.custom_data_id).where(link.c.setowner_id == owner.id)).all()
        assert len(rows) == 1


def test_owned_session_makes_custom_data_visible_immediately(engine: Engine) -> None:
    owner = SetOwner(name="owned")
    owner.add()
    assert owner.id is not None

    set_custom_data(owner, {"colour": "blue"})

    assert _owner_data(engine, SetOwner, owner.id) == {"colour": "blue"}


# --- public export -------------------------------------------------------------


def test_set_custom_data_is_exported_from_orm_package() -> None:
    assert herogold.orm.set_custom_data is set_custom_data


# --- no FastAPI at import time ------------------------------------------------


def test_custom_data_module_imports_without_fastapi() -> None:
    code = "import sys, herogold.orm.custom_data; assert 'fastapi' not in sys.modules, 'fastapi imported'"
    result = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False)  # noqa: S603
    assert result.returncode == 0, result.stderr
