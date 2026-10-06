from __future__ import annotations

from collections import deque
from functools import partial
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


class CallQueue[**P, R]:
    """Queue calls to `func` and yield their results in submission order.

    Arguments are checked against `func`'s signature through the ParamSpec, so
    `submit` accepts exactly what `func` accepts.

    Usage:
    ```py
        def add(x: int, y: int) -> int:
            return x + y
        q = CallQueue(add)
        q.submit(1, 2)
        q.submit(x=3, y=4)
        results = list(q)  # results == [3, 7]
    ```
    """

    def __init__(self, func: Callable[P, R], /) -> None:
        """Store the callable that every queued call is made against."""
        self._func = func
        self._pending: deque[Callable[[], R]] = deque()

    def __len__(self) -> int:
        """Return the number of queued calls."""
        return len(self._pending)

    def __iter__(self) -> Iterator[R]:
        """Return the queue itself; iterating drains it."""
        return self

    def __next__(self) -> R:
        """Run the oldest queued call and return its result."""
        if not self._pending:
            raise StopIteration
        return self._pending.popleft()()

    def submit(self, *args: P.args, **kwargs: P.kwargs) -> Self:
        """Queue a call to `func` with the given arguments."""
        self._pending.append(partial(self._func, *args, **kwargs))
        return self


# Example
if __name__ == "__main__":

    def add(x: int, y: int) -> int:
        return x + y

    q = CallQueue(add)
    q.submit(1, 1).submit(x=2, y=9)
    for result in q:
        print(f"Result: {result}")
