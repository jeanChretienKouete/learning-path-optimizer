from collections import defaultdict
from typing import Dict, List

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from models.dataclasses.activity import Activity
from models.dataclasses.lesson import Lesson
from utils.lesson_graph_builder import build_lesson_graph


class PureLevelSprintBuilder:
    def __init__(
        self,
        lessons: Dict[str, Lesson],
        activities: List[Activity],
        max_sprint_size: int = 5,
        use_clustering: bool = True,
    ):
        self.lessons = lessons
        self.activities = activities
        self.max_sprint_size = max_sprint_size
        self.use_clustering = use_clustering  # New flag to toggle clustering
        self.lesson_graph = build_lesson_graph(lessons)
        self.lesson_levels = self._compute_lesson_levels()
        self.all_lesson_ids = sorted(lessons.keys())  # Needed for encoding

    def _compute_lesson_levels(self) -> Dict[str, int]:
        """Compute topological levels using Kahn's algorithm"""
        levels = {}
        current_level = 0
        graph = self.lesson_graph.copy()

        while True:
            level_nodes = [n for n in graph.nodes() if graph.in_degree(n) == 0]  # type: ignore
            if not level_nodes:
                break

            for node in level_nodes:
                levels[node] = current_level
            graph.remove_nodes_from(level_nodes)
            current_level += 1

        return levels

    def _encode_activity(self, activity: Activity) -> np.ndarray:
        """Create feature vector: lesson_coverage"""
        return np.array(
            [
                1 if lesson_id in activity.effectiveness else 0
                for lesson_id in self.all_lesson_ids
            ]
        )

    def _cluster_activities(self, activities: List[Activity]) -> List[List[Activity]]:
        """Cluster activities within a level using K-means"""
        if len(activities) <= self.max_sprint_size:
            return [activities]

        # Encode and scale features
        encoded = StandardScaler().fit_transform(
            [self._encode_activity(a) for a in activities]  # type: ignore
        )

        # Determine cluster count
        k = max(
            1,
            min(
                len(activities) // 2,  # At least 2 activities per cluster
                int(np.ceil(len(activities) / self.max_sprint_size)),
            ),
        )

        # Cluster
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = kmeans.fit_predict(encoded)

        # Group by cluster
        clusters = [[] for _ in range(k)]
        for activity, label in zip(activities, labels):
            clusters[label].append(activity)

        return clusters

    def build_sprints(self) -> List[List[Activity]]:
        """Build sprints with optional within-level clustering"""
        # 1. Group by topological level
        level_groups = defaultdict(list)
        for activity in self.activities:
            if not activity.effectiveness:
                continue
            max_level = max(
                self.lesson_levels[lesson_id] for lesson_id in activity.effectiveness
            )
            level_groups[max_level].append(activity)

        # 2. Process each level
        ordered_sprints = []
        for level in sorted(level_groups):
            activities = level_groups[level]

            if self.use_clustering and len(activities) > self.max_sprint_size:
                # Use K-means clustering for large levels
                clusters = self._cluster_activities(activities)
                ordered_sprints.extend(clusters)
            else:
                # Simple splitting for small levels
                for i in range(0, len(activities), self.max_sprint_size):
                    ordered_sprints.append(activities[i : i + self.max_sprint_size])

        return ordered_sprints


class DepthAwareSprintBuilder:
    def __init__(
        self,
        lessons: Dict[str, Lesson],
        activities: List[Activity],
        max_sprint_size: int = 4,
        coverage_weight: float = 0.0,
        depth_weight: float = 1.0,
    ):
        self.lessons = lessons
        self.activities = activities
        self.max_sprint_size = max_sprint_size
        self.coverage_weight = coverage_weight  # Weight for lesson coverage
        self.depth_weight = depth_weight  # Weight for depth features

        self.lesson_graph = build_lesson_graph(lessons)
        self.lesson_depths = self._compute_lesson_depths()
        self.all_lesson_ids = sorted(lessons.keys())

    def _compute_lesson_depths(self) -> Dict[str, int]:
        """Compute topological levels using Kahn's algorithm (preferred approach)"""
        levels = {}
        current_level = 0
        graph = self.lesson_graph.copy()

        while True:
            # Find all nodes with no incoming edges
            level_nodes = [n for n in graph.nodes() if graph.in_degree(n) == 0]  # type: ignore
            if not level_nodes:
                break

            for node in level_nodes:
                levels[node] = current_level
            graph.remove_nodes_from(level_nodes)
            current_level += 1

        return levels

    def _encode_activity(self, activity: Activity) -> np.ndarray:
        """Create combined feature vector with configurable weights"""
        # Lesson coverage (binary)
        coverage = (
            np.array(
                [
                    1 if lesson_id in activity.effectiveness else 0
                    for lesson_id in self.all_lesson_ids
                ]
            )
            * self.coverage_weight
        )

        # Depth features (0 for uncovered lessons)
        depth_vec = (
            np.array(
                [
                    self.lesson_depths[lesson_id]
                    if lesson_id in activity.effectiveness
                    else 0
                    for lesson_id in self.all_lesson_ids
                ]
            )
            * self.depth_weight
        )

        return np.concatenate([coverage, depth_vec])

    def build_sprints(self) -> List[List[Activity]]:
        """Build sprints with depth-aware clustering"""
        # Handle edge cases
        if not self.activities:
            return []

        if len(self.activities) == 1:
            return [self.activities]  # Single activity = single sprint

        # Encode all activities
        encoded = StandardScaler().fit_transform(
            [self._encode_activity(a) for a in self.activities]  # type: ignore
        )

        # Determine safe cluster count
        k = min(
            max(2, len(self.activities) // 2),  # At least 2 activities per sprint
            max(2, int(len(self.activities) / self.max_sprint_size)),
            len(self.activities),  # Cannot exceed number of activities
        )

        # Cluster with K-means (now guaranteed k <= n_samples)
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = kmeans.fit_predict(encoded)

        # Group activities by cluster
        clusters = defaultdict(list)
        for activity, label in zip(self.activities, labels):
            clusters[label].append(activity)

        # Convert to sprints and sort by average depth
        sprints = list(clusters.values())
        sprints.sort(
            key=lambda s: np.mean(
                [
                    max(self.lesson_depths[lid] for lid in a.effectiveness)
                    for a in s
                    if a.effectiveness  # Handle empty effectivness
                ]
                or [0]  # type: ignore
            )
        )  # Default to 0 if no lessons

        return sprints
