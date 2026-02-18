"""Given an array where elements are sorted in ascending order,
convert it to a height balanced BST.
"""
from herogold.algorithms import TreeNode


def array_to_bst[T](nums: list[T]) -> TreeNode[T] | None:
    """Convert sorted array to a height-balanced BST."""
    if not nums:
        return None
    mid = len(nums) // 2
    node = TreeNode(nums[mid])
    node.left = array_to_bst(nums[:mid])
    node.right = array_to_bst(nums[mid + 1 :])
    return node
