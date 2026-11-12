from __future__ import annotations

import asyncio
import functools
import inspect
import os
from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa
from sqlmodel import SQLModel

from herogold.orm import Repository, Scoped, bound, on_commit
from herogold.orm.core.model import BaseModel
from herogold.orm.transactions import transactional

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterator


def async_test[**P](fn: Callable[P, Coroutine[object, object, None]]) -> Callable[P, None]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        asyncio.run(fn(*args, **kwargs))

    return wrapper


POSTGRES_URL = os.environ.get("HEROPY_TEST_POSTGRES_URL")


class TxSale(BaseModel, table=True):
    title: str = ""
    percent: int = 0


class TxProp(BaseModel, table=True):
    sale_id: int = 0
    kind: str = ""


class Sales(Scoped, Repository[TxSale]):
    pass


class Props(Scoped, Repository[TxProp]):
    pass


TABLES = [TxSale.__table__, TxProp.__table__]


class Refused(Exception):  # noqa: N818
    pass


class Db:
    def __init__(self, url: str) -> None:
        self.engine = sa.create_engine(url)
        self.watcher = sa.create_engine(url)

    def counts(self) -> tuple[int, int]:
        with self.watcher.connect() as c:
            sales = c.execute(sa.text("select count(*) from txsale")).scalar_one()
            props = c.execute(sa.text("select count(*) from txprop")).scalar_one()
        return sales, props

    def reset(self) -> None:
        with self.watcher.begin() as c:
            c.execute(sa.text("delete from txsale"))
            c.execute(sa.text("delete from txprop"))


NEEDS_POSTGRES = pytest.mark.skipif(not POSTGRES_URL, reason="HEROPY_TEST_POSTGRES_URL unset")


@pytest.fixture(params=["sqlite", pytest.param("postgres", marks=NEEDS_POSTGRES)])
def db(request: pytest.FixtureRequest, tmp_path: object) -> Iterator[Db]:
    if request.param == "sqlite":
        database = Db(f"sqlite:///{tmp_path}/tx.db")
    else:
        assert POSTGRES_URL
        database = Db(POSTGRES_URL)
    SQLModel.metadata.create_all(database.engine, tables=TABLES)
    database.reset()
    yield database
    SQLModel.metadata.drop_all(database.engine, tables=TABLES)
    for engine in (database.engine, database.watcher):
        engine.dispose()


class Cog:
    def __init__(self, engine: sa.Engine) -> None:
        self.bind = engine

    @transactional(engine=lambda cog: cog.bind)
    async def add(self, mode: str = "ok") -> None:
        async with Sales.begin() as sales:
            sales.upsert([TxSale(id=1, title="a", percent=1)])
        if mode == "crash":
            msg = "boom"
            raise RuntimeError(msg)
        if mode == "refuse":
            msg = "already subscribed"
            raise Refused(msg)

    @transactional(engine=lambda cog: cog.bind, commit_on=(Refused,))
    async def add_counting_refusals(self, mode: str = "ok") -> None:
        async with Sales.begin() as sales:
            sales.upsert([TxSale(id=1, title="attempt", percent=1)])
        if mode == "refuse":
            msg = "already subscribed"
            raise Refused(msg)
        if mode == "crash":
            msg = "boom"
            raise RuntimeError(msg)

    @transactional(engine=lambda cog: cog.bind)
    async def outer(self) -> None:
        async with Sales.begin() as sales:
            sales.upsert([TxSale(id=1, title="a", percent=1)])
        await self.inner()
        msg = "outer fails after inner succeeded"
        raise RuntimeError(msg)

    @transactional(engine=lambda cog: cog.bind)
    async def inner(self) -> None:
        async with Props.begin() as props:
            props.add_all([TxProp(id=1, sale_id=1, kind="dlc")])

    @transactional(engine=lambda cog: cog.bind, durable=True)
    async def must_be_outermost(self) -> None: ...

    @transactional(engine=lambda cog: cog.bind)
    async def calls_durable(self) -> None:
        await self.must_be_outermost()


