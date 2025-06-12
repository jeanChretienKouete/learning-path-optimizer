from models.cp.path_optimizer import LearningPathOptimizer
from utils.data_loader import load_data

lessons, activities = load_data()

optimizer = LearningPathOptimizer(
    lessons, activities, target_lessons=set(lessons.keys())
)
optimizer.run(max_sprints=5, minimize="duration")
