import datetime
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set

from src.dataclasses.activity import Activity
from utils.data_loader import load_data

lessons, activities = load_data()


@dataclass
class ActivityPerformance:
    """
    Represents the performance score for a specific activity.

    Attributes:
        activity_id (str): ID of the activity performed.
        performance (float): Learner's performance score (typically between 0.0 and 1.0).
    """

    activity_id: str
    performance: float


@dataclass
class SprintLog:
    """
    Represents a log of a single sprint, including activities and mastery state.

    Attributes:
        sprint_id (int): Unique identifier for the sprint.
        activities (List[str]): List of activity IDs performed in this sprint.
        performances (Dict[str, float]): Mapping of activity IDs to performance scores.
        timestamp (datetime.datetime): Time when the sprint was recorded.
        mastery_after (Dict[str, int]): Mastery level of the learner for each lesson after the sprint.
    """

    sprint_id: int
    activities: List[str]
    performances: Dict[str, float]
    timestamp: datetime.datetime
    mastery_after: Dict[str, int]


class LearnerModel:
    """
    Simulates a learner model for tracking mastery and activity history.

    This model keeps track of completed lessons, user preferences,
    and sprint history to simulate learning progress over time.
    """

    def __init__(self, target_lessons: Set[str]) -> None:
        """
        Initializes the learner model with target lessons and default states.

        Args:
            target_lessons (Set[str]): Set of lesson IDs the learner aims to master.
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
        """
        Returns the set of lesson IDs where mastery meets or exceeds the required threshold.

        Returns:
            Set[str]: IDs of completed lessons.
        """
        return {
            l_id
            for l_id in self.current_mastery
            if self.current_mastery[l_id] >= lessons[l_id].min_mastery
        }

    @property
    def completed_activity_ids(self) -> Set[str]:
        """
        Returns the set of activity IDs completed across all recorded sprints.

        Returns:
            Set[str]: IDs of completed activities.
        """
        return {a_id for log in self.sprint_history for a_id in log.activities}

    def record_sprint(
        self, performances: List[ActivityPerformance], activities: List[Activity]
    ) -> None:
        """
        Records a sprint by updating mastery based on performance and logging the result.

        Args:
            performances (List[ActivityPerformance]): List of activity performances in the sprint.
            activities (List[Activity]): List of available activities with effectiveness details.
        """
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

    def print_sprints(self) -> None:
        """
        Prints the most recent sprint's performance and mastery updates.

        If no sprints have been recorded yet, a message is printed instead.
        """

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
