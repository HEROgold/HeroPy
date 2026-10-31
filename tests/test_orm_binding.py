"""Binding an app-supplied engine, owned sessions, and import side effects."""

from __future__ import annotations

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import StaticPool, create_engine
from sqlmodel import Session, SQLModel

import herogold.orm as orm
from herogold.orm.core.errors import NoEngineBoundError
from herogold.orm.core.model import BaseModel

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine

SRC = Path(__file__).resolve().parents[1] / "src"


class BindingWidget(BaseModel, table=True):
    """Table used only by the binding tests."""

    name: str


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    eng = create_engine(f"sqlite:///{tmp_path / 'b.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


def test_import_has_no_side_effects(tmp_path: Path) -> None:
    code = (
        "import herogold.orm\n"
        "from herogold.orm import BaseModel, User\n"
        "User.__tablename__\n"
    )
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-I", "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []


def test_public_exports() -> None:
    assert callable(orm.bind)
    assert callable(orm.bound)
    assert orm.NoEngineBoundError is NoEngineBoundError


def test_owned_session_without_binding_raises() -> None:
    with pytest.raises(NoEngineBoundError):
        BindingWidget.get_all()


def test_caller_session_works_without_binding() -> None:
    eng = create_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    with Session(eng) as sess:
        BindingWidget(name="a").add(sess)
        assert [w.name for w in BindingWidget.get_all(sess)] == ["a"]


def test_bound_restores_after_block(engine: Engine) -> None:
    with orm.bound(engine):
        BindingWidget(name="a").add()
    with pytest.raises(NoEngineBoundError):
        BindingWidget.get_all()


def test_bound_restores_after_exception(engine: Engine) -> None:
    other = create_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(other)
    with orm.bound(engine):
        with pytest.raises(RuntimeError), orm.bound(other):
            raise RuntimeError
        BindingWidget(name="a").add()
        assert len(BindingWidget.get_all()) == 1


def test_bind_does_not_dispose_engine(engine: Engine) -> None:
    with orm.bound(engine):
        BindingWidget(name="a").add()
    with Session(engine) as sess:
        assert len(BindingWidget.get_all(sess)) == 1


def test_returned_objects_readable_after_call(engine: Engine) -> None:
    with orm.bound(engine):
        BindingWidget(name="keep").add()
        widget = BindingWidget.get_all()[0]
        assert widget.name == "keep"
        assert widget.id is not None
        assert BindingWidget.get(widget.id).name == "keep"


def test_threads_use_separate_owned_sessions(engine: Engine) -> None:
    with orm.bound(engine):
        def work(i: int) -> int:
            BindingWidget(name=f"w{i}").add()
            return len(BindingWidget.get_all())

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(work, range(8)))
        assert BindingWidget.count() == 8


def test_count_sees_rows_from_another_session(engine: Engine) -> None:
    with orm.bound(engine):
        assert BindingWidget.count() == 0
        with Session(engine) as other:
            BindingWidget(name="x").add(other)
            other.commit()  # the caller owns the commit
        assert BindingWidget.count() == 1
        with Session(engine) as other:
            BindingWidget(name="y").add(other)
            other.commit()
        assert BindingWidget.count() == 2


def test_url_from_config_missing_file_raises_and_creates_nothing(tmp_path: Path) -> None:
    path = tmp_path / "db.ini"
    with pytest.raises(FileNotFoundError):
        orm.url_from_config(path)
    assert not path.exists()


def test_url_from_config_reads_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "db.ini"
    path.write_text("[DbUrl]\ndriver = sqlite\nhost = example\nport = 1234\n")
    before = path.read_text()
    url = orm.url_from_config(path)
    assert url.drivername == "sqlite"
    assert url.host == "example"
    assert url.port == 1234
    assert url.username == "postgres"
    assert path.read_text() == before
