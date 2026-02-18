"""Queue Abstract Data Type.

Implementations of the queue ADT using both a fixed-size array and a
linked list. Both support enqueue, dequeue, peek, is_empty, len, and iter.

Reference: https://en.wikipedia.org/wiki/Queue_(abstract_data_type)

Complexity:
    Time:  O(1) for enqueue/dequeue/peek (amortized for ArrayQueue)
    Space: O(n)
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterator

T = TypeVar("T")


class AbstractQueue(Generic[T], metaclass=ABCMeta):
    """Abstract base class for queue implementations."""

    def __init__(self) -> None:
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        """Check if the queue is empty.

        Returns:
            True if the queue has no elements.

        """
        return self._size == 0

    @abstractmethod
    def enqueue(self, value: T) -> None:
        pass

    @abstractmethod
    def dequeue(self) -> T:
        pass

    @abstractmethod
    def peek(self) -> T:
        pass

    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        pass


class ArrayQueue(AbstractQueue[T]):
    """Queue implemented with a dynamic array.

    Examples:
        >>> q = ArrayQueue()
        >>> q.enqueue(1)
        >>> q.dequeue()
        1

    """

    def __init__(self, capacity: int = 10) -> None:
        """Initialize with a fixed-capacity array.

        Args:
            capacity: Initial capacity of the underlying array.

        """
        super().__init__()
        self._array: list[T | None] = [None] * capacity
        self._front = 0
        self._rear = 0

    def __iter__(self) -> Iterator[T]:
        probe = self._front
        while True:
            if probe == self._rear:
                return
            yield self._array[probe]  # type: ignore[misc]
            probe += 1

    def enqueue(self, value: T) -> None:
        """Add an item to the rear of the queue.

        Args:
            value: The value to enqueue.

        """
        if self._rear == len(self._array):
            self._expand()
        self._array[self._rear] = value
        self._rear += 1
        self._size += 1

    def dequeue(self) -> T:
        """Remove and return the front item.

        Returns:
            The front element.

        Raises:
            IndexError: If the queue is empty.

        """
        if self.is_empty():
            msg = "Queue is empty"
            raise IndexError(msg)
        value = self._array[self._front]
        self._array[self._front] = None
        self._front += 1
        self._size -= 1
        return value  # type: ignore[return-value]

    def peek(self) -> T:
        """Return the front element without removing it.

        Returns:
            The front element.

        Raises:
            IndexError: If the queue is empty.

        """
        if self.is_empty():
            msg = "Queue is empty"
            raise IndexError(msg)
        return self._array[self._front]  # type: ignore[return-value]

    def _expand(self) -> None:
        """Double the size of the underlying array."""
        self._array += [None] * len(self._array)


class QueueNode[T]:
    """A single node in a linked-list-based queue."""

    def __init__(self, value: T) -> None:
        self.value = value
        self.next: QueueNode[T] | None = None


class LinkedListQueue(AbstractQueue[T]):
    """Queue implemented with a singly linked list.

    Examples:
        >>> q = LinkedListQueue()
        >>> q.enqueue(1)
        >>> q.dequeue()
        1

    """

    def __init__(self) -> None:
        super().__init__()
        self._front: QueueNode[T] | None = None
        self._rear: QueueNode[T] | None = None

    def __iter__(self) -> Iterator[T]:
        probe = self._front
        while True:
            if probe is None:
                return
            yield probe.value
            probe = probe.next

    def enqueue(self, value: T) -> None:
        """Add an item to the rear of the queue.

        Args:
            value: The value to enqueue.

        """
        node = QueueNode(value)
        if self._front is None:
            self._front = node
            self._rear = node
        else:
            self._rear.next = node  # type: ignore[union-attr]
            self._rear = node
        self._size += 1

    def dequeue(self) -> T:
        """Remove and return the front item.

        Returns:
            The front element.

        Raises:
            IndexError: If the queue is empty.

        """
        if self.is_empty():
            msg = "Queue is empty"
            raise IndexError(msg)
        value = self._front.value  # type: ignore[union-attr]
        if self._front is self._rear:
            self._front = None
            self._rear = None
        else:
            self._front = self._front.next  # type: ignore[union-attr]
        self._size -= 1
        return value

    def peek(self) -> T:
        """Return the front element without removing it.

        Returns:
            The front element.

        Raises:
            IndexError: If the queue is empty.

        """
        if self.is_empty():
            msg = "Queue is empty"
            raise IndexError(msg)
        return self._front.value  # type: ignore[union-attr]
