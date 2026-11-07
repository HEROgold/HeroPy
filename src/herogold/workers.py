"""Workers for handling background tasks."""

from __future__ import annotations

import asyncio
import multiprocessing as mp
import pickle
import signal
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable, Generator, Iterator
from multiprocessing.reduction import ForkingPickler
from typing import TYPE_CHECKING, Self, cast

if TYPE_CHECKING:
    from multiprocessing.queues import JoinableQueue
    from multiprocessing.sharedctypes import Synchronized
    from types import FrameType, TracebackType

type Action = Callable[[], None]


class BaseWorkerPool(ABC):
    """Base class for worker pools."""

    size: int
    ctx: mp.context.SpawnContext

    def __init__(self, size: int = 1, ctx: mp.context.SpawnContext | None = None) -> None:
        """Initialize the worker pool with the given size and multiprocessing context."""
        self.size = size
        self.ctx = ctx or mp.get_context("spawn")
        self._tasks: JoinableQueue[Action | None] = self.ctx.JoinableQueue()
        self._errors: mp.Queue[BaseException] = self.ctx.Queue()
        self._error_count: Synchronized[int] = self.ctx.Value("i", 0)
        self._errors_popped = 0
        self._processes: list[mp.Process] = []
        self._setup_signal_handlers()

    def start(self) -> None:
        """Start the worker processes if they haven't been started already."""
        if self._processes:
            return
        self._processes = [
            cast("mp.Process", self.ctx.Process(target=_worker, args=(self._tasks, self._errors, self._error_count)))
            for _ in range(self.size)
        ]
        for p in self._processes:
            p.start()

    def close(self, *, force: bool = False) -> None:
        """Signal the worker processes to exit and wait for them to finish."""
        if force:
            for p in self._processes:
                if p.is_alive():
                    p.terminate()
        else:
            for _ in self._processes:
                self._tasks.put(None)
        for p in self._processes:
            p.join()

    @abstractmethod
    def submit(self, action: Action) -> Awaitable[None] | None:
        """Submit a task to be executed by the worker processes."""

    @abstractmethod
    def pop_errors(self) -> Iterator[BaseException] | AsyncIterator[BaseException]:
        """Retrieve all errors that occurred during task execution."""

    @abstractmethod
    def wait(self) -> Awaitable[None] | None:
        """Wait for all worker processes to finish."""

    def _setup_signal_handlers(self) -> None:
        """Register signal handlers to close on SIGTERM/SIGINT."""

        def _handle_signal(_signum: int, _frame: FrameType | None) -> None:
            self.close()

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)


class WorkerPool(BaseWorkerPool):
    """A pool of worker processes for handling background tasks."""

    def __enter__(self) -> Self:
        """Context manager entry."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit — close on exit."""
        self.close(force=exc_type is not None)

    def submit(self, action: Action) -> None:
        """Submit a task to be executed by the worker processes."""
        self._tasks.put(action)

    def pop_errors(self) -> Generator[BaseException]:
        """Retrieve all errors that occurred during task execution."""
        while self._errors_popped < self._error_count.value:
            error = self._errors.get()
            self._errors_popped += 1
            yield error

    def wait(self) -> None:
        """Wait for all worker processes to finish."""
        self._tasks.join()


class AsyncWorkerPool(BaseWorkerPool):
    """A pool of worker processes for handling background tasks."""

    async def __aenter__(self) -> Self:
        """Context manager entry."""
        self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit — close on exit."""
        self.close(force=exc_type is not None)

    async def submit(self, action: Action) -> None:
        """Submit a task to be executed by the worker processes."""
        self._tasks.put(action)

    async def pop_errors(self) -> AsyncGenerator[BaseException]:
        """Retrieve all errors that occurred during task execution."""
        while self._errors_popped < self._error_count.value:
            error = await asyncio.to_thread(self._errors.get)
            self._errors_popped += 1
            yield error

    async def wait(self) -> None:
        """Wait for all worker processes to finish."""
        await asyncio.to_thread(self._tasks.join)


def _picklable(exc: BaseException) -> BaseException:
    """Return exc if it can be pickled, otherwise a RuntimeError describing it.

    A queue pickles its items in a feeder thread, and drops an item that fails to pickle.
    The parent would then wait forever for an error it counted.
    """
    try:
        ForkingPickler.dumps(exc)
    except (pickle.PicklingError, TypeError, AttributeError):
        return RuntimeError(repr(exc))
    return exc


def _worker(
    task_q: JoinableQueue[Action | None],
    err_q: mp.Queue[BaseException],
    error_count: Synchronized[int],
) -> None:
    while True:
        action = task_q.get()
        try:
            if action is None:
                return
            action()
        except BaseException as exc:  # noqa: BLE001
            err_q.put(_picklable(exc))
            # Count the error only after it is queued. The parent reads this count, not Queue.empty(),
            # because a queued item can still be in the feeder thread's buffer.
            with error_count.get_lock():
                error_count.value += 1
        finally:
            task_q.task_done()
