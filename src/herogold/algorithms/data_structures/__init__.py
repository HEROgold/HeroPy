"""Reusable data structure implementations.

This package contains the core data structures used throughout the library.
Each module provides a self-contained implementation suitable for study.

    >>> from algorithms.data_structures import BinaryHeap, ArrayStack
"""

# Tree data structures (moved from tree/ subdirectories in Phase 8)
from herogold.algorithms.data_structures.avl_tree import AvlTree
from herogold.algorithms.data_structures.b_tree import BTree
from herogold.algorithms.data_structures.bst import BST
from herogold.algorithms.data_structures.fenwick_tree import Fenwick_Tree
from herogold.algorithms.data_structures.graph import DirectedEdge, DirectedGraph, Node
from herogold.algorithms.data_structures.hash_table import HashTable, ResizableHashTable
from herogold.algorithms.data_structures.heap import AbstractHeap, BinaryHeap
from herogold.algorithms.data_structures.iterative_segment_tree import SegmentTree
from herogold.algorithms.data_structures.kd_tree import KDTree
from herogold.algorithms.data_structures.linked_list import DoublyLinkedListNode, SinglyLinkedListNode
from herogold.algorithms.data_structures.priority_queue import PriorityQueue, PriorityQueueNode
from herogold.algorithms.data_structures.queue import AbstractQueue, ArrayQueue, LinkedListQueue, QueueNode
from herogold.algorithms.data_structures.red_black_tree import RBTree
from herogold.algorithms.data_structures.segment_tree import SegmentTree as SegmentTreeRecursive
from herogold.algorithms.data_structures.separate_chaining_hash_table import SeparateChainingHashTable
from herogold.algorithms.data_structures.sqrt_decomposition import SqrtDecomposition
from herogold.algorithms.data_structures.stack import AbstractStack, ArrayStack, LinkedListStack, StackNode
from herogold.algorithms.data_structures.trie import Trie
from herogold.algorithms.data_structures.union_find import Union

__all__ = [
    "BST",
    "AbstractHeap",
    "AbstractQueue",
    "AbstractStack",
    "ArrayQueue",
    "ArrayStack",
    # Tree data structures
    "AvlTree",
    "BTree",
    "BinaryHeap",
    "DirectedEdge",
    "DirectedGraph",
    "DoublyLinkedListNode",
    "Fenwick_Tree",
    "HashTable",
    "KDTree",
    "LinkedListQueue",
    "LinkedListStack",
    "Node",
    "PriorityQueue",
    "PriorityQueueNode",
    "QueueNode",
    "RBTree",
    "ResizableHashTable",
    "SegmentTree",
    "SegmentTreeRecursive",
    "SeparateChainingHashTable",
    "SinglyLinkedListNode",
    "SqrtDecomposition",
    "StackNode",
    "Trie",
    "Union",
]
