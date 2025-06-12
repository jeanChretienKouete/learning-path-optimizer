from typing import List


class MissingPrerequisitesError(RuntimeError):
    def __init__(self, missing_prereqs: List[str]):
        super().__init__(f"🔴 Stuck: Missing prerequisites: {missing_prereqs}")
        self.missing_prereqs: List[str] = missing_prereqs
