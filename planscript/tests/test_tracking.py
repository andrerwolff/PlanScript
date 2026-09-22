import unittest
import textwrap

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