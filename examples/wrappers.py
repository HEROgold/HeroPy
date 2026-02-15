from collections.abc import Callable
from functools import wraps


def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs) -> F:
        return func(*args, **kwargs)
    return inner

def decorator_factory[**P, F](*args: P.args, **kwargs: P.kwargs) -> Callable[[Callable[P, F]], Callable[P, F]]:
    def wrapper(func: Callable[P, F]) -> Callable[P, F]:
        @wraps(func)
        def inner(*_: P.args, **__: P.kwargs) -> F:
            return func(*args, **kwargs)  # type: ignore[return-value]
        return inner  # type: ignore[return-value]
    return wrapper
