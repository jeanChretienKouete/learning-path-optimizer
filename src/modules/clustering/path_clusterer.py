from collections import defaultdict
from typing import Dict, List, Literal

import numpy as np
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import pairwise_distances
from sklearn.preprocessing import StandardScaler

from src.dataclasses.activity import Activity
from src.dataclasses.lesson import Lesson
from utils.lesson_graph_builder import build_lesson_graph
from utils.lessons_topology import compute_lesson_levels


class SprintBuilder:
    """
    Constructs learning sprints by grouping activities based on lesson dependencies
    and clustering them using activity similarity.

    Sprints aim to deliver manageable groups of activities that are topologically coherent
    and pedagogically effective.

    Attributes:
        lessons (Dict[str, Lesson]): Mapping of lesson IDs to lessons.
        activities (List[Activity]): List of available learning activities.
        max_sprint_size (int): Maximum number of activities per sprint.
        use_clustering (bool): Whether to use clustering to group activities.
        cluster_distance (Literal["euclidean", "jaccard"]): Distance metric for clustering.
    """

    def __init__(
        self,
        lessons: Dict[str, Lesson],
        activities: List[Activity],
        max_sprint_size: int = 5,
        use_clustering: bool = True,
        cluster_distance: Literal["euclidean", "jaccard"] = "jaccard",
    ) -> None:
        """
        Initializes the SprintBuilder with data and configuration.

        Args:
            lessons (Dict[str, Lesson]): All lessons with prerequisite info.
            activities (List[Activity]): Activities to organize into sprints.
            max_sprint_size (int, optional): Max activities per sprint. Defaults to 5.
            use_clustering (bool, optional): Whether to use clustering. Defaults to True.
            cluster_distance (str, optional): Distance metric for clustering. "euclidean" or "jaccard". Defaults to "jaccard".
        """
        self.lessons = lessons
        self.activities = activities
        self.max_sprint_size = max_sprint_size
        self.use_clustering = use_clustering
        self.cluster_distance = cluster_distance
        self.lesson_graph = build_lesson_graph(lessons)
        self.lesson_levels = self._compute_lesson_levels()
        self.all_lesson_ids = sorted(lessons.keys())

    def _compute_lesson_levels(self) -> Dict[str, int]:
        """
        Computes lesson levels using topological sort from the prerequisite graph.

        Returns:
            Dict[str, int]: Mapping of lesson ID to its depth level in the DAG.
        """

        return compute_lesson_levels(self.lesson_graph)

    def _encode_activity(self, activity: Activity) -> np.ndarray:
        """
        Encodes an activity as a binary vector indicating which lessons it affects.

        Args:
            activity (Activity): The activity to encode.

        Returns:
            np.ndarray: Binary vector of shape (num_lessons,).
        """
        return np.array(
            [
                1 if lesson_id in activity.effectiveness else 0
                for lesson_id in self.all_lesson_ids
            ]
        )

    def _cluster_activities(self, activities: List[Activity]) -> List[List[Activity]]:
        """
        Clusters activities into groups using the selected distance metric.

        Uses KMeans for Euclidean distance or Agglomerative Clustering for Jaccard.

        Args:
            activities (List[Activity]): Activities to cluster.

        Returns:
            List[List[Activity]]: A list of clustered activity groups.

        Raises:
            ValueError: If an unsupported distance metric is specified.
        """
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
            encoded_binary = np.array(encoded).astype(bool)
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
        """
        Builds sprints from activities grouped by lesson dependency levels.

        Activities are grouped by topological level, then clustered
        into sprints.

        Returns:
            List[List[Activity]]: Ordered list of activity sprints.
        """
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
