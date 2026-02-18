"""Implement Binary Search Tree. It has method:
1. Insert
2. Search
3. Size
4. Traversal (Preorder, Inorder, Postorder).
"""

import unittest
from typing import TypeVar

T = TypeVar("T")


class Node[T]:
    def __init__(self, data: T) -> None:
        self.data = data
        self.left: Node[T] | None = None
        self.right: Node[T] | None = None


class BST[T]:
    def __init__(self) -> None:
        self.root: Node[T] | None = None

    def get_root(self) -> Node[T] | None:
        return self.root

    """
        Get the number of elements
        Using recursion. Complexity O(logN)
    """

    def size(self) -> int:
        return self.recur_size(self.root)

    def recur_size(self, root: Node[T] | None) -> int:
        if root is None:
            return 0
        return 1 + self.recur_size(root.left) + self.recur_size(root.right)

    """
        Search data in bst
        Using recursion. Complexity O(logN)
    """

    def search(self, data: T) -> bool:
        return self.recur_search(self.root, data)

    def recur_search(self, root: Node[T] | None, data: T) -> bool:
        if root is None:
            return False
        if root.data == data:
            return True
        if data > root.data:  # type: ignore[operator]  # Go to right root
            return self.recur_search(root.right, data)
        # Go to left root
        return self.recur_search(root.left, data)

    """
        Insert data in bst
        Using recursion. Complexity O(logN)
    """

    def insert(self, data: T) -> bool:
        if self.root:
            return self.recur_insert(self.root, data)
        self.root = Node(data)
        return True

    def recur_insert(self, root: Node[T], data: T) -> bool:
        if root.data == data:  # The data is already there
            return False
        if data < root.data:  # type: ignore[operator]  # Go to left root
            if root.left:  # If left root is a node
                return self.recur_insert(root.left, data)
            # left root is a None
            root.left = Node(data)
            return True
        if root.right:  # If right root is a node
            return self.recur_insert(root.right, data)
        root.right = Node(data)
        return True

    """
        Preorder, Postorder, Inorder traversal bst
    """

    def preorder(self, root) -> None:
        if root:
            self.preorder(root.left)
            self.preorder(root.right)

    def inorder(self, root) -> None:
        if root:
            self.inorder(root.left)
            self.inorder(root.right)

    def postorder(self, root) -> None:
        if root:
            self.postorder(root.left)
            self.postorder(root.right)


"""
    The tree is created for testing:

                    10
                 /      \
               6         15
              / \\       /   \
            4     9   12      24
                 /          /    \
                7         20      30
                         /
                       18
"""


class TestSuite(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = BST()
        self.tree.insert(10)
        self.tree.insert(15)
        self.tree.insert(6)
        self.tree.insert(4)
        self.tree.insert(9)
        self.tree.insert(12)
        self.tree.insert(24)
        self.tree.insert(7)
        self.tree.insert(20)
        self.tree.insert(30)
        self.tree.insert(18)

    def test_search(self) -> None:
        assert self.tree.search(24)
        assert not self.tree.search(50)

    def test_size(self) -> None:
        assert self.tree.size() == 11


if __name__ == "__main__":
    unittest.main()
