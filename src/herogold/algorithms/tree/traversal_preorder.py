"""Time complexity : O(n)."""
from collections.abc import Generator

from herogold.algorithms import TreeNode


def pre_order[T](root: TreeNode[T] | None) -> list[T]:
    """Function to Preorder."""
    res: list[T] = []
    if not root:
        return res
    stack: list[TreeNode[T]] = []
    stack.append(root)
    while stack:
        root = stack.pop()
        res.append(root.val)
        if root.right:
            stack.append(root.right)
        if root.left:
            stack.append(root.left)
    return res


def pre_order_rec[T](root: TreeNode[T] | None, res: list[T] | None = None) -> list[T]:
    """Recursive Implementation."""
    if root is None:
        return []
    if res is None:
        res = []
    res.append(root.val)
    pre_order_rec(root.left, res)
    pre_order_rec(root.right, res)
    return res

def pre_order_gen[T](root: TreeNode[T] | None) -> Generator[T]:
    """Recursive Implementation with Generator."""
    if root is None:
        return
    yield root.val
    yield from pre_order_rec(root.left)
    yield from pre_order_rec(root.right)
