import contextlib
import json
import logging
import os

from scripts.data_generator import Activity, Lesson
from utils.logger import CustomLogger

with open(os.devnull, "w") as fnull:
    with contextlib.redirect_stdout(fnull):
        from ortools.sat.python import cp_model

SCALE = 100

logger = CustomLogger(__name__, logging.INFO)


def extract_required_mastery_levels(lessons) -> dict[str, int]:
    return {
        lesson.lesson_id: int(lesson.required_mastery_level * SCALE)
        for lesson in lessons
    }


def extract_lessons_prerequisites(lessons: list[Lesson]) -> dict[str, dict[str, int]]:
    return {
        lesson.lesson_id: {
            list(prerequisite.keys())[0]: int(list(prerequisite.values())[0] * 100)
            for prerequisite in lesson.prerequisites
        }
        for lesson in lessons
    }


def extract_acquisition_matrices(
    activities: list[Activity], lessons: list[Lesson]
) -> dict[str, dict[str, int]]:
    # Initialize acquisition matrices
    acquisition_matrix = {
        activity.activity_id: {lesson.lesson_id: 0 for lesson in lessons}
        for activity in activities
    }

    for activity in activities:
        activity_id = activity.activity_id
        lesson_contributions = activity.lesson_contributions

        for lesson in lessons:
            lesson_id = lesson.lesson_id
            if lesson_id in lesson_contributions:
                contribution = lesson_contributions[lesson_id]
                acquisition_matrix[activity_id][lesson_id] = int(contribution * SCALE)

    return acquisition_matrix


def get_activity_limits(activities: list[Activity]) -> dict[str, int]:
    return {
        activity.activity_id: activity.max_selection_limit for activity in activities
    }


def get_lesson_min_coverages(lessons: list[Lesson]) -> dict[str, int]:
    return {lesson.lesson_id: lesson.min_coverage for lesson in lessons}


