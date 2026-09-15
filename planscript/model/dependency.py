"""Dependency model for PlanScript.

Dependencies define scheduling relationships between tasks, including the
relationship type and optional lag between the predecessor and successor.
"""

from dataclasses import dataclass
from collections import deque
from datetime import timedelta
from enum import Enum

from planscript.model.task import Task


class DependencyType(Enum):
    """Supported predecessor-to-successor scheduling relationships."""

    FINISH_START = "FS"
    START_START = "SS"
    FINISH_FINISH = "FF"
    START_FINISH = "SF"

@dataclass
class Dependency:
    """A scheduling relationship between two tasks.

    The predecessor and successor identify the tasks being related.
    Dependency type determines which start or finish dates are constrained,
    while lag offsets the resulting relationship.

    Attributes:
        predecessor: Task that establishes the scheduling constraint.
        successor: Task whose schedule is constrained.
        dep_type: Type of scheduling relationship.
        lag: Time offset applied to the dependency relationship.
        lag_unit: Unit used to represent the lag in PlanScript.
    """

    predecessor: Task
    successor: Task
    dep_type: DependencyType = DependencyType.FINISH_START
    lag: timedelta = timedelta(0)
    lag_unit: str = "d"

    def __str__(self) -> str:
        """Return a concise human-readable representation of the dependency."""

        return f"{self.predecessor.number} -> {self.successor.number} ({self.dep_type.value}, Lag: {self.lag.days}d)"


class DependencyGraph:
    """Derived graph representation of a project's task dependencies.

    The graph indexes the project's authoritative Dependency objects by
    predecessor and successor task ID. It provides graph operations used by
    scheduling and other dependency-based analysis.

    The graph is derived from the Project and is not an independent source
    of project data.
    """

    def __init__(self, project):
        """Build a dependency graph from the project's tasks and dependencies."""        

        self.predecessors = {task_id: [] for task_id in project.tasks}
        self.successors = {task_id: [] for task_id in project.tasks}

        for dependency in project.dependencies:
            predecessor_id = dependency.predecessor.number
            successor_id = dependency.successor.number

            self.successors[predecessor_id].append(dependency)
            self.predecessors[successor_id].append(dependency)

    def topological_sort(self) -> list[str]:
        """Return task IDs in dependency order.

        Every task appears after all of its dependency predecessors.
        Summary tasks are included because dependency ordering applies to
        the entire task graph, even though summary tasks are excluded from
        CPM calculations.

        Raises:
            ValueError: If the dependency graph contains a cycle.
        """

        ordered_task_ids = []
        dependency_count = {}

        for task_id in self.predecessors:
            dependency_count[task_id] = len(self.predecessors[task_id])

        queue = deque()

        for task_id, count in dependency_count.items():
            if count == 0:
                queue.append(task_id)

        while queue:
            task_id = queue.popleft()
            ordered_task_ids.append(task_id)

            for dependency in self.successors[task_id]:
                successor_id = dependency.successor.number
                dependency_count[successor_id] -= 1

                if dependency_count[successor_id] == 0:
                    queue.append(successor_id)

        if len(ordered_task_ids) != len(self.predecessors):
            raise ValueError("Circular dependency detected")
        return ordered_task_ids