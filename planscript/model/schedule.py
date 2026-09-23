"""Derived schedule model for PlanScript.

A Schedule contains the results of scheduling a Project plan. It includes
CPM timing values, task ordering, float, critical paths, and calendar-based
start and finish dates.

Schedule data is derived and is not authoritative project data.
"""

from dataclasses import dataclass
from datetime import date, timedelta

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
        early_start: Earliest start offset for each task, as a timedelta from
            the project's start day.
        early_finish: Earliest finish offset for each task, as a timedelta
            from the project's start day.
        late_start: Latest start offset for each task without delaying the
            project, as a timedelta.
        late_finish: Latest finish offset for each task without delaying the
            project, as a timedelta.
        total_float: Total float for each task as a timedelta; None for
            summary tasks.
        critical_tasks: Task IDs with zero total float.
        critical_paths: Complete paths through the critical-task network.
        duration: Calculated project duration as a timedelta.
        start_dates: Calendar start date for each task, or None when the
            project has no start_date (calculated-only schedule).
        finish_dates: Calendar finish date for each task, or None when the
            project has no start_date (calculated-only schedule).
    """

    hierarchy: TaskHierarchy
    ordered_task_ids: list[str]
    early_start: dict[str, timedelta]
    early_finish: dict[str, timedelta]
    late_start: dict[str, timedelta]
    late_finish: dict[str, timedelta]
    total_float: dict[str, timedelta | None]
    critical_tasks: list[str]
    critical_paths: list[list[str]]
    duration: timedelta
    start_dates: dict[str, date] | None
    finish_dates: dict[str, date] | None