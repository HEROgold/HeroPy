"""Delete Nth Occurrence.

Given a list and a number N, create a new list that contains each element
of the original list at most N times, without reordering.

Reference: https://www.geeksforgeeks.org/remove-duplicates-from-an-array/

Complexity:
    delete_nth_naive:
        Time:  O(n^2) due to list.count()
        Space: O(n)
    delete_nth:
        Time:  O(n)
        Space: O(n)
"""

from __future__ import annotations

import collections
from typing import TypeVar

T = TypeVar("T")


def delete_nth_naive[T](array: list[T], n: int) -> list[T]:
    """Keep at most n copies of each element using naive counting.

    Args:
        array: Source list of integers.
        n: Maximum number of allowed occurrences per element.

    Returns:
        New list with each element appearing at most n times.

    Examples:
        >>> delete_nth_naive([1, 2, 3, 1, 2, 1, 2, 3], 2)
        [1, 2, 3, 1, 2, 3]

    """
    result = []
    for num in array:
        if result.count(num) < n:
            result.append(num)
    return result


def delete_nth[T](array: list[T], n: int) -> list[T]:
    """Keep at most n copies of each element using a hash table.

    Args:
        array: Source list of elements.
        n: Maximum number of allowed occurrences per element.

    Returns:
        New list with each element appearing at most n times.

    Examples:
        >>> delete_nth([1, 2, 3, 1, 2, 1, 2, 3], 2)
        [1, 2, 3, 1, 2, 3]

    """
    result: list[T] = []
    counts: collections.defaultdict[T, int] = collections.defaultdict(int)

    for element in array:
        if counts[element] < n:
            result.append(element)
            counts[element] += 1

    return result
