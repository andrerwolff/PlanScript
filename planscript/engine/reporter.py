"""Status reporting for PlanScript projects.

ReportBuilder composes the derived models into a ProjectReport and renders it
for the console. Every reported figure has exactly one source:

    planned dates and durations  ->  project.Schedule and task.duration
    actual dates and durations   ->  project.Tracker, at the report's as_of date
    variances and progress       ->  Analyzer, at the report's as_of date
    forecasts                    ->  Forecaster, at the report's as_of date
    money                        ->  Budget for planned amounts, and Tracker
                                     invoice allocations for actuals

The report's as_of date is the single data date for the whole report. A value
that cannot be derived from that data is reported as n/a rather than as a zero,
and tracking entries dated after the data date are listed as data notices so a
truncated figure is explained instead of silently dropped.

Reports are derived information and do not modify the project, schedule,
budget, or tracking history.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional

from planscript.engine.analyzer import Analyzer
from planscript.engine.forecaster import Forecaster
from planscript.exceptions import SchedulingError
from planscript.model.project import Project
from planscript.model.schedule import Schedule
from planscript.model.tracker import TaskStatus, TaskState

CURRENCY = Decimal("0.01")
NOT_AVAILABLE = "n/a"


def _whole_days(value: timedelta) -> float:
    """Return a timedelta as a number of days, including a fraction of a day."""

    return value.total_seconds() / 86400

def _format_money(amount: Decimal | None) -> str:
    """Format an amount of money, keeping zero distinct from unknown.

    A negative amount is shown in accounting parentheses. An unknown amount is
    reported as n/a, so an unmeasured value is never read as zero.
    """

    if amount is None:
        return NOT_AVAILABLE

    amount = amount.quantize(CURRENCY, rounding=ROUND_HALF_UP)
    if amount < 0:
        return f"(${abs(amount):,})"
    return f"${amount:,}"

def _format_percent(value: float | None) -> str:
    """Format a 0..1 fraction, keeping zero distinct from unknown."""

    if value is None:
        return NOT_AVAILABLE
    return f"{value:.1%}"

def _format_days(value: timedelta | None) -> str:
    """Format a variance as signed whole days, such as '+5d', '-4d', or '0d'."""

    if value is None:
        return NOT_AVAILABLE

    days = _whole_days(value)
    if days == 0:
        return "0d"
    if days == int(days):
        return f"{int(days):+d}d"
    return f"{days:+g}d"

def _format_duration(value: timedelta | None) -> str:
    """Format a duration in days, such as '5d' or '1.5d'."""

    if value is None:
        return NOT_AVAILABLE

    days = _whole_days(value)
    if days == int(days):
        return f"{int(days)}d"
    return f"{days:g}d"

def _format_date(value: date | None) -> str:
    """Format a date, keeping an unknown date distinct from any real date."""

    if value is None:
        return NOT_AVAILABLE
    return f"{value}"


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
              f"\nProject Schedule Report\n"
              f"--------------------------------------\n"
              f"    Planned Start: {_format_date(self.planned_start)}\n"
              f"    Planned Finish: {_format_date(self.planned_finish)}\n"
              f"    Planned Duration: {_format_duration(self.planned_duration)}\n"
              f"    Actual Start: {_format_date(self.actual_start)}\n"
              f"    Forecast Finish: {_format_date(self.forecast_finish)}\n"
              f"    Schedule Variance: {_format_days(self.schedule_variance)}\n")
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
    finish_variance: timedelta | None

    forecast_start: date | None
    forecast_finish: date | None
    forecast_duration: timedelta | None
    forecast_variance: timedelta | None
    

    def is_milestone(self) -> bool:
        """Return True when the task has no planned duration."""

        return self.planned_duration == timedelta(0)

    def render_text(self) -> str:
        """Render the planned, actual, and (once available) forecast schedule.

        Only values the report could derive are printed: an unfinished task
        shows the duration elapsed so far, and milestones report no duration
        rather than an inclusive one-day span.
        """

        text = (f"--------------------------------------"
              f"\nSchedule Report    Status: {self.schedule_condition.value}\n"
              f"--------------------------------------\n")

        if self.is_milestone():
            text += f"    Planned Milestone Date: {_format_date(self.planned_finish)}\n"
            if self.actual_start is not None:
                text += (f"    Actual Milestone Date: {_format_date(self.actual_start)}\n"
                         f"    Schedule Variance: {_format_days(self.finish_variance)}\n")
            return text + f"\n"

        
        text += f"    Planned Start / Finish / Duration: {_format_date(self.planned_start)} / {_format_date(self.planned_finish)} / {_format_duration(self.planned_duration)}\n"
        
        if self.actual_start is not None:
            #Completed
            if self.actual_finish is not None:
                text += (f"    Actual Start / Finish / Duration: {_format_date(self.actual_start)} / {_format_date(self.actual_finish)} / {_format_duration(self.actual_duration)}\n"
                         f"    Schedule Variance: {_format_days(self.finish_variance)}\n")
                return text + f"\n"
            #Started / In Progress
            text += (f"    Actual Start / Time Elapsed: {_format_date(self.actual_start)} / {_format_duration(self.actual_duration)}\n"
                     f"    Forecasted Finish / Duration: {_format_date(self.forecast_finish)} / {_format_duration(self.forecast_duration)}\n"
                     f"    Forecasted Schedule Variance: {_format_days(self.forecast_variance)}\n")
            return text + f"\n"

        else:
            #Not Started
            text += (f"    Forecasted Start / Finish / Duration: {_format_date(self.forecast_start)} / {_format_date(self.forecast_finish)} / {_format_duration(self.forecast_duration)}\n"
                     f"    Forecasted Schedule Variance: {_format_days(self.forecast_variance)}\n")
            return text + f"\n"
    
@dataclass
class ProjectBudgetReport:
    """Planned and actual project money to the report's data date.

    Only the planned and actual amounts are stored. Remaining and variance are
    derived from them, so the two can never disagree with each other.
    """

    project_budget: Decimal | None
    project_actual: Decimal | None

    @property
    def project_remaining(self) -> Decimal | None:
        """Return budget minus actual, where a positive value is under budget."""

        if self.project_budget is None or self.project_actual is None:
            return None
        return self.project_budget - self.project_actual

    @property
    def project_variance(self) -> Decimal | None:
        """Return actual minus budget, where a positive value is over budget."""

        if self.project_budget is None or self.project_actual is None:
            return None
        return self.project_actual - self.project_budget

    def render_text(self) -> str:
        text = (f"--------------------------------------"
              f"\nProject Budget Report\n"
              f"--------------------------------------\n"
              f"    Planned Budget: {_format_money(self.project_budget)}\n"
              f"    Actual Cost: {_format_money(self.project_actual)}\n"
              f"    Remaining Budget: {_format_money(self.project_remaining)}\n"
              f"    Cost Variance (actual - budget): {_format_money(self.project_variance)}\n")
        return text

@dataclass
class TaskBudgetReport:
    """Planned and actual money for one task to the report's data date."""

    task_budget: Decimal | None
    task_actual: Decimal | None

    @property
    def task_remaining(self) -> Decimal | None:
        """Return budget minus actual, or None when the task has no budget."""

        if self.task_budget is None or self.task_actual is None:
            return None
        return self.task_budget - self.task_actual

    @property
    def cost_variance(self) -> Decimal | None:
        """Return actual minus budget, or None when the task has no budget."""

        if self.task_budget is None or self.task_actual is None:
            return None
        return self.task_actual - self.task_budget

    def render_text(self) -> str:
        text = (f"--------------------------------------"
              f"\nBudget Report\n"
              f"--------------------------------------\n"
              f"    Planned Budget: {_format_money(self.task_budget)}\n"
              f"    Actual Cost: {_format_money(self.task_actual)}\n"
              f"    Remaining Budget: {_format_money(self.task_remaining)}\n\n")
        return text

