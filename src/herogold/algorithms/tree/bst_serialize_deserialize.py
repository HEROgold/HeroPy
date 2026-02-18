from typing import LiteralString


class TreeNode:
    def __init__(self, x) -> None:
        self.val = x
        self.left = None
        self.right = None


def serialize(root) -> LiteralString:
    def build_string(node) -> None:
        if node:
            vals.append(str(node.val))
            build_string(node.left)
            build_string(node.right)
        else:
            vals.append("#")

    vals = []
    build_string(root)
    return " ".join(vals)


def deserialize(data) -> TreeNode | None:
    def build_tree() -> TreeNode | None:
        val = next(vals)
        if val == "#":
            return None
        node = TreeNode(int(val))
        node.left = build_tree()
        node.right = build_tree()
        return node

    vals = iter(data.split())
    return build_tree()
