"""Pythonic data structures and algorithms for education.

Shared types are available at the top level::

    >>> from algorithms import TreeNode, ListNode, Graph
    >>> from algorithms.data_structures import BinaryHeap, HashTable
    >>> from algorithms.graph import dijkstra
"""

from . import data_structures
from .common import Graph, ListNode, TreeNode

__all__ = ["Graph", "ListNode", "TreeNode", "data_structures"]
