# ruff: noqa: PT012
from __future__ import annotations

import asyncio
import functools
import os
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Self

import pytest
import sqlalchemy as sa
from sqlmodel import Session, SQLModel

from herogold.orm import NoEngineBoundError, Repository, Scoped, ScopeRolledBack, bind, bound, on_commit, orm_session
from herogold.orm.core.model import BaseModel

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterator
    from contextlib import AbstractContextManager


def async_test[**P](fn: Callable[P, Coroutine[object, object, None]]) -> Callable[P, None]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        asyncio.run(fn(*args, **kwargs))

    return wrapper


POSTGRES_URL = os.environ.get("HEROPY_TEST_POSTGRES_URL")


class ScopeSale(BaseModel, table=True):
    title: str = ""
    percent: int = 0


class ScopeProp(BaseModel, table=True):
    sale_id: int = 0
    kind: str = ""


class Sales(Scoped, Repository[ScopeSale]):
    pass


class Props(Scoped, Repository[ScopeProp]):
    pass


TABLES = [ScopeSale.__table__, ScopeProp.__table__]


class Db:
    def __init__(self, url: str) -> None:
        self.url = url
        self.engine = sa.create_engine(url)
        self.watcher = sa.create_engine(url)  # its own pool, so observing never competes with the scopes
        self.other_engine = sa.create_engine(url)

    def small_engine(self) -> sa.Engine:
        """Return an engine with a pool of one connection, so a held connection is visible."""
        return sa.create_engine(self.url, pool_size=1, max_overflow=0, pool_timeout=0.4)

    def counts(self) -> tuple[int, int]:
        with self.watcher.connect() as c:
            sales = c.execute(sa.text("select count(*) from scopesale")).scalar_one()
            props = c.execute(sa.text("select count(*) from scopeprop")).scalar_one()
        return sales, props

    def reset(self) -> None:
        with self.watcher.begin() as c:
            c.execute(sa.text("delete from scopesale"))
            c.execute(sa.text("delete from scopeprop"))


NEEDS_POSTGRES = pytest.mark.skipif(not POSTGRES_URL, reason="HEROPY_TEST_POSTGRES_URL unset")


@pytest.fixture(params=["sqlite", pytest.param("postgres", marks=NEEDS_POSTGRES)])
def db(request: pytest.FixtureRequest, tmp_path: object) -> Iterator[Db]:
    if request.param == "sqlite":
        url = f"sqlite:///{tmp_path}/scopes.db"
        database = Db(url)
    else:
        assert POSTGRES_URL
        database = Db(POSTGRES_URL)
    SQLModel.metadata.create_all(database.engine, tables=TABLES)
    database.reset()
    yield database
    SQLModel.metadata.drop_all(database.engine, tables=TABLES)
    for engine in (database.engine, database.watcher, database.other_engine):
        engine.dispose()


def sale() -> list[ScopeSale]:
    return [ScopeSale(id=1, title="a", percent=1)]


def prop() -> list[ScopeProp]:
    return [ScopeProp(id=1, sale_id=1, kind="dlc")]


# ---- joining, rollback, savepoints (proto7) ----


def test_nested_independent_scope_leaves_an_orphan_after_outer_rollback(db: Db) -> None:
    with pytest.raises(RuntimeError, match="boom"), Sales.begin(db.engine) as sales:
        sales.upsert(sale())
        with Props.begin(db.engine, new=True) as props:
            props.add_all(prop())
        msg = "boom"
        raise RuntimeError(msg)
    assert db.counts() == (0, 1)


def test_nested_begin_joins_and_shares_the_outer_session(db: Db) -> None:
    with Sales.begin(db.engine) as sales, Props.begin() as props:
        assert props.session is sales.session


def test_outer_rollback_undoes_the_nested_block(db: Db) -> None:
    with pytest.raises(RuntimeError, match="boom"), Sales.begin(db.engine) as sales:
        sales.upsert(sale())
        with Props.begin() as props:
            props.add_all(prop())
        msg = "boom"
        raise RuntimeError(msg)
    assert db.counts() == (0, 0)


def test_only_the_outermost_scope_commits_and_it_commits_both(db: Db) -> None:
    with Sales.begin(db.engine) as sales:
        sales.upsert(sale())
        with Props.begin() as props:
            props.add_all(prop())
        assert db.counts() == (0, 0)
    assert db.counts() == (1, 1)


def test_caught_inner_failure_rolls_back_only_the_inner_block(db: Db) -> None:
    with Sales.begin(db.engine) as sales:
        sales.upsert(sale())
        with pytest.raises(RuntimeError, match="inner failed"), Props.begin() as props:
            props.add_all(prop())
            props.session.flush()
            msg = "inner failed"
            raise RuntimeError(msg)
    assert db.counts() == (1, 0)


