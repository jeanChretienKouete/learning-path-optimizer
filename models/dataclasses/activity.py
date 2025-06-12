from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class Activity:
    id: str
    name: str
    duration: int
    style: str
    effectiveness: Dict[str, int]  # lesson_id -> effectiveness
    difficulty: str
    type: str
