from dataclasses import dataclass
from typing import Dict


@dataclass
class Activity:
    """
    Represents a learning activity linked to one or more lessons.

    Attributes:
        id (str): Unique identifier for the activity.
        name (str): Human-readable name of the activity.
        duration (int): Estimated duration of the activity in minutes.
        style (str): Style of the activity (e.g., "visual", "auditory").
        effectiveness (Dict[str, int]): Mapping from lesson IDs to effectiveness scores (1-100).
        difficulty (str): Difficulty level of the activity ("easy", "medium", "hard").
        type (str): Type of the activity (e.g., "video", "reading", "quiz").
    """

    id: str
    name: str
    duration: int
    style: str
    effectiveness: Dict[str, int]
    difficulty: str
    type: str
