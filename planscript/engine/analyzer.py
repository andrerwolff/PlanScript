"""Analysis of planned versus actual project performance.

Analyzer compares values from the project's planned Schedule with actual
values derived by Tracker. It calculates start, finish, and duration
variances for individual tasks.

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

        Returns:
            A timedelta variance, or None if the task has not started.
        """

        actual = self.project.tracker.actual_start(task_id)
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

        actual = self.project.tracker.actual_finish(task_id)
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
        if planned == timedelta(0):
            return timedelta(0)
        elif planned is None:
            start_dates, finish_dates = self._require_dates()
            planned = finish_dates[task_id] - start_dates[task_id] + timedelta(days=1)

        actual = self.project.tracker.actual_duration(task_id, current_date=self.as_of)

        if actual is None:
            return None

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
            start = self.project.tracker.actual_start(task_id)
            if start:
                actual_starts.append(start)
        if actual_starts:
            return min(actual_starts)
        return None

    def actual_progress(self, task_id) -> float | None:
        task = self.project.tasks[task_id]
        state = self.project.tracker.get_task_state(task_id)

        if task.duration is None:
            return None
        duration = task.duration.total_seconds()
        if duration <= 0:
            return None
        num = duration * (state.percent_complete / 100)
        denom = duration
        if denom:
            return num/denom
        return None

    def actual_project_progress(self) -> float | None:
        num = 0
        denom = 0
        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            task = self.project.tasks[task_id]
            state = self.project.tracker.get_task_state(task_id)

            if task.duration is None:
                continue

            duration = task.duration.total_seconds()

            if duration <= 0:
                continue

            num += duration * (state.percent_complete / 100) 
            denom += duration
        if denom:
            return num/denom
        return None

    def planned_progress(self, task_id) -> float | None:
        print(task_id)
        planned_duration = timedelta(0)
        
        task = self.project.tasks[task_id]
        duration = task.duration
        start = self.project.schedule.start_dates[task_id]
        finish = self.project.schedule.finish_dates[task_id]

        if self.as_of >= finish:
            planned_duration = duration
        elif self.as_of > start:
            planned_duration = (self.as_of - start)

        if duration == timedelta(0):
            return 1
        progress = planned_duration / duration
        if progress is not None:
            return progress
        return 1
        
    def planned_project_progress(self) -> float | None:
        total_duration = timedelta(0)
        planned_duration = timedelta(0)

        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            task = self.project.tasks[task_id]

            duration = task.duration
            start = self.project.schedule.start_dates[task_id]
            finish = self.project.schedule.finish_dates[task_id]

            total_duration += duration
            if self.as_of >= finish:
                planned_duration += duration
            elif self.as_of > start:
                planned_duration += (self.as_of - start)

        if total_duration == timedelta(0):
            return None

        return planned_duration / total_duration

    def project_consumed_cost(self) -> float | None:
        total_actual_cost = self.project.tracker.total_actual_cost()
        total_planned_budget = self.project.budget.total
        return total_actual_cost / total_planned_budget
