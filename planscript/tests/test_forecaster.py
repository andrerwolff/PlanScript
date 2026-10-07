"""Tests for the Forecaster: a forecast schedule derived from actuals.

The Forecaster builds a throwaway copy of the project in which every task's
remaining duration and constraints are derived from tracking state at a single
data date (`as_of`):

* completed tasks keep no duration and are pinned to their actual finish
  (mandatory finish),
* every unfinished task - started, in progress, or not started - keeps its
  remaining duration, `(1 - percent_complete) * planned`, floored at the data
  date (start-no-earlier-than), so remaining work projects forward from the
  data date and an open task never forecasts a finish before it,
* summary tasks carry no duration and take no constraint.

The forecast is scheduled by the normal CPM Scheduler, so dependencies, lag,
milestones, and summary rollups behave exactly as they do for the plan. The
source project must never be modified: forecasts are derived information.

Edge cases pinned here: a data date before the project start (the floor must
not pull work earlier than the network), a data date with no `as_of` (no floor
is applied), a future data date with future actuals (the pin must still land),
a bare `start` event versus `progress 0%` (identical forecasts), 100% progress
without `complete`, fractional remaining duration, an out-of-order actual the
finished-work pin cannot accommodate (raises `SchedulingError`), an
out-of-order start the floor absorbs, and a project without a start date.

Constraint-level tests read `_build_forecast_project` directly because the
built forecast project is discarded by `forecast()`; everything else asserts
the forecast schedule, which is what callers actually consume.
"""

import unittest
import textwrap
from datetime import date, timedelta

from planscript.engine.forecaster import Forecaster
from planscript.engine.parser import Parser
from planscript.engine.scheduler import Scheduler
from planscript.exceptions import SchedulingError, ValidationError
from planscript.model.constraint import ConstraintType
from planscript.model.dependency import DependencyType
from planscript.model.schedule import Schedule


FIXTURE = textwrap.dedent("""\
    project: Forecast Fixture
        start: 2026-08-01
        finish: 2026-11-30

    task 1 Work Stream
    task 1.1 Done First 5d
    task 1.2 Doing Now 10d
        depends 1.1
    task 1.3 Not Yet 4d
        depends 1.2 SS +2d
    task 1.4 Gate 0d
        depends 1.3

    ;Tracking:
    2026-08-01 1.1 start
    2026-08-03 1.1 complete
    2026-08-04 1.2 start
    2026-08-08 1.2 progress 40%
    """)

AS_OF = date(2026, 8, 10)


def parse_plan(plan_text=FIXTURE):
    """Parse a plan and calculate its planned schedule, as reporting does."""

    project = Parser().parse(plan_text)
    project.schedule = Scheduler().calculate(project)
    return project


def build_forecast(project, as_of=AS_OF):
    """Return the forecast project and its schedule at a data date."""

    forecast_project = Forecaster()._build_forecast_project(project, as_of)
    schedule = Scheduler().calculate(forecast_project)
    return forecast_project, schedule


def constraints_of(forecast_project):
    """Map task number -> (ConstraintType, date) on the forecast project."""

    return {constraint.task.number: (constraint.con_type, constraint.con_date)
            for constraint in forecast_project.constraints}


