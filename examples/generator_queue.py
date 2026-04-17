from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


def queue[**P, R](func: Callable[P, R], /) -> Generator[R | None, *P | None, NoReturn]:
    """Send arguments for callable `f` and yield the result of calling `f`.


    Usage:
    ```py
        def add(x: int, y: int) -> int:
            return x + y
        q = queue(add)
        x = next(q) or 0  # Prime the generator
        q.send((x, 3))  # Returns None, but queues the arguments for processing
        result = next(q)  # result == 3
    ```

    Tip:
        - Using `next(q) or 0` helps to prime the generator, using 0 as a fallback for when the generator yields `None`.
    """
    queue: list[P.args | P.kwargs] = []
    input_ = yield None  # Prime the generator
    while True:
        match input_, queue[0] if queue else None:
            case dict() as kwargs, _value:
                queue.append(kwargs)
                input_ = yield None
            case tuple() as args, _value:
                queue.append(args)
                input_ = yield None
            # *args, **kwargs are mutually exclusive. so we ignore missing-argument.
            case None, dict() as kwargs:
                input_ = yield func(**kwargs)  # ty:ignore[missing-argument]
                queue.pop(0)
            case None, tuple() as args:
                input_ = yield func(*args)  # ty:ignore[missing-argument]
                queue.pop(0)

# Example
if __name__ == "__main__":
    def add(x: int, y: int) -> int:
        return x + y

    q = queue(add)
    while (x := next(q) or 1):
        print(f"Sending: {x}")
        q.send((x, 1))
        q.send({"x": x, "y": 9})
