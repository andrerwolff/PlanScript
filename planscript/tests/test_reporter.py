"""Tests for the status report's metrics, labels, and as-of consistency.

Every test states its own data date, so none of them depend on the wall clock.

Reported figures are verified two ways:

* by source - a reported figure must equal the value derived from the model it
  claims to come from (Schedule, Tracker, Analyzer, or Budget), and
* by invariant - figures must reconcile with each other, such as
  budget = actual + remaining for the same data date, and the per-task rows
  must reach the project totals.

The fixture mirrors the shape of ``Simple.plan``: a summary with weighted
children, a milestone, an unbudgeted task, a direct charge to a summary, and a
tracking entry dated after the report date.

Hand-checked budget figures for the fixture (weights resolve from task 1's
$10,000): 1.1 = $1,000 (10%), 1.2 = $4,000 (40%), 1.3 = $5,000 (50%), and the
project total is $10,000. The invoice of $750 splits $100 to task 1, $200 to
1.1, $300 to 1.2, and $150 to the unbudgeted 4.1, so the task rows reach $650
and the remaining $100 is the direct charge to summary task 1.
"""

import unittest
import textwrap
from datetime import date, timedelta
from decimal import Decimal

from planscript.engine.analyzer import Analyzer
from planscript.engine.budgeter import Budgeter
from planscript.engine.parser import Parser
from planscript.engine.reporter import (NOT_AVAILABLE, ProjectStatus,
                                        ReportBuilder, ScheduleCondition)
from planscript.engine.scheduler import Scheduler
from planscript.engine.tracker import TaskStatus


FIXTURE = textwrap.dedent("""\
    project: Reporting Fixture
        start: 2026-08-01
        finish: 2026-12-31

    task 1 Phase One
        budget $10000
    task 1.1 Kickoff 0d
        budget 10%
    task 1.2 Build 10d
        depends 1.1
        budget 40%
    task 1.3 Review 5d
        depends 1.2
        budget 50%

    task 2 Extra Work
    task 2.1 Effort 4d
        depends 1.2

    task 3 Follow On
    task 3.1 Handover 2d
        depends 2.1

    task 4 Pipeline
    task 4.1 Later 2d
        depends 3.1

    ;Tracking:
    2026-08-01
        1.1 start
        1.1 complete

    2026-08-02 1.2 start
    2026-08-06 1.2 progress 50%
    2026-08-12 1.2 complete

    2026-12-01 4.1 start

    2026-08-20 invoice $750
        1 $100
        1.1 $200
        1.2 $300
        4.1 $150
    """)

# Data dates covering before the project start, an in-flight period, the
# blocked/late window, the day the invoice lands, and long after the invoice.
DATA_DATES = (
    date(2026, 7, 15),
    date(2026, 8, 2),
    date(2026, 8, 10),
    date(2026, 8, 14),
    date(2026, 8, 18),
    date(2026, 8, 20),
    date(2026, 9, 30),
)


def build(plan_text=FIXTURE, as_of=date(2026, 8, 20)):
    """Parse, schedule, budget, and report a plan at a data date.

    Returns the project and its report, so a test can compare a reported figure
    against the model it came from.
    """

    project = Parser().parse(plan_text)
    project.schedule = Scheduler().calculate(project)
    project.budget = Budgeter().calculate(project)
    report = ReportBuilder(project, as_of).build()
    return project, report


def task_of(report, task_id):
    """Return the report row for a task."""

    for task_report in report.all_tasks:
        if task_report.task_id == task_id:
            return task_report
    raise AssertionError(f"no report row for task '{task_id}'")