class TestForecastStatusMapping(unittest.TestCase):
    """Tracking state at the data date decides duration and pin."""

    def setUp(self):
        self.project = parse_plan()
        self.forecast, self.schedule = build_forecast(self.project)

    def test_completed_task_keeps_no_duration_and_pins_its_actual_finish(self):
        forecast_task = self.forecast.tasks["1.1"]
        self.assertEqual(forecast_task.duration, timedelta(0))
        self.assertEqual(constraints_of(self.forecast)["1.1"],
                         (ConstraintType.MANDATORY_FINISH, date(2026, 8, 3)))

        # The forecast milestone lands on the actual finish, not the plan's.
        self.assertEqual(self.schedule.start_dates["1.1"], date(2026, 8, 3))
        self.assertEqual(self.schedule.finish_dates["1.1"], date(2026, 8, 3))

    def test_in_progress_task_forecasts_its_remaining_duration(self):
        forecast_task = self.forecast.tasks["1.2"]

        # 40% of the 10d plan is done, so 6d remains, projected forward from
        # the data date rather than replayed from the actual start of
        # 2026-08-04: the stall counts, and the finish lands after the data
        # date.
        self.assertEqual(forecast_task.duration, timedelta(days=6))
        self.assertEqual(constraints_of(self.forecast)["1.2"],
                         (ConstraintType.START_NO_EARLIER_THAN, AS_OF))
        self.assertEqual(self.schedule.start_dates["1.2"], AS_OF)
        self.assertEqual(self.schedule.finish_dates["1.2"], date(2026, 8, 15))

    def test_not_started_task_is_floored_at_the_data_date(self):
        forecast_task = self.forecast.tasks["1.3"]

        self.assertEqual(forecast_task.duration, timedelta(days=4))
        self.assertEqual(constraints_of(self.forecast)["1.3"],
                         (ConstraintType.START_NO_EARLIER_THAN, AS_OF))
        # The floor is recorded but not binding here: the SS +2d link from
        # 1.2's data-date start (2026-08-10) pushes 1.3 to 2026-08-12.
        self.assertEqual(self.schedule.start_dates["1.3"], date(2026, 8, 12))

    def test_not_started_milestone_keeps_zero_duration(self):
        forecast_task = self.forecast.tasks["1.4"]

        self.assertEqual(forecast_task.duration, timedelta(0))
        self.assertEqual(constraints_of(self.forecast)["1.4"],
                         (ConstraintType.START_NO_EARLIER_THAN, AS_OF))
        # The network still places the gate after its predecessor: the floor
        # is a floor, not a pin.
        self.assertEqual(self.schedule.start_dates["1.4"], date(2026, 8, 16))

    def test_summary_task_carries_no_duration_and_no_constraint(self):
        forecast_task = self.forecast.tasks["1"]

        self.assertIsNone(forecast_task.duration)
        self.assertNotIn("1", constraints_of(self.forecast))

        # Summary dates roll up from the forecast descendants.
        self.assertEqual(self.schedule.start_dates["1"], date(2026, 8, 3))
        self.assertEqual(self.schedule.finish_dates["1"], date(2026, 8, 16))

    def test_bare_start_and_zero_progress_forecast_identically(self):
        # Typing `progress 0%` must not change the forecast: both tasks
        # started on 2026-08-02 with nothing reported done.
        plan = textwrap.dedent("""\
            project: Start Invariance
                start: 2026-08-01

            task 1.1 Bare Start 5d
            task 1.2 Progress Zero 5d

            ;Tracking:
            2026-08-02 1.1 start
            2026-08-02 1.2 start
            2026-08-02 1.2 progress 0%
            """)
        project = parse_plan(plan)
        _, schedule = build_forecast(project, as_of=date(2026, 8, 6))

        self.assertEqual(schedule.start_dates["1.1"], schedule.start_dates["1.2"])
        self.assertEqual(schedule.finish_dates["1.1"], schedule.finish_dates["1.2"])
        # Both floor at the data date and run the full 5d from there.
        self.assertEqual(schedule.finish_dates["1.1"], date(2026, 8, 10))


class TestForecastPreservesThePlan(unittest.TestCase):
    """The forecast reuses the plan's structure without rewriting it."""

    def setUp(self):
        self.project = parse_plan()
        self.forecast, self.schedule = build_forecast(self.project)

    def test_forecast_is_a_schedule(self):
        self.assertIsInstance(self.schedule, Schedule)

    def test_task_numbers_are_carried_over(self):
        self.assertEqual(set(self.forecast.tasks), set(self.project.tasks))

    def test_forecast_names_are_prefixed_and_the_source_is_untouched(self):
        self.assertEqual(self.forecast.tasks["1.2"].name, "f_Doing Now")
        self.assertEqual(self.project.tasks["1.2"].name, "Doing Now")

    def test_forecasting_does_not_modify_the_source_project(self):
        planned_schedule = self.project.schedule

        build_forecast(self.project)

        self.assertEqual(self.project.constraints, [])
        self.assertEqual(self.project.tasks["1.2"].duration, timedelta(days=10))
        self.assertIs(self.project.schedule, planned_schedule)

    def test_dependencies_are_carried_with_type_and_lag(self):
        dependencies = {(dep.predecessor.number, dep.successor.number): dep
                        for dep in self.forecast.dependencies}

        self.assertEqual(len(dependencies), len(self.project.dependencies))

        ss_lagged = dependencies[("1.2", "1.3")]
        self.assertIs(ss_lagged.dep_type, DependencyType.START_START)
        self.assertEqual(ss_lagged.lag, timedelta(days=2))
        self.assertEqual(ss_lagged.lag_unit, "d")

        finish_start = dependencies[("1.1", "1.2")]
        self.assertIs(finish_start.dep_type, DependencyType.FINISH_START)
        self.assertEqual(finish_start.lag, timedelta(0))