def test_failed_block_without_savepoint_rolls_everything_back_and_says_so(db: Db) -> None:
    with pytest.raises(ScopeRolledBack, match="rolled back"), Sales.begin(db.engine) as sales:
        sales.upsert(sale())
        with pytest.raises(RuntimeError, match="inner failed"), Props.begin(savepoint=False) as props:
            props.add_all(prop())
            props.session.flush()
            msg = "inner failed"
            raise RuntimeError(msg)
    assert db.counts() == (0, 0)


def test_durable_works_outermost_and_raises_when_nested(db: Db) -> None:
    with Sales.begin(db.engine, durable=True) as sales:
        sales.upsert(sale())
    with Sales.begin(db.engine), pytest.raises(RuntimeError, match="outermost"), Props.begin(durable=True):
        pass
    assert db.counts() == (1, 0)


def test_on_commit_runs_after_the_commit_in_registration_order(db: Db) -> None:
    log: list[str] = []
    with Sales.begin(db.engine) as sales:
        sales.upsert(sale())
        on_commit(lambda: log.append("first"))
        on_commit(lambda: log.append(f"sees {db.counts()}"))
        log.append("body end")
    assert log == ["body end", "first", "sees (1, 0)"]


def test_on_commit_is_discarded_by_a_rollback(db: Db) -> None:
    log: list[str] = []
    with pytest.raises(RuntimeError, match="boom"), Sales.begin(db.engine) as sales:
        sales.upsert(sale())
        on_commit(lambda: log.append("should not run"))
        msg = "boom"
        raise RuntimeError(msg)
    assert log == []


def test_on_commit_drops_callbacks_of_a_rolled_back_savepoint_block(db: Db) -> None:
    log: list[str] = []
    with Sales.begin(db.engine):
        on_commit(lambda: log.append("outer"))
        with pytest.raises(RuntimeError, match="inner failed"), Props.begin():
            on_commit(lambda: log.append("inner, failed block"))
            msg = "inner failed"
            raise RuntimeError(msg)
        with Props.begin():
            on_commit(lambda: log.append("inner, ok block"))
    assert log == ["outer", "inner, ok block"]


def test_on_commit_outside_a_scope_runs_immediately() -> None:
    log: list[str] = []
    on_commit(lambda: log.append("immediately"))
    assert log == ["immediately"]


def test_new_scope_is_an_independent_transaction_on_purpose(db: Db) -> None:
    with pytest.raises(RuntimeError, match="boom"), Sales.begin(db.engine) as sales:
        sales.upsert(sale())
        with Props.begin(new=True) as props:
            props.add_all(prop())
        msg = "boom"
        raise RuntimeError(msg)
    assert db.counts() == (0, 1)


def test_new_scope_defaults_to_the_outer_engine(db: Db) -> None:
    with Sales.begin(db.engine) as sales, Props.begin(new=True) as props:
        assert props.session.get_bind() is db.engine
        assert props.session is not sales.session


def test_thread_task_and_other_engine_never_join(db: Db) -> None:
    seen: dict[str, int] = {}
    with Sales.begin(db.engine) as sales:
        outer = id(sales.session)

        def in_thread() -> None:
            with Sales.begin(db.engine) as s2:
                seen["thread"] = id(s2.session)

        t = threading.Thread(target=in_thread)
        t.start()
        t.join()

        async def in_task() -> None:
            with Sales.begin(db.engine) as s3:
                seen["task"] = id(s3.session)

        async def go() -> None:
            await asyncio.create_task(in_task())  # the task copies the context, and so the ambient scope

        asyncio.run(go())
        with Sales.begin(db.other_engine) as s4:
            seen["engine"] = id(s4.session)
    assert seen["thread"] != outer
    assert seen["task"] != outer
    assert seen["engine"] != outer


def test_no_scope_is_left_ambient_after_the_outermost_block(db: Db) -> None:
    with Sales.begin(db.engine):
        pass
    log: list[str] = []
    on_commit(lambda: log.append("immediately"))
    assert log == ["immediately"]
    with Sales.begin(db.engine) as sales:
        assert sales.session is not None


def test_scope_without_engine_names_bind() -> None:
    with pytest.raises(NoEngineBoundError, match=r"bind\(engine\)"), orm_session():
        pass


def test_bound_engine_is_the_default_and_is_restored(db: Db) -> None:
    with bound(db.engine):
        with orm_session() as session:
            assert session.get_bind() is db.engine
        with bound(db.other_engine), orm_session() as session:
            assert session.get_bind() is db.other_engine
        with orm_session() as session:
            assert session.get_bind() is db.engine
    with pytest.raises(NoEngineBoundError), orm_session():
        pass


