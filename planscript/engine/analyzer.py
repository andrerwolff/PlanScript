"""Analysis of planned versus actual project performance.

Analyzer compares values from the project's planned Schedule with actual
values derived by Tracker. It calculates start, finish, and duration
variances for individual tasks.

Analysis is derived information and does not modify the project, schedule,
or tracking history.
"""

from datetime import timedelta, date
from dataclasses import dataclass


@dataclass
class TaskVariance:
    start: timedelta | None
    finish: timedelta | None
    duration: timedelta | None

class Analyzer:
    """Calculate variances between planned and actual task performance.

    Analyzer reads planned values from the project's Schedule and task model
    and actual values from the project's Tracker.
    """

    def __init__(self, project):
        self.project = project

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
        return actual - self.project.schedule.start_dates[task_id]
    
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
        return  actual - self.project.schedule.finish_dates[task_id]

    def duration_variance(self, task_id):
        """Return the difference between actual and planned task duration.

        Summary-task planned duration is derived from its scheduled calendar
        dates. Milestones have zero duration and therefore zero duration
        variance.

        Returns:
            A timedelta variance, or None if the task has no actual duration.
        """        
        
        planned = self.project.tasks[task_id].duration
        if planned == timedelta(0):
            return timedelta(0)
        elif planned is None:
            planned = self.project.schedule.finish_dates[task_id] - self.project.schedule.start_dates[task_id] + timedelta(days=1)

        actual = self.project.tracker.actual_duration(task_id)

        if actual is None:
            return None

        return actual - planned

    def task_variance(self, task_id):
        return TaskVariance(
            start = self.start_variance(task_id),
            finish = self.finish_variance(task_id),
            duration = self.duration_variance(task_id)
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

    def project_progress(self) -> float | None:
        num = 0
        denom = 0
        for task_id in self.project.tasks:
            if self.project.schedule.hierarchy.is_summary(task_id):
                continue
            task = self.project.tasks[task_id]
            state = self.project.tracker.get_task_state(task_id)

            if task.duration is None:
                continue

            duration = task.duration.total_seconds()

            if duration <= 0:
                continue

            num += duration * (state.percent_complete) 
            denom += duration
        if denom:
            return num/denom
        return None
