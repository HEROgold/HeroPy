"""Workers for handling background tasks."""

from __future__ import annotations

import asyncio
import multiprocessing as mp
import signal
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, AsyncIterator, Awaitable, Callable, Generator, Iterator
from typing import TYPE_CHECKING, Self, cast

if TYPE_CHECKING:
    from multiprocessing.queues import JoinableQueue
    from types import FrameType, TracebackType

type Action = Callable[[], None]


def _worker(task_q: JoinableQueue[Action | None], err_q: mp.Queue[BaseException]) -> None:
    while True:
        action = task_q.get()
        try:
            if action is None:
                return
            action()
        except BaseException as exc:  # noqa: BLE001
            err_q.put(exc)
        finally:
            task_q.task_done()


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
        self._processes: list[mp.Process] = []
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Register signal handlers to close on SIGTERM/SIGINT."""

        def _handle_signal(_signum: int, _frame: FrameType | None) -> None:
            self.close()

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

    def start(self) -> None:
        """Start the worker processes if they haven't been started already."""
        if self._processes:
            return
        self._processes = [
            cast("mp.Process", self.ctx.Process(target=_worker, args=(self._tasks, self._errors))) for _ in range(self.size)
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
    def submit(self, action: Action) -> None | Awaitable[None]:
        """Submit a task to be executed by the worker processes."""

    @abstractmethod
    def pop_errors(self) -> Iterator[BaseException] | AsyncIterator[BaseException]:
        """Retrieve all errors that occurred during task execution."""

    @abstractmethod
    def wait(self) -> None | Awaitable[None]:
        """Wait for all worker processes to finish."""


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
        while not self._errors.empty():
            yield self._errors.get()

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
        while not self._errors.empty():
            yield self._errors.get()

    async def wait(self) -> None:
        """Wait for all worker processes to finish."""
        await asyncio.to_thread(self._tasks.join)
