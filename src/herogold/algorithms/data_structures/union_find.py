"""Union-Find (Disjoint Set) Data Structure.

A Union-Find data structure supporting add, find (root), and unite operations.
Uses union by size and path compression for near-constant amortized time.

Reference: https://en.wikipedia.org/wiki/Disjoint-set_data_structure

Complexity:
    Time:  O(alpha(n)) amortized per operation (inverse Ackermann)
    Space: O(n)
"""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


class Union[T]:
    """A Union-Find (Disjoint Set) data structure.

    Supports adding elements, finding set representatives, and merging sets.
    Uses union by size and path compression for near-constant amortized time.

    Examples:
        >>> uf = Union()
        >>> uf.add(1); uf.add(2); uf.add(3)
        >>> uf.unite(1, 2)
        >>> uf.root(1) == uf.root(2)
        True
        >>> uf.root(1) == uf.root(3)
        False

    """

    def __init__(self) -> None:
        self.parents: dict[T, T] = {}
        self.size: dict[T, int] = {}
        self.count: int = 0

    def add(self, element: T) -> None:
        """Add a new singleton set containing the given element.

        Args:
            element: The element to add.

        """
        self.parents[element] = element
        self.size[element] = 1
        self.count += 1

    def root(self, element: T) -> T:
        """Find the root representative of the set containing element.

        Args:
            element: The element whose root to find.

        Returns:
            The root representative of the element's set.

        """
        while element != self.parents[element]:
            self.parents[element] = self.parents[self.parents[element]]
            element = self.parents[element]
        return element

    def unite(self, element1: T, element2: T) -> None:
        """Merge the sets containing the two elements.

        Args:
            element1: An element in the first set.
            element2: An element in the second set.

        """
        root1, root2 = self.root(element1), self.root(element2)
        if root1 == root2:
            return
        if self.size[root1] > self.size[root2]:
            root1, root2 = root2, root1
        self.parents[root1] = root2
        self.size[root2] += self.size[root1]
        self.count -= 1
