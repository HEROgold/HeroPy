"""The `transactional` decorator: run a sync or async function in one session scope.

The function runs in `orm_session()`'s kind of scope. Any exception rolls the scope back. Exceptions listed in `commit_on`
commit it first and are then raised again. A decorated function called from another joins the caller's scope.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Protocol, cast, overload

from herogold.asynchronous import dual_wraps
from herogold.orm.scopes import _ScopeCM

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy import Engine

__all__ = ["transactional"]

type EngineSource = Engine | Callable[[Any], Engine | None] | None


class _Decorator(Protocol):
    def __call__[**P, R](self, func: Callable[P, R], /) -> Callable[P, R]: ...


@overload
def transactional[**P, R](
    func: Callable[P, R],
    *,
    engine: EngineSource = None,
    commit_on: tuple[type[BaseException], ...] = (),
    new: bool = False,
    savepoint: bool = True,
    durable: bool = False,
) -> Callable[P, R]: ...
@overload
def transactional(
    func: None = None,
    *,
    engine: EngineSource = None,
    commit_on: tuple[type[BaseException], ...] = (),
    new: bool = False,
    savepoint: bool = True,
    durable: bool = False,
) -> _Decorator: ...
def transactional(  # noqa: PLR0913
    func: Callable[..., Any] | None = None,
    *,
    engine: EngineSource = None,
    commit_on: tuple[type[BaseException], ...] = (),
    new: bool = False,
    savepoint: bool = True,
    durable: bool = False,
) -> Any:
    """Run the function in a scope. Works bare, as `@transactional`, and with arguments.

    `engine` is an `Engine`, `None` for the bound engine, or a function of the first argument, such as
    `lambda cog: cog.bind`. A function is called with the first positional argument, so calling the decorated
    function with keyword arguments only raises `TypeError`. `new`, `savepoint` and `durable` are those of
    `orm_session`. Put it directly on the function, below decorators such as `@Cog.command`.
    """

    def decorate(target: Callable[..., Any]) -> Callable[..., Any]:
        if not inspect.isroutine(target):
            msg = (
                f"@transactional wraps a function, but got {type(target).__name__}; "
                "put it directly on the function, below @Cog.command and friends"
            )
            raise TypeError(msg)

        def scope(args: tuple[Any, ...]) -> _ScopeCM[Any]:
            if callable(engine) and not args:
                msg = (
                    f"{target.__qualname__} was called without positional arguments, but its engine= function "
                    "needs the first positional argument; pass it positionally"
                )
                raise TypeError(msg)
            chosen = cast("Engine | None", engine(args[0]) if callable(engine) else engine)
            return _ScopeCM(chosen, new=new, savepoint=savepoint, durable=durable)

        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            held: BaseException | None = None
            with scope(args):
                try:
                    return target(*args, **kwargs)
                except commit_on as exc:
                    held = exc  # leave the scope normally, so it commits
            raise cast("BaseException", held)

        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            held: BaseException | None = None
            async with scope(args):
                try:
                    return await target(*args, **kwargs)
                except commit_on as exc:
                    held = exc
            raise cast("BaseException", held)

        return cast("Any", dual_wraps)(target, sync_wrapper, async_wrapper)

    return decorate if func is None else decorate(func)
