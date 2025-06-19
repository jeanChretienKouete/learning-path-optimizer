import random

from src.dataclasses.learner import ActivityPerformance, LearnerModel
from src.modules.clustering.path_clusterer import SprintBuilder
from src.modules.cp.path_optimizer import LearningPathOptimizer
from utils.data_loader import load_data

lessons, activities = load_data()


def print_selected_activities(selected_activities) -> None:
    """
    Print a list of selected activities with duration and total time.

    Args:
        selected_activities (List[Activity]): Activities selected by the optimizer.
    """
    print("Selected Activities:")
    for act in selected_activities:
        print(f"- {act.name} (Duration: {act.duration})")

    print("\nTotal Time:", sum(activity.duration for activity in selected_activities))


def print_sprints(sprints) -> None:
    """
    Print each sprint and its associated activities and covered lessons.

    Args:
        sprints (List[List[Activity]]): Grouped activities for each sprint.
    """
    for i, sprint in enumerate(sprints):
        print(f"\n🏃 Sprint {i + 1} — {len(sprint)} activities")
        all_lessons = set()
        for a in sprint:
            all_lessons.update(a.effectiveness.keys())
        print("  Covers lessons:", ", ".join(sorted(all_lessons)))
        for a in sprint:
            print(f"    - {a.id}: {a.type} ({a.difficulty}, {a.duration}min)")


def test_path() -> None:
    """
    End-to-end test simulating the learner's journey through multiple sprints.

    Steps:
    - Uses CP-SAT to select optimal activities.
    - Clusters activities into sprints.
    - Simulates user performance.
    - Updates learner state.
    Repeats until learning goals are complete or no feasible paths remain.
    """
    learner = LearnerModel(set(lessons.keys()))
    all_activities = activities.copy()

    while True:
        # 1. Select next set of activities via CP Optimizer
        optimizer = LearningPathOptimizer(lessons, all_activities, learner)
        selected_activities = None
        try:
            selected_activities = optimizer.run()
        except ValueError:
            print("🎯 No more feasible sprints or learning goal achieved.")
        except RuntimeError:
            print("🛑 Solver failed. Ending learning path.")
            break

        if not selected_activities:  # type:ignore
            print("🛑 No activities selected. Ending learning path.")
            break

        # 2. Cluster activities into sprints based lessons dependancies
        sprints = []
        try:
            builder = SprintBuilder(
                lessons,
                selected_activities,
                use_clustering=True,
                cluster_distance="jaccard",
            )
            sprints = builder.build_sprints()
        except Exception as e:
            print(f"❌ Error during sprint building: {e}")
            break

        print_sprints(sprints)

        # 3. Simulate learner performance and update model
        performances = [
            ActivityPerformance(
                activity_id=a.id, performance=round(random.uniform(0.5, 1.0), 2)
            )
            for a in sprints[0]
        ]
        learner.record_sprint(performances, all_activities)

        learner.print_sprints()


if __name__ == "__main__":
    test_path()
