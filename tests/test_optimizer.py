from models.cp.path_optimizer import LearningPathOptimizer
from models.dataclasses.learner import LearnerModel
from utils.data_loader import load_data

lessons, activities = load_data()


def print_selected_activities(selected_activities):
    print("Selected Activities:")
    for act in selected_activities:
        print(f"- {act.name} (Duration: {act.duration})")

    print("\nTotal Time:", sum(activity.duration for activity in selected_activities))


def test_optimizer():
    learner = LearnerModel(set(lessons.keys()))
    all_activities = activities.copy()

    optimizer = LearningPathOptimizer(lessons, all_activities, learner)
    selected_activities = optimizer.run()

    if selected_activities:
        print_selected_activities(selected_activities)
    else:
        print("🛑 No activities selected. Ending learning path.")


if __name__ == "__main__":
    test_optimizer()
