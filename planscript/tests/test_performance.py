import unittest
import textwrap

from planscript.cli.exceptions import   ValidationError, ParseError
from planscript.engine.scheduler import Scheduler
from planscript.parser.parser import Parser

class ValidatePerformance(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    def test_negative_start_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2026-01-01
        
                task 1.1 First Task 5d
                task 1.2 Second Task 5d
                    depends 1.1
                task 1.3 Third Task 5d
                    depends 1.2 +5d
        
                ;Tracking
                2026-01-05 1.2 start
                """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(-1, project.start_variance("1.2").days)

    def test_positive_start_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2026-01-01
        
                task 1.1 First Task 5d
                task 1.2 Second Task 5d
                    depends 1.1
                task 1.3 Third Task 5d
                    depends 1.2 +5d
        
                ;Tracking
                2026-01-08 1.2 start
                """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(2, project.start_variance("1.2").days)

    def test_zero_start_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2026-01-01
        
                task 1.1 First Task 5d
                task 1.2 Second Task 5d
                    depends 1.1
                task 1.3 Third Task 5d
                    depends 1.2 +5d
        
                ;Tracking
                2026-01-01 1.1 start
                2026-01-06 1.2 start
                """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(0, project.start_variance("1.1").days)
        self.assertEqual(0, project.start_variance("1.2").days)

    def test_none_start_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2026-01-01
        
                task 1.1 First Task 5d
                task 1.2 Second Task 5d
                    depends 1.1
                task 1.3 Third Task 5d
                    depends 1.2 +5d
        
                ;Tracking
                2026-01-01 1.1 start
                """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertIsNone(project.start_variance("1.2"))


    def test_negative_start_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2026-01-01
        
                task 1.1 First Task 5d
                task 1.2 Second Task 5d
                    depends 1.1
                task 1.3 Third Task 5d
                    depends 1.2 +5d
        
                ;Tracking
                2026-01-01 1.1 start
                2026-01-03 1.1 progress 50%
                2026-01-04 1.1 complete
                """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(-1, project.start_variance("1.1").days)

    def test_positive_start_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2026-01-01
        
                task 1.1 First Task 5d
                task 1.2 Second Task 5d
                    depends 1.1
                task 1.3 Third Task 5d
                    depends 1.2 +5d
        
                ;Tracking
                2026-01-01 1.1 start
                2026-01-03 1.1 progress 50%
                2026-01-07 1.1 complete
                """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(2, project.start_variance("1.1").days)

    def test_zero_finish_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2026-01-01
        
                task 1.1 First Task 5d
                task 1.2 Second Task 5d
                    depends 1.1
                task 1.3 Third Task 5d
                    depends 1.2 +5d
        
                ;Tracking
                2026-01-01 1.1 start
                2026-01-03 1.1 progress 50%
                2026-01-05 1.1 complete
                """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(0, project.finish_variance("1.1").days)

    def test_none_finish_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2026-01-01
        
                task 1.1 First Task 5d
                task 1.2 Second Task 5d
                    depends 1.1
                task 1.3 Third Task 5d
                    depends 1.2 +5d
        
                ;Tracking
                2026-01-01 1.1 start
                """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        print(project.tasks["1.1"].duration)
        print(project.schedule.early_start["1.1"])
        print(project.schedule.start_dates["1.1"])
        print(project.schedule.early_finish["1.1"])
        print(project.schedule.finish_dates["1.1"])

        self.assertIsNone(project.finish_variance("1.1"))
