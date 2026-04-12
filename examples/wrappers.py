from __future__ import annotations

from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs) -> F:
        return func(*args, **kwargs)
    return inner

def decorator_factory[**P, F](*args: P.args, **kwargs: P.kwargs) -> Callable[[Callable[P, F]], Callable[P, F]]:
    def wrapper[F](func: Callable[P, F]) -> Callable[P, F]:
        @wraps(func)
        def inner(*_: P.args, **__: P.kwargs) -> F:
            return func(*args, **kwargs)
        return inner
    return wrapper
