"""Analysis of planned versus actual project performance.

Analyzer compares values from the project's planned Schedule with actual
values derived by Tracker. It calculates start, finish, and duration
variances for individual tasks.

Every derived value is measured to a single data date (`as_of`, defaulting to
today). Tracker ignores tracking events and invoices after that date, so a
backdated analysis is deterministic and cannot report work that had not
happened yet.

Analysis is derived information and does not modify the project, schedule,
or tracking history.
"""

from datetime import timedelta, date
from dataclasses import dataclass
from decimal import Decimal

from planscript.exceptions import SchedulingError
from planscript.model.project import Project


@dataclass
class TaskVariance:
    start: timedelta | None
    finish: timedelta | None
    duration: timedelta | None
    cost: Decimal | None

class Analyzer:
    """Calculate variances between planned and actual task performance.

    Analyzer reads planned values from the project's Schedule and task model
    and actual values from the project's Tracker.
    """

    def __init__(self, project:Project, as_of=None):
        self.project = project
        self.as_of = as_of if as_of is not None else date.today()

    def _require_dates(self):
        """Return the schedule's calendar-date maps.

        Raises:
            SchedulingError: If the schedule is calculated-only (no project
                start date), so calendar dates do not exist to compare against.
        """
        if self.project.schedule.start_dates is None:
            raise SchedulingError(
                "No project start date is available for date projection."
            )
        return self.project.schedule.start_dates, self.project.schedule.finish_dates

    def start_variance(self, task_id):
        """Return the variance between planned and actual start dates.

        Positive values indicate the actual start occurred after the planned
        start; negative values indicate it occurred before the planned start.

        Only work recorded on or before the Analyzer's data date counts, so a
        backdated analysis does not report a start that had not happened yet.

        Returns:
            A timedelta variance, or None if the task has not started.
        """

        actual = self.project.tracker.actual_start(task_id, self.as_of)
        if actual is None:
            return None
        start_dates, _ = self._require_dates()
        return actual - start_dates[task_id]
    
    def finish_variance(self, task_id):
        """Return the variance between planned and actual finish dates.

        Positive values indicate the actual finish occurred after the planned
        finish; negative values indicate it occurred before the planned finish.

        Returns:
            A timedelta variance, or None if the task has not finished.
        """

        actual = self.project.tracker.actual_finish(task_id, self.as_of)
        if actual is None:
            return None
        _, finish_dates = self._require_dates()
        return actual - finish_dates[task_id]

    def duration_variance(self, task_id):
        """Return the difference between actual and planned task duration.

        Summary-task planned duration is derived from its scheduled calendar
        dates. Milestones have zero duration and therefore zero duration
        variance.

        An unfinished task's elapsed duration is measured to the Analyzer's
        reference date, so a backdated analysis does not pick up time that has
        elapsed since.

        Returns:
            A timedelta variance, or None if the task has no actual duration.
        """        
        
        planned = self.project.tasks[task_id].duration

        if planned is None:
            start_dates, finish_dates = self._require_dates()
            planned = finish_dates[task_id] - start_dates[task_id] + timedelta(days=1)

        actual = self.project.tracker.actual_duration(task_id, as_of=self.as_of)

        # A milestone that has not happened has no duration to compare, so it
        # reports no variance rather than a zero one.
        if actual is None:
            return None

        if planned == timedelta(0):
            return timedelta(0)

        return actual - planned

    def cost_variance(self, task_id):
        budget = self.project.budget.get(task_id)
        actual = self.project.tracker.actual_cost(task_id, self.as_of)
        if budget is None or actual is None:
            return None

        return actual - budget

    def total_cost_variance(self):
        actual = self.project.tracker.total_actual_cost(self.as_of)
        budget = self.project.budget.total

        if actual is None or budget is None:
            return None

        return actual - budget    

    def task_variance(self, task_id):
        return TaskVariance(
            start = self.start_variance(task_id),
            finish = self.finish_variance(task_id),
            duration = self.duration_variance(task_id),
            cost = self.cost_variance(task_id)
        )

    def project_actual_start(self) -> date | None:
        actual_starts = []
        for task_id in self.project.tasks:
            start = self.project.tracker.actual_start(task_id, self.as_of)
            if start:
                actual_starts.append(start)
        if actual_starts:
            return min(actual_starts)
        return None

    def actual_progress(self, task_id) -> float | None:
        """Return a task's reported progress as a 0..1 fraction.

        Progress is derived from the tracking events recorded on or before the
        data date, so a backdated analysis does not pick up later progress. A
        milestone has no duration to measure, so it reports as complete or not
        complete rather than as a percentage.

        Returns:
            A fraction between 0 and 1, or None if the task has no duration.
        """

        task = self.project.tasks[task_id]
        state = self.project.tracker.get_task_state(task_id, self.as_of)

        if task.duration is None:
            return None

        if task.duration <= timedelta(0):
            # A milestone has no duration to measure, so it is reported as
            # complete or not complete; completing a task sets 100%.
            return 1.0 if state.percent_complete >= 100 else 0.0

        return state.percent_complete / 100

    def actual_project_progress(self) -> float | None:
        """Return duration-weighted actual progress over the scheduled leaves."""

        num = 0.0
        denom = 0.0
        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            task = self.project.tasks[task_id]
            progress = self.actual_progress(task_id)

            if task.duration is None or progress is None:
                continue

            duration = task.duration.total_seconds()

            if duration <= 0:
                continue

            num += duration * progress
            denom += duration
        if denom:
            return num/denom
        return None

    def _planned_elapsed(self, task_id) -> timedelta | None:
        """Return how much of a task's planned duration should have elapsed.

        Planned work is measured in calendar days to the Analyzer's data date,
        inclusive of the task's planned start day, and is capped at the task's
        planned duration so planned progress never exceeds 100%.

        Milestones have no duration to elapse, and summary tasks have no
        planned duration of their own.

        Returns:
            The elapsed planned duration, or None if the task has no duration.
        """

        duration = self.project.tasks[task_id].duration

        if duration is None:
            return None

        if duration <= timedelta(0):
            return timedelta(0)

        start = self.project.schedule.start_dates[task_id]
        finish = self.project.schedule.finish_dates[task_id]

        if self.as_of >= finish:
            return duration
        if self.as_of >= start:
            return min(self.as_of - start + timedelta(days=1), duration)
        return timedelta(0)

    def planned_progress(self, task_id) -> float | None:
        """Return a task's planned progress as a 0..1 fraction.

        A milestone has no duration to elapse, so it counts as planned once its
        date is reached and not before.
        """

        duration = self.project.tasks[task_id].duration
        elapsed = self._planned_elapsed(task_id)

        if duration is None or elapsed is None:
            return None

        if duration <= timedelta(0):
            finish = self.project.schedule.finish_dates[task_id]
            return 1.0 if self.as_of >= finish else 0.0

        return elapsed / duration

    def planned_project_progress(self) -> float | None:
        """Return duration-weighted planned progress over the scheduled leaves."""

        total_duration = timedelta(0)
        planned_duration = timedelta(0)

        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            task = self.project.tasks[task_id]
            elapsed = self._planned_elapsed(task_id)

            if task.duration is None or elapsed is None:
                continue

            if task.duration <= timedelta(0):
                continue

            total_duration += task.duration
            planned_duration += elapsed

        if total_duration <= timedelta(0):
            return None

        return planned_duration / total_duration

    def project_consumed_cost(self) -> float | None:
        """Return the share of the project budget consumed to the data date.

        Returns:
            A fraction, or None when the project has no planned budget.
        """

        total_actual_cost = self.project.tracker.total_actual_cost(self.as_of)
        total_planned_budget = self.project.budget.total

        if not total_planned_budget:
            return None

        return float(total_actual_cost / total_planned_budget)