class TestTrackerDataDate(unittest.TestCase):
    """Tracker ignores anything dated after the data date."""

    def setUp(self):
        self.project = Parser().parse(FIXTURE)
        self.project.schedule = Scheduler().calculate(self.project)
        self.project.budget = Budgeter().calculate(self.project)
        self.tracker = self.project.tracker

    def test_state_excludes_later_events(self):
        self.assertIs(
            self.tracker.get_task_state("1.2", date(2026, 8, 10)).status,
            TaskStatus.IN_PROGRESS)
        self.assertIs(
            self.tracker.get_task_state("1.2", date(2026, 8, 14)).status,
            TaskStatus.COMPLETED)

    def test_progress_excludes_later_events(self):
        self.assertEqual(
            self.tracker.get_task_state("1.2", date(2026, 8, 10)).percent_complete,
            50)
        self.assertEqual(
            self.tracker.get_task_state("1.2", date(2026, 8, 14)).percent_complete,
            100)

    def test_future_start_is_not_a_start(self):
        # 4.1's start is recorded for 2026-12-01.
        self.assertIsNone(self.tracker.actual_start("4.1", date(2026, 9, 30)))
        self.assertEqual(self.tracker.actual_start("4.1", date(2026, 12, 1)),
                         date(2026, 12, 1))

    def test_future_finish_is_not_a_finish(self):
        self.assertIsNone(self.tracker.actual_finish("1.2", date(2026, 8, 10)))
        self.assertEqual(self.tracker.actual_finish("1.2", date(2026, 8, 14)),
                         date(2026, 8, 12))

    def test_elapsed_duration_never_goes_negative(self):
        # Without a data date that excludes the future start, elapsed time would
        # run backwards; instead the task has no actual duration yet.
        self.assertIsNone(self.tracker.actual_duration("4.1", date(2026, 8, 20)))
        self.assertEqual(self.tracker.actual_duration("1.2", date(2026, 8, 10)),
                         timedelta(days=9))

    def test_cost_excludes_later_invoices(self):
        self.assertEqual(self.tracker.actual_cost("1.2", date(2026, 8, 18)),
                         Decimal("0"))
        self.assertEqual(self.tracker.actual_cost("1.2", date(2026, 8, 20)),
                         Decimal("300"))

    def test_future_dated_events_are_reported_not_dropped(self):
        events = self.tracker.future_dated_events(date(2026, 8, 20))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].task_id, "4.1")
        self.assertEqual(events[0].date, date(2026, 12, 1))

    def test_all_task_events_are_truncated(self):
        self.assertEqual(len(self.tracker.get_all_task_events(date(2026, 8, 10))),
                         4)


class TestReportBudgetConsistency(unittest.TestCase):
    """Money in the report reconciles with the budget and invoice history."""

    def test_hand_checked_budget_split(self):
        project, report = build()

        self.assertEqual(project.budget.amounts["1.1"], Decimal("1000"))
        self.assertEqual(project.budget.amounts["1.2"], Decimal("4000"))
        self.assertEqual(project.budget.amounts["1.3"], Decimal("5000"))
        self.assertEqual(report.budget_report.project_budget, Decimal("10000"))
        self.assertEqual(task_of(report, "1.1").budget_report.task_budget,
                         Decimal("1000"))

    def test_project_actual_matches_the_tracker_at_every_data_date(self):
        for as_of in DATA_DATES:
            with self.subTest(as_of=as_of):
                project, report = build(as_of=as_of)

                self.assertEqual(
                    report.budget_report.project_actual,
                    project.tracker.total_actual_cost(as_of))

    def test_invoice_after_the_data_date_is_excluded_everywhere(self):
        _, report = build(as_of=date(2026, 8, 18))

        self.assertEqual(report.budget_report.project_actual, Decimal("0"))
        self.assertEqual(report.budget_report.project_remaining, Decimal("10000"))
        self.assertEqual(task_of(report, "1.1").budget_report.task_actual,
                         Decimal("0"))
        self.assertEqual(task_of(report, "1.1").budget_report.task_remaining,
                         Decimal("1000"))

    def test_budget_equals_actual_plus_remaining(self):
        for as_of in DATA_DATES:
            with self.subTest(as_of=as_of):
                _, report = build(as_of=as_of)
                budget = report.budget_report

                self.assertEqual(budget.project_actual + budget.project_remaining,
                                 budget.project_budget)

    def test_remaining_is_the_negation_of_variance(self):
        for as_of in DATA_DATES:
            with self.subTest(as_of=as_of):
                _, report = build(as_of=as_of)
                budget = report.budget_report

                self.assertEqual(budget.project_remaining,
                                 -budget.project_variance)

    def test_task_rows_reach_the_project_total(self):
        # Summing the reported task rows must reach the project's actual cost,
        # including the $100 charged directly to summary task 1.
        project, report = build(as_of=date(2026, 8, 20))

        rows = sum((task_report.budget_report.task_actual
                    for task_report in report.all_tasks), Decimal("0"))

        self.assertEqual(rows, Decimal("650"))
        self.assertEqual(report.budget_report.project_actual, Decimal("750"))
        self.assertEqual(report.budget_report.project_actual - rows,
                         Decimal("100"))
        # Summary task 1 carries its own $100 charge plus its children's $500.
        self.assertEqual(project.tracker.actual_cost("1", date(2026, 8, 20)),
                         Decimal("600"))

    def test_task_cost_variance_matches_the_analyzer(self):
        as_of = date(2026, 9, 30)
        project, report = build(as_of=as_of)
        analysis = Analyzer(project, as_of)

        for task_report in report.all_tasks:
            with self.subTest(task=task_report.task_id):
                self.assertEqual(
                    task_report.budget_report.cost_variance,
                    analysis.cost_variance(task_report.task_id))

    def test_task_progress_matches_the_analyzer(self):
        as_of = date(2026, 8, 10)
        project, report = build(as_of=as_of)
        analysis = Analyzer(project, as_of)

        for task_report in report.all_tasks:
            with self.subTest(task=task_report.task_id):
                self.assertEqual(task_report.progress_report.planned_progress,
                                 analysis.planned_progress(task_report.task_id))
                self.assertEqual(task_report.progress_report.actual_progress,
                                 analysis.actual_progress(task_report.task_id))

    def test_unbudgeted_task_reports_no_budget_and_no_variance(self):
        _, report = build(as_of=date(2026, 9, 30))
        task_report = task_of(report, "4.1").budget_report

        # 4.1 is charged $150 but has no planned budget, so its variance is not
        # zero - it is unmeasurable, and must not be reported as $0.00.
        self.assertIsNone(task_report.task_budget)
        self.assertEqual(task_report.task_actual, Decimal("150"))
        self.assertIsNone(task_report.task_remaining)
        self.assertIsNone(task_report.cost_variance)

    def test_budget_consumed_is_the_share_of_the_budget_spent(self):
        _, report = build(as_of=date(2026, 9, 30))

        # $750 of the $10,000 budget is spent.
        self.assertEqual(report.progress_report.budget_consumed, 0.075)

    def test_project_without_a_budget_has_no_consumed_cost(self):
        plan = textwrap.dedent("""\
            project: No Budget
                start: 2026-08-01

            task 1.1 Work 3d
            """)
        project = Parser().parse(plan)
        project.schedule = Scheduler().calculate(project)
        project.budget = Budgeter().calculate(project)

        self.assertEqual(project.budget.total, Decimal("0"))
        self.assertIsNone(
            Analyzer(project, date(2026, 8, 10)).project_consumed_cost())


