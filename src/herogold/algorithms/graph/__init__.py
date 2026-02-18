"""Collection of graph algorithms."""

from __future__ import annotations

from herogold.algorithms.data_structures.graph import DirectedEdge, DirectedGraph, Node
from herogold.algorithms.graph.a_star import a_star
from herogold.algorithms.graph.all_factors import get_factors, get_factors_iterative1, get_factors_iterative2
from herogold.algorithms.graph.all_pairs_shortest_path import all_pairs_shortest_path
from herogold.algorithms.graph.bellman_ford import bellman_ford
from herogold.algorithms.graph.blossom import max_matching
from herogold.algorithms.graph.check_bipartite import check_bipartite
from herogold.algorithms.graph.clone_graph import UndirectedGraphNode, clone_graph, clone_graph1, clone_graph2
from herogold.algorithms.graph.count_islands_bfs import count_islands
from herogold.algorithms.graph.count_islands_dfs import num_islands as num_islands_dfs
from herogold.algorithms.graph.count_islands_unionfind import num_islands as num_islands_unionfind
from herogold.algorithms.graph.dijkstra import Dijkstra
from herogold.algorithms.graph.dijkstra_heapq import dijkstra
from herogold.algorithms.graph.find_all_cliques import find_all_cliques
from herogold.algorithms.graph.kahns_algorithm import Solution as KahnsSolution
from herogold.algorithms.graph.markov_chain import iterating_markov_chain, next_state
from herogold.algorithms.graph.maximum_flow import dinic, edmonds_karp, ford_fulkerson
from herogold.algorithms.graph.maximum_flow_bfs import maximum_flow_bfs
from herogold.algorithms.graph.maximum_flow_dfs import maximum_flow_dfs
from herogold.algorithms.graph.maze_search_bfs import maze_search
from herogold.algorithms.graph.maze_search_dfs import find_path as find_path_dfs
from herogold.algorithms.graph.minimum_spanning_tree import DisjointSet, Edge, kruskal
from herogold.algorithms.graph.pacific_atlantic import pacific_atlantic
from herogold.algorithms.graph.prims_minimum_spanning import prims_minimum_spanning
from herogold.algorithms.graph.satisfiability import solve_sat
from herogold.algorithms.graph.shortest_distance_from_all_buildings import shortest_distance
from herogold.algorithms.graph.sudoku_solver import Sudoku
from herogold.algorithms.graph.tarjan import Tarjan
from herogold.algorithms.graph.topological_sort_bfs import topological_sort
from herogold.algorithms.graph.topological_sort_dfs import top_sort, top_sort_recursive
from herogold.algorithms.graph.traversal import bfs_traverse, dfs_traverse, dfs_traverse_recursive
from herogold.algorithms.graph.walls_and_gates import walls_and_gates
from herogold.algorithms.graph.word_ladder import ladder_length

__all__ = [
    # dijkstra
    "Dijkstra",
    # graph
    "DirectedEdge",
    "DirectedGraph",
    # minimum_spanning_tree
    "DisjointSet",
    "Edge",
    # kahns_algorithm
    "KahnsSolution",
    "Node",
    # sudoku_solver
    "Sudoku",
    # tarjan
    "Tarjan",
    # clone_graph
    "UndirectedGraphNode",
    # a_star
    "a_star",
    # all_pairs_shortest_path
    "all_pairs_shortest_path",
    # bellman_ford
    "bellman_ford",
    # traversal
    "bfs_traverse",
    # check_bipartite
    "check_bipartite",
    "clone_graph",
    "clone_graph1",
    "clone_graph2",
    # count_islands (bfs)
    "count_islands",
    "dfs_traverse",
    "dfs_traverse_recursive",
    "dijkstra",
    # maximum_flow
    "dinic",
    "edmonds_karp",
    # find_all_cliques
    "find_all_cliques",
    # maze_search (dfs)
    "find_path_dfs",
    "ford_fulkerson",
    # all_factors
    "get_factors",
    "get_factors_iterative1",
    "get_factors_iterative2",
    # markov_chain
    "iterating_markov_chain",
    "kruskal",
    # word_ladder
    "ladder_length",
    # blossom
    "max_matching",
    # maximum_flow_bfs
    "maximum_flow_bfs",
    # maximum_flow_dfs
    "maximum_flow_dfs",
    # maze_search (bfs)
    "maze_search",
    "next_state",
    # count_islands (dfs)
    "num_islands_dfs",
    # count_islands_unionfind
    "num_islands_unionfind",
    # pacific_atlantic
    "pacific_atlantic",
    # prims_minimum_spanning
    "prims_minimum_spanning",
    # shortest_distance_from_all_buildings
    "shortest_distance",
    # satisfiability
    "solve_sat",
    # topological_sort_dfs
    "top_sort",
    "top_sort_recursive",
    # topological_sort (bfs)
    "topological_sort",
    # walls_and_gates
    "walls_and_gates",
]
