from typing import Dict

from networkx import DiGraph


def compute_lesson_levels(lesson_graph: DiGraph) -> Dict[str, int]:
    """Compute topological levels using Kahn's algorithm"""
    levels = {}
    current_level = 0
    graph = lesson_graph.copy()

    while True:
        level_nodes = [n for n in graph.nodes() if graph.in_degree(n) == 0]  # type: ignore
        if not level_nodes:
            break

        for node in level_nodes:
            levels[node] = current_level
        graph.remove_nodes_from(level_nodes)
        current_level += 1

    return levels
