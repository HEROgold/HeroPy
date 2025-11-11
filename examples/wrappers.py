from functools import wraps
from typing import Any, Callable


def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:  # noqa: D103
    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs) -> F:
        return func(*args, **kwargs)
    return inner


def decorator_factory(_arg: Any) -> Callable[..., Callable[...]]:  # noqa: ANN401, D103
    def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
        @wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> F:
            return func(*args, **kwargs)
        return inner
    return wrapper