class TestDataDateEdgeCases(unittest.TestCase):
    """The data date drives the floor, the pins, and what gets floored at all."""

    def test_data_date_before_the_project_start_forecasts_the_plan(self):
        # A floor before the network's own dates must not pull work earlier
        # than the plan: every forecast date equals the planned date.
        project = parse_plan()

        forecast = Forecaster().forecast(project, date(2026, 7, 15))

        self.assertEqual(forecast.start_dates, project.schedule.start_dates)
        self.assertEqual(forecast.finish_dates, project.schedule.finish_dates)

    def test_no_data_date_leaves_unfinished_work_unfloored(self):
        # Without an as_of there is no data date to floor remaining work at,
        # so only finished work carries its history pin.
        project = parse_plan()

        forecast_project = Forecaster()._build_forecast_project(project, None)
        constraints = constraints_of(forecast_project)

        self.assertIn("1.1", constraints)  # completed -> mandatory finish
        self.assertNotIn("1.2", constraints)  # in progress -> nothing to floor at
        self.assertNotIn("1.3", constraints)
        self.assertNotIn("1.4", constraints)

        # The forecast still schedules without the floor.
        schedule = Scheduler().calculate(forecast_project)
        self.assertIsNotNone(schedule.start_dates)

    def test_future_data_date_pins_future_actuals(self):
        # Actuals dated after today's wall-clock date still count when the
        # data date says they happened; the pin must not be dropped.
        plan = textwrap.dedent("""\
            project: Future Actuals
                start: 2026-11-02

            task 1.1 Wrap Up 4d

            ;Tracking:
            2026-11-03 1.1 start
            2026-11-06 1.1 complete
            """)
        project = parse_plan(plan)

        forecast_project, schedule = build_forecast(
            project, as_of=date(2026, 11, 13))

        self.assertEqual(constraints_of(forecast_project)["1.1"],
                         (ConstraintType.MANDATORY_FINISH, date(2026, 11, 6)))
        self.assertEqual(schedule.finish_dates["1.1"], date(2026, 11, 6))

    def test_started_task_without_progress_is_floored_not_pinned(self):
        # A bare `start` event forecasts like any unfinished work: the full
        # planned duration, no earlier than the data date. Its actual start
        # anchors history, not the projection.
        plan = textwrap.dedent("""\
            project: Started Only
                start: 2026-08-01

            task 1.1 Waiting 3d

            ;Tracking:
            2026-08-02 1.1 start
            """)
        project = parse_plan(plan)
        as_of = date(2026, 8, 6)

        forecast_project, schedule = build_forecast(project, as_of)

        self.assertEqual(forecast_project.tasks["1.1"].duration, timedelta(days=3))
        self.assertEqual(constraints_of(forecast_project)["1.1"],
                         (ConstraintType.START_NO_EARLIER_THAN, as_of))
        self.assertEqual(schedule.start_dates["1.1"], as_of)


