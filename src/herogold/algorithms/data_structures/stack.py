"""Stack Abstract Data Type.

Implementations of the stack ADT using both a fixed-size array and a
linked list. Both support push, pop, peek, is_empty, len, iter, and str.

Reference: https://en.wikipedia.org/wiki/Stack_(abstract_data_type)

Complexity:
    Time:  O(1) for push/pop/peek (amortized for ArrayStack)
    Space: O(n)
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterator

T = TypeVar("T")


class AbstractStack(Generic[T], metaclass=ABCMeta):
    """Abstract base class for stack implementations."""

    def __init__(self) -> None:
        self._top = -1

    def __len__(self) -> int:
        return self._top + 1

    def __str__(self) -> str:
        result = " ".join(map(str, self))
        return "Top-> " + result

    def is_empty(self) -> bool:
        """Check if the stack is empty.

        Returns:
            True if the stack has no elements.

        """
        return self._top == -1

    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        pass

    @abstractmethod
    def push(self, value: T) -> None:
        pass

    @abstractmethod
    def pop(self) -> T:
        pass

    @abstractmethod
    def peek(self) -> T:
        pass


class ArrayStack(AbstractStack[T]):
    """Stack implemented with a dynamic array.

    Examples:
        >>> s = ArrayStack()
        >>> s.push(1)
        >>> s.pop()
        1

    """

    def __init__(self, size: int = 10) -> None:
        """Initialize with a fixed-size array.

        Args:
            size: Initial capacity of the underlying array.

        """
        super().__init__()
        self._array: list[T | None] = [None] * size

    def __iter__(self) -> Iterator[T]:
        probe = self._top
        while True:
            if probe == -1:
                return
            yield self._array[probe]  # type: ignore[misc]
            probe -= 1

    def push(self, value: T) -> None:
        """Push a value onto the stack.

        Args:
            value: The value to push.

        """
        self._top += 1
        if self._top == len(self._array):
            self._expand()
        self._array[self._top] = value

    def pop(self) -> T:
        """Remove and return the top element.

        Returns:
            The top element.

        Raises:
            IndexError: If the stack is empty.

        """
        if self.is_empty():
            msg = "Stack is empty"
            raise IndexError(msg)
        value = self._array[self._top]
        self._top -= 1
        return value  # type: ignore[return-value]

    def peek(self) -> T:
        """Return the top element without removing it.

        Returns:
            The top element.

        Raises:
            IndexError: If the stack is empty.

        """
        if self.is_empty():
            msg = "Stack is empty"
            raise IndexError(msg)
        return self._array[self._top]  # type: ignore[return-value]

    def _expand(self) -> None:
        """Double the size of the underlying array."""
        self._array += [None] * len(self._array)


class StackNode[T]:
    """A single node in a linked-list-based stack."""

    def __init__(self, value: T) -> None:
        self.value = value
        self.next: StackNode[T] | None = None


class LinkedListStack(AbstractStack[T]):
    """Stack implemented with a singly linked list.

    Examples:
        >>> s = LinkedListStack()
        >>> s.push(1)
        >>> s.pop()
        1

    """

    def __init__(self) -> None:
        super().__init__()
        self.head: StackNode[T] | None = None

    def __iter__(self) -> Iterator[T]:
        probe = self.head
        while True:
            if probe is None:
                return
            yield probe.value
            probe = probe.next

    def push(self, value: T) -> None:
        """Push a value onto the stack.

        Args:
            value: The value to push.

        """
        node = StackNode(value)
        node.next = self.head
        self.head = node
        self._top += 1

    def pop(self) -> T:
        """Remove and return the top element.

        Returns:
            The top element.

        Raises:
            IndexError: If the stack is empty.

        """
        if self.is_empty():
            msg = "Stack is empty"
            raise IndexError(msg)
        value = self.head.value  # type: ignore[union-attr]
        self.head = self.head.next  # type: ignore[union-attr]
        self._top -= 1
        return value

    def peek(self) -> T:
        """Return the top element without removing it.

        Returns:
            The top element.

        Raises:
            IndexError: If the stack is empty.

        """
        if self.is_empty():
            msg = "Stack is empty"
            raise IndexError(msg)
        return self.head.value  # type: ignore[union-attr]
