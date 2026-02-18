"""Given a non-empty binary search tree and a target value,
find the value in the BST that is closest to the target.

Note:
Given target value is a floating point.
You are guaranteed to have only one unique value in the BST
that is closest to the target.

"""  # noqa: D205


from herogold.algorithms import TreeNode
from herogold.supports import SupportsNumeric


def closest_value[T: SupportsNumeric](root: TreeNode[T] | None, target: SupportsNumeric) -> T:
    """Find the value in the BST that is closest to the target."""
    if not root:
        msg = "BST must be non-empty"
        raise ValueError(msg)
    a = root.val
    kid = root.left if target < a else root.right
    if not kid:
        return a
    b = closest_value(kid, target)
    def _distance_from_target(x: T) -> T:
        difference = target - x
        return abs(difference)

    return min((a, b), key=_distance_from_target)
