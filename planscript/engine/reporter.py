from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from datetime import date, timedelta

from planscript.model.project import Project
from planscript.engine.tracker import TaskStatus, TaskState, Invoice
from planscript.engine.analyzer import Analyzer
from planscript.exceptions import SchedulingError
from planscript.cli.display import _format_currency

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

class BudgetCondition(Enum):
    """Derived status of a task based on budget."""

    ON_TRACK = "On Track"
    AT_RISK = "At Risk"
    NOT_TRACKED = "Not Tracked"

@dataclass
class ProjectScheduleReport:
    planned_start: date | None
    planned_finish: date | None
    planned_duration: timedelta | None
    actual_start: date | None
    forecast_finish: date | None
    schedule_variance: timedelta | None

    def render_text(self) -> str:
        text = (f"--------------------------------------"
              f"\nSchedule Report\n"
              f"--------------------------------------\n"
              f"    Planned Start: {self.planned_start}\n"
              f"    Planned Finish: {self.planned_finish}\n"
              f"    Actual Start: {self.actual_start}\n"
              f"    Forecast Finish: {self.forecast_finish}\n"
              f"    Forecast Variance: {self.schedule_variance}\n\n")
        return text

@dataclass
class TaskScheduleReport:
    state: TaskState
    schedule_condition: ScheduleCondition
    planned_start: date | None
    planned_finish: date | None
    planned_duration: timedelta | None

    actual_start: date | None
    actual_finish: date| None
    actual_duration: timedelta | None
    duration_variance: timedelta | None

    forecast_start: date | None
    forecast_finish: date | None
    forecast_duration: timedelta | None
    forecast_variance: timedelta | None
    

    def render_text(self) -> str:
        status = self.state.status
        text = (f"--------------------------------------"
              f"\nSchedule Report\n    Status: {self.schedule_condition.value()}" 
              f"--------------------------------------\n"
              f"    Planned Start / Finish: {self.planned_start} / {self.planned_finish}\n"
              f"    Planned Duration: {self.planned_duration}\n")
        if status == TaskStatus.COMPLETED:
            text += (f"    Actual Start / Finish: {self.actual_start} / {self.actual_finish}\n"
                    f"    Actual Duration (Variance): {self.actual_duration} ({self.duration_variance}d)\n")
        elif status in(TaskStatus.IN_PROGRESS, TaskStatus.STARTED):
            text += (f"    Actual Start: {self.actual_start}\n"
                    f"    Forecast Finish: {self.forecast_finish}\n"
                    f"    Forecast Duration (Variance): {self.forecast_duration} ({self.forecast_variance}d)\n")
        if status == TaskStatus.NOT_STARTED:
            text += (f"    Forecast Start (Earliest): {self.forecast_start}\n"
                    f"    Forecast Finish (Earliest): {self.forecast_finish}\n"
                    f"    Forecast Duration (Variance): {self.forecast_duration} ({self.forecast_variance}d)\n")
        return text
    
@dataclass
class ProjectBudgetReport:
    project_budget: Decimal
    project_invoiced: Decimal
    project_remaining: Decimal
    project_variance: Decimal

    def render_text(self) -> str:
        text = (f"--------------------------------------"
              f"\nBudget Report\n"
              f"--------------------------------------\n"
              f"    Planned Budget: {self.project_budget}\n"
              f"    Actual Cost: {self.project_invoiced}\n"
              f"    Remaining Budget: {self.project_remaining}\n"
              f"    Project Cost Variance: {self.project_variance}\n\n")
        return text

@dataclass
class TaskBudgetReport:
    project_budget: Decimal
    project_invoiced: Decimal
    project_remaining: Decimal
    project_variance: Decimal

    def render_text(self) -> str:
        text = (f"--------------------------------------"
              f"\nBudget Report\n"
              f"--------------------------------------\n"
              f"    Planned Budget: {self.project_budget}\n"
              f"    Actual Cost: {self.project_invoiced}\n"
              f"    Remaining Budget: {self.project_remaining}\n"
              f"    Project Cost Variance: {self.project_variance}\n\n")
        return text

@dataclass
class ProjectProgressReport:
    planned_progress: float
    actual_progress: float
    actual_effort: float

    def render_text(self) -> str:
        text = (f"--------------------------------------"
              f"\nProgress Report\n"
              f"--------------------------------------\n"
              f"    Planned Progress: {self.planned_progress:.1%}\n"
              f"    Actual Progress: {self.actual_progress:.1%}\n"
              f"    Budget Consumed: {self.actual_effort:.1%}\n\n")
        return text    