class TestReportInvariants(unittest.TestCase):
    """Properties that must hold at every data date."""

    TASK_IDS = ("1.1", "1.2", "1.3", "2.1", "3.1", "4.1")

    def test_no_negative_durations(self):
        for as_of in DATA_DATES:
            _, report = build(as_of=as_of)
            for task_id in self.TASK_IDS:
                with self.subTest(as_of=as_of, task=task_id):
                    schedule = task_of(report, task_id).schedule_report

                    for value in (schedule.actual_duration,
                                  schedule.forecast_duration):
                        if value is not None:
                            self.assertGreaterEqual(value, timedelta(0))

    def test_duration_variance_never_beats_zero_remaining(self):
        # A finished-in-an-instant task is the best case, so the variance can be
        # negative (ahead of plan) but never worse than -planned duration.
        for as_of in DATA_DATES:
            _, report = build(as_of=as_of)
            for task_id in self.TASK_IDS:
                with self.subTest(as_of=as_of, task=task_id):
                    schedule = task_of(report, task_id).schedule_report

                    if schedule.duration_variance is None:
                        continue

                    planned = schedule.planned_duration or timedelta(0)
                    self.assertGreaterEqual(schedule.duration_variance, -planned)

    def test_no_actual_date_is_after_the_data_date(self):
        for as_of in DATA_DATES:
            with self.subTest(as_of=as_of):
                _, report = build(as_of=as_of)
                actual_start = report.schedule_report.actual_start

                if actual_start is not None:
                    self.assertLessEqual(actual_start, as_of)

                for task_report in report.all_tasks:
                    for actual in (task_report.schedule_report.actual_start,
                                   task_report.schedule_report.actual_finish):
                        if actual is not None:
                            self.assertLessEqual(actual, as_of)

    def test_progress_stays_between_zero_and_one(self):
        for as_of in DATA_DATES:
            with self.subTest(as_of=as_of):
                _, report = build(as_of=as_of)
                progress = report.progress_report

                values = [progress.planned_progress,
                          progress.actual_progress,
                          progress.budget_consumed]
                for task_report in report.all_tasks:
                    values.append(task_report.progress_report.planned_progress)
                    values.append(task_report.progress_report.actual_progress)

                for value in values:
                    if value is not None:
                        self.assertGreaterEqual(value, 0)
                        self.assertLessEqual(value, 1)

    def test_actual_cost_never_decreases_as_time_advances(self):
        costs = [build(as_of=as_of)[1].budget_report.project_actual
                 for as_of in DATA_DATES]

        self.assertEqual(costs, sorted(costs))

    def test_actual_progress_never_decreases_as_time_advances(self):
        progress = [build(as_of=as_of)[1].progress_report.actual_progress
                    for as_of in DATA_DATES]

        self.assertEqual(progress, sorted(progress))

    def test_project_progress_matches_the_analyzer(self):
        for as_of in DATA_DATES:
            with self.subTest(as_of=as_of):
                project, report = build(as_of=as_of)
                analysis = Analyzer(project, as_of)

                self.assertEqual(report.progress_report.planned_progress,
                                 analysis.planned_project_progress())
                self.assertEqual(report.progress_report.actual_progress,
                                 analysis.actual_project_progress())
                self.assertEqual(report.progress_report.budget_consumed,
                                 analysis.project_consumed_cost())

    def test_completed_tasks_report_full_progress(self):
        _, report = build(as_of=date(2026, 9, 30))

        for task_id in ("1.1", "1.2"):
            with self.subTest(task=task_id):
                schedule = task_of(report, task_id).schedule_report
                progress = task_of(report, task_id).progress_report

                self.assertIs(schedule.state.status, TaskStatus.COMPLETED)
                self.assertEqual(progress.actual_progress, 1.0)

    def test_unstarted_tasks_report_no_actual_dates(self):
        for as_of in DATA_DATES:
            _, report = build(as_of=as_of)
            for task_id in self.TASK_IDS:
                with self.subTest(as_of=as_of, task=task_id):
                    schedule = task_of(report, task_id).schedule_report

                    if schedule.state.status is TaskStatus.NOT_STARTED:
                        self.assertIsNone(schedule.actual_start)
                        self.assertIsNone(schedule.actual_duration)
                        self.assertIsNone(schedule.duration_variance)

    def test_rendered_report_has_no_unformatted_placeholders(self):
        for as_of in DATA_DATES:
            with self.subTest(as_of=as_of):
                _, report = build(as_of=as_of)
                text = report.render_text()

                self.assertNotIn("None", text)
                self.assertNotIn("Noned", text)