class ActivityScheduler:
    def __init__(
        self, lessons: list[Lesson], activities: list[Activity], timesteps: int
    ) -> None:
        """Initialize the lesson scheduler with lessons, activities, prerequisites, and coverage."""

        self.required_mastery_levels = extract_required_mastery_levels(lessons)
        self.acquisition_matrix = extract_acquisition_matrices(activities, lessons)
        self.activity_limits = get_activity_limits(activities)
        self.lesson_coverages = get_lesson_min_coverages(lessons)
        self.lesson_prerequisites = extract_lessons_prerequisites(lessons)
        self.timesteps = timesteps
        self.P = self.M = self.X = self.Y = dict()

        self.model = cp_model.CpModel()

        self.create_variables()
        logger.info("Variables created")
        self.add_constraints()
        logger.info("Constraints added")
        self.set_objective()
        logger.info("Objective set")

    def create_variables(self) -> None:
        for t in range(0, self.timesteps + 1):
            for lesson_id in self.lesson_coverages:
                self.M[lesson_id, t] = self.model.NewIntVar(
                    0,
                    int(SCALE * self.required_mastery_levels[lesson_id]),
                    f"X[{lesson_id}][{t}]",
                )

            if t == 0:
                continue

            self.Y[t] = self.model.NewBoolVar(f"Y[{t}]")
            for activity_id in self.activity_limits:
                self.X[activity_id, t] = self.model.NewBoolVar(f"X[{activity_id}][{t}]")

            for lesson_id in self.lesson_prerequisites:
                self.P[lesson_id, t] = self.model.NewBoolVar(f"P[{lesson_id}][{t}]")

    def add_constraints(self) -> None:
        # If any activity is selected at t, then Y[t] must be 1
        for t in range(1, self.timesteps + 1):
            self.model.AddMaxEquality(
                self.Y[t],
                [self.X[activity_id, t] for activity_id in self.activity_limits],
            )

        # If an activity contributes to lesson l, and lesson l has prerequisites,
        # then that activity can only be selected at time t if all prerequisites are satisfied at time −1
        for lesson_l, prerequisites in self.lesson_prerequisites.items():
            for t in range(1, self.timesteps + 1):
                # For each prerequisite, create satisfaction condition
                prereq_satisfied_bools = []
                for prereq_lesson in prerequisites:
                    bool_var = self.model.NewBoolVar(
                        f"satisfy_{prereq_lesson}_before_{lesson_l}_t{t}"
                    )
                    self.model.Add(
                        self.M[prereq_lesson, t - 1] >= prerequisites[prereq_lesson]
                    ).OnlyEnforceIf(bool_var)
                    self.model.Add(
                        self.M[prereq_lesson, t - 1] < prerequisites[prereq_lesson]
                    ).OnlyEnforceIf(bool_var.Not())
                    prereq_satisfied_bools.append(bool_var)

                # Combine all prerequisite satisfaction into one
                all_satisfied = self.model.NewBoolVar(
                    f"all_prereqs_met_{lesson_l}_t{t}"
                )
                self.model.AddBoolAnd(prereq_satisfied_bools).OnlyEnforceIf(
                    all_satisfied
                )
                self.model.AddBoolOr(
                    [b.Not() for b in prereq_satisfied_bools]
                ).OnlyEnforceIf(all_satisfied.Not())

                # For each activity that contributes to this lesson, enforce the constraint
                for activity_id in self.acquisition_matrix:
                    if self.acquisition_matrix[activity_id].get(lesson_l, 0) > 0:
                        self.model.Add(self.X[activity_id, t] == 0).OnlyEnforceIf(
                            all_satisfied.Not()
                        )

        # Each time step must have exactly one activity selected
        for t in range(1, self.timesteps + 1):
            self.model.Add(
                sum(self.X[activity, t] for activity in self.activity_limits) <= 1
            )

        # Activity selection contiguity constraint
        for t in range(1, self.timesteps):
            self.model.Add(
                sum(self.X[activity_id, t] for activity_id in self.activity_limits)
                >= sum(
                    self.X[activity_id, t + 1] for activity_id in self.activity_limits
                )
            )

        # Each activity can be used up to ca times
        for activity_id in self.activity_limits:
            self.model.Add(
                sum(self.X[activity_id, t] for t in range(1, self.timesteps + 1))
                <= self.activity_limits[activity_id]
            )

        # Initial mastery is zero
        for lesson_id in self.required_mastery_levels:
            self.model.Add(self.M[lesson_id, 0] == 0)

        # Mastery levels are updated based on selected activity
        # Also ensure that mastery level doesn't decrease over time
        for lesson_id in self.required_mastery_levels:
            for t in range(1, self.timesteps + 1):
                self.model.Add(
                    self.M[lesson_id, t]
                    == self.M[lesson_id, t - 1]
                    + sum(
                        self.acquisition_matrix[activity_id][lesson_id]
                        * self.X[activity_id, t]
                        for activity_id in self.acquisition_matrix
                    )
                )

        # Mastery level must be greater than or equal to required mastery level
        for lesson_id in self.required_mastery_levels:
            self.model.Add(
                self.M[lesson_id, self.timesteps]
                >= self.required_mastery_levels[lesson_id]
            )

        # Each lesson must be covered sufficiently at least a mininum number of time
        for lesson_id in self.required_mastery_levels:
            self.model.Add(
                sum(
                    sum(
                        self.X[activity_id, t]
                        for activity_id in self.acquisition_matrix
                        if self.acquisition_matrix[activity_id][lesson_id] > 0
                    )
                    for t in range(1, self.timesteps + 1)
                )
                >= self.lesson_coverages[lesson_id]
            )

    def set_objective(self) -> None:
        # Minimize the number of time steps
        self.model.Minimize(sum(self.Y[t] for t in range(1, self.timesteps + 1)))

    def solve(self) -> None:
        """Solve the model and return the results."""
        solver = cp_model.CpSolver()
        logger.info("Solving...")
        status = solver.Solve(self.model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            logger.info("Solution found.")
            for t in range(1, self.timesteps + 1):
                if solver.Value(self.Y[t]):
                    for activity_id in self.activity_limits:
                        if solver.Value(self.X[activity_id, t]):
                            print(f"Time step {t}: Activity {activity_id} selected")
        else:
            logger.info("No solution found.")


def main() -> None:
    with open("data/lessons.json", "r") as f:
        lessons = json.load(f)
        lessons = [Lesson(**lesson) for lesson in lessons]

    with open("data/activities.json", "r") as f:
        activities = json.load(f)
        activities = [Activity(**activity) for activity in activities]

    TIMESETPS = 500

    scheduler = ActivityScheduler(lessons, activities, TIMESETPS)
    scheduler.solve()


if __name__ == "__main__":
    main()