@dataclass
class ProgressReport:
    """Planned, actual, and consumed progress, as 0..1 fractions.

    Values are None when they cannot be derived from the report's data.
    """

    planned_progress: float | None
    actual_progress: float | None
    budget_consumed: float | None

    heading = "Progress Report"

    def render_text(self) -> str:
        text = (f"--------------------------------------"
              f"\n{self.heading}\n"
              f"--------------------------------------\n"
              f"    Planned Progress: {_format_percent(self.planned_progress)}\n"
              f"    Actual Progress: {_format_percent(self.actual_progress)}\n"
              f"    Budget Consumed: {_format_percent(self.budget_consumed)}\n")
        return text

@dataclass
class ProjectProgressReport(ProgressReport):
    """Project-level progress."""

    heading = "Project Progress Report"

@dataclass
class TaskProgressReport(ProgressReport):
    """Task-level progress."""

@dataclass
class TaskReport:
    """Everything the report derived for one task at its data date."""

    task_id: str
    name: str

    schedule_report: TaskScheduleReport
    budget_report: TaskBudgetReport
    progress_report: TaskProgressReport

    #days_overdue: timedelta | None = None
    #days_late: timedelta | None = None
    #days_waiting: timedelta | None = None

    #blocked_by: list[str] = field(default_factory=list)
    #root_causes: list[str] = field(default_factory=list)

    def render_text(self, report_type) -> str:
        text = f"{self.task_id} - {self.name}\n"
        if "schedule" in report_type:
            text += self.schedule_report.render_text()

        if "budget" in report_type:
            text += self.budget_report.render_text()
        if "progress" in report_type:
            text += self.progress_report.render_text()
        return text
    
    def __str__(self):
        return f"{self.task_id} - {self.name}"

@dataclass
class ProjectReport:
    """The rendered status report for a project at its data date."""

    name: str
    status: ProjectStatus
    as_of: date
    schedule_report: ProjectScheduleReport | None = None
    budget_report: ProjectBudgetReport | None = None
    progress_report: ProjectProgressReport | None = None
    all_tasks: list[TaskReport] | None = None
    data_notices: list[str] = field(default_factory=list)
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
              f"    Status: {self.status.value}\n")

        if self.data_notices:
            text += "\nData Notices\n"
            for notice in self.data_notices:
                text += f"    {notice}\n"

        text += "\n"
        text += self.schedule_report.render_text()
        text += self.budget_report.render_text()
        text += self.progress_report.render_text()
        for t_report in self.all_tasks:
            if t_report is None:
                continue
            text += t_report.render_text(("schedule", "budget", "progress"))


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

# NEW IMPLEMENTATIONS _________________________________________________________________________________________________



@dataclass
class TaskView:
    """Derived data for one task at a report's data date.

    TaskView is plain data with no rendering logic. Renderers consume
    TaskView instances to produce console tables, text blocks, or other
    output formats.

    Attributes:
        task_id: The task's PlanScript identifier.
        name: The task's human-readable name.
        depth: the hierarchy level of the task.
        is_summary: True when the task has child tasks.
        is_milestone: True when the task has zero planned duration.
        schedule_condition: The task's derived schedule condition.
        total_float: The task's total float from CPM, or None.
        planned_start: The task's planned start date.
        planned_finish: The task's planned finish date.
        planned_duration: The task's planned duration.
        actual_start: The task's actual start date, or None.
        actual_finish: The task's actual finish date, or None.
        actual_duration: The task's actual duration, or None.
        forecast_start: The task's forecast start date, or None.
        forecast_finish: The task's forecast finish date, or None.
        forecast_duration: The task's forecast remaining duration, or None.
        finish_variance: Actual finish minus planned finish, or None.
        forecast_variance: Forecast finish minus planned finish, or None.
        task_budget: The task's planned budget, or None.
        task_actual: The task's actual cost to as_of, or None.
        task_remaining: Budget minus actual, or None.
        cost_variance: Actual minus budget, or None.
        planned_progress: Planned progress as a 0..1 fraction, or None.
        actual_progress: Actual progress as a 0..1 fraction, or None.
        budget_consumed: Share of budget spent, or None.
        days_overdue: Days past planned finish, or None.
        days_late: Days past planned start, or None.
        days_waiting: Days waiting on predecessors, or None.
        blocked_by: Descriptions of incomplete predecessors.
        root_causes: Terminal blockers resolved from the dependency chain.
    """

    task_id: str
    name: str
    depth: int =0
    is_summary: bool = False
    is_milestone: bool = False

    schedule_condition: ScheduleCondition = ScheduleCondition.ON_SCHEDULE
    total_float: timedelta | None = None

    planned_start: date | None = None
    planned_finish: date | None = None
    planned_duration: timedelta | None = None

    actual_start: date | None = None
    actual_finish: date | None = None
    actual_duration: timedelta | None = None

    forecast_start: date | None = None
    forecast_finish: date | None = None
    forecast_duration: timedelta | None = None

    finish_variance: timedelta | None = None
    forecast_variance: timedelta | None = None

    task_budget: Decimal | None = None
    task_actual: Decimal | None = None
    task_remaining: Decimal | None = None
    cost_variance: Decimal | None = None

    planned_progress: float | None = None
    actual_progress: float | None = None
    budget_consumed: float | None = None

    days_overdue: timedelta | None = None
    days_late: timedelta | None = None
    days_waiting: timedelta | None = None
    blocked_by: list[str] = field(default_factory=list)
    root_causes: list[str] = field(default_factory=list)