class TestScheduleConditions(unittest.TestCase):
    """Task conditions follow the dependency and finish state at the date."""

    def test_task_started_but_unfinished_is_on_schedule(self):
        _, report = build(as_of=date(2026, 8, 10))

        self.assertIs(
            task_of(report, "1.2").schedule_report.schedule_condition,
            ScheduleCondition.ON_SCHEDULE)
        self.assertIs(task_of(report, "1.2").schedule_report.state.status,
                      TaskStatus.IN_PROGRESS)

    def test_unstarted_task_with_a_finished_predecessor_is_late(self):
        _, report = build(as_of=date(2026, 8, 14))

        self.assertIs(
            task_of(report, "1.3").schedule_report.schedule_condition,
            ScheduleCondition.LATE)
        self.assertIs(task_of(report, "1.3").schedule_report.state.status,
                      TaskStatus.NOT_STARTED)

    def test_unstarted_task_with_an_incomplete_predecessor_is_blocked(self):
        _, report = build(as_of=date(2026, 8, 18))

        self.assertIs(
            task_of(report, "3.1").schedule_report.schedule_condition,
            ScheduleCondition.BLOCKED)
        self.assertIs(
            task_of(report, "2.1").schedule_report.schedule_condition,
            ScheduleCondition.LATE)

    def test_task_with_a_future_entry_is_not_started_yet(self):
        # 4.1 carries a start entry dated 2026-12-01, after every data date
        # below, so the report must not treat the work as begun.
        for as_of in (date(2026, 8, 20), date(2026, 9, 30)):
            with self.subTest(as_of=as_of):
                _, report = build(as_of=as_of)

                self.assertIs(
                    task_of(report, "4.1").schedule_report.state.status,
                    TaskStatus.NOT_STARTED)
                self.assertIsNone(
                    task_of(report, "4.1").schedule_report.actual_start)

    def test_root_causes_are_resolved_at_the_data_date(self):
        project, _ = build(as_of=date(2026, 8, 18))

        # At 2026-08-18, 3.1 is blocked by 2.1, which is itself late rather than
        # blocked, so 2.1 is the task that must actually be actioned.
        self.assertEqual(
            ReportBuilder(project, date(2026, 8, 18))._root_causes(
                "3.1", date(2026, 8, 18)),
            ["2.1 [Late]"])

        # At 2026-08-05 the same chain stops at the work still in flight.
        self.assertEqual(
            ReportBuilder(project, date(2026, 8, 5))._root_causes(
                "3.1", date(2026, 8, 5)),
            ["1.2 [On Schedule]"])

    def test_project_status_by_date(self):
        expected = {
            date(2026, 7, 15): ProjectStatus.NOT_STARTED,
            date(2026, 8, 2): ProjectStatus.IN_PROGRESS,
            date(2026, 8, 10): ProjectStatus.IN_PROGRESS,
            date(2026, 9, 30): ProjectStatus.IN_PROGRESS,
        }

        for as_of, status in expected.items():
            with self.subTest(as_of=as_of):
                self.assertIs(build(as_of=as_of)[1].status, status)

    def test_project_is_not_started_before_the_first_entry(self):
        _, report = build(as_of=date(2026, 7, 15))

        self.assertIs(report.status, ProjectStatus.NOT_STARTED)
        self.assertEqual(report.progress_report.actual_progress, 0.0)

    def test_project_is_completed_when_every_task_is_complete(self):
        plan = textwrap.dedent("""\
            project: Complete
                start: 2026-08-01
                finish: 2026-09-01

            task 1.1 Only Task 3d

            ;Tracking
            2026-08-01 1.1 start
            2026-08-03 1.1 complete
            """)

        self.assertIs(build(plan, as_of=date(2026, 8, 10))[1].status,
                      ProjectStatus.COMPLETED)


