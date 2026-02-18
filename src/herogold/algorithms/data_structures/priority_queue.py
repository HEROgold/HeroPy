"""Priority Queue (Linear Array).

A priority queue implementation using a sorted linear array. Elements
are inserted in order so that extraction of the minimum is O(1).

Reference: https://en.wikipedia.org/wiki/Priority_queue

Complexity:
    Time:  O(n) for push, O(1) for pop
    Space: O(n)
"""

from __future__ import annotations

import itertools
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterable

D = TypeVar("D")
P = TypeVar("P")


class PriorityQueueNode[D, P]:
    """A node holding data and its priority.

    Args:
        data: The stored value.
        priority: The priority of this node.

    """

    def __init__(self, data: D, priority: P) -> None:
        self.data = data
        self.priority = priority

    def __repr__(self) -> str:
        """Return a string representation of the node.

        Returns:
            Formatted string with data and priority.

        """
        return f"{self.data}: {self.priority}"


class PriorityQueue[D, P]:
    """Priority queue backed by a sorted linear array.

    Examples:
        >>> pq = PriorityQueue([3, 1, 2])
        >>> pq.pop()
        1
        >>> pq.size()
        2

    """

    def __init__(
        self,
        items: Iterable[D] | None = None,
        priorities: Iterable[P] | None = None,
    ) -> None:
        """Create a priority queue, optionally from items and priorities.

        Args:
            items: Initial items to insert.
            priorities: Corresponding priorities; defaults to item values.

        """
        self.priority_queue_list: list[PriorityQueueNode[D, P]] = []
        if items is None:
            return
        if priorities is None:
            priorities = itertools.repeat(None)  # type: ignore[assignment]
        for item, priority in zip(items, priorities, strict=False):
            self.push(item, priority=priority)

    def __repr__(self) -> str:
        """Return a string representation of the priority queue.

        Returns:
            Formatted string.

        """
        return f"PriorityQueue({self.priority_queue_list!r})"

    def size(self) -> int:
        """Return the number of elements in the queue.

        Returns:
            The queue size.

        """
        return len(self.priority_queue_list)

    def push(self, item: D, priority: P | None = None) -> None:
        """Insert an item with the given priority.

        Args:
            item: The value to insert.
            priority: Priority value; defaults to the item itself.

        """
        priority = item if priority is None else priority  # type: ignore[assignment]
        node = PriorityQueueNode(item, priority)
        for index, current in enumerate(self.priority_queue_list):
            if current.priority < node.priority:  # type: ignore[operator]
                self.priority_queue_list.insert(index, node)
                return
        self.priority_queue_list.append(node)

    def pop(self) -> D:
        """Remove and return the item with the lowest priority.

        Returns:
            The data of the lowest-priority node.

        """
        return self.priority_queue_list.pop().data  # type: ignore[return-value]
