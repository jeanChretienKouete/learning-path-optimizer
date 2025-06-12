TIERS_CONFIG = {
    "basic": {
        "num_instances": 3,
        "lessons_range": (5, 8),
        "activities_range": (50, 70),
        "max_lessons_per_activity": 2,
        "max_prereqs": 2,
        "effectiveness_range": (30, 40),
    },
    "intermediate": {
        "num_instances": 3,
        "lessons_range": (20, 40),
        "activities_range": (300, 400),
        "max_lessons_per_activity": 3,
        "max_prereqs": 4,
        "effectiveness_range": (20, 25),
    },
    "advanced": {
        "num_instances": 3,
        "lessons_range": (50, 60),
        "activities_range": (800, 1000),
        "max_lessons_per_activity": 5,
        "max_prereqs": 7,
        "effectiveness_range": (7, 12),
    },
}


LEARNING_STYLES = [
    "visual",
    "auditory",
    "reading/writing",
    "kinesthetic",
]

DIFFICULTY_SETTINGS = {
    "easy": {"duration_range": (10, 25)},
    "medium": {"duration_range": (20, 40)},
    "hard": {"duration_range": (30, 60)},
}

ACTIVITY_TYPES = {
    "reading": {"styles": ["reading/writing"]},
    "video": {"styles": ["visual", "auditory"]},
    "quiz": {"styles": ["reading/writing"]},
    "discussion": {"styles": ["auditory"]},
    "exercise": {"styles": ["kinesthetic"]},
    "project": {"styles": ["kinesthetic", "visual"]},
    "game": {"styles": ["kinesthetic", "visual"]},
    "simulation": {"styles": ["visual", "kinesthetic"]},
}
