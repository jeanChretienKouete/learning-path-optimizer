import time
from typing import Dict, List, Literal

import networkx as nx
import pandas as pd
from ortools.sat.python import cp_model

from models.dataclasses.activity import Activity
from models.dataclasses.learner import LearnerModel
from models.dataclasses.lesson import Lesson
from utils.lesson_graph_builder import build_lesson_graph


class LearningPathOptimizer:
    def __init__(
        self,
        lessons: Dict[str, Lesson],
        activities: List[Activity],
        learner: LearnerModel,
    ):
        self.learner = learner
        self.lessons = lessons
        self.lesson_graph = build_lesson_graph(lessons)
        self.activities = [
            activity
            for activity in activities
            if activity.id not in self.learner.completed_activity_ids
        ]
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.solver.parameters.max_time_in_seconds = 600
        self.solver.parameters.random_seed = 42

        self.solver.parameters.log_search_progress = True

    def _build_variables(self):
        self.x = {a.id: self.model.NewBoolVar(f"x_{a.id}") for a in self.activities}

        self.mastery = {
            l_id: self.model.NewIntVar(
                self.learner.current_mastery.get(l_id, 0),
                100,
                f"mastery_{l_id}",
            )
            for l_id in self.lessons
        }

    def _add_constraints(self):
        # 1. Mastery accumulation
        for l_id, lesson in self.lessons.items():
            self.model.Add(
                self.mastery[l_id]
                == self.learner.current_mastery.get(l_id, 0)
                + sum(
                    a.effectiveness.get(l_id, 0) * self.x[a.id] for a in self.activities
                )
            )

            # 2. Enforce lesson's minimum requirement
            self.model.Add(self.mastery[l_id] >= lesson.min_mastery)

        for a in self.activities:
            for lesson_id in a.effectiveness:
                prereqs = nx.ancestors(self.lesson_graph, lesson_id)
                for pre_id in prereqs:
                    # 3. If an activity is selected, all its lesson prerequisites must meet min_mastery
                    self.model.Add(
                        self.mastery[pre_id] >= self.lessons[pre_id].min_mastery
                    ).OnlyEnforceIf(self.x[a.id])

    def _build_objective(self, minimize: str | None = None):
        if minimize == "duration":
            self.model.Minimize(sum(a.duration * self.x[a.id] for a in self.activities))
        else:
            self.model.Minimize(sum(self.x[a.id] for a in self.activities))

    def _add_decision_heuristics(
        self,
        val_strategy: Literal["SELECT_MAX_VALUE", "SELECT_MIN_VALUE"],
        mastery_val_strategy: Literal["SELECT_MIN_VALUE", "SELECT_MAX_VALUE"] | None,
    ):
        """Configurable heuristic for both activity and mastery variables."""
        # 1. Pre-sort activities based on chosen ordering
        topo_order = list(nx.topological_sort(self.lesson_graph))
        lesson_rank = {l_id: i for i, l_id in enumerate(topo_order)}

        sorted_activities = sorted(
            self.activities,
            key=lambda a: max(lesson_rank[l_id] for l_id in a.effectiveness),
        )
        activity_vars = [self.x[a.id] for a in sorted_activities]

        # 2. Sort mastery variables by topological order
        mastery_vars = [self.mastery[l_id] for l_id in topo_order]

        # 3. Apply strategies
        self.model.AddDecisionStrategy(
            activity_vars,
            cp_model.CHOOSE_FIRST,
            getattr(cp_model, val_strategy),  # e.g., SELECT_MAX_VALUE/SELECT_MIN_VALUE
        )

        if mastery_val_strategy:
            self.model.AddDecisionStrategy(
                mastery_vars,
                cp_model.CHOOSE_FIRST,  # Follow topological order
                getattr(
                    cp_model, mastery_val_strategy
                ),  # e.g., SELECT_MIN_VALUE/SELECT_MAX_VALUE
            )

    def run_experiment(self, heuristic_combinations: list[dict]):
        """Test multiple heuristic combinations and log results."""
        results = []
        for config in heuristic_combinations:
            self.model = cp_model.CpModel()  # Reset model
            self._build_variables()
            self._add_constraints()
            self._add_decision_heuristics(**config)
            self._build_objective()

            self.solver = cp_model.CpSolver()
            self.solver.parameters.max_time_in_seconds = 600
            self.solver.parameters.search_branching = cp_model.FIXED_SEARCH
            self.solver.parameters.log_search_progress = True

            start_time = time.time()
            status = self.solver.Solve(self.model)
            solve_time = time.time() - start_time

            results.append(
                {
                    **config,
                    "time_sec": solve_time,
                    "objective": self.solver.ObjectiveValue()
                    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
                    else None,
                    "status": self.solver.StatusName(status),
                    "conflicts": self.solver.NumConflicts(),
                    "branches": self.solver.NumBranches(),
                }
            )

        return pd.DataFrame(results)

    def run(self):
        print("🎯 Set of activities selection")
        try:
            print("🎯 Adding constraints")
            self._build_variables()
            print("🎯 Adding constraints")
            self._add_constraints()
            print("🎯 Building objective")
            self._build_objective()
            print("🎯 Solving model")
            start = time.time()
            status = self.solver.Solve(self.model)
            print(f"✅ Solver finished in {time.time() - start} seconds.")
        except Exception as e:
            print(f"❌ Solver failed: {e}")
            raise RuntimeError(f"Solver failed: {e}")

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(
                f"✅ Learning complete or no more feasible sprints. Status: {self.solver.StatusName(status)}"
            )
            raise ValueError("Learning complete or no feasible activities remain.")

        selected_activities = [
            a for a in self.activities if self.solver.Value(self.x[a.id]) == 1
        ]

        print(f"\n🎉 Finished selecting {len(selected_activities)} activities.")
        return selected_activities
