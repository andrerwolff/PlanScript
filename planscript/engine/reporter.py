"""Status reporting for PlanScript projects.

ReportBuilder composes the derived models into a ProjectReport and renders it
for the console. Every reported figure has exactly one source:

    planned dates and durations  ->  project.Schedule and task.duration
    actual dates and durations   ->  project.Tracker, at the report's as_of date
    variances and progress       ->  Analyzer, at the report's as_of date
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
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from datetime import date, timedelta

from planscript.model.project import Project
from planscript.engine.tracker import TaskStatus, TaskState, Invoice
from planscript.engine.analyzer import Analyzer
from planscript.exceptions import SchedulingError

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

def _format_date(value: date | None) -> str:
    """Format a date, keeping an unknown date distinct from any real date."""

    if value is None:
        return NOT_AVAILABLE
    return f"{value}"

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
              f"    Schedule Variance: {_format_days(self.schedule_variance)}\n\n")
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
              f"--------------------------------------\n"
              f"    Planned Start / Finish: {_format_date(self.planned_start)} / {_format_date(self.planned_finish)}\n")

        if self.is_milestone():
            text += (f"    Planned Duration: - (milestone)\n"
                     f"    Actual Start / Finish: {_format_date(self.actual_start)} / {_format_date(self.actual_finish)}\n"
                     f"    Duration Variance: {_format_days(self.duration_variance)} (milestone)\n")
            return text + "\n"

        text += f"    Planned Duration: {_format_duration(self.planned_duration)}\n"

        if self.actual_start is not None:
            if self.actual_finish is not None:
                text += (f"    Actual Start / Finish: {_format_date(self.actual_start)} / {_format_date(self.actual_finish)}\n")
            else:
                text += f"    Actual Start: {_format_date(self.actual_start)}\n"

            text += (f"    Actual Duration (so far) (Variance): {_format_duration(self.actual_duration)}"
                     f" ({_format_days(self.duration_variance)})\n")

        if self.forecast_finish is not None:
            text += f"    Forecast Finish: {_format_date(self.forecast_finish)}\n"

        if self.forecast_duration is not None:
            text += (f"    Forecast Duration (Variance): {_format_duration(self.forecast_duration)}"
                     f" ({_format_days(self.forecast_variance)})\n")

        return text + "\n"
    
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
              f"    Cost Variance (actual - budget): {_format_money(self.project_variance)}\n\n")
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
              f"    Remaining Budget: {_format_money(self.task_remaining)}\n"
              f"    Cost Variance (actual - budget): {_format_money(self.cost_variance)}\n\n")
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
              f"    Budget Consumed: {_format_percent(self.budget_consumed)}\n\n")
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

@dataclass
class ReportBuilder:
    """Build a ProjectReport at a single data date.

    The builder is the only place that decides where a reported figure comes
    from, so every value in the report is derived from the same as_of date.
    """

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
            progress_report=self._project_progress_report(analysis),
            all_tasks=summary["all"],
            data_notices=self._data_notices()
        )
            #blocked_tasks=summary["blocked"],
            #late_tasks=summary["lates"],
            #upcoming_deadlines=summary["deadlines"],
            #upcoming_starts=summary["starts"],
            #charged_tasks=summary["charged"],
            #look_ahead=self.look_ahead

    def _data_notices(self) -> list[str]:
        """Describe tracking data the report's data date excluded.

        A truncated figure is explained rather than silently dropped: entries
        dated after as_of are summarised per task, with the count and the latest
        date so the reader knows recorded work is missing from the report.
        Tracker.future_dated_events() returns the entries themselves.
        """

        by_task = {}
        for event in self.project.tracker.future_dated_events(self.as_of):
            by_task.setdefault(event.task_id, []).append(event)

        notices = []
        for task_id in sorted(by_task):
            events = by_task[task_id]
            noun = "entry" if len(events) == 1 else "entries"
            latest = max(event.date for event in events)
            notices.append(
                f"{task_id}: {len(events)} tracking {noun} after this report's "
                f"as-of date ({self.as_of}), latest {latest}; not included.")
        return notices


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
            state = self.project.tracker.get_task_state(task_id, self.as_of)
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

    def _task_summary(self, analysis, as_of: date, look_ahead: timedelta):
        all_tasks = []
        overdues = []
        blocked = []
        lates = []
        upcoming_deadlines = []
        upcoming_starts = []
        charged_tasks = []

        for task_id in self.project.schedule.hierarchy.get_leaf_ids():
            state = self.project.tracker.get_task_state(task_id, as_of)
            task_report = self._task_report(analysis, task_id, state, as_of)
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

    def _task_report(self, analysis, task_id, state, as_of) -> TaskReport:
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
            schedule_report=self._task_schedule_report(analysis, task_id, state, schedule_condition),
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

    def _project_schedule_report(self, analysis:Analyzer) -> ProjectScheduleReport:

        return ProjectScheduleReport(planned_start=self.project.start_date,
                                     planned_finish=self.project.finish_date,
                                     planned_duration=self.project.schedule.duration,
                                     actual_start=analysis.project_actual_start(),
                                     forecast_finish=None,
                                     schedule_variance=None)

    def _project_budget_report(self, analysis:Analyzer) -> ProjectBudgetReport:
        """Report project money to the data date.

        Both amounts come from the same data date: the budget is the resolved
        plan, and the actual cost is invoice allocations up to as_of.
        """

        return ProjectBudgetReport(project_budget=self.project.budget.total,
                                    project_actual=self.project.tracker.total_actual_cost(self.as_of))

    def _project_progress_report(self, analysis:Analyzer) -> ProjectProgressReport:

        return ProjectProgressReport(planned_progress=analysis.planned_project_progress(),
                                     actual_progress=analysis.actual_project_progress(),
                                     budget_consumed=analysis.project_consumed_cost())

    def _task_schedule_report(self, analysis:Analyzer, task_id, state:TaskState, condition:ScheduleCondition) -> TaskScheduleReport:
        schedule = self.project.schedule
        tracker = self.project.tracker
        return TaskScheduleReport(state=state,
            schedule_condition=condition,
            planned_start=schedule.start_dates[task_id],
            planned_finish=schedule.finish_dates[task_id],
            planned_duration=self.project.tasks[task_id].duration,
        
            actual_start=tracker.actual_start(task_id, self.as_of),
            actual_finish=tracker.actual_finish(task_id, self.as_of),
            actual_duration=tracker.actual_duration(task_id, self.as_of),
            duration_variance=analysis.duration_variance(task_id),
        
            forecast_start=None,
            forecast_finish=None,
            forecast_duration=None,
            forecast_variance=None)

    def _task_budget_report(self, analysis:Analyzer, task_id) -> TaskBudgetReport:
        """Report a task's planned and actual money to the data date.

        Remaining and variance are derived from these two amounts, so a task
        with no budget reports n/a rather than a zero variance.
        """

        return TaskBudgetReport(task_budget=self.project.budget.get(task_id),
                                    task_actual=self.project.tracker.actual_cost(task_id, self.as_of))

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

        actual = self.project.tracker.actual_cost(task_id, self.as_of)
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







    

