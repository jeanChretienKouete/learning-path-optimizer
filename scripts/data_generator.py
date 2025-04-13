import json
import logging
import random
from collections import defaultdict
from dataclasses import asdict, dataclass

from utils.logger import CustomLogger

# ========== CONFIGURABLE PARAMETERS ==========
NUM_LESSONS = 10
NUM_ACTIVITIES = 70
NUM_TIME_STEPS = 12

MASTERY_MIN = 0.6
MASTERY_MAX = 1.0
COVERAGE_MIN = 1
COVERAGE_MAX = 3

ACTIVITY_LESSONS_MIN = 1
ACTIVITY_LESSONS_MAX = 3
ACTIVITY_CONTRIBUTION_MIN = 0.1
ACTIVITY_CONTRIBUTION_MAX = 0.4
ACTIVITY_SELECTION_LIMIT_MIN = 1
ACTIVITY_SELECTION_LIMIT_MAX = 3

RANDOM_SEED = 42
# ============================================

# Setup logging
logger = CustomLogger("Data Generator", logging.INFO)
random.seed(RANDOM_SEED)


# ========== DATA CLASSES ==========
@dataclass
class Lesson:
    lesson_id: str
    required_mastery_level: float
    min_coverage: int
    prerequisites: list[dict[str, float]]


@dataclass
class Activity:
    activity_id: str
    max_selection_limit: int
    lesson_contributions: dict[str, float]


# ========== GENERATORS ==========
def generate_lessons() -> list[Lesson]:
    lessons = [
        Lesson(
            lesson_id=f"L{index + 1}",
            required_mastery_level=round(random.uniform(MASTERY_MIN, MASTERY_MAX), 2),
            min_coverage=random.randint(COVERAGE_MIN, COVERAGE_MAX),
            prerequisites=[],
        )
        for index in range(NUM_LESSONS)
    ]

    # Establish prerequisites
    for index in range(1, NUM_LESSONS):
        # Randomly decide how many prerequisites to add (at least one)
        num_prerequisites = random.randint(
            1, min(index, 3)
        )  # Up to 3 prerequisites from previous lessons
        selected_prerequisites = random.sample(
            range(index), num_prerequisites
        )  # Select unique previous lessons

        for prerequisite_index in selected_prerequisites:
            prerequisite_lesson_id = lessons[prerequisite_index].lesson_id
            required_mastery_level = round(random.uniform(MASTERY_MIN, MASTERY_MAX), 2)

            lessons[index].prerequisites.append(
                {prerequisite_lesson_id: required_mastery_level}
            )

    return lessons


def generate_activities(lessons: list[Lesson]) -> list[Activity]:
    activities = []
    lesson_ids = [lesson.lesson_id for lesson in lessons]
    mastery_targets = {
        lesson.lesson_id: lesson.required_mastery_level for lesson in lessons
    }
    current_mastery = defaultdict(float)
    remaining_activities = NUM_ACTIVITIES

    # Phase 1: Prioritize lessons based on unmet mastery
    unmet_lessons = set(lesson_ids)

    while unmet_lessons and remaining_activities > 0:
        # Sort lessons by how much mastery they need
        sorted_lessons = sorted(
            unmet_lessons,
            key=lambda lid: mastery_targets[lid] - current_mastery[lid],
            reverse=True,
        )
        sample_size = random.randint(
            ACTIVITY_LESSONS_MIN, min(ACTIVITY_LESSONS_MAX, len(unmet_lessons))
        )
        lesson_subset = sorted_lessons[
            :sample_size
        ]  # Take the top lessons that need the most attention

        contributions = {}
        for lid in lesson_subset:
            needed = mastery_targets[lid] - current_mastery[lid]
            max_possible_contrib = min(ACTIVITY_CONTRIBUTION_MAX, needed)
            contrib = round(
                random.uniform(ACTIVITY_CONTRIBUTION_MIN, max_possible_contrib), 2
            )
            contributions[lid] = contrib
            current_mastery[lid] += contrib

            if current_mastery[lid] >= mastery_targets[lid]:
                unmet_lessons.discard(lid)

        activities.append(
            Activity(
                activity_id=f"A{len(activities) + 1}",
                max_selection_limit=random.randint(
                    ACTIVITY_SELECTION_LIMIT_MIN, ACTIVITY_SELECTION_LIMIT_MAX
                ),
                lesson_contributions=contributions,
            )
        )
        remaining_activities -= 1

    # Phase 2: Random contributions for remaining activities
    for _ in range(remaining_activities):
        sample_size = random.randint(ACTIVITY_LESSONS_MIN, ACTIVITY_LESSONS_MAX)
        lesson_subset = random.sample(lesson_ids, sample_size)

        activities.append(
            Activity(
                activity_id=f"A{len(activities) + 1}",
                max_selection_limit=random.randint(
                    ACTIVITY_SELECTION_LIMIT_MIN, ACTIVITY_SELECTION_LIMIT_MAX
                ),
                lesson_contributions={
                    lid: round(
                        random.uniform(
                            ACTIVITY_CONTRIBUTION_MIN, ACTIVITY_CONTRIBUTION_MAX
                        ),
                        2,
                    )
                    for lid in lesson_subset
                },
            )
        )

    return activities


# ========== CHECK ==========
def check_coherence(lessons: list[Lesson], activities: list[Activity]) -> None:
    total_contrib = {lesson.lesson_id: 0.0 for lesson in lessons}
    for activity in activities:
        for lesson_id, val in activity.lesson_contributions.items():
            total_contrib[lesson_id] += val
    for lesson in lessons:
        if total_contrib[lesson.lesson_id] < lesson.required_mastery_level:
            logger.warning(
                f"{lesson.lesson_id} may not reach mastery: "
                f"{total_contrib[lesson.lesson_id]:.2f} < {lesson.required_mastery_level:.2f}"
            )


# ========== MAIN ==========
def main() -> None:
    lessons = generate_lessons()
    activities = generate_activities(lessons)
    check_coherence(lessons, activities)

    lessons = [asdict(lesson) for lesson in lessons]
    activities = [asdict(activity) for activity in activities]

    with open("data/lessons.json", "w") as f:
        json.dump(lessons, f, indent=2)
    with open("data/activities.json", "w") as f:
        json.dump(activities, f, indent=2)

    logger.info(f"{NUM_LESSONS} lessons and {NUM_ACTIVITIES} activities generated.")


if __name__ == "__main__":
    main()
