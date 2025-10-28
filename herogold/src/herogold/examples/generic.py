from typing import Callable


def generic[T](i: T) -> T:
    """Typesafe generic function that returns the input value."""
    return i



def wrapper[F, **P](func: Callable[P, F]) -> Callable[P, F]:
    """Typesafe wrapper function that returns the original function."""
    def inner(*args: P.args, **kwargs: P.kwargs) -> F:
        return func(*args, **kwargs)
    return inner