def test_bind_sets_and_unsets_the_default_engine(db: Db) -> None:
    bind(db.engine)
    try:
        with orm_session() as session:
            assert session.get_bind() is db.engine
    finally:
        bind(None)
    with pytest.raises(NoEngineBoundError), orm_session():
        pass


# ---- on_commit with coroutines (proto8) ----


@async_test
async def test_async_with_runs_sync_and_coroutine_callbacks_in_order(db: Db) -> None:
    log: list[str] = []

    async def aio(tag: str) -> None:
        await asyncio.sleep(0)
        log.append(tag)

    async with Sales.begin(db.engine) as sales:
        sales.upsert(sale())
        on_commit(lambda: log.append("sync-1"))
        on_commit(lambda: aio("async-2"))
        on_commit(lambda: log.append("sync-3"))
        log.append("body end")
    assert log == ["body end", "sync-1", "async-2", "sync-3"]


@async_test
async def test_plain_with_refuses_a_coroutine_function_up_front(db: Db) -> None:
    async def coro_function() -> None:
        pass

    with pytest.raises(TypeError, match="async with"), Sales.begin(db.engine):
        on_commit(coro_function)


@async_test
async def test_plain_with_catches_a_lambda_returning_a_coroutine_after_the_commit(db: Db) -> None:
    async def coro_function() -> None:
        pass

    with pytest.raises(ExceptionGroup) as info, Sales.begin(db.engine) as sales:
        sales.upsert(sale())
        on_commit(lambda: coro_function())  # noqa: PLW0108
    assert "async with" in str(info.value.exceptions[0])
    assert db.counts() == (1, 0)


@async_test
async def test_outside_a_scope_a_coroutine_function_is_refused() -> None:
    async def coro_function() -> None:
        pass

    with pytest.raises(TypeError, match="nothing to await"):
        on_commit(coro_function)


@async_test
async def test_failing_callback_does_not_stop_the_others_or_undo_the_commit(db: Db) -> None:
    log: list[str] = []

    async def aio(tag: str) -> None:
        await asyncio.sleep(0)
        log.append(tag)

    async def failing() -> None:
        msg = "callback failed"
        raise ValueError(msg)

    with pytest.raises(ExceptionGroup) as info:
        async with Sales.begin(db.engine) as sales:
            sales.upsert(sale())
            on_commit(failing)
            on_commit(lambda: aio("still runs"))
    assert isinstance(info.value.exceptions[0], ValueError)
    assert log == ["still runs"]
    assert db.counts() == (1, 0)


@async_test
async def test_rollback_discards_coroutine_callbacks_too(db: Db) -> None:
    log: list[str] = []

    async def aio() -> None:
        log.append("never")

    with pytest.raises(RuntimeError, match="boom"):
        async with Sales.begin(db.engine) as sales:
            sales.upsert(sale())
            on_commit(aio)
            msg = "boom"
            raise RuntimeError(msg)
    assert log == []
    assert db.counts() == (0, 0)


@async_test
async def test_coroutine_callback_registered_in_a_joined_async_block_of_a_plain_scope_is_refused(db: Db) -> None:
    async def coro_function() -> None:
        pass

    with Sales.begin(db.engine):
        async with Props.begin():
            with pytest.raises(TypeError, match="plain `with`"):
                on_commit(coro_function)


@async_test
async def test_handler_reply_through_on_commit_follows_the_commit(db: Db) -> None:
    log: list[str] = []

    async def respond(text: str) -> None:
        log.append(f"{text}:{db.counts()[0]}")

    async def direct() -> None:
        async with orm_session(db.engine):
            async with Sales.begin() as sales:
                sales.upsert(sale())
            await respond("direct")

    async def after_commit() -> None:
        async with orm_session(db.engine):
            async with Sales.begin() as sales:
                sales.upsert(sale())
            on_commit(lambda: respond("after"))

    await direct()
    assert log == ["direct:0"]  # a plain reply goes out before the commit
    db.reset()
    await after_commit()
    assert log[-1] == "after:1"


@async_test
async def test_handler_failure_rolls_back_and_the_error_reply_follows_the_rollback(db: Db) -> None:
    async def handler() -> None:
        async with orm_session(db.engine):
            async with Sales.begin() as sales:
                sales.upsert(sale())
            msg = "boom"
            raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="boom"):
        await handler()
    assert db.counts() == (0, 0)


@async_test
async def test_scope_that_never_queries_holds_no_connection(db: Db) -> None:
    engine = db.small_engine()
    async with orm_session(engine):
        assert engine.pool.checkedout() == 0  # ty: ignore[unresolved-attribute]


