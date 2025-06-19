from typing import Dict

import networkx as nx

from src.dataclasses.lesson import Lesson


def build_lesson_graph(lessons: Dict[str, Lesson]) -> nx.DiGraph:
    """Build a graph of lessons and their prerequisites."""

    G = nx.DiGraph()
    for lesson in lessons.values():
        G.add_node(lesson.id)
        for prereq in lesson.prerequisites:
            G.add_edge(prereq, lesson.id)
    return G
