import json
from functools import lru_cache
from typing import Dict, List

from models.dataclasses.activity import Activity
from models.dataclasses.lesson import Lesson


@lru_cache(maxsize=None)
def load_data() -> tuple[Dict[str, Lesson], List[Activity]]:
    with open("benchmarks/advanced/instance_01/lessons.json", "r") as f:
        lessons = json.load(f)
        lessons = {lesson["id"]: Lesson(**lesson) for lesson in lessons}

    with open("benchmarks/advanced/instance_01/activities.json", "r") as f:
        activities = json.load(f)
        activities = [Activity(**activity) for activity in activities]

    return lessons, activities