@dataclass
class TaskBuilder:
    """Build TaskView objects from a project's derived data.

    Leaf tasks are populated from Schedule, Tracker, Analyzer, and
    Forecaster. Summary tasks are rolled up from their leaf descendants.

    This class does not filter, render, or modify project data.
    """

    project: Project
    analysis: Analyzer
    forecast: Schedule
    as_of: date

    def build (self) -> list[TaskView]:
        """Build all task views in hierarchy display order."""
        hierarchy = self.project.schedule.hierarchy
        views_by_id: dict[str, TaskView] = {}

        # Build leaves before parents so summary tasks can roll up their already-built descendants.
        for task_id in hierarchy.get_bottom_up_order():
            if hierarchy.is_summary(task_id):
                view = self._build_summary_view(task_id, views_by_id)
            else:
                view = self._build_leaf_view(task_id)

            views_by_id[task_id] = view

        # Return the views in parent-before-child display order.
        views = []
        for task_id in hierarchy.get_top_down_order():
            views.append(views_by_id[task_id])
        return views

    def _build_leaf_view(self, task_id: str) -> TaskView:
        """Build a TaskView directly from the derived data sources."""

        task = self.project.tasks[task_id]
        schedule = self.project.schedule
        tracker = self.project.tracker
        budget = self.project.budget

        state = tracker.get_task_state(task_id, self.as_of)
        condition = self._schedule_condition(task_id, state)

        planned_start = schedule.start_dates[task_id]
        planned_finish = schedule.finish_dates[task_id]
        forecast_finish = self.forecast.finish_dates[task_id]

        # CPM durations are offsets. Calendar dates are inclusive, so
        # use the CPM values rather than subtracting the displayed dates.
        forecast_duration = (self.forecast.early_finish[task_id] 
                             - self.forecast.early_start[task_id])

        task_budget = budget.get(task_id)
        task_actual = tracker.actual_cost(task_id, self.as_of)

        task_remaining = None
        cost_variance = None
        if task_budget is not None and task_actual is not None:
            task_remaining = task_budget - task_actual
            cost_variance = task_actual - task_budget

        days_overdue = None
        days_late = None
        days_waiting = None
        blocked_by = []
        root_causes = []

        if condition is ScheduleCondition.OVERDUE:
            days_overdue = self.as_of - planned_finish

        elif condition is ScheduleCondition.LATE:
            days_late = self.as_of - planned_start

        elif condition is ScheduleCondition.BLOCKED:
            days_waiting = self.as_of - planned_start
            blocked_by = self._describe_blockers(task_id)
            root_causes = self._root_causes(task_id)

        return TaskView(
            task_id=task_id,
            name=task.name,
            depth=len(schedule.hierarchy.get_ancestors(task_id)),
            is_summary=False,
            is_milestone=(task.duration == timedelta(0)),

            schedule_condition=condition,
            total_float=schedule.total_float.get(task_id),

            planned_start=planned_start,
            planned_finish=planned_finish,
            planned_duration=task.duration,

            actual_start=tracker.actual_start(task_id, self.as_of),
            actual_finish=tracker.actual_finish(task_id, self.as_of),
            actual_duration=tracker.actual_duration(task_id, self.as_of),

            forecast_start=self.forecast.start_dates[task_id],
            forecast_finish=forecast_finish,
            forecast_duration=forecast_duration,

            finish_variance=self.analysis.finish_variance(task_id),
            forecast_variance=forecast_finish - planned_finish,

            task_budget=budget.get(task_id),
            task_actual=task_actual,
            task_remaining=task_remaining,
            cost_variance=cost_variance,

            planned_progress=self.analysis.planned_progress(task_id),
            actual_progress=self.analysis.actual_progress(task_id),
            budget_consumed=self._task_budget_consumed(task_id),

            days_overdue=days_overdue,
            days_late=days_late,
            days_waiting=days_waiting,
            blocked_by=blocked_by,
            root_causes=root_causes,
        )

    def _build_summary_view( self, task_id: str, views_by_id: dict[str, TaskView]) -> TaskView:
        """Build a summary TaskView by rolling up its leaf descendants."""

        hierarchy = self.project.schedule.hierarchy
        task = self.project.tasks[task_id]

        leaf_ids = hierarchy.get_leaves(task_id)
        leaves = [views_by_id[leaf_id] for leaf_id in leaf_ids]

        if not leaves:
            raise ValueError(f"Summary task '{task_id}' has no leaf descendants.")

        planned_starts = []
        planned_finishes = []
        actual_starts = []
        actual_finishes = []
        forecast_starts = []
        forecast_finishes = []
        task_budgets = []
        task_actuals = []
        overdues = []
        lates = []
        waitings = []
        for view in leaves:
            planned_starts.append(view.planned_start)
            planned_finishes.append(view.planned_finish)
            actual_starts.append(view.actual_start)
            forecast_starts.append(view.forecast_start)
            forecast_finishes.append(view.forecast_finish)
            task_budgets.append(view.task_budget)
            task_actuals.append(view.task_actual)
            overdues.append(view.days_overdue)
            lates.append(view.days_late)
            waitings.append(view.days_waiting)

        planned_start = self._earliest(planned_starts)
        planned_finish = self._latest(planned_finishes)
        actual_start = self._earliest(actual_starts)
        forecast_start = self._earliest(forecast_starts)
        forecast_finish = self._latest(forecast_finishes)
        task_budget = self._sum_known(task_budgets)
        task_actual = self._sum_known(task_actuals)
        days_overdue = self._latest(overdues)
        days_late = self._latest(lates)
        days_waiting = self._latest(waitings)

        all_completed = True
        for view in leaves:
            if view.actual_finish is None:
                all_completed = False
                break
            else:
                continue

        if all_completed:
            for view in leaves:
                actual_finishes.append(view.actual_finish)
            actual_finish = self.latest(actual_finishes)
        else:
            actual_finish = None

        actual_duration = None
        if actual_start is not None:
            if all_completed:
                actual_end = actual_finish
            else:
                actual_end = self.as_of
            actual_duration = actual_end - actual_start


        planned_duration = self._date_span(planned_start, planned_finish)
        forecast_duration = self._date_span(forecast_start, forecast_finish)

        task_remaining = None
        cost_variance = None
        if task_budget is not None and task_actual is not None:
            task_remaining = task_budget - task_actual
            cost_variance = task_actual - task_budget

        budget_consumed = None
        if task_budget is not None and task_budget != 0:
            budget_consumed = float(task_actual / task_budget)

        planned_progress = self._weighted_progress(leaves, "planned_progress")
        actual_progress = self._weighted_progress(leaves, "actual_progress")

        condition = self._summary_schedule_condition(leaves)

        finish_variance = None
        if actual_finish is not None and planned_finish is not None:
            finish_variance = actual_finish - planned_finish

        forecast_variance = None
        if forecast_finish is not None and planned_finish is not None:
            forecast_variance = forecast_finish - planned_finish

        blocked_by = sorted({
            blocker
            for view in leaves
            for blocker in view.blocked_by
        })
        root_causes = sorted({
            cause
            for view in leaves
            for cause in view.root_causes
        })

        return TaskView(
            task_id=task_id,
            name=task.name,
            depth=len(hierarchy.get_ancestors(task_id)),
            is_summary=True,
            is_milestone=False,

            schedule_condition=condition,
            total_float=None,

            planned_start=planned_start,
            planned_finish=planned_finish,
            planned_duration=planned_duration,

            actual_start=actual_start,
            actual_finish=actual_finish,
            actual_duration=actual_duration,

            forecast_start=forecast_start,
            forecast_finish=forecast_finish,
            forecast_duration=forecast_duration,

            finish_variance=finish_variance,
            forecast_variance=forecast_variance,

            task_budget=task_budget,
            task_actual=task_actual,
            task_remaining=task_remaining,
            cost_variance=cost_variance,

            planned_progress=planned_progress,
            actual_progress=actual_progress,
            budget_consumed=budget_consumed,

            days_overdue=days_overdue,
            days_late=days_late,
            days_waiting=days_waiting,
            blocked_by=blocked_by,
            root_causes=root_causes,
        )

    def _schedule_condition(self, task_id: str, state: TaskState) -> ScheduleCondition:
        """Classify a leaf task's schedule condition."""

        start = self.project.schedule.start_dates[task_id]
        finish = self.project.schedule.finish_dates[task_id]

        if state.status is TaskStatus.COMPLETED:
            return ScheduleCondition.ON_SCHEDULE

        if self.as_of > start and state.status is TaskStatus.NOT_STARTED:
            if self._has_incomplete_predecessors(task_id):
                return ScheduleCondition.BLOCKED
            return ScheduleCondition.LATE

        if self.as_of > finish:
            return ScheduleCondition.OVERDUE

        return ScheduleCondition.ON_SCHEDULE

    def _summary_schedule_condition(
        self,
        leaves: list[TaskView],
    ) -> ScheduleCondition:
        """Classify a summary based on its unfinished leaf descendants.

        Priority:
        1. Overdue if any unfinished descendant is overdue.
        2. Late if any unfinished descendant is late.
        3. Blocked if every unfinished descendant is blocked.
        4. Otherwise on schedule.
        """
        unfinished = []
        for view in leaves:
            if view.actual_finish is None:
                unfinished.append(view)

        if not unfinished:
            return ScheduleCondition.ON_SCHEDULE

        conditions = set()
        for view in unfinished:
            conditions.add(view.schedule_condition)

        if ScheduleCondition.OVERDUE in conditions:
            return ScheduleCondition.OVERDUE

        if ScheduleCondition.LATE in conditions:
            return ScheduleCondition.LATE

        if conditions == {ScheduleCondition.BLOCKED}:
            return ScheduleCondition.BLOCKED

        return ScheduleCondition.ON_SCHEDULE

    def _has_incomplete_predecessors(self, task_id: str) -> bool:
        return bool(self._incomplete_predecessors(task_id))

    def _incomplete_predecessors(self, task_id: str):
        """Return predecessors not complete at the report data date."""

        task = self.project.tasks[task_id]
        incomplete = []

        for predecessor in self.project.get_predecessors(task):
            state = self.project.tracker.get_task_state(predecessor.number, self.as_of)
            if state.status is not TaskStatus.COMPLETED:
                incomplete.append(predecessor)

        return incomplete

    def _describe_blockers(self, task_id: str) -> list[str]:
        """Describe incomplete predecessors of a blocked task."""

        descriptions = []

        for predecessor in self._incomplete_predecessors(task_id):
            state = self.project.tracker.get_task_state(predecessor.number, self.as_of)
            due = self.project.schedule.finish_dates[predecessor.number]

            description = (
                f"{predecessor.number} - {predecessor.name} "
                f"[{state.status.value}] (due {due}"
            )

            if self.as_of > due:
                description += f", {(self.as_of - due).days}d overdue"

            descriptions.append(description + ")")

        return descriptions

    def _root_causes(self, task_id: str) -> list[str]:
        """Resolve a blocked task's dependency chain to terminal blockers."""

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
                state = self.project.tracker.get_task_state(predecessor.number, self.as_of)
                condition = self._schedule_condition(predecessor.number, state)
                roots[predecessor.number] = (f"{predecessor.number} [{condition.value}]")

        return sorted(roots.values())

    def _task_budget_consumed(self, task_id: str) -> float | None:
        """Return actual cost divided by planned budget."""

        budget = self.project.budget.get(task_id)

        if budget is None or budget == 0:
            return None

        actual = self.project.tracker.actual_cost(task_id, self.as_of)

        if actual is None:
            return None

        return float(actual / budget)

    @staticmethod
    def _earliest(values):
        known = [value for value in values if value is not None]
        return min(known) if known else None

    @staticmethod
    def _latest(values):
        known = [value for value in values if value is not None]
        return max(known) if known else None

    @staticmethod
    def _date_span(start: date | None, finish: date | None) -> timedelta | None:
        if start is None or finish is None:
            return None
        return finish - start

    @staticmethod
    def _sum_known(values) -> Decimal | None:
        known = [value for value in values if value is not None]
        if not known:
            return None
        return sum(known, Decimal("0"))

    @staticmethod
    def _weighted_progress(leaves: list[TaskView], attribute: str) -> float | None:
        """Calculate progress weighted by planned task duration."""

        weighted_total = 0.0
        total_weight = 0.0

        for view in leaves:
            progress = getattr(view, attribute)
            duration = view.planned_duration

            if progress is None or duration is None:
                continue

            weight = duration.total_seconds()
            if weight <= 0:
                continue

            weighted_total += progress * weight
            total_weight += weight

        if total_weight == 0:
            return None

        return weighted_total / total_weight

