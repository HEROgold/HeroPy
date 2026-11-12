"""Session scopes: one transaction per outermost block, SAVEPOINTs for blocks that join it.

`orm_session()` and `Scoped.begin()` return a scope that works as `with` and as `async with`. The outermost scope opens a
session, commits it on success and rolls it back on failure. A scope opened inside it, in the same thread and asyncio task
on the same engine, joins it instead of opening a second transaction. The ORM never commits a session it did not open.
"""

from __future__ import annotations

import asyncio
import inspect
import threading
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self, cast

from sqlmodel import Session

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from types import TracebackType

    from sqlalchemy import Engine
    from sqlalchemy.orm import SessionTransaction

__all__ = [
    "NoEngineBoundError",
    "ScopeRolledBack",
    "Scoped",
    "bind",
    "bound",
    "on_commit",
    "orm_session",
]

type ScopeSpan = Callable[[], AbstractContextManager[object]]
type Callback = Callable[[], object]


class NoEngineBoundError(RuntimeError):
    """Raised when a scope needs an engine and none was passed or bound."""


class ScopeRolledBack(RuntimeError):  # noqa: N818
    """Raised when the outermost scope rolled back because a nested `savepoint=False` block failed."""


_engine: Engine | None = None
_scope_span: ScopeSpan | None = None


def bind(engine: Engine | None, *, scope_span: ScopeSpan | None = None) -> None:
    """Set the default engine for scopes, and optionally a `scope_span` that wraps each outermost scope.

    `scope_span` is a callable returning a context manager. Pass `None` as the engine to unbind.
    """
    global _engine, _scope_span
    _engine, _scope_span = engine, scope_span


@contextmanager
def bound(engine: Engine | None, *, scope_span: ScopeSpan | None = None) -> Generator[None]:
    """Bind a default engine for the block, then restore the previous binding. Meant for tests."""
    previous = _engine, _scope_span
    bind(engine, scope_span=scope_span)
    try:
        yield
    finally:
        bind(previous[0], scope_span=previous[1])


type _Owner = tuple[int, asyncio.Task[Any] | None]


def _owner() -> _Owner:
    """Return the thread and asyncio task the caller runs in."""
    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    return threading.get_ident(), task


@dataclass(eq=False)
class _Scope:
    session: Session
    engine: Engine
    owner: _Owner
    is_async: bool
    rollback_only: bool = False
    callbacks: list[Callback] = field(default_factory=list)


_ambient: ContextVar[_Scope | None] = ContextVar("herogold_orm_scope", default=None)


def _begin_sqlite_transaction(session: Session) -> None:
    """Start the transaction ourselves on pysqlite, so a SAVEPOINT is not the statement that starts it.

    pysqlite begins a transaction only before DML. A SAVEPOINT issued first would start it, and RELEASE would then commit
    it, so an outer rollback could not undo the nested work.
    """
    connection = session.connection()
    dbapi_connection = connection.connection.dbapi_connection
    if connection.dialect.driver == "pysqlite" and not cast("Any", dbapi_connection).in_transaction:
        connection.exec_driver_sql("BEGIN")