class TestDataNotices(unittest.TestCase):
    """Truncated figures come with an explanation."""

    def test_future_dated_entries_are_announced(self):
        _, report = build(as_of=date(2026, 9, 30))

        self.assertEqual(len(report.data_notices), 1)
        self.assertIn("4.1", report.data_notices[0])
        self.assertIn("2026-12-01", report.data_notices[0])
        self.assertIn("Data Notices", report.render_text())

    def test_no_notice_when_nothing_is_excluded(self):
        _, report = build(as_of=date(2026, 12, 1))

        self.assertEqual(report.data_notices, [])
        self.assertNotIn("Data Notices", report.render_text())


class TestRenderedValues(unittest.TestCase):
    """The rendered report shows what the report model holds."""

    def test_milestone_shows_no_duration(self):
        _, report = build(as_of=date(2026, 8, 2))
        schedule = task_of(report, "1.1").schedule_report

        self.assertTrue(schedule.is_milestone())

        text = schedule.render_text()
        self.assertIn("Planned Duration: 0d (milestone)", text)
        self.assertIn("Duration Variance: 0d (milestone)", text)
        self.assertNotIn("1d", text)

    def test_milestone_planned_progress_is_reached_or_not(self):
        _, before = build(as_of=date(2026, 7, 15))
        _, after = build(as_of=date(2026, 8, 2))

        self.assertEqual(
            task_of(before, "1.1").progress_report.planned_progress, 0.0)
        self.assertEqual(
            task_of(after, "1.1").progress_report.planned_progress, 1.0)

    def test_elapsed_duration_is_shown_for_an_unfinished_task(self):
        _, report = build(as_of=date(2026, 8, 10))

        text = task_of(report, "1.2").schedule_report.render_text()
        self.assertIn("Actual Start: 2026-08-02", text)
        self.assertIn("Actual Duration (so far) (Variance): 9d (-1d)", text)

    def test_rendered_values_are_the_derived_values(self):
        _, report = build(as_of=date(2026, 9, 30))

        # $750 invoiced against a $10,000 budget, so 7.5% consumed.
        project_text = (report.budget_report.render_text()
                        + report.progress_report.render_text())
        self.assertIn("Planned Budget: $10,000.00", project_text)
        self.assertIn("Actual Cost: $750.00", project_text)
        self.assertIn("Remaining Budget: $9,250.00", project_text)
        self.assertIn("Budget Consumed: 7.5%", project_text)

        task_text = task_of(report, "1.3").budget_report.render_text()
        self.assertIn("Planned Budget: $5,000.00", task_text)
        self.assertIn("Actual Cost: $0.00", task_text)
        self.assertIn("Remaining Budget: $5,000.00", task_text)

    def test_missing_values_are_not_rendered_as_zero(self):
        _, report = build(as_of=date(2026, 8, 20))
        budget = task_of(report, "4.1").budget_report.render_text()
        progress = task_of(report, "4.1").progress_report.render_text()

        self.assertIn(f"Planned Budget: {NOT_AVAILABLE}", budget)
        self.assertIn("Actual Cost: $150.00", budget)
        self.assertIn(f"Budget Consumed: {NOT_AVAILABLE}", progress)

    def test_zero_is_not_rendered_as_missing(self):
        _, report = build(as_of=date(2026, 8, 18))
        budget = report.budget_report.render_text()

        self.assertIn("Actual Cost: $0.00", budget)
        self.assertNotIn(f"Actual Cost: {NOT_AVAILABLE}", budget)


if __name__ == "__main__":
    unittest.main()