@dataclass
class ReportSpec:
    """Specification for what a report should contain.

    A ReportSpec defines the axes of a report independent of how it is
    rendered. Templates are preset ReportSpec instances so a user does
    not need to assemble filters manually.

    Attributes:
        basis: Which derived data to compute. 
            "schedule" computes CPM schedule figures only. 
            "finance" computes budget and actual cost figures only.
            "both" computes schedule, budget, and progress figures. 
            #TODO investigate progress for both
        scope: Level of granularity. 
            "project" rolls up to project-level figures only.
            "task" lists every task. 
            "summary" groups tasks under their summary parents.
        filter: Which tasks to include. 
            "all" includes every task.
            "critical" includes only tasks on the critical path.
            "behind" includes tasks that are late or overdue.
            "overdue" includes tasks that have passed their planned finish. 
            "blocked" includes tasks waiting on incomplete predecessors.
            "late" includes unstarted tasks whose planned start has passed.
            "upcoming" includes tasks starting or finishing within look_ahead.
            "ready_to_start" includes unstarted tasks whose predecessors are complete.
        renderer: Output format. 
            "detail" renders each task as a block of text.
            "table" renders tasks as rows in a compact table.
        as_of: The data date for the report. 
            Defaults to today.
        look_ahead: Number of days to look ahead for upcoming tasks.
            Defaults to 21 days.
    """

    basis: str = "both"
    scope: str = "task"
    filter: str = "all"
    renderer: str = "detail"
    as_of: date = field(default_factory=date.today)
    look_ahead: timedelta = timedelta(days=21)

