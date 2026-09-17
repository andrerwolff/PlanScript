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

@dataclass
class TaskReport:
    task_id: str
    name: str
    state: TaskState

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
        overdue_tasks, upcoming_deadlines, upcoming_starts = self._task_summary(analysis, self.as_of, self.look_ahead)


        return ProjectReport(
            name = self.project.name,
            status = self._project_status(),
            as_of=self.as_of,
            planned_start = self.project.start_date,
            planned_finish = self.project.finish_date,
            planned_duration = self.project.schedule.duration,
            actual_start = analysis.project_actual_start(),
            progress = analysis.project_progress(),
            overdue_tasks = overdue_tasks,
            upcoming_deadlines = upcoming_deadlines,
            upcoming_starts= upcoming_starts,
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
        upcoming_deadlines = []
        upcoming_starts = []

        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            state = self.project.tracker.get_task_state(task_id)

            if state.status is TaskStatus.COMPLETED:
                continue

            finish = self.project.schedule.finish_dates[task_id]
            start = self.project.schedule.start_dates[task_id]

            if as_of > finish:
                overdues.append(self._task_report(analysis, task_id, state))
                #print(f"{task} - {(date.today() - self.project.schedule.finish_dates[task_id]).days} days overdue")
            if as_of <= finish <= as_of + look_ahead:
                upcoming_deadlines.append(self._task_report(analysis, task_id, state))
                #print(f"{task} - due {self.project.schedule.finish_dates[task_id]}")
            if as_of <= start <= as_of + look_ahead:
                if state.status is TaskStatus.NOT_STARTED:
                    upcoming_starts.append(self._task_report(analysis, task_id, state))
                    #print(f"{task} - Starts {self.project.schedule.start_dates[task_id]}")
        return overdues, upcoming_deadlines, upcoming_starts

    def _task_report(self, analysis, task_id, state) -> TaskReport:

        return TaskReport(
            task_id = task_id,
            name = self.project.tasks[task_id].name,
            state = state,
            planned_start = self.project.schedule.start_dates[task_id],
            planned_finish = self.project.schedule.finish_dates[task_id],
            actual_start= self.project.tracker.actual_start(task_id),
            actual_finish= self.project.tracker.actual_finish(task_id),
            start_variance = analysis.start_variance(task_id),
            finish_variance = analysis.finish_variance(task_id),
            duration_variance = analysis.duration_variance(task_id),
        )






    

