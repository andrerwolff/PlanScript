import unittest
import textwrap

from planscript.cli.exceptions import   ValidationError, ParseError
from planscript.engine.tracker import   TrackingEvent, Tracker, EventDirective
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

        events = project.tracker.get_task_events("1.1")

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

        self.assertEqual(len(project.tracker.events), 3)

        for task_id in ("1.1", "1.2", "1.3"):
            events = project.tracker.get_task_events(task_id)

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].directive, EventDirective.START)


    def test_tracking_entries_inherit_date(self):
        plan = textwrap.dedent("""\
        project: Test

        task 1.1 First Task 5d
        task 1.2 Second Task 5d

        ;Tracking
        2026-09-11
            1.1 start
            1.2 progress 50%
        """)

        project = self.parser.parse(plan)

        event_1 = project.tracker.get_task_events("1.1")[0]
        event_2 = project.tracker.get_task_events("1.2")[0]

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

        events_1 = project.tracker.get_task_events("1.1")
        events_2 = project.tracker.get_task_events("1.2")

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