@dataclass
class ReportBuilder:
    """Build a ProjectReport at a single data date.

    The builder is the only place that decides where a reported figure comes
    from, so every value in the report is derived from the same as_of date.
    """

    project: Project
    spec: ReportSpec
    #as_of: date = field(default_factory=date.today)
    #look_ahead: timedelta = timedelta(days=21)

    def _data_notices(self) -> list[str]:
        """Describe tracking data the report's data date excluded.

        A truncated figure is explained rather than silently dropped: entries
        dated after as_of are summarised per task, with the count and the latest
        date so the reader knows recorded work is missing from the report.
        Tracker.future_dated_events() returns the entries themselves.
        """

        by_task = {}
        for event in self.project.tracker.future_dated_events(self.spec.as_of):
            by_task.setdefault(event.task_id, []).append(event)

        notices = []
        for task_id in sorted(by_task):
            events = by_task[task_id]
            noun = "entry" if len(events) == 1 else "entries"
            latest = max(event.date for event in events)
            notices.append(
                f"{task_id}: {len(events)} tracking {noun} after this report's "
                f"as-of date ({self.spec.as_of}), latest {latest}; not included.")
        return notices

    def build_view(self) -> "ReportView":
        """Build a ReportView from the same derivation logic as build().

        This is the entry point for the modular reporting framework. It
        delegates to TaskBuilder for task-level data and to the existing
        helper methods for project-level figures, so the report model
        stays consistent while callers use the filtered TaskView list.

        Returns:
            A ReportView containing filtered task views, project figures,
            and data notices for the report's data date.
        """
        analysis = Analyzer(self.project, self.spec.as_of)
        forecast = Forecaster().forecast(project=self.project, as_of=self.spec.as_of)
        task_builder = TaskBuilder(project=self.project, analysis=analysis, forecast=forecast, as_of=self.spec.as_of)

        # Task-level data
        task_views = task_builder.build()
        filtered_views = TaskFilter.apply(task_views, self.spec)

        # Project-level figures
        schedule_report = self._project_schedule_report(analysis, forecast)
        budget_report = self._project_budget_report(analysis)
        progress_report = self._project_progress_report(analysis)

        # Project status and data notices
        status = self._project_status()
        data_notices = self._data_notices()

        return ReportView(
            name=self.project.name,
            status=status,
            spec=self.spec,
            #as_of=self.spec.as_of,
            #look_ahead=self.spec.look_ahead,
            schedule_report=schedule_report,
            budget_report=budget_report,
            progress_report=progress_report,
            task_views=filtered_views,
            data_notices=data_notices,
        )


    def _project_status(self) -> ProjectStatus:
        """Return the project's derived status at the report's data date.

        Status is aggregated from leaf-task states:
        - Not Started: no leaf task has begun.
        - Started: work has begun, but nothing is finished or progressing.
        - In Progress: work is in flight, or some work is finished while other
          work has not begun.
        - Completed: every leaf task is complete.
        """

        statuses = set()
        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            state = self.project.tracker.get_task_state(task_id, self.spec.as_of)
            statuses.add(state.status)

        if not statuses:
            return ProjectStatus.NOT_STARTED

        if statuses <= {TaskStatus.COMPLETED}:
            return ProjectStatus.COMPLETED

        if statuses <= {TaskStatus.NOT_STARTED}:
            return ProjectStatus.NOT_STARTED

        if statuses <= {TaskStatus.NOT_STARTED, TaskStatus.STARTED}:
            return ProjectStatus.STARTED

        return ProjectStatus.IN_PROGRESS

    def _task_summary(self, analysis, forecast:Schedule, as_of: date, look_ahead: timedelta):
        all_tasks = []
        overdues = []
        blocked = []
        lates = []
        upcoming_deadlines = []
        upcoming_starts = []
        charged_tasks = []

        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            state = self.project.tracker.get_task_state(task_id, as_of)
            task_report = self._task_report(analysis, forecast, task_id, state, as_of)
            schedule_report = task_report.schedule_report

            all_tasks.append(task_report)
            if self.project.budget.get(task_id) is not None:
                charged_tasks.append(task_report)

            if schedule_report.schedule_condition is ScheduleCondition.OVERDUE:
                overdues.append(task_report)
            elif schedule_report.schedule_condition is ScheduleCondition.BLOCKED:
                blocked.append(task_report)
            elif schedule_report.schedule_condition is ScheduleCondition.LATE:
                lates.append(task_report)

            if schedule_report.planned_finish is not None:
                if as_of <= schedule_report.planned_finish <= as_of + look_ahead:
                    upcoming_deadlines.append(task_report)

            if schedule_report.planned_start is not None:
                if as_of <= schedule_report.planned_start <= as_of + look_ahead:
                    if state.status is TaskStatus.NOT_STARTED:
                        upcoming_starts.append(task_report)

        summary = {"all": all_tasks, "overdues": overdues, "blocked": blocked, 
                   "lates": lates, "deadlines": upcoming_deadlines, 
                   "starts": upcoming_starts, "charged": charged_tasks}
        return summary

    def _task_report(self, analysis, forecast:Schedule, task_id, state, as_of) -> TaskReport:
        task = self.project.tasks[task_id]
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
            name=task.name,
            schedule_report=self._task_schedule_report(analysis, forecast, task_id, state, schedule_condition),
            budget_report=self._task_budget_report(analysis, task_id),
            progress_report=self._task_progress_report(analysis, task_id),

            #planned_start=planned_start,
            #planned_finish=planned_finish,
            #actual_start=self.project.tracker.actual_start(task_id),
            #actual_finish=self.project.tracker.actual_finish(task_id),
            #start_variance=analysis.start_variance(task_id),
            #finish_variance=analysis.finish_variance(task_id),
            #duration_variance=analysis.duration_variance(task_id),
            #cost_variance=analysis.cost_variance(task_id),
            #days_overdue=days_overdue,
            #days_late=days_late,
            #days_waiting=days_waiting,
            #blocked_by=blocked_by,
            #root_causes=root_causes,
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
            if self._has_incomplete_predecessors(task_id, as_of):
                return ScheduleCondition.BLOCKED
            return ScheduleCondition.LATE
        
        if as_of > finish:
            return ScheduleCondition.OVERDUE
        
        return ScheduleCondition.ON_SCHEDULE

    def _project_schedule_report(self, analysis:Analyzer, forecast:Schedule) -> ProjectScheduleReport:
        planned_finish = self.project.finish_date

        # The forecast network's latest calendar finish, matching how task
        # rows render forecast dates.
        forecast_finish = max(forecast.finish_dates.values())

        # The variance is forecast against the project's target finish; a
        # project without a target reports n/a rather than crashing or
        # inventing a comparison date.
        schedule_variance = (forecast_finish - planned_finish
                             if planned_finish is not None else None)
        return ProjectScheduleReport(planned_start=self.project.start_date,
                                     planned_finish=planned_finish,
                                     planned_duration=self.project.schedule.duration,
                                     actual_start=analysis.project_actual_start(),
                                     forecast_finish=forecast_finish,
                                     schedule_variance=schedule_variance)

    def _project_budget_report(self, analysis:Analyzer) -> ProjectBudgetReport:
        """Report project money to the data date.

        Both amounts come from the same data date: the budget is the resolved
        plan, and the actual cost is invoice allocations up to as_of.
        """

        return ProjectBudgetReport(project_budget=self.project.budget.total,
                                    project_actual=self.project.tracker.total_actual_cost(self.spec.as_of))

    def _project_progress_report(self, analysis:Analyzer) -> ProjectProgressReport:

        return ProjectProgressReport(planned_progress=analysis.planned_project_progress(),
                                     actual_progress=analysis.actual_project_progress(),
                                     budget_consumed=analysis.project_consumed_cost())

    def _task_schedule_report(self, analysis:Analyzer, forecast:Schedule, task_id, state:TaskState, condition:ScheduleCondition) -> TaskScheduleReport:
        schedule = self.project.schedule
        tracker = self.project.tracker

        planned_finish = schedule.finish_dates[task_id]
        forecast_finish = forecast.finish_dates[task_id]
        forecast_start = forecast.start_dates[task_id]

        # CPM offsets measure the forecast duration exactly; the calendar
        # dates span one day less because both ends are inclusive.
        forecast_duration = forecast.early_finish[task_id] - forecast.early_start[task_id]
        forecast_variance = forecast_finish - planned_finish
        
        return TaskScheduleReport(state=state,
            schedule_condition=condition,
            planned_start=schedule.start_dates[task_id],
            planned_finish=planned_finish,
            planned_duration=self.project.tasks[task_id].duration,
        
            actual_start=tracker.actual_start(task_id, self.spec.as_of),
            actual_finish=tracker.actual_finish(task_id, self.spec.as_of),
            actual_duration=tracker.actual_duration(task_id, self.spec.as_of),
            finish_variance=analysis.finish_variance(task_id),
            
            forecast_start=forecast_start,
            forecast_finish=forecast_finish,
            forecast_duration=forecast_duration,
            forecast_variance=forecast_variance)

    def _task_budget_report(self, analysis:Analyzer, task_id) -> TaskBudgetReport:
        """Report a task's planned and actual money to the data date.

        Remaining and variance are derived from these two amounts, so a task
        with no budget reports n/a rather than a zero variance.
        """

        return TaskBudgetReport(task_budget=self.project.budget.get(task_id),
                                    task_actual=self.project.tracker.actual_cost(task_id, self.spec.as_of))

    def _task_progress_report(self, analysis:Analyzer, task_id) -> TaskProgressReport:
        planned = analysis.planned_progress(task_id)
        actual = analysis.actual_progress(task_id)

        return TaskProgressReport(planned_progress=planned,
                                     actual_progress=actual,
                                     budget_consumed=self._task_budget_consumed(task_id))

    def _task_budget_consumed(self, task_id) -> float | None:
        """Return the share of a task's budget spent to the data date.

        Returns None when the task has no planned budget to measure against.
        """

        budget = self.project.budget.get(task_id)
        if not budget:
            return None

        actual = self.project.tracker.actual_cost(task_id, self.spec.as_of)
        return float(actual / budget)

    def _has_incomplete_predecessors(self, task_id, as_of):
        return bool(self._incomplete_predecessors(task_id, as_of))

    def _incomplete_predecessors(self, task_id, as_of):
        """Return the task's predecessor Tasks that are not yet completed.

        Completion is judged at the report's data date, so a predecessor that
        finished after the report date still blocks the work.
        """

        task = self.project.tasks[task_id]
        incomplete = []
        for predecessor in self.project.get_predecessors(task):
            state = self.project.tracker.get_task_state(predecessor.number, as_of)
            if state.status is not TaskStatus.COMPLETED:
                incomplete.append(predecessor)
        return incomplete

    def _describe_blockers(self, task_id, as_of):
        """Describe the incomplete predecessors that are holding up a blocked task."""

        descriptions = []
        for predecessor in self._incomplete_predecessors(task_id, as_of):
            state = self.project.tracker.get_task_state(predecessor.number, as_of)
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
        pending = self._incomplete_predecessors(task_id, as_of)

        while pending:
            predecessor = pending.pop()
            if predecessor.number in visited:
                continue
            visited.add(predecessor.number)

            blockers = self._incomplete_predecessors(predecessor.number, as_of)
            if blockers:
                pending.extend(blockers)
            else:
                state = self.project.tracker.get_task_state(predecessor.number, as_of)
                condition = self._schedule_condition(predecessor.number, state, as_of)
                roots[predecessor.number] = f"{predecessor.number} [{condition.value}]"

        return sorted(roots.values())

