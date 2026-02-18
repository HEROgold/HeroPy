"""Shared data types used across all algorithm categories.

These types are the connective tissue of the library — every algorithm
accepts and returns these types, making them composable.

    >>> from algorithms.common import TreeNode, ListNode, Graph
"""

from herogold.algorithms.common.graph import Graph
from herogold.algorithms.common.list_node import ListNode
from herogold.algorithms.common.tree_node import TreeNode

__all__ = ["Graph", "ListNode", "TreeNode"]
