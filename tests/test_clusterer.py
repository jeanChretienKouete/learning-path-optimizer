from src.modules.clustering.path_clusterer import SprintBuilder
from utils.data_loader import load_data

lessons, activities = load_data()


def print_sprints(sprints) -> None:
    for i, sprint in enumerate(sprints):
        print(f"\n🏃 Sprint {i + 1} — {len(sprint)} activities")
        all_lessons = set()
        for a in sprint:
            all_lessons.update(a.effectiveness.keys())
        print("  Covers lessons:", ", ".join(sorted(all_lessons)))
        for a in sprint:
            print(f"    - {a.id}: {a.type} ({a.difficulty}, {a.duration}min)")


def test_clusterer() -> None:
    all_activities = activities.copy()

    # 2. Cluster activities into sprints based on unlocked lessons
    sprints = []
    try:
        builder = SprintBuilder(lessons, all_activities)
        sprints = builder.build_sprints()
    except Exception as e:
        print(f"❌ Error during sprint building: {e}")

    print_sprints(sprints)


if __name__ == "__main__":
    test_clusterer()