@dataclass
class ReportView:
    """Derived data for a project report at a single data date.

    ReportView is plain data with no rendering logic. It is the result
    of building a ReportSpec against a Project. Renderers consume
    ReportView instances to produce output.

    Attributes:
        name: The project name.
        status: The project's derived status.
        as_of: The data date for the report.
        look_ahead: The look-ahead window used for upcoming filters.
        schedule_report: Project-level schedule figures, or None.
        budget_report: Project-level budget figures, or None.
        progress_report: Project-level progress figures, or None.
        task_views: Filtered list of task views.
        data_notices: Tracking data excluded by the data date.
    """

    name: str
    status: ProjectStatus
    spec: ReportSpec
    #as_of: date
    #look_ahead: timedelta

    schedule_report: ProjectScheduleReport | None = None
    budget_report: ProjectBudgetReport | None = None
    progress_report: ProjectProgressReport | None = None

    task_views: list[TaskView] = field(default_factory=list)
    data_notices: list[str] = field(default_factory=list)

@dataclass
class TaskView:
    """Derived data for one task at a report's data date.

    TaskView is plain data with no rendering logic. Renderers consume
    TaskView instances to produce console tables, text blocks, or other
    output formats.

    Attributes:
        task_id: The task's PlanScript identifier.
        name: The task's human-readable name.
        depth: the hierarchy level of the task.
        is_summary: True when the task has child tasks.
        is_milestone: True when the task has zero planned duration.
        schedule_condition: The task's derived schedule condition.
        total_float: The task's total float from CPM, or None.
        planned_start: The task's planned start date.
        planned_finish: The task's planned finish date.
        planned_duration: The task's planned duration.
        actual_start: The task's actual start date, or None.
        actual_finish: The task's actual finish date, or None.
        actual_duration: The task's actual duration, or None.
        forecast_start: The task's forecast start date, or None.
        forecast_finish: The task's forecast finish date, or None.
        forecast_duration: The task's forecast remaining duration, or None.
        finish_variance: Actual finish minus planned finish, or None.
        forecast_variance: Forecast finish minus planned finish, or None.
        task_budget: The task's planned budget, or None.
        task_actual: The task's actual cost to as_of, or None.
        task_remaining: Budget minus actual, or None.
        cost_variance: Actual minus budget, or None.
        planned_progress: Planned progress as a 0..1 fraction, or None.
        actual_progress: Actual progress as a 0..1 fraction, or None.
        budget_consumed: Share of budget spent, or None.
        days_overdue: Days past planned finish, or None.
        days_late: Days past planned start, or None.
        days_waiting: Days waiting on predecessors, or None.
        blocked_by: Descriptions of incomplete predecessors.
        root_causes: Terminal blockers resolved from the dependency chain.
    """

    task_id: str
    name: str
    depth: int =0
    is_summary: bool = False
    is_milestone: bool = False

    schedule_condition: ScheduleCondition = ScheduleCondition.ON_SCHEDULE
    total_float: timedelta | None = None

    planned_start: date | None = None
    planned_finish: date | None = None
    planned_duration: timedelta | None = None

    actual_start: date | None = None
    actual_finish: date | None = None
    actual_duration: timedelta | None = None

    forecast_start: date | None = None
    forecast_finish: date | None = None
    forecast_duration: timedelta | None = None

    finish_variance: timedelta | None = None
    forecast_variance: timedelta | None = None

    task_budget: Decimal | None = None
    task_actual: Decimal | None = None
    task_remaining: Decimal | None = None
    cost_variance: Decimal | None = None

    planned_progress: float | None = None
    actual_progress: float | None = None
    budget_consumed: float | None = None

    days_overdue: timedelta | None = None
    days_late: timedelta | None = None
    days_waiting: timedelta | None = None
    blocked_by: list[str] = field(default_factory=list)
    root_causes: list[str] = field(default_factory=list)

