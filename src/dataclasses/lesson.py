from dataclasses import dataclass
from typing import Set


@dataclass
class Lesson:
    id: str
    name: str
    min_mastery: int
    prerequisites: Set[str]
