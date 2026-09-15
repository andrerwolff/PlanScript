"""Derived schedule model for PlanScript.

A Schedule contains the results of scheduling a Project plan. It includes
CPM timing values, task ordering, float, critical paths, and calendar-based
start and finish dates.

Schedule data is derived and is not authoritative project data.
"""

from dataclasses import dataclass
from datetime import date

from planscript.model.hierarchy import TaskHierarchy

@dataclass
class Schedule:
    """Calculated schedule for a PlanScript project.

    Schedule stores the results produced by the scheduler rather than the
    underlying project plan. It contains CPM timing values, task ordering,
    critical tasks and paths, project duration, and calendar-based dates.

    Summary-task dates are derived from the dates of their descendants after
    the schedule is calculated.

    Attributes:
        hierarchy: Task hierarchy used to interpret summary relationships.
        ordered_task_ids: Tasks in dependency-based scheduling order.
        early_start: Earliest start time for each task, in working-time units.
        early_finish: Earliest finish time for each task, in working-time units.
        late_start: Latest start time for each task without delaying the project.
        late_finish: Latest finish time for each task without delaying the project.
        total_float: Total available float for each task.
        critical_tasks: Task IDs with zero total float.
        critical_paths: Complete paths through the critical-task network.
        duration: Calculated project duration in working-time units.
        start_dates: Calendar start date for each task.
        finish_dates: Calendar finish date for each task.
    """

    hierarchy: TaskHierarchy
    ordered_task_ids: list[str]
    early_start: dict[str, int]
    early_finish: dict[str, int]
    late_start: dict[str, int]
    late_finish: dict[str, int]
    total_float: dict[str, int | None]
    critical_tasks: list[str]
    critical_paths: list[list[str]]
    duration: int
    start_dates: dict[str, date]
    finish_dates: dict[str, date]