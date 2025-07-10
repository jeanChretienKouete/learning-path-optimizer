import json
import os
import random
from typing import Any, Dict, List

import networkx as nx

from src.constants.constants import ACTIVITY_TYPES, DIFFICULTY_SETTINGS, TIERS_CONFIG
from src.dataclasses.activity import Activity
from src.dataclasses.lesson import Lesson
from utils.instance_graph import (
    save_interactive_instance_graph,
    save_interactive_lesson_graph,
)


class BenchmarkGenerator:
    """
    A class to generate and save a benchmark instance for a given tier.

    This includes generating lessons and activities, assigning prerequisites,
    calculating graph metrics, and saving the instance to JSON files.
    """

    def __init__(
        self, config: dict, tier_name: str, instance_id: int, output_dir="benchmarks"
    ) -> None:
        """
        Initializes the BenchmarkGenerator.

        Args:
            config (dict): Configuration dictionary containing ranges and limits for generation.
            tier_name (str): Name of the tier (e.g., "basic", "advanced").
            instance_id (int): Unique identifier for this instance.
            output_dir (str, optional): Directory to save generated files. Defaults to "benchmarks".
        """
        self.config = config
        self.tier_name = tier_name
        self.instance_id = instance_id
        self.output_dir = output_dir
        self.lessons: Dict[str, Lesson] = {}
        self.activities: List[Activity] = []
        self.graph = nx.DiGraph()

        # Set a random seed for reproducibility
        random.seed(instance_id * 100 + ord(tier_name[0]))

    def generate(self) -> Dict[str, Any]:
        """
         Generates a benchmark instance including lessons, activities, and prerequisites.

        It also saves the generated data to JSON and creates interactive graphs.
        Metrics about the graph structure are computed and returned.

        Returns:
            Dict[str, Any]: Dictionary containing graph metrics for the instance.
        """
        self._create_lessons()
        self._assign_prerequisites()
        self._create_activities()
        self._save_to_json()
        self._save_lesson_graph()
        # self._save_instance_graph()

        return self._calculate_graph_metrics()

    def _create_lessons(self):
        """
        Randomly generates a set of lessons based on the specified configuration.
        Each lesson will be assigned a unique ID and a random mastery value.
        """
        num_lessons = random.randint(*self.config["lessons_range"])
        for i in range(num_lessons):
            lid = f"Lesson_{i + 1:03d}"
            self.lessons[lid] = Lesson(
                id=lid,
                name=f"Lesson {i + 1}",
                min_mastery=random.randint(70, 100),
                prerequisites=set(),
            )
            self.graph.add_node(lid)

    def _assign_prerequisites(self):
        """
        Assigns prerequisites to lessons with a natural progression of difficulty.

        Earlier lessons are easier and have fewer prerequisites. The number of
        prerequisites scales with lesson position in the graph.
        """
        lesson_ids = list(self.lessons.keys())

        # Assign difficulty based on topological position
        for i, lid in enumerate(lesson_ids):
            # Earlier lessons are easier (fewer prereqs)
            difficulty = i / len(lesson_ids)  # 0 (easiest) to 1 (hardest)

            # Number of prerequisites scales with difficulty
            max_prereqs = min(
                int(
                    self.config["max_prereqs"] * difficulty * 1.5
                ),  # At most 1.5x config
                i,  # Can't exceed available lessons
            )
            num_prereqs = random.randint(0, max_prereqs)

            if num_prereqs > 0:
                prereqs = random.sample(lesson_ids[:i], num_prereqs)
                self.lessons[lid].prerequisites = set(prereqs)
                for p in prereqs:
                    self.graph.add_edge(p, lid)

    def _create_activities(self) -> None:
        """
        Randomly generates a set of activities based on the specified configuration.
        Each activity will be assigned a unique ID, type, duration, and effectiveness.
        """
        num_activities = random.randint(*self.config["activities_range"])
        lesson_ids = list(self.lessons.keys())

        # Precompute lesson complexity
        max_depth = self._get_max_dag_depth()
        lesson_complexity = {
            lid: len(list(nx.descendants(self.graph, lid))) / max(max_depth, 1)
            for lid in lesson_ids
        }

        for _ in range(num_activities):
            # Select activity type
            activity_type = random.choice(list(ACTIVITY_TYPES.keys()))

            # Link to lessons (1 to max_lessons_per_activity)
            num_lessons = random.randint(1, self.config["max_lessons_per_activity"])
            linked_lessons = random.sample(lesson_ids, num_lessons)
            avg_complexity = sum(
                lesson_complexity[lesson] for lesson in linked_lessons
            ) / len(linked_lessons)

            # Duration scales with complexity (20% to 80% longer for complex lessons)
            base_duration = random.randint(
                *DIFFICULTY_SETTINGS["medium"]["duration_range"]
            )
            duration = int(base_duration * (0.5 + avg_complexity * 1.5))

            # Effectiveness depends on:
            # 1. Base activity type effectiveness
            # 2. Alignment with lesson complexity
            effectiveness = {}
            for lid in linked_lessons:
                base = random.randint(*self.config["effectiveness_range"])
                adjusted = int(base * (0.7 + lesson_complexity[lid] * 0.6))
                effectiveness[lid] = min(20, max(1, adjusted))

            self.activities.append(
                Activity(
                    id=f"Activity_{len(self.activities) + 1:03d}",
                    name=f"Activity {len(self.activities) + 1}",
                    duration=duration,
                    style=random.choice(ACTIVITY_TYPES[activity_type]["styles"]),
                    effectiveness=effectiveness,
                    difficulty=self._get_difficulty_label(avg_complexity),
                    type=activity_type,
                )
            )

    def _get_max_dag_depth(self) -> int:
        """Returns the maximum depth of the DAG"""
        if not self.graph.nodes():
            return 0
        try:
            return nx.dag_longest_path_length(self.graph)
        except nx.NetworkXNotImplemented:
            return 0

    def _get_difficulty_label(self, complexity: float) -> str:
        """Convert complexity score (0-1) to difficulty tier"""
        if complexity < 0.33:
            return "easy"
        elif complexity < 0.66:
            return "medium"
        else:
            return "hard"

    def _save_to_json(self) -> None:
        """Save generated data to JSON files with additional metrics"""
        path = os.path.join(
            self.output_dir, self.tier_name, f"instance_{self.instance_id + 1:02d}"
        )
        os.makedirs(path, exist_ok=True)

        # Convert lessons to dictionaries with all attributes
        lessons_dict = [
            {**lesson.__dict__, "prerequisites": list(lesson.prerequisites)}
            for lesson in self.lessons.values()
        ]

        # Convert activities to dictionaries with all attributes
        activities_dict = [
            {**activity.__dict__, "effectiveness": dict(activity.effectiveness)}
            for activity in self.activities
        ]

        # Add metadata
        metrics = self._calculate_graph_metrics()
        metadata = {
            "tier_name": self.tier_name,
            "instance_id": self.instance_id,
            "config": self.config,
            "metrics": metrics,
            "generation_date": "__DATE__",
            "is_dag": metrics.get("is_dag", False),
        }

        # Save all data
        with open(os.path.join(path, "lessons.json"), "w") as f:
            json.dump(lessons_dict, f, indent=4)
        with open(os.path.join(path, "activities.json"), "w") as f:
            json.dump(activities_dict, f, indent=4)
        with open(os.path.join(path, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=4)

        print(f"✅ Saved instance to: {path}")

    def _calculate_graph_metrics(self):
        """Calculate useful metrics about the graph structure"""
        is_dag = nx.is_directed_acyclic_graph(self.graph)

        metrics = {
            "num_lessons": len(self.lessons),
            "num_activities": len(self.activities),
            "root_nodes": len(
                [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
            ),
            "leaf_nodes": len(
                [n for n in self.graph.nodes() if self.graph.out_degree(n) == 0]
            ),
            "max_path_length": 0,
            "avg_path_length": 0,
            "avg_prerequisites": sum(
                len(self.lessons[n].prerequisites) for n in self.lessons
            )
            / len(self.lessons)
            if self.lessons
            else 0,
            "max_prerequisites": max(
                (len(self.lessons[n].prerequisites) for n in self.lessons), default=0
            ),
            "connectivity": 0,
            "num_disconnected_groups": len(
                list(nx.weakly_connected_components(self.graph))
            ),
            "standalone_lessons": len(
                [
                    n
                    for n in self.graph.nodes()
                    if self.graph.in_degree(n) == 0 and self.graph.out_degree(n) == 0
                ]
            ),
            "is_dag": is_dag,
        }

        # Calculate path lengths
        if len(self.graph.nodes()) > 1:
            try:
                root_nodes = [
                    n for n in self.graph.nodes() if self.graph.in_degree(n) == 0
                ]
                leaf_nodes = [
                    n for n in self.graph.nodes() if self.graph.out_degree(n) == 0
                ]

                path_lengths = []

                for source in root_nodes:
                    for target in leaf_nodes:
                        try:
                            paths = list(
                                nx.all_simple_paths(self.graph, source, target)
                            )
                            path_lengths.extend([len(p) - 1 for p in paths])
                        except nx.NetworkXNoPath:
                            pass

                if path_lengths:
                    metrics["max_path_length"] = max(path_lengths)
                    metrics["avg_path_length"] = sum(path_lengths) / len(path_lengths)

                n = len(self.graph.nodes())
                max_possible_edges = n * (n - 1) // 2
                actual_edges = len(self.graph.edges())
                metrics["connectivity"] = (
                    actual_edges / max_possible_edges if max_possible_edges > 0 else 0
                )
            except Exception as e:
                print(f"Warning: Error calculating graph metrics: {e}")

        return metrics

    def _save_instance_graph(self) -> None:
        """Save an interactive visualization of the graph of lessons and activities"""
        html_file = save_interactive_instance_graph(
            self.graph,
            self.lessons,
            self.activities,
            title=f"{self.tier_name.title()} Tier - Instance {self.instance_id + 1}",
        )

        print(f"Interactive visualization saved to: {html_file}")

    def _save_lesson_graph(self) -> None:
        """Save an interactive visualization of the graph of lessons"""
        html_file = save_interactive_lesson_graph(
            self.graph,
            self.lessons,
            title=f"{self.tier_name.title()} Tier - Instance {self.instance_id + 1}",
        )
        print(f"Interactive visualization saved to: {html_file}")


def generate_all_tiers(output_dir="benchmarks") -> Dict[str, Any]:
    """
    Generates benchmark instances for all configured tiers and saves them.

    Args:
        output_dir (str, optional): Root directory to store generated benchmark data. Defaults to "benchmarks".

    Returns:
        Dict[str, Any]: A dictionary with tier names as keys and lists of instance metrics as values.
    """
    all_metrics = {}
    for tier_name, config in TIERS_CONFIG.items():
        tier_metrics = []
        for i in range(config["num_instances"]):
            gen = BenchmarkGenerator(config, tier_name, i, output_dir)
            tier_metrics.append(gen.generate())
        all_metrics[tier_name] = tier_metrics
    return all_metrics


if __name__ == "__main__":
    generate_all_tiers()
