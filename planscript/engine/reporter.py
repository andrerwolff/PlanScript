from dataclasses import dataclass, field
from enum import Enum
from datetime import date, timedelta

from planscript.model.project import Project
from planscript.engine.tracker import TaskStatus, TaskState
from planscript.engine.analyzer import Analyzer

class ProjectStatus(Enum):
    """Derived status of a project based on its tasks."""

    NOT_STARTED = "Not Started"
    STARTED = "Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

class ScheduleCondition(Enum):
    """Derived status of a task based on schedule."""
    
    ON_SCHEDULE = "On Schedule"
    LATE = "Late"
    BLOCKED = "Blocked"
    OVERDUE = "Overdue"

@dataclass
class TaskReport:
    task_id: str
    name: str
    state: TaskState
    condition: ScheduleCondition

    planned_start: date | None
    planned_finish: date | None

    actual_start: date | None
    actual_finish: date | None

    start_variance: timedelta | None = None
    finish_variance: timedelta | None = None
    duration_variance: timedelta | None = None
    days_overdue: timedelta | None = None

    def __str__(self):
        return f"{self.task_id} - {self.name} [{self.state.status.value}]"

@dataclass
class ProjectReport:
    
    name: str
    status: ProjectStatus
    as_of: date
    planned_start: date | None
    planned_finish: date | None
    planned_duration: timedelta | None
    actual_start: date | None
    progress: float | None
    overdue_tasks: list[TaskReport]
    blocked_tasks: list[TaskReport]
    late_tasks: list[TaskReport]
    upcoming_deadlines: list[TaskReport]
    upcoming_starts: list[TaskReport]
    look_ahead: timedelta

    def render_text(self):
        str = (f"\nStatus Report as-of {self.as_of}\n"
              f"=======================================\n"
              f"Project Name: {self.name}\n\n"
              f"    Status: {self.status.value}\n\n"
              f"    Planned Start: {self.planned_start}\n"
              f"    Planned Finish: {self.planned_finish}\n"
              f"    Planned Duration: {self.planned_duration.days}d\n"
              f"    Actual Start: {self.actual_start}\n"
              f"    Progress: {self.progress:.2g}%\n\n"
              f"Overdue Tasks\n")
        for t_report in self.overdue_tasks:
            str += (f"    {t_report} is overdue\n")
        str += (f"Upcoming Deadlines (+{self.look_ahead.days}d)\n")
        for t_report in self.upcoming_deadlines:
            str += (f"    {t_report} is due on {t_report.planned_finish}\n")
        str += (f"Upcoming Tasks (+{self.look_ahead.days}d)\n")
        for t_report in self.upcoming_starts:
            str += (f"    {t_report} starts on {t_report.planned_start}\n")
        return str

@dataclass
class ReportBuilder:
    project: Project
    as_of: date = field(default_factory=date.today)
    look_ahead: timedelta = timedelta(days=21)
    

    def build(self) -> ProjectReport:
        analysis = Analyzer(self.project)
        summary = self._task_summary(analysis, self.as_of, self.look_ahead)


        return ProjectReport(
            name=self.project.name,
            status=self._project_status(),
            as_of=self.as_of,
            planned_start=self.project.start_date,
            planned_finish=self.project.finish_date,
            planned_duration=self.project.schedule.duration,
            actual_start=analysis.project_actual_start(),
            progress=analysis.project_progress(),
            overdue_tasks=summary["overdues"],
            blocked_tasks=summary["blocked"],
            late_tasks=summary["lates"],
            upcoming_deadlines=summary["deadlines"],
            upcoming_starts=summary["starts"],
            look_ahead=self.look_ahead
        )

    def _project_status(self) -> ProjectStatus:
        statuses = set()
        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            statuses.add(self.project.tracker.get_task_state(task_id).status)

        if statuses and statuses <= {TaskStatus.COMPLETED}:
            return ProjectStatus.COMPLETED
        
        if TaskStatus.IN_PROGRESS in statuses:
            return ProjectStatus.IN_PROGRESS

        if TaskStatus.STARTED in statuses:
            if TaskStatus.COMPLETED in statuses:
                return ProjectStatus.IN_PROGRESS
            return ProjectStatus.STARTED

        if TaskStatus.COMPLETED in statuses:
            return ProjectStatus.STARTED

        return ProjectStatus.NOT_STARTED

    def _task_summary(self, analysis, as_of: date, look_ahead: timedelta):
        overdues = []
        blocked = []
        lates = []
        upcoming_deadlines = []
        upcoming_starts = []

        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            state = self.project.tracker.get_task_state(task_id)
            report = self._task_report(analysis, task_id, state)

            if report.condition is ScheduleCondition.OVERDUE:
                overdues.append(report)
            elif report.condition is ScheduleCondition.BLOCKED:
                blocked.append(report)
            elif report.condition is ScheduleCondition.LATE:
                lates.append(report)

            if as_of <= report.planned_finish <= as_of + look_ahead:
                upcoming_deadlines.append(self._task_report(analysis, task_id, state))
                #print(f"{task} - due {self.project.schedule.finish_dates[task_id]}")
            if as_of <= report.planned_start <= as_of + look_ahead:
                if state.status is TaskStatus.NOT_STARTED:
                    upcoming_starts.append(self._task_report(analysis, task_id, state))
                    #print(f"{task} - Starts {self.project.schedule.start_dates[task_id]}")
        summary = {"overdues": overdues, "blocked": blocked, "lates": lates, 
                   "deadlines": upcoming_deadlines, "starts": upcoming_starts}
        return summary

    def _task_report(self, analysis, task_id, state) -> TaskReport:
        condition = self._schedule_condition(task_id, state, analysis.as_of)

        return TaskReport(
            task_id=task_id,
            name=self.project.tasks[task_id].name,
            state=state,
            condition=condition,
            planned_start=self.project.schedule.start_dates[task_id],
            planned_finish=self.project.schedule.finish_dates[task_id],
            actual_start=self.project.tracker.actual_start(task_id),
            actual_finish=self.project.tracker.actual_finish(task_id),
            start_variance=analysis.start_variance(task_id),
            finish_variance=analysis.finish_variance(task_id),
            duration_variance=analysis.duration_variance(task_id),
        )

    def _schedule_condition(self, task_id, state, as_of) -> ScheduleCondition:
        
        start = self.project.schedule.start_dates[task_id]
        finish = self.project.schedule.finish_dates[task_id]

        if state.status is TaskStatus.COMPLETED:
            return ScheduleCondition.ON_SCHEDULE
        if as_of > finish:
            return ScheduleCondition.OVERDUE
        if as_of > start and state.status is TaskStatus.NOT_STARTED:
            if self._has_incomplete_predecessors(task_id):
                return ScheduleCondition.BLOCKED
            return ScheduleCondition.LATE
        return ScheduleCondition.ON_SCHEDULE






    