class TaskFilter:
    """Filter a list of TaskView instances by common report criteria.

    Each method returns a new list and does not modify the input.
    """

    @staticmethod
    def all_tasks(views: list[TaskView]) -> list[TaskView]:
        """Return all task views unchanged."""
        return list(views)

    @staticmethod
    def critical(views: list[TaskView]) -> list[TaskView]:
        """Return tasks on the critical path (total float is zero).

        A task is critical when its total float is exactly zero, meaning
        any delay in the task delays the project finish.
        """
        result = []
        for view in views:
            if view.total_float is not None and view.total_float == timedelta(0):
                result.append(view)
        return result

    @staticmethod
    def behind(views: list[TaskView]) -> list[TaskView]:
        """Return tasks that are late or overdue.

        A task is behind when it is late (unstarted but planned start passed)
        or overdue (started but planned finish passed). Blocked tasks are
        excluded: they are waiting on predecessors, not behind on their own
        work.
        """
        result = []
        for view in views:
            if view.schedule_condition in (
                ScheduleCondition.LATE,
                ScheduleCondition.OVERDUE,
            ):
                result.append(view)
        return result

    @staticmethod
    def overdue(views: list[TaskView]) -> list[TaskView]:
        """Return tasks whose planned finish has passed and work remains.

        An overdue task has started but has not finished by its planned
        finish date.
        """
        result = []
        for view in views:
            if view.schedule_condition is ScheduleCondition.OVERDUE:
                result.append(view)
        return result

    @staticmethod
    def blocked(views: list[TaskView]) -> list[TaskView]:
        """Return tasks waiting on incomplete predecessors.

        A blocked task cannot start because at least one predecessor is
        not yet complete.
        """
        result = []
        for view in views:
            if view.schedule_condition is ScheduleCondition.BLOCKED:
                result.append(view)
        return result

    @staticmethod
    def late(views: list[TaskView]) -> list[TaskView]:
        """Return unstarted tasks whose planned start has passed.

        A late task has no start event, all predecessors are complete, but
        the planned start date has already passed.
        """
        result = []
        for view in views:
            if view.schedule_condition is ScheduleCondition.LATE:
                result.append(view)
        return result

    @staticmethod
    def upcoming(
        views: list[TaskView],
        as_of: date,
        look_ahead: timedelta,
    ) -> list[TaskView]:
        """Return tasks starting or finishing within the look-ahead window.

        Only unstarted tasks are included: a task already in progress is
        not "upcoming" even if its finish date is near.
        """
        result = []
        window_end = as_of + look_ahead
        for view in views:
            if view.actual_start is not None:
                continue
            if view.planned_start is not None:
                if as_of <= view.planned_start <= window_end:
                    result.append(view)
                    continue
            if view.planned_finish is not None:
                if as_of <= view.planned_finish <= window_end:
                    result.append(view)
        return result

    @staticmethod
    def ready_to_start(views: list[TaskView]) -> list[TaskView]:
        """Return unstarted tasks whose predecessors are all complete.

        A task is ready to start when it has no start event and is not
        blocked on an incomplete predecessor.
        """
        result = []
        for view in views:
            if view.actual_start is not None:
                continue
            if view.schedule_condition is not ScheduleCondition.BLOCKED:
                result.append(view)
        return result

    @staticmethod
    def charged(views: list[TaskView]) -> list[TaskView]:
        """Return tasks that have a planned budget.

        A charged task has a non-None task_budget, meaning it carries
        either an explicit or weighted budget allocation.
        """
        result = []
        for view in views:
            if view.task_budget is not None:
                result.append(view)
        return result

    @staticmethod
    def apply(views: list[TaskView], spec: ReportSpec) -> list[TaskView]:
        """Apply the filter named in spec to the list of task views.

        Returns the filtered list without modifying the input. Raises
        ValueError when the filter name is not recognized.
        """
        filter_name = spec.filter
        if filter_name == "all":
            return TaskFilter.all_tasks(views)
        if filter_name == "critical":
            return TaskFilter.critical(views)
        if filter_name == "behind":
            return TaskFilter.behind(views)
        if filter_name == "overdue":
            return TaskFilter.overdue(views)
        if filter_name == "blocked":
            return TaskFilter.blocked(views)
        if filter_name == "late":
            return TaskFilter.late(views)
        if filter_name == "upcoming":
            return TaskFilter.upcoming(views, spec.as_of, spec.look_ahead)
        if filter_name == "ready_to_start":
            return TaskFilter.ready_to_start(views)
        if filter_name == "charged":
            return TaskFilter.charged(views)
        raise ValueError(f"Unknown report filter: {filter_name}")

