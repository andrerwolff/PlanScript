import unittest
import textwrap
from datetime import date
from decimal import Decimal

from planscript.exceptions import   ValidationError, ParseError
from planscript.engine.tracker import   TaskEvent, Tracker, EventDirective, TaskStatus
from planscript.parser.parser import Parser

class ValidateTracker(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    def test_tracking_single_line(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1.1 First Task 5d

        ;Tracking
        2026-09-11 1.1 start
        """)

        project = self.parser.parse(plan)

        events = project.tracker.get_tasks_events("1.1")

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].task_id, "1.1")
        self.assertEqual(events[0].directive, EventDirective.START)

    def test_tracking_multiple_entries_same_date(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1.1 First Task 5d
        task 1.2 Second Task 5d
        task 1.3 Third Task 5d

        ;Tracking
        2026-09-11
            1.1 start
            1.2 start
            1.3 start
        """)

        project = self.parser.parse(plan)

        self.assertEqual(len(project.tracker.task_events), 3)

        for task_id in ("1.1", "1.2", "1.3"):
            events = project.tracker.get_tasks_events(task_id)

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].directive, EventDirective.START)

    def test_tracking_entries_inherit_date(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1.1 First Task 5d
        task 1.2 Second Task 5d

        ;Tracking
        2026-09-10 1.2 start
        2026-09-11
            1.1 start
            1.2 progress 50%
        """)

        project = self.parser.parse(plan)

        event_1 = project.tracker.get_tasks_events("1.1")[0]
        event_2 = project.tracker.get_tasks_events("1.2")[1]

        self.assertEqual(event_1.date, event_2.date)
        self.assertEqual(event_1.date.strftime("%Y-%m-%d"), "2026-09-11")

    def test_tracking_entry_without_date_fails(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1.1 First Task 5d

        ;Tracking
            1.1 start
        """)

        with self.assertRaises(ParseError):
            self.parser.parse(plan)

    def test_tracking_mixed_syntax(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1.1 First Task 5d
        task 1.2 Second Task 5d

        ;Tracking
        2026-09-11
            1.1 start
            1.2 start
        2026-09-12 1.1 progress 50%
        """)

        project = self.parser.parse(plan)

        events_1 = project.tracker.get_tasks_events("1.1")
        events_2 = project.tracker.get_tasks_events("1.2")

        self.assertEqual(len(events_1), 2)
        self.assertEqual(len(events_2), 1)

        self.assertEqual(
            events_1[0].date.strftime("%Y-%m-%d"),
            "2026-09-11"
        )
        self.assertEqual(
            events_1[1].date.strftime("%Y-%m-%d"),
            "2026-09-12"
        )

        self.assertEqual(events_1[0].directive, EventDirective.START)
        self.assertEqual(events_1[1].directive, EventDirective.PROGRESS)
        self.assertEqual(events_2[0].directive, EventDirective.START)

    def test_get_all_task_events_orders_by_date(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1.1 First Task 5d
        task 1.2 Second Task 5d

        ;Tracking
        2026-09-12 1.1 start
        2026-09-10 1.2 start
        """)

        project = self.parser.parse(plan)

        events = project.tracker.get_all_task_events()

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].task_id, "1.2")
        self.assertEqual(events[1].task_id, "1.1")

    def test_get_latest_task_event(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1.1 First Task 5d
        task 1.2 Second Task 5d

        ;Tracking
        2026-09-10 1.1 start
        2026-09-12 1.2 start
        """)

        project = self.parser.parse(plan)

        latest = project.tracker.get_latest_task_event()

        self.assertEqual(latest.task_id, "1.2")
        self.assertEqual(latest.date.strftime("%Y-%m-%d"), "2026-09-12")

    def test_get_latest_task_event_without_events(self):
        project = self.parser.parse("project: Test\n")

        self.assertIsNone(project.tracker.get_latest_task_event())

class TestTaskState(unittest.TestCase):

    def setUp(self):
            self.parser = Parser()

    def test_start(self):
        plan = textwrap.dedent("""\
            project: Test

            task 1.1 First Task 5d

            ;Tracking
            2026-09-11 1.1 start
            """)

        project = self.parser.parse(plan)
        state = project.tracker.get_task_state("1.1")

        self.assertEqual(state.status, TaskStatus.STARTED)
        self.assertEqual(state.percent_complete, 0)

    def test_start_twice_raises_error(self):
        plan = textwrap.dedent("""\
            project: Test

            task 1.1 First Task 5d

            ;Tracking
            2026-09-11 1.1 start
            2026-09-12 1.1 start
            """)

        with self.assertRaises(ValidationError):
            project = self.parser.parse(plan)
            #project.tracker.get_task_state("1.1")

    def test_start_then_progress_zero(self):
        plan = textwrap.dedent("""\
            project: Test

            task 1.1 First Task 5d

            ;Tracking
            2026-09-11 1.1 start
            2026-09-12 1.1 progress 0%
            """)

        project = self.parser.parse(plan)
        state = project.tracker.get_task_state("1.1")

        self.assertEqual(state.status, TaskStatus.IN_PROGRESS)
        self.assertEqual(state.percent_complete, 0)

    def test_start_then_progress_25(self):
        plan = textwrap.dedent("""\
            project: Test

            task 1.1 First Task 5d

            ;Tracking
            2026-09-11 1.1 start
            2026-09-12 1.1 progress 25%
            """)

        project = self.parser.parse(plan)
        state = project.tracker.get_task_state("1.1")

        self.assertEqual(state.status, TaskStatus.IN_PROGRESS)
        self.assertEqual(state.percent_complete, 25)

    def test_progress_before_start_raises_error(self):
        plan = textwrap.dedent("""\
            project: Test

            task 1.1 First Task 5d

            ;Tracking
            2026-09-11 1.1 progress 25%
            """)
        
        with self.assertRaises(ValidationError):
            project = self.parser.parse(plan)
            #project.tracker.get_task_state("1.1")

    def test_progress_after_complete_raises_error(self):
        plan = textwrap.dedent("""\
            project: Test

            task 1.1 First Task 5d

            ;Tracking
            2026-09-11 1.1 start
            2026-09-12 1.1 complete
            2026-09-13 1.1 progress 25%
            """)

        with self.assertRaises(ValidationError):
            project = self.parser.parse(plan)
            #project.tracker.get_task_state("1.1")

    def test_complete(self):
        plan = textwrap.dedent("""\
            project: Test

            task 1.1 First Task 5d

            ;Tracking
            2026-09-10 1.1 start
            2026-09-11 1.1 complete
            """)

        project = self.parser.parse(plan)
        state = project.tracker.get_task_state("1.1")

        self.assertEqual(state.status, TaskStatus.COMPLETED)
        self.assertEqual(state.percent_complete, 100)

    def test_complete_twice_raises_error(self):
        plan = textwrap.dedent("""\
            project: Test

            task 1.1 First Task 5d

            ;Tracking
            2026-09-11 1.1 complete
            2026-09-12 1.1 complete
            """)

        

        with self.assertRaises(ValidationError):
            project = self.parser.parse(plan)
            #project.tracker.get_task_state("1.1")

    def test_note_does_not_change_state(self):
        plan = textwrap.dedent("""\
            project: Test

            task 1.1 First Task 5d

            ;Tracking
            2026-09-11 1.1 start
            2026-09-12 1.1 note Some note
            """)

        project = self.parser.parse(plan)
        state = project.tracker.get_task_state("1.1")

        self.assertEqual(state.status, TaskStatus.STARTED)
        self.assertEqual(state.percent_complete, 0)

    def test_progress_over_100_raises_error(self):
        plan = textwrap.dedent("""\
            project: Test

            task 1.1 First Task 5d

            ;Tracking
            2026-09-11 1.1 start
            2026-09-12 1.1 progress 101%
            """)

        with self.assertRaises(ValidationError):
            project = self.parser.parse(plan)
            #project.tracker.get_task_state("1.1")


class ValidateActualCost(unittest.TestCase):
    """Actual cost is the invoiced amount, rolled up through summary tasks.

    A task's cost includes the amounts invoiced directly to it, even when it is
    a summary task. A summary task also includes the costs of its descendants,
    so a charge made directly to a summary is additional to the charges beneath
    it.
    """

    def setUp(self):
        self.parser = Parser()
        self.as_of = date(2026, 6, 30)

    def test_leaf_task_cost(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1 Summary
        task 1.1 First 5d
        task 1.2 Second 5d

        ;Tracking
        2026-06-01 invoice $100
            1.1 $100
        """)

        project = self.parser.parse(plan)

        self.assertEqual(project.tracker.actual_cost("1.1", self.as_of), Decimal("100"))
        self.assertEqual(project.tracker.actual_cost("1.2", self.as_of), Decimal("0"))

    def test_summary_task_rolls_up_descendants(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1 Summary
        task 1.1 First 5d
        task 1.2 Second 5d

        ;Tracking
        2026-06-01 invoice $200
            1.1 $125
            1.2 $75
        """)

        project = self.parser.parse(plan)

        self.assertEqual(project.tracker.actual_cost("1", self.as_of), Decimal("200"))

    def test_direct_charge_to_summary_is_additional(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1 Summary
        task 1.1 First 5d
        task 1.2 Second 5d

        ;Tracking
        2026-06-01 invoice $300
            1 $100
            1.1 $100
            1.2 $100
        """)

        project = self.parser.parse(plan)

        self.assertEqual(project.tracker.actual_cost("1.1", self.as_of), Decimal("100"))
        self.assertEqual(project.tracker.actual_cost("1.2", self.as_of), Decimal("100"))
        self.assertEqual(project.tracker.actual_cost("1", self.as_of), Decimal("300"))

    def test_nested_summary_rolls_up_to_root(self):
        plan = textwrap.dedent("""\
        project: Test

        task 2 Outer
        task 2.1 Inner
        task 2.1.1 Leaf 5d
        task 2.2 Sibling 5d

        ;Tracking
        2026-06-01 invoice $150
            2.1 $50
            2.1.1 $50
            2.2 $50
        """)

        project = self.parser.parse(plan)

        self.assertEqual(project.tracker.actual_cost("2.1.1", self.as_of), Decimal("50"))
        self.assertEqual(project.tracker.actual_cost("2.1", self.as_of), Decimal("100"))
        self.assertEqual(project.tracker.actual_cost("2.2", self.as_of), Decimal("50"))
        self.assertEqual(project.tracker.actual_cost("2", self.as_of), Decimal("150"))

    def test_cost_excludes_invoices_after_as_of(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1 Summary
        task 1.1 First 5d

        ;Tracking
        2026-06-01 invoice $100
            1.1 $100
        2026-07-01 invoice $50
            1 $50
        """)

        project = self.parser.parse(plan)

        self.assertEqual(project.tracker.actual_cost("1", date(2026, 6, 30)), Decimal("100"))
        self.assertEqual(project.tracker.actual_cost("1", date(2026, 7, 31)), Decimal("150"))

    def test_cost_without_a_date_uses_today(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1.1 First 5d

        ;Tracking
        2026-06-01 invoice $100
            1.1 $100
        """)

        project = self.parser.parse(plan)

        # The only invoice predates any run of this test.
        self.assertEqual(project.tracker.actual_cost("1.1"), Decimal("100"))

    def test_root_costs_sum_to_invoiced_total(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1 Summary
        task 1.1 First 5d
        task 1.2 Second 5d
        task 2 Other Summary
        task 2.1 Third 5d

        ;Tracking
        2026-06-01 invoice $300
            1 $100
            1.1 $100
            2.1 $100
        """)

        project = self.parser.parse(plan)

        roots = project.tracker.hierarchy.get_roots()
        rolled_up = sum((project.tracker.actual_cost(task_id, self.as_of)
                         for task_id in roots), Decimal("0"))
        invoiced = sum((invoice.invoice_amount
                        for invoice in project.tracker.invoice_events), Decimal("0"))

        self.assertEqual(project.tracker.actual_cost("1", self.as_of), Decimal("200"))
        self.assertEqual(project.tracker.actual_cost("2", self.as_of), Decimal("100"))
        self.assertEqual(rolled_up, invoiced)