class _ScopeCM[T]:
    """One scope, usable as `with` and as `async with`. Only `async with` can await coroutine callbacks."""

    def __init__(
        self,
        engine: Engine | None = None,
        *,
        new: bool = False,
        savepoint: bool = True,
        durable: bool = False,
        factory: Callable[[Session], T] | None = None,
    ) -> None:
        """Describe the scope. Nothing opens until `with` or `async with` starts."""
        self.engine, self.new, self.savepoint, self.durable, self.factory = engine, new, savepoint, durable, factory
        self._scope: _Scope | None = None
        self._joined = False
        self._mark = 0
        self._nested: SessionTransaction | None = None
        self._token: Token[_Scope | None] | None = None
        self._span: AbstractContextManager[object] | None = None
        self._entered_by: _Owner | None = None

    def _enter(self, *, is_async: bool) -> Session:
        owner = _owner()
        ambient = _ambient.get()
        mine = ambient is not None and ambient.owner == owner
        if self.durable and mine:
            msg = "durable=True: this block must be the outermost scope, but one is already open"
            raise RuntimeError(msg)
        self._entered_by = owner
        if ambient is not None and mine and not self.new and (self.engine is None or self.engine is ambient.engine):
            self._joined = True
            self._scope = ambient
            self._mark = len(ambient.callbacks)
            if self.savepoint:
                _begin_sqlite_transaction(ambient.session)
                self._nested = ambient.session.begin_nested()
            return ambient.session
        engine = self.engine or (ambient.engine if mine and ambient else None) or _engine
        if engine is None:
            msg = "no engine given and none bound: call bind(engine) or pass the engine"
            raise NoEngineBoundError(msg)
        if _scope_span is not None:
            self._span = _scope_span()
            self._span.__enter__()
        session = Session(engine, expire_on_commit=False)
        self._scope = _Scope(session, engine, owner, is_async)
        self._token = _ambient.set(self._scope)
        return session

    def _check_same_task(self) -> None:
        if self._entered_by != _owner():
            msg = "a scope must exit in the thread and asyncio task that entered it"
            raise RuntimeError(msg)

    def _close_span(self, failure: BaseException | None) -> None:
        """Leave the `scope_span` context with the real exception, or with Nones when the scope succeeded."""
        if self._span is None:
            return
        if failure is None:
            self._span.__exit__(None, None, None)
        else:
            self._span.__exit__(type(failure), failure, failure.__traceback__)

    def _exit(self, exc: BaseException | None) -> list[Callback]:
        """Finish the scope and return the callbacks to run, which is empty unless the outermost scope committed."""
        self._check_same_task()
        scope = cast("_Scope", self._scope)
        if self._joined:
            if self.savepoint:
                nested = cast("SessionTransaction", self._nested)
                if exc is None:
                    nested.commit()
                else:
                    nested.rollback()
                    del scope.callbacks[self._mark :]
            elif exc is not None:
                scope.rollback_only = True
            return []
        callbacks: list[Callback] = []
        failure = exc
        try:
            try:
                if exc is not None:
                    scope.session.rollback()
                    scope.callbacks.clear()
                elif scope.rollback_only:
                    scope.session.rollback()
                    scope.callbacks.clear()
                    msg = "a nested block without a savepoint failed, so the whole transaction was rolled back"
                    raise ScopeRolledBack(msg)  # noqa: TRY301
                else:
                    scope.session.commit()
                    callbacks = list(scope.callbacks)
            except BaseException as error:
                failure = error  # a rollback error or a failed commit reaches the span too
                scope.session.rollback()
                scope.callbacks.clear()
                raise
            finally:
                _ambient.reset(cast("Token[_Scope | None]", self._token))
                scope.session.close()
        finally:
            self._close_span(failure)
        return callbacks

    def _wrap(self, session: Session) -> T:
        return self.factory(session) if self.factory else cast("T", session)

    def __enter__(self) -> T:
        """Open or join the scope and return the session, or the repository built on it."""
        return self._wrap(self._enter(is_async=False))

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None) -> bool:
        """Commit or roll back, then run the callbacks. A coroutine returned by a callback raises `TypeError`."""
        errors: list[Exception] = []
        for callback in self._exit(exc):
            try:
                result = callback()
                if inspect.isawaitable(result):
                    if inspect.iscoroutine(result):
                        result.close()
                    msg = "a callback returned a coroutine; use `async with` so it can be awaited"
                    raise TypeError(msg)  # noqa: TRY301
            except Exception as error:  # noqa: BLE001
                errors.append(error)
        if errors:
            msg = "on_commit callbacks failed after the commit"
            raise ExceptionGroup(msg, errors)
        return False

    async def __aenter__(self) -> T:
        """Open or join the scope and return the session, or the repository built on it."""
        return self._wrap(self._enter(is_async=True))

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        """Commit or roll back, then run and await the callbacks in registration order."""
        errors: list[Exception] = []
        for callback in self._exit(exc):
            try:
                result = callback()
                if inspect.isawaitable(result):
                    await result
            except Exception as error:  # noqa: BLE001
                errors.append(error)  # every callback runs, and the commit is already done
        if errors:
            msg = "on_commit callbacks failed after the commit"
            raise ExceptionGroup(msg, errors)
        return False


def orm_session(
    engine: Engine | None = None,
    *,
    new: bool = False,
    savepoint: bool = True,
    durable: bool = False,
) -> _ScopeCM[Session]:
    """Return a scope that yields a session.

    Outermost, it opens a session on `engine` (else the enclosing scope's engine, else the bound one), commits on success
    and rolls back on failure. Inside another scope of the same thread, task and engine it joins that scope in a SAVEPOINT.
    `new=True` opens an independent transaction. `savepoint=False` joins without a SAVEPOINT, and a failure then makes the
    outermost scope roll back and raise `ScopeRolledBack`. `durable=True` raises if a scope is already open.
    """
    return _ScopeCM(engine, new=new, savepoint=savepoint, durable=durable)


class Scoped:
    """Mixin for a `Repository` subclass that adds `begin()`."""

    @classmethod
    def begin(
        cls,
        engine: Engine | None = None,
        *,
        new: bool = False,
        savepoint: bool = True,
        durable: bool = False,
    ) -> _ScopeCM[Self]:
        """Return a scope that yields `cls(session)`. The arguments are those of `orm_session`."""
        return _ScopeCM(engine, new=new, savepoint=savepoint, durable=durable, factory=cast("Any", cls))


def on_commit(fn: Callback) -> None:
    """Run `fn` after the outermost scope commits, in registration order.

    A rollback discards it, also when only the savepoint block that registered it rolled back. Outside a scope it runs now.
    A coroutine function needs the outermost scope to be an `async with`, else `TypeError`.
    """
    scope = _ambient.get()
    in_scope = scope is not None and scope.owner == _owner()
    if inspect.iscoroutinefunction(fn):
        if scope is None or not in_scope:
            msg = "outside a scope there is nothing to await a coroutine callback"
            raise TypeError(msg)
        if not scope.is_async:
            msg = "a coroutine callback needs `async with`, but the outermost scope is a plain `with`"
            raise TypeError(msg)
    if scope is None or not in_scope:
        fn()
        return
    scope.callbacks.append(fn)