@async_test
async def test_two_scopes_waiting_on_the_network_starve_a_pool_of_one(db: Db) -> None:
    engine = db.small_engine()

    async def slow() -> None:
        async with Sales.begin(engine) as sales:
            sales.qs().count()
            await asyncio.sleep(0.8)

    outcomes = await asyncio.gather(slow(), slow(), return_exceptions=True)
    assert any(isinstance(o, sa.exc.TimeoutError) for o in outcomes)


@async_test
async def test_short_scopes_around_the_database_work_do_not_starve_the_pool(db: Db) -> None:
    engine = db.small_engine()

    async def short() -> None:
        async with Sales.begin(engine) as sales:
            sales.qs().count()
        await asyncio.sleep(0.8)  # the wait happens outside the scope

    outcomes = await asyncio.gather(short(), short(), return_exceptions=True)
    assert outcomes == [None, None]


# ---- scope lifecycle ----


@async_test
async def test_scope_exited_in_another_task_raises(db: Db) -> None:
    scope = Sales.begin(db.engine)
    scope.__enter__()
    errors: list[BaseException] = []

    async def other() -> None:
        try:
            scope.__exit__(None, None, None)
        except RuntimeError as error:
            errors.append(error)

    await asyncio.create_task(other())
    assert "must exit in the thread and asyncio task that entered it" in str(errors[0])
    scope.__exit__(None, None, None)


def test_scope_span_wraps_each_outermost_scope_only(db: Db) -> None:
    events: list[str] = []

    class Span:
        def __enter__(self) -> Self:
            events.append("enter")
            return self

        def __exit__(self, *args: object) -> None:
            events.append("exit")

    with bound(db.engine, scope_span=Span), Sales.begin() as sales:
        events.append("body")
        with Props.begin():
            events.append("nested")
        sales.upsert(sale())
    assert events == ["enter", "body", "nested", "exit"]


def _recording_span(seen: list[BaseException | None]) -> Callable[[], AbstractContextManager[None]]:
    @contextmanager
    def span() -> Iterator[None]:
        try:
            yield
        except BaseException as exc:
            seen.append(exc)
            raise
        seen.append(None)

    return span


def test_scope_span_sees_none_on_success(db: Db) -> None:
    seen: list[BaseException | None] = []
    with bound(db.engine, scope_span=_recording_span(seen)), Sales.begin() as sales:
        sales.upsert(sale())
    assert seen == [None]


def test_scope_span_receives_the_body_exception(db: Db) -> None:
    seen: list[BaseException | None] = []
    with pytest.raises(RuntimeError, match="boom"), bound(db.engine, scope_span=_recording_span(seen)), Sales.begin():
        msg = "boom"
        raise RuntimeError(msg)
    assert [type(exc) for exc in seen] == [RuntimeError]


def test_scope_span_receives_scope_rolled_back(db: Db) -> None:
    seen: list[BaseException | None] = []
    with (
        pytest.raises(ScopeRolledBack),
        bound(db.engine, scope_span=_recording_span(seen)),
        Sales.begin(),
        pytest.raises(RuntimeError, match="inner"),
        Props.begin(savepoint=False),
    ):
        msg = "inner"
        raise RuntimeError(msg)
    assert [type(exc) for exc in seen] == [ScopeRolledBack]


def test_scope_span_receives_a_commit_failure(db: Db, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[BaseException | None] = []

    def failing_commit(self: Session) -> None:
        msg = "commit failed"
        raise RuntimeError(msg)

    monkeypatch.setattr(Session, "commit", failing_commit)
    with (
        pytest.raises(RuntimeError, match="commit failed"),
        bound(db.engine, scope_span=_recording_span(seen)),
        Sales.begin() as sales,
    ):
        sales.upsert(sale())
    assert [str(exc) for exc in seen] == ["commit failed"]


# ---- the SQLite transaction fix ----


def test_first_statement_savepoint_is_undone_by_an_outer_rollback(db: Db) -> None:
    # the nested block is the first statement of the scope, which breaks on pysqlite without the scope-local BEGIN
    with pytest.raises(RuntimeError, match="boom"), orm_session(db.engine):
        with Sales.begin() as sales:
            sales.upsert(sale())
        msg = "boom"
        raise RuntimeError(msg)
    assert db.counts() == (0, 0)


def test_scoped_begin_is_a_repository_over_a_sqlmodel_session(db: Db) -> None:
    with Sales.begin(db.engine) as sales:
        assert isinstance(sales.session, Session)
        sales.upsert(sale())
        assert sales.qs().count() == 1
