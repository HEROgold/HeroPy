"""Binary Tree to Doubly Linked List.

Converts a binary tree to a sorted doubly linked list in-place by
rearranging the left and right pointers of each node.

Reference: https://en.wikipedia.org/wiki/Binary_tree

Complexity:
    Time:  O(n)
    Space: O(n) due to recursion stack
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from herogold.algorithms.tree.tree import TreeNode


def bin_tree_to_list[T](root: TreeNode[T] | None) -> TreeNode[T] | None:
    """Convert a binary tree to a sorted doubly linked list.

    Args:
        root: The root of the binary tree.

    Returns:
        The head (leftmost node) of the resulting doubly linked list,
        or None if the tree is empty.

    Examples:
        >>> bin_tree_to_list(None) is None
        True

    """
    if leaf := _bin_tree_to_list_util(root):
        while leaf.left:
            leaf = leaf.left
        return leaf
    return None


def _bin_tree_to_list_util[T](root: TreeNode[T] | None) -> TreeNode[T] | None:
    """Recursively convert subtree nodes into a doubly linked list.

    Args:
        root: The root of the subtree to convert.

    Returns:
        The root of the partially converted subtree.

    """
    if not root:
        return root
    if root.left:
        if left := _bin_tree_to_list_util(root.left):
            while left.right:
                left = left.right
        else:
            return root
        left.right = root
        root.left = left
    if root.right:
        if right := _bin_tree_to_list_util(root.right):
            if not right:
                return root
            while right.left:
                right = right.left
            right.left = root
            root.right = right
        else:
            return root
    return root