class TestProgressEdgeCases(unittest.TestCase):
    """Progress values map to remaining duration exactly."""

    PROGRESS_FIXTURE = textwrap.dedent("""\
        project: Progress Edges
            start: 2026-08-01

        task 1.1 Fully Progressed 10d
        task 1.2 Fractional Left 10d

        ;Tracking:
        2026-08-01 1.1 start
        2026-08-05 1.1 progress 100%
        2026-08-02 1.2 start
        2026-08-06 1.2 progress 15%
        """)

    def setUp(self):
        self.project = parse_plan(self.PROGRESS_FIXTURE)
        self.as_of = date(2026, 8, 7)
        self.forecast, self.schedule = build_forecast(self.project, self.as_of)

    def test_progress_of_one_hundred_percent_leaves_no_duration(self):
        # `progress 100%` is not `complete`: nothing remains to schedule, and
        # the still-open task forecasts from the data date, not in the past.
        forecast_task = self.forecast.tasks["1.1"]

        self.assertEqual(forecast_task.duration, timedelta(0))
        self.assertEqual(constraints_of(self.forecast)["1.1"],
                         (ConstraintType.START_NO_EARLIER_THAN, self.as_of))
        self.assertEqual(self.schedule.start_dates["1.1"], self.as_of)
        self.assertEqual(self.schedule.finish_dates["1.1"], self.as_of)

    def test_fractional_remaining_duration_is_kept_exactly(self):
        # 15% of 10d leaves 8.5d; the forecast duration must not be rounded
        # away by whole-day calendar arithmetic.
        forecast_task = self.forecast.tasks["1.2"]
        remaining = timedelta(days=8, hours=12)

        self.assertEqual(forecast_task.duration, remaining)
        self.assertEqual(self.schedule.early_finish["1.2"]
                         - self.schedule.early_start["1.2"], remaining)


class TestForecastFailureModes(unittest.TestCase):
    """Failures surface loudly instead of silently forecasting a fiction."""

    def test_scheduling_error_when_the_network_cannot_hold_an_actual(self):
        # The successor finished on 2026-08-05 while its predecessor never
        # started; the predecessor's floor pushes past the pinned finish, so
        # the network cannot accommodate the actual.
        plan = textwrap.dedent("""\
            project: Out Of Order
                start: 2026-08-01

            task 1 Pred 5d
            task 2 Succ 3d
                depends 1

            ;Tracking:
            2026-08-03 2 start
            2026-08-05 2 complete
            """)
        project = parse_plan(plan)

        with self.assertRaisesRegex(SchedulingError,
                                    "violates mandatory finish constraint"):
            Forecaster().forecast(project, date(2026, 8, 6))

    def test_out_of_order_start_is_absorbed_by_the_floor(self):
        # The successor started while its predecessor has not. Open work is
        # never pinned, so the floor absorbs the contradiction and the
        # forecast stays feasible instead of failing the report.
        plan = textwrap.dedent("""\
            project: Out Of Order Start
                start: 2026-08-01

            task 1 Pred 5d
            task 2 Succ 3d
                depends 1

            ;Tracking:
            2026-08-02 2 start
            """)
        project = parse_plan(plan)

        forecast = Forecaster().forecast(project, date(2026, 8, 6))

        # The predecessor floors at the data date (finishing 2026-08-10), so
        # the successor runs after it: 2026-08-11 .. 2026-08-13.
        self.assertEqual(forecast.finish_dates["2"], date(2026, 8, 13))
        self.assertGreaterEqual(forecast.finish_dates["2"], date(2026, 8, 6))

    def test_dateless_project_forecasts_without_calendar_dates(self):
        plan = textwrap.dedent("""\
            project: No Dates
            task 1.1 Work 3d
            """)
        project = Parser().parse(plan)

        # No data date means no floor, so no constraint needs a calendar
        # anchor and the forecast stays calculated-only like the plan.
        forecast = Forecaster().forecast(project)

        self.assertIsNone(forecast.start_dates)
        self.assertEqual(forecast.duration, timedelta(days=3))

    def test_dateless_project_with_a_data_date_raises(self):
        plan = textwrap.dedent("""\
            project: No Dates
            task 1.1 Work 3d
            """)
        project = Parser().parse(plan)

        with self.assertRaisesRegex(ValidationError, "without a start date"):
            Forecaster().forecast(project, date(2026, 8, 10))


if __name__ == "__main__":
    unittest.main()

