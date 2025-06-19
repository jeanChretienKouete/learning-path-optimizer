from src.dataclasses.learner import LearnerModel
from src.modules.cp.path_optimizer import LearningPathOptimizer
from utils.data_loader import load_data

lessons, activities = load_data()

combinations_to_test = [
    # Baseline -> X=0
    {
        "val_strategy": "SELECT_MIN_VALUE",
        "mastery_val_strategy": None,
    },
    # Baseline -> X=1
    {
        "val_strategy": "SELECT_MAX_VALUE",
        "mastery_val_strategy": None,
    },
    # Baseline -> M(min) & X=1
    {
        "val_strategy": "SELECT_MAX_VALUE",
        "mastery_val_strategy": "SELECT_MIN_VALUE",
    },
    # Baseline -> M(min) & X=0
    {
        "val_strategy": "SELECT_MIN_VALUE",
        "mastery_val_strategy": "SELECT_MIN_VALUE",
    },
    # Baseline -> M(max) & X=1
    {
        "val_strategy": "SELECT_MAX_VALUE",
        "mastery_val_strategy": "SELECT_MAX_VALUE",
    },
    # Baseline -> M(max) & X=0
    {
        "val_strategy": "SELECT_MIN_VALUE",
        "mastery_val_strategy": "SELECT_MAX_VALUE",
    },
]

learner = LearnerModel(set(lessons.keys()))

# output_path = "output/heuristics/heuristic_results_advanced_inst_1.csv"

optimizer = LearningPathOptimizer(lessons, activities, learner)
results = optimizer.run_experiment(combinations_to_test)
# results.to_csv(output_path, index=False)

print(results)
