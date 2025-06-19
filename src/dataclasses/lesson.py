from dataclasses import dataclass
from typing import Set


@dataclass
class Lesson:
    """
    Represents a lesson.

    Attributes:
        id (str): Unique identifier for the lesson.
        name (str): Human-readable name of the lesson.
        min_mastery (int): Minimum mastery level required to consider the lesson mastered.
        prerequisites (Set[str]): Set of lesson IDs that must be completed before this lesson.
    """

    id: str
    name: str
    min_mastery: int
    prerequisites: Set[str]