@dataclass
class TaskProgressReport:
    planned_progress: float
    actual_progress: float
    actual_effort: float

    def render_text(self) -> str:
        text = (f"--------------------------------------"
              f"\nProgress Report\n"
              f"--------------------------------------\n"
              f"    Planned Progress: {self.planned_progress:.1%}\n"
              f"    Actual Progress: {self.actual_progress:.1%}\n"
              f"    Budget Consumed: {self.actual_effort:.1%}\n\n")
        return text  

@dataclass
class TaskReport:
    task_id: str
    name: str
    duration: timedelta | None
    state: TaskState
    condition: ScheduleCondition

    schedule_report = _task_schedule_report()
    #days_overdue: timedelta | None = None
    #days_late: timedelta | None = None
    #days_waiting: timedelta | None = None

    #blocked_by: list[str] = field(default_factory=list)
    #root_causes: list[str] = field(default_factory=list)

    def render_text(self, report_type) -> str:
        text = f"{self.task_id} - {self.name} [{self.state.status.value}]\n"
        if report_type == "schedule":
            text += (f"    Planned Start: {self.planned_start}\n"
                    f"    Planned Finish: {self.planned_finish}\n"
                    f"    Planned Duration: {self.duration}\n\n"
                    f"    Actual Start: {self.actual_start}\n"
                    f"    Actual Finish: {self.actual_finish}\n\n"
                    f"  Schedule Condition: {self.condition}\n"
                    f"    Start Variance: {self.start_variance}\n"
                    f"    Finish Variance: {self.finish_variance}\n"
                    f"    Duration Variance: {self.duration_variance}\n\n"
                    )

        if report_type == "budget":
            pass
        if report_type == "progress":
            pass
        return text
    
    def __str__(self):
        return f"{self.task_id} - {self.name} [{self.state.status.value}]"

@dataclass
class ProjectReport:
    
    name: str
    status: ProjectStatus
    as_of: date
    schedule_report: ProjectScheduleReport | None = None
    budget_report: ProjectBudgetReport | None = None
    progress_report: ProjectProgressReport | None = None
    all_tasks: list[TaskReport] | None = None
    #overdue_tasks: list[TaskReport]
    #blocked_tasks: list[TaskReport]
    #late_tasks: list[TaskReport]
    #upcoming_deadlines: list[TaskReport]
    #upcoming_starts: list[TaskReport]
    #charged_tasks: list[TaskReport]
    #look_ahead: timedelta

    def render_text(self):
        text = (f"\nStatus Report as-of {self.as_of}\n"
              f"=======================================\n"
              f"Project Name: {self.name}\n"
              f"    Status: {self.status.value}\n\n")
        text += self.schedule_report.render_text()
        text += self.budget_report.render_text()
        text += self.progress_report.render_text()
        for t_report in self.all_tasks:
            if t_report is None:
                continue
            text += t_report.render_text("schedule")

        """text += f"Overdue Tasks\n"
        for t_report in self.overdue_tasks:
            detail = "" if t_report.days_overdue is None else f" by {t_report.days_overdue.days}d"
            text += (f"    {t_report} is overdue{detail}\n")
        text += "Blocked Tasks\n"
        for t_report in self.blocked_tasks:
            waiting = "" if t_report.days_waiting is None else f" (waiting {t_report.days_waiting.days}d)"
            text += (f"    {t_report} is blocked{waiting}\n")
            for blocker in t_report.blocked_by:
                text += (f"        by {blocker}\n")
            if t_report.root_causes:
                text += (f"        root cause: {', '.join(t_report.root_causes)}\n")
        text += "Late Tasks\n"
        for t_report in self.late_tasks:
            detail = "" if t_report.days_late is None else f" by {t_report.days_late.days}d"
            text += (f"    {t_report} is late{detail}\n")
        text += (f"Upcoming Deadlines (+{self.look_ahead.days}d)\n")
        for t_report in self.upcoming_deadlines:
            text += (f"    {t_report} is due on {t_report.planned_finish}\n")
        text += (f"Upcoming Tasks (+{self.look_ahead.days}d)\n")
        for t_report in self.upcoming_starts:
            text += (f"    {t_report} starts on {t_report.planned_start}\n")
        for t_report in self.charged_tasks:
            text += (f"    {t_report.task_id} - ${t_report.cost_variance}\n")"""
        return text