class ReportRenderer:
    """Render a ReportView without calculating or modifying report data."""

    def render(self, report: ReportView) -> None:
        """Render a report view."""

        if report.spec.renderer == "detail":
            self.render_detail(report)
        elif report.spec.renderer == "table":
            self.render_table(report)
        else:
            raise ValueError(f"Unknown report renderer: {report.spec.renderer}")
    
    def _render_header(self, report: ReportView) -> None:
        print(f"\nStatus Report as-of {report.spec.as_of}")
        print("=" * 60)
        print(f"Project Name: {report.name}")
        print(f"    Status: {report.status.value}")

        if report.data_notices:
            print("\nData Notices")
            for notice in report.data_notices:
                print(f"    {notice}")

        print()

    def _render_project_detail(self, report:ReportView) -> None:
        if report.spec.basis in ("schedule", "both"):
            schedule = report.schedule_report

            if schedule is not None:
                #TODO Expand placeholder see cgpt
                print(schedule.render_text())
        if report.spec.basis in ("finance", "both"):
            budget = report.budget_report

            if budget is not None:
                #TODO Expand placeholder see cgpt
                print(budget.render_text())

        if report.spec.basis == "both":
            progress = report.progress_report

            if progress is not None:
                #TODO Expand placeholder see cgpt
                print(progress.render_text())

    def _render_task_detail(self, view: TaskView, spec: ReportSpec) -> None:
        indent = "    " * view.depth
        print(f"{indent}{view.task_id} - {view.name}")
        if view.is_summary:
            print(f"{indent}    Summary Task")
        elif view.is_milestone:
            print(f"{indent}    Milestone")

        if spec.basis in ("schedule", "both"):
            print(f"{indent}    Schedule Status: HERE")

            if view.is_milestone:
                print(f"{indent}    Planned Milestone: "
                      f"{_format_date(view.planned_finish)}")
                if view.actual_start is not None:
                    print(f"{indent}    Actual Milestone: "
                          f"{_format_date(view.actual_start)}")
                print(f"{indent}    Forecast Milestone: "
                      f"{_format_date(view.forecast_finish)}")
            else:
                print(f"{indent}    Planned Start / Finish / Duration: "
                      f"{indent}    Actual Start / Finish / Duration:"
                      f"{indent}    Forecast Start / Finish / Duration:")
            print(f"{indent}    Finish Variance")
            print(f"{indent}    Forecast Variance: ")
            print(f"{indent}    Total Float: ")

            if view.days_overdue is not None:
                print(f"{indent}    Days Overdue: ")
            if view.days_late is not None:
                print(f"{indent}    Days Late: ")
            if view.days_waiting is not None:
                print(f"{indent}    Days Waiting: ")

            for blocker in view.blocked_by:
                print(f"{indent}    Blocked By: {blocker} ")
            if view.root_causes:
                print(f"{indent}    Root Causes: {','.join(view.root_causes)}")

        if spec.basis in ("finance", "both"):
            print(f"{indent}    Planned Budget: {_format_money(view.task_budget)}")
            print(f"{indent}    Actual Cost: {_format_money(view.task_actual)}")
            print(f"{indent}    Remaining Budget: {_format_money(view.task_remaining)}")
            print(f"{indent}    Cost Variance: {_format_money(view.cost_variance)}")

        if spec.basis == "both":
            print(f"{indent}    Planned Progress: ")
            print(f"{indent}    Actual Progress:")
            print(f"{indent}    Budget Progress: ")

        print()


    def render_detail(self, report: ReportView) -> None:
        self._render_header(report)
        if report.spec.scope == "project":
            self._render_project_detail(report)
            return

        self._render_project_detail(report)

        for view in report.task_views:
            self._render_task_detail(view, report.spec) #include spec?

        print("DETAIL REPORT FOLLOWS")