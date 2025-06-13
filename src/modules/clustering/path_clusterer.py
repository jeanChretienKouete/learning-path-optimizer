from collections import defaultdict
from typing import Dict, List, Literal

import numpy as np
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import StandardScaler

from src.dataclasses.activity import Activity
from src.dataclasses.lesson import Lesson
from utils.lesson_graph_builder import build_lesson_graph


class SprintBuilder:
    def __init__(
        self,
        lessons: Dict[str, Lesson],
        activities: List[Activity],
        max_sprint_size: int = 5,
        use_clustering: bool = True,
        cluster_distance: Literal["euclidean", "jaccard"] = "jaccard",
    ) -> None:
        self.lessons = lessons
        self.activities = activities
        self.max_sprint_size = max_sprint_size
        self.use_clustering = use_clustering
        self.cluster_distance = cluster_distance
        self.lesson_graph = build_lesson_graph(lessons)
        self.lesson_levels = self._compute_lesson_levels()
        self.all_lesson_ids = sorted(lessons.keys())

    def _compute_lesson_levels(self) -> Dict[str, int]:
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
        return np.array(
            [
                1 if lesson_id in activity.effectiveness else 0
                for lesson_id in self.all_lesson_ids
            ]
        )

    def _cluster_activities(self, activities: List[Activity]) -> List[List[Activity]]:
        if len(activities) <= self.max_sprint_size:
            return [activities]

        encoded = [self._encode_activity(a) for a in activities]

        k = max(
            1,
            min(
                len(activities) // 2,
                int(np.ceil(len(activities) / self.max_sprint_size)),
            ),
        )

        if self.cluster_distance == "euclidean":
            encoded_scaled = StandardScaler().fit_transform(encoded)  # type: ignore
            kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
            labels = kmeans.fit_predict(encoded_scaled)

        elif self.cluster_distance == "jaccard":
            encoded_binary = np.array(encoded).astype(bool).astype(int)
            dist_matrix = pairwise_distances(encoded_binary, metric="jaccard")
            clustering = AgglomerativeClustering(
                n_clusters=k, metric="precomputed", linkage="average"
            )
            labels = clustering.fit_predict(dist_matrix)

        else:
            raise ValueError("Distance must be 'euclidean' or 'jaccard'")

        clusters = [[] for _ in range(k)]
        for activity, label in zip(activities, labels):
            clusters[label].append(activity)

        return clusters

    def build_sprints(self) -> List[List[Activity]]:
        level_groups = defaultdict(list)
        for activity in self.activities:
            if not activity.effectiveness:
                continue
            max_level = max(
                self.lesson_levels[lesson_id] for lesson_id in activity.effectiveness
            )
            level_groups[max_level].append(activity)

        ordered_sprints = []
        for level in sorted(level_groups):
            activities = level_groups[level]

            if self.use_clustering and len(activities) > self.max_sprint_size:
                clusters = self._cluster_activities(activities)
                ordered_sprints.extend(clusters)
            else:
                for i in range(0, len(activities), self.max_sprint_size):
                    ordered_sprints.append(activities[i : i + self.max_sprint_size])

        return ordered_sprints
