import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set

from src.dataclasses.activity import Activity
from utils.data_loader import load_data

lessons, activities = load_data()


@dataclass
class ActivityPerformance:
    activity_id: str
    performance: float  # 0.0 to 1.0 (normalized score)


@dataclass
class SprintLog:
    sprint_id: int
    activities: List[str]  # activity IDs
    performances: Dict[str, float]  # activity_id: performance
    timestamp: datetime.datetime
    mastery_after: Dict[str, int]  # lesson_id: mastery (0 to 100)


class LearnerModel:
    def __init__(self, target_lessons: Set[str]):
        """
        Tracks learner's state and goals
        """
        self.target_lessons = target_lessons
        self.sprint_history: List[SprintLog] = []
        self.current_mastery: Dict[str, int] = defaultdict(int)
        self.style_preferences: Dict[str, float] = defaultdict(lambda: 0.5)
        self.activity_type_preferences: Dict[str, float] = defaultdict(lambda: 0.5)
        self.difficulty_preferences: Dict[str, float] = defaultdict(lambda: 0.5)
        self.preference_ema_alpha = 0.3
        self.next_sprint_id = 1

    @property
    def completed_lesson_ids(self) -> Set[str]:
        """Derive completed lessons from history"""
        return {
            l_id
            for l_id in self.current_mastery
            if self.current_mastery[l_id] >= lessons[l_id].min_mastery
        }

    @property
    def completed_activity_ids(self) -> Set[str]:
        """Derive completed activities from history"""
        return {a_id for log in self.sprint_history for a_id in log.activities}

    def record_sprint(
        self, performances: List[ActivityPerformance], activities: List[Activity]
    ):
        # Calculate mastery gains
        activity_map = {a.id: a for a in activities}
        for perf in performances:
            activity = activity_map[perf.activity_id]
            for lesson_id, effectiveness in activity.effectiveness.items():
                self.current_mastery[lesson_id] = min(
                    100,
                    self.current_mastery.get(lesson_id, 0)
                    + int(effectiveness * perf.performance),
                )

        # Log this sprint
        self.sprint_history.append(
            SprintLog(
                sprint_id=self.next_sprint_id,
                activities=[p.activity_id for p in performances],
                performances={p.activity_id: p.performance for p in performances},
                timestamp=datetime.datetime.now(),
                mastery_after=self.current_mastery.copy(),
            )
        )
        self.next_sprint_id += 1

    def print_sprints(self):
        if not self.sprint_history:
            print("No sprints recorded yet.")
            return
        log = self.sprint_history[-1]
        print("=" * 40)
        print(f"Sprint ID     : {log.sprint_id}")
        print(f"Timestamp     : {log.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\nActivities Performed:")
        for a_id in log.activities:
            perf = log.performances[a_id]
            print(f"  - {a_id} (ID: {a_id}, Performance: {perf:.2f})")

        print("\nMastery After Sprint:")
        for lesson_id, mastery in log.mastery_after.items():
            print(f"  - {lessons[lesson_id].name} (ID: {lesson_id}): {mastery}%")

        print("=" * 40)
        print()
