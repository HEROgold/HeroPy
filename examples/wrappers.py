from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

type Decorator[**P, R] = Callable[P, R]
type DecoratorFactory[**P, R] = Callable[[Callable[P, R]], Decorator[P, R]]


def wrapper[F, **P](func: Callable[P, F]) -> Decorator[P, F]:
    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs) -> F:
        return func(*args, **kwargs)

    return inner


def decorator_factory[**P, F](*args: P.args, **kwargs: P.kwargs) -> DecoratorFactory[P, F]:
    def wrapper(func: Decorator[P, F]) -> Decorator[P, F]:
        @wraps(func)
        def inner(*_: P.args, **__: P.kwargs) -> F:
            return func(*args, **kwargs)

        return inner

    return wrapper
