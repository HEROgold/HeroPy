from collections.abc import Callable
from functools import wraps
from typing import Any


def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs) -> F:
        return func(*args, **kwargs)
    return inner

def decorator_factory(_arg: Any) -> Callable[..., Callable[..., Any]]:  # noqa: ANN401
    def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
        @wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> F:
            return func(*args, **kwargs)
        return inner
    return wrapper
