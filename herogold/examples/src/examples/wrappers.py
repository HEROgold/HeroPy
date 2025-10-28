from typing import Any, Callable


def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
    """Wrapper Doc."""
    def inner(*args: P.args, **kwargs: P.kwargs) -> F:
        return func(*args, **kwargs)
    return inner


def decorator_factory(argument1: Any): # how to type hint this?
    def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
        def inner(*args: P.args, **kwargs: P.kwargs) -> F:
            return func(*args, **kwargs)
        return inner
    return wrapper