@dataclass
class ReportBuilder:
    project: Project
    as_of: date = field(default_factory=date.today)
    look_ahead: timedelta = timedelta(days=21)
    

    def build(self) -> ProjectReport:
        if self.project.schedule.start_dates is None:
            raise SchedulingError(
                "No project start date is available for date projection."
            )
        analysis = Analyzer(self.project, self.as_of)
        summary = self._task_summary(analysis, self.as_of, self.look_ahead)


        return ProjectReport(
            name=self.project.name,
            status=self._project_status(),
            as_of=self.as_of,
            schedule_report=self._project_schedule_report(analysis),
            budget_report=self._project_budget_report(analysis),
            progress_report=self._project_progress_budget(analysis),
            all_tasks=summary["all"]
        )
            #blocked_tasks=summary["blocked"],
            #late_tasks=summary["lates"],
            #upcoming_deadlines=summary["deadlines"],
            #upcoming_starts=summary["starts"],
            #charged_tasks=summary["charged"],
            #look_ahead=self.look_ahead


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
        all_tasks = []
        overdues = []
        blocked = []
        lates = []
        upcoming_deadlines = []
        upcoming_starts = []
        charged_tasks = []

        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            state = self.project.tracker.get_task_state(task_id)
            report = self._task_report(analysis, task_id, state, as_of)
            all_tasks.append(report)
            if self.project.budget.get(task_id) is not None:
                charged_tasks.append(report)

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

        summary = {"all": all_tasks, "overdues": overdues, "blocked": blocked, 
                   "lates": lates, "deadlines": upcoming_deadlines, 
                   "starts": upcoming_starts, "charged": charged_tasks}
        return summary

    def _task_report(self, analysis, task_id, state, as_of) -> TaskReport:
        schedule_condition = self._schedule_condition(task_id, state, as_of)
        #budget_condition = self._budget_condition(task_id, state, as_of)

        planned_start = self.project.schedule.start_dates[task_id]
        planned_finish = self.project.schedule.finish_dates[task_id]

        days_overdue = None
        days_late = None
        days_waiting = None
        blocked_by = []
        root_causes = []

        if schedule_condition is ScheduleCondition.OVERDUE:
            days_overdue = as_of - planned_finish
        elif schedule_condition is ScheduleCondition.LATE:
            days_late = as_of - planned_start
        elif schedule_condition is ScheduleCondition.BLOCKED:
            days_waiting = as_of - planned_start
            blocked_by = self._describe_blockers(task_id, as_of)
            root_causes = self._root_causes(task_id, as_of)

        return TaskReport(
            task_id=task_id,
            name=self.project.tasks[task_id].name,
            duration=self.project.tasks[task_id].duration,
            state=state,
            condition=schedule_condition,
            planned_start=planned_start,
            planned_finish=planned_finish,
            actual_start=self.project.tracker.actual_start(task_id),
            actual_finish=self.project.tracker.actual_finish(task_id),
            start_variance=analysis.start_variance(task_id),
            finish_variance=analysis.finish_variance(task_id),
            duration_variance=analysis.duration_variance(task_id),
            cost_variance=analysis.cost_variance(task_id),
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

    def _project_schedule_report(self, analysis:Analyzer) -> ProjectScheduleReport:

        return ProjectScheduleReport(planned_start=self.project.start_date,
                                     planned_finish=self.project.finish_date,
                                     planned_duration=self.project.schedule.duration,
                                     actual_start=analysis.project_actual_start(),
                                     forecast_finish=None,
                                     schedule_variance=None)

    def _project_budget_report(self, analysis:Analyzer) -> ProjectBudgetReport:

        return ProjectBudgetReport(project_budget=_format_currency(self.project.budget.total),
                                    project_invoiced=_format_currency(self.project.tracker.total_actual_cost()),
                                    project_remaining=_format_currency(-analysis.total_cost_variance()),
                                    project_variance=None)

    def _project_progress_budget(self, analysis:Analyzer) -> ProjectProgressReport:

        return ProjectProgressReport(planned_progress=analysis.planned_project_progress(),
                                     actual_progress=analysis.actual_project_progress(),
                                     actual_effort=analysis.project_consumed_cost())

    def _task_schedule_report(self, analysis:Analyzer) -> TaskScheduleReport:

        return TaskScheduleReport(state=
            schedule_condition=
            planned_start=
            planned_finish=
            planned_duration=
        
            actual_start=
            actual_finish=
            actual_duration=
            duration_variance=
        
            forecast_start=
            forecast_finish=
            forecast_duration=
            forecast_variance=)

    def _task_budget_report(self, analysis:Analyzer) -> TaskBudgetReport:

        return TaskBudgetReport(project_budget=_format_currency(self.project.budget.total),
                                    project_invoiced=_format_currency(self.project.tracker.total_actual_cost()),
                                    project_remaining=_format_currency(-analysis.total_cost_variance()),
                                    project_variance=None)

    def _task_progress_budget(self, analysis:Analyzer) -> TaskProgressReport:

        return TaskProgressReport(planned_progress=analysis.planned_project_progress(),
                                     actual_progress=analysis.actual_project_progress(),
                                     actual_effort=analysis.project_consumed_cost())

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







    