@async_test
async def test_success_commits(db: Db) -> None:
    await Cog(db.engine).add()
    assert db.counts() == (1, 0)


@async_test
async def test_an_exception_rolls_back(db: Db) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        await Cog(db.engine).add("crash")
    assert db.counts() == (0, 0)


@async_test
async def test_a_refused_rolls_back_by_default(db: Db) -> None:
    with pytest.raises(Refused):
        await Cog(db.engine).add("refuse")
    assert db.counts() == (0, 0)


@async_test
async def test_commit_on_commits_and_still_raises(db: Db) -> None:
    with pytest.raises(Refused, match="already subscribed"):
        await Cog(db.engine).add_counting_refusals("refuse")
    assert db.counts() == (1, 0)


@async_test
async def test_commit_on_does_not_cover_other_exceptions(db: Db) -> None:
    with pytest.raises(RuntimeError, match="boom"):
        await Cog(db.engine).add_counting_refusals("crash")
    assert db.counts() == (0, 0)


@async_test
async def test_decorated_handler_calling_another_joins_it(db: Db) -> None:
    with pytest.raises(RuntimeError, match="outer fails"):
        await Cog(db.engine).outer()
    assert db.counts() == (0, 0)


@async_test
async def test_durable_passes_through(db: Db) -> None:
    with pytest.raises(RuntimeError, match="outermost"):
        await Cog(db.engine).calls_durable()


def test_wrong_stacking_raises_a_clear_type_error() -> None:
    class Command:
        def __init__(self, func: object) -> None:
            self.func = func

    with pytest.raises(TypeError, match=r"put it directly on the function, below @Cog\.command"):
        transactional(Command(lambda: None))


def test_signature_name_docstring_and_listener_tag_survive() -> None:
    @transactional
    async def handler(self: object, interaction: object, user: int) -> None:
        """Doc."""

    handler.__listener_event__ = "ready"  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]

    def tagged(self: object, x: int) -> int:
        return x

    tagged.__listener_event__ = "ready"  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
    outside = transactional(tagged)

    assert list(inspect.signature(handler).parameters) == ["self", "interaction", "user"]
    assert inspect.iscoroutinefunction(handler)
    assert handler.__name__ == "handler"
    assert handler.__doc__ == "Doc."
    assert outside.__listener_event__ == "ready"  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]


def test_explicit_engine_and_bound_engine_on_sync_functions(db: Db) -> None:
    class Plain:
        @transactional(engine=db.engine)
        def sync_job(self) -> str:
            with Sales.begin() as sales:
                sales.upsert([TxSale(id=2, title="s", percent=1)])
            return "done"

        @transactional
        def bound_job(self) -> str:
            with Sales.begin() as sales:
                sales.upsert([TxSale(id=3, title="b", percent=1)])
            on_commit(lambda: None)
            return "bound"

    plain = Plain()
    assert not inspect.iscoroutinefunction(plain.sync_job)
    assert plain.sync_job() == "done"
    assert db.counts() == (1, 0)
    with bound(db.engine):
        assert plain.bound_job() == "bound"
    assert db.counts() == (2, 0)


def test_callable_engine_without_positional_args_raises_a_clear_type_error(db: Db) -> None:
    @transactional(engine=lambda owner: owner.bind)
    def job(owner: object) -> None:
        raise AssertionError

    with pytest.raises(TypeError, match=r"job.*positional.*engine"):
        job(owner=Cog(db.engine))


@async_test
async def test_callable_engine_without_positional_args_raises_on_async_functions(db: Db) -> None:
    @transactional(engine=lambda owner: owner.bind)
    async def job(owner: object) -> None:
        raise AssertionError

    with pytest.raises(TypeError, match=r"job.*positional.*engine"):
        await job(owner=Cog(db.engine))
