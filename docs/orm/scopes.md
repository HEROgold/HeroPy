# Scopes

A scope is one transaction around a block of code. The outermost scope opens a session, commits when the block succeeds and rolls back when it fails. The ORM never commits a session it did not open (see [ADR 0001](../adr/0001-orm-commits-only-owned-sessions.md)).

## Binding an engine

```python
from sqlalchemy import create_engine

from herogold.orm import bind

bind(create_engine("postgresql+psycopg:///app"))
```

`bind(engine)` sets the default engine for scopes. `bind(None)` unbinds it. A scope that finds no engine, bound or passed, raises `NoEngineBoundError`. In tests, `with bound(engine): ...` binds for the block and restores the previous binding.

## orm_session and Scoped.begin

```python
from herogold.orm import Repository, Scoped, orm_session


class Sales(Scoped, Repository[Sale]):
    pass


with orm_session() as session:  # a Session
    session.add(Sale(title="spring"))

with Sales.begin() as sales:  # a Sales built on the session
    sales.add(Sale(title="summer"))
```

Both return a scope that works as `with` and as `async with`. The engine is, in order, the `engine` argument, the enclosing scope's engine, or the bound one. The session uses `expire_on_commit=False`, so rows stay readable after the commit.

`Scoped.begin()` takes the same arguments as `orm_session()` and yields `cls(session)`. A service class can use `Scoped` too, as long as it takes a session in its constructor.

## Nesting

A scope opened inside another scope joins it, if it runs in the same thread and asyncio task and uses the same engine (or none). It does not open a second transaction. The reasons are in [ADR 0003](../adr/0003-a-nested-begin-joins-the-outer-scope.md).

```python
with orm_session() as outer:
    outer.add(Sale(title="kept"))
    try:
        with orm_session() as inner:  # runs in a SAVEPOINT
            inner.add(Sale(title="undone"))
            raise ValueError
    except ValueError:
        pass
# commits "kept" only
```

- A joined block runs in a SAVEPOINT. If it fails and the outer code catches the error, only the inner block is undone. Only the outermost scope commits.
- `savepoint=False` joins without a SAVEPOINT. If that block fails, the scope becomes rollback-only. The outermost block then rolls back and raises `ScopeRolledBack`, even if the outer code caught the error.
- `durable=True` raises `RuntimeError` when a scope is already open. Use it for code that must be the outermost transaction.
- `new=True` opens an independent session and transaction, for example an audit row that must survive the outer rollback. It defaults to the outer scope's engine.
- Another engine, another thread or another asyncio task never joins. It starts its own scope.

### SQLite

pysqlite starts a transaction only before a data-changing statement. Without a fix, a SAVEPOINT would be the first statement, `RELEASE` would then commit, and an outer rollback could not undo the nested work. A joined scope on pysqlite therefore sends `BEGIN` itself before it opens the SAVEPOINT, if none is open. Other drivers are not touched.

## on_commit

```python
from herogold.orm import on_commit

with orm_session() as session:
    session.add(Sale(title="spring"))
    on_commit(lambda: print("committed"))
```

`on_commit(fn)` runs `fn` after the outermost scope commits, in registration order. A rollback discards it, and so does a rolled-back SAVEPOINT block that registered it. Outside a scope it runs at once.

If a callback raises, the others still run, and the scope raises an `ExceptionGroup` after all have run. The commit has already happened.

A callback may be a coroutine function only when the outermost scope is an `async with`.

```python
async def notify() -> None: ...


async with orm_session() as session:
    session.add(Sale(title="spring"))
    on_commit(notify)  # awaited after the commit
```

In a plain `with`, registering a coroutine function raises `TypeError`, and so does a callback that returns an awaitable.

## transactional

`@transactional` runs a sync or async function in a scope. It works bare or with arguments.

```python
from herogold.orm import transactional


@transactional
async def sell(title: str) -> None:
    async with Sales.begin() as sales:  # joins the decorator's scope
        sales.add(Sale(title=title))


@transactional(commit_on=(Refused,))
def refuse(sale_id: int) -> None: ...
```

- Any exception rolls the scope back. An exception listed in `commit_on` commits first and is then raised again.
- `engine` is an `Engine`, or `None` for the bound engine, or a function of the first argument, such as `engine=lambda cog: cog.bind`. `new`, `savepoint` and `durable` are those of `orm_session()`.
- A decorated function called from another joins the caller's scope.
- The decorator keeps the function's name, signature and docstring, and an async function stays a coroutine function.

Stacking rule. Put `@transactional` directly on the function, below decorators such as `@Cog.command`. A class or other object that is not a function or method raises `TypeError` when the decorator is applied.

`commit_on` applies only to the scope that sees the exception. If a decorated function calls another decorated function and the inner one raises a listed exception, the inner scope joins and does not roll back. The exception then passes through the outer function, which rolls back unless it lists the exception too.

## scope_span

`bind(engine, scope_span=fn)` wraps each outermost scope in a context manager, for tracing or timing. `fn` takes no arguments and returns a context manager. The ORM enters it when the outermost scope opens and exits it after the commit or rollback. On a failure, including a rollback, `ScopeRolledBack` or a failed commit, the span's exit receives the real exception, so a span written with `@contextmanager` sees it raised at the `yield`. After a successful commit it receives none. Joined scopes do not create a span.

```python
from contextlib import contextmanager


@contextmanager
def span():
    started = time.perf_counter()
    try:
        yield
    finally:
        logger.info("scope took %.3f s", time.perf_counter() - started)


bind(engine, scope_span=span)
```

## Known limits

- Forward references resolve by `eval` against the module globals of the model. A name that exists only inside a function cannot be resolved, so declare models at module level.
- Loading is sync only. An async session must read relationships inside `await session.run_sync(...)`. Plain attribute access on an async session raises `AsyncLoadError`.
- `create_all` and Alembic must run after `configure()`. Before that, the generated `<name>_id` columns do not exist, and the ORM warns on first use, on `create_all` and when it reads an unconfigured relationship.
- `Relationship[T]()` and the old `Relationship(Target)` form coexist. Type checkers type them differently: the typed form gives `T` on instances, the old form gives `Target | None`. Issue #112 tracks this.
- A scope must exit in the thread and asyncio task that entered it. Entering in one task and exiting in another raises `RuntimeError`.
