"""Deepest Left Leaf.

Given a binary tree, find the deepest node that is the left child of its
parent node.

Reference: https://en.wikipedia.org/wiki/Binary_tree

Complexity:
    Time:  O(n)
    Space: O(n) due to recursion stack
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from herogold.algorithms import TreeNode


class DeepestLeft:
    """Container to track the deepest left node found during traversal.

    Examples:
        >>> dl = DeepestLeft()
        >>> dl.depth
        0

    """

    def __init__(self) -> None:
        self.depth: int = 0
        self.Node: TreeNode | None = None


def find_deepest_left(
    root: TreeNode | None, depth: int, res: DeepestLeft,
) -> None:
    """Recursively find the deepest left child in a binary tree.

    Args:
        root: The current node being examined.
        depth: The current depth in the tree.
        res: A DeepestLeft instance tracking the best result so far.

    Examples:
        >>> res = DeepestLeft()
        >>> find_deepest_left(None, 1, res)

    """
    if not root:
        return
    # Check left child
    if root.left:
        if depth + 1 > res.depth:
            res.depth = depth + 1
            res.Node = root.left
        find_deepest_left(root.left, depth + 1, res)
    # Continue with right child
    if root.right:
        find_deepest_left(root.right, depth + 1, res)
