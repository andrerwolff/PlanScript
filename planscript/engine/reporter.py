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
    days_late: timedelta | None = None
    days_waiting: timedelta | None = None

    blocked_by: list[str] = field(default_factory=list)
    root_causes: list[str] = field(default_factory=list)

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
            detail = "" if t_report.days_overdue is None else f" by {t_report.days_overdue.days}d"
            str += (f"    {t_report} is overdue{detail}\n")
        str += "Blocked Tasks\n"
        for t_report in self.blocked_tasks:
            waiting = "" if t_report.days_waiting is None else f" (waiting {t_report.days_waiting.days}d)"
            str += (f"    {t_report} is blocked{waiting}\n")
            for blocker in t_report.blocked_by:
                str += (f"        by {blocker}\n")
            if t_report.root_causes:
                str += (f"        root cause: {', '.join(t_report.root_causes)}\n")
        str += "Late Tasks\n"
        for t_report in self.late_tasks:
            detail = "" if t_report.days_late is None else f" by {t_report.days_late.days}d"
            str += (f"    {t_report} is late{detail}\n")
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
        analysis = Analyzer(self.project, self.as_of)
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

        if not statuses:
            return ProjectStatus.NOT_STARTED

        if statuses <= {TaskStatus.COMPLETED}:
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
            report = self._task_report(analysis, task_id, state, as_of)

            if report.condition is ScheduleCondition.OVERDUE:
                overdues.append(report)
            elif report.condition is ScheduleCondition.BLOCKED:
                blocked.append(report)
            elif report.condition is ScheduleCondition.LATE:
                lates.append(report)

            if report.planned_finish is not None:
                if as_of <= report.planned_finish <= as_of + look_ahead:
                    upcoming_deadlines.append(report)

            if report.planned_start is not None:
                if as_of <= report.planned_start <= as_of + look_ahead:
                    if state.status is TaskStatus.NOT_STARTED:
                        upcoming_starts.append(report)

        summary = {"overdues": overdues, "blocked": blocked, "lates": lates, 
                   "deadlines": upcoming_deadlines, "starts": upcoming_starts}
        return summary

    def _task_report(self, analysis, task_id, state, as_of) -> TaskReport:
        condition = self._schedule_condition(task_id, state, as_of)

        planned_start = self.project.schedule.start_dates[task_id]
        planned_finish = self.project.schedule.finish_dates[task_id]

        days_overdue = None
        days_late = None
        days_waiting = None
        blocked_by = []
        root_causes = []

        if condition is ScheduleCondition.OVERDUE:
            days_overdue = as_of - planned_finish
        elif condition is ScheduleCondition.LATE:
            days_late = as_of - planned_start
        elif condition is ScheduleCondition.BLOCKED:
            days_waiting = as_of - planned_start
            blocked_by = self._describe_blockers(task_id, as_of)
            root_causes = self._root_causes(task_id, as_of)

        return TaskReport(
            task_id=task_id,
            name=self.project.tasks[task_id].name,
            state=state,
            condition=condition,
            planned_start=planned_start,
            planned_finish=planned_finish,
            actual_start=self.project.tracker.actual_start(task_id),
            actual_finish=self.project.tracker.actual_finish(task_id),
            start_variance=analysis.start_variance(task_id),
            finish_variance=analysis.finish_variance(task_id),
            duration_variance=analysis.duration_variance(task_id),
            days_overdue=days_overdue,
            days_late=days_late,
            days_waiting=days_waiting,
            blocked_by=blocked_by,
            root_causes=root_causes,
        )

    def _schedule_condition(self, task_id, state, as_of) -> ScheduleCondition:
        """
        Classify a task's current schedule condition.

        An unstarted task takes precedence over an overdue finish:
        - Blocked: planned start has passed and a predecessor is incomplete.
        - Late: planned start has passed but all predecessors are complete.
        - Overdue: task has started but planned finish has passed.

        This prioritizes identifying work that has not started over identifying
        work that has missed its finish date.
        """
        
        start = self.project.schedule.start_dates[task_id]
        finish = self.project.schedule.finish_dates[task_id]

        if state.status is TaskStatus.COMPLETED:
            return ScheduleCondition.ON_SCHEDULE
        
        if as_of > start and state.status is TaskStatus.NOT_STARTED:
            if self._has_incomplete_predecessors(task_id):
                return ScheduleCondition.BLOCKED
            return ScheduleCondition.LATE
        
        if as_of > finish:
            return ScheduleCondition.OVERDUE
        
        return ScheduleCondition.ON_SCHEDULE        


    def _has_incomplete_predecessors(self, task_id):
        return bool(self._incomplete_predecessors(task_id))

    def _incomplete_predecessors(self, task_id):
        """Return the task's predecessor Tasks that are not yet completed."""

        task = self.project.tasks[task_id]
        incomplete = []
        for predecessor in self.project.get_predecessors(task):
            state = self.project.tracker.get_task_state(predecessor.number)
            if state.status is not TaskStatus.COMPLETED:
                incomplete.append(predecessor)
        return incomplete

    def _describe_blockers(self, task_id, as_of):
        """Describe the incomplete predecessors that are holding up a blocked task."""

        descriptions = []
        for predecessor in self._incomplete_predecessors(task_id):
            state = self.project.tracker.get_task_state(predecessor.number)
            due = self.project.schedule.finish_dates[predecessor.number]

            description = f"{predecessor.number} - {predecessor.name} [{state.status.value}] (due {due}"
            if as_of > due:
                description += f", {(as_of - due).days}d overdue"
            descriptions.append(description + ")")
        return descriptions

    def _root_causes(self, task_id, as_of):
        """Resolve a blocked task's dependency chain to its terminal blockers.

        A terminal blocker has no incomplete predecessor of its own, so it is
        the task that must actually be actioned: overdue work that has slipped,
        or late work that was never started.
        """

        roots = {}
        visited = set()
        pending = self._incomplete_predecessors(task_id)

        while pending:
            predecessor = pending.pop()
            if predecessor.number in visited:
                continue
            visited.add(predecessor.number)

            blockers = self._incomplete_predecessors(predecessor.number)
            if blockers:
                pending.extend(blockers)
            else:
                state = self.project.tracker.get_task_state(predecessor.number)
                condition = self._schedule_condition(predecessor.number, state, as_of)
                roots[predecessor.number] = f"{predecessor.number} [{condition.value}]"

        return sorted(roots.values())







    

