import unittest
import textwrap
from datetime import date, timedelta

from planscript.exceptions import   ValidationError, ParseError
from planscript.engine.scheduler import Scheduler
from planscript.engine.analyzer import Analyzer
from planscript.engine.parser import Parser
from planscript.engine.budgeter import Budgeter
from decimal import Decimal

class ValidatePerformance(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    def test_negative_start_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2027-01-01
        
                task 1.1 First Task 5d
                task 1.2 Second Task 6d
                    depends 1.1
                task 1.3 Third Task 5d
                    depends 1.2 +5d
        
                ;Tracking
                2026-01-05 1.2 start
                """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)
        analysis = Analyzer(project)

        self.assertEqual(-1, analysis.start_variance("1.2").days)

    def test_positive_start_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2027-01-01
        
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
        analysis = Analyzer(project)
        
        self.assertEqual(2, analysis.start_variance("1.2").days)

    def test_zero_start_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2027-01-01
        
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
        analysis = Analyzer(project)

        self.assertEqual(0, analysis.start_variance("1.1").days)
        self.assertEqual(0, analysis.start_variance("1.2").days)

    def test_none_start_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2027-01-01
        
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
        analysis = Analyzer(project)

        self.assertIsNone(analysis.start_variance("1.2"))


    def test_negative_finish_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2027-01-01
        
                task 1.1 First Task 5d
                task 1.2 Second Task 6d
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
        analysis = Analyzer(project)

        self.assertEqual(-1, analysis.finish_variance("1.1").days)

    def test_positive_finish_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2027-01-01
        
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
        analysis = Analyzer(project)

        self.assertEqual(2, analysis.finish_variance("1.1").days)

    def test_zero_finish_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2027-01-01
        
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
        analysis = Analyzer(project)

        self.assertEqual(0, analysis.finish_variance("1.1").days)

    def test_none_finish_variance(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01
                    finish: 2027-01-01
        
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
        analysis = Analyzer(project)

        self.assertIsNone(analysis.finish_variance("1.1"))


    def test_summary_earliest_starts(self):
        plan = textwrap.dedent("""\
            project: Test
                start: 2026-01-01
                finish: 2027-01-01
    
            task 1 Summary
            task 1.1 First Task 5d
            task 1.2 Second Task 6d
                depends 1.1
            task 2 Summary(2)
            task 2.1 Third Task 7d
                depends 1.2 +5d
            task 2.2 Fourth Task 2d
                depends 2.1
    
            ;Tracking
            2026-01-01 1.1 start
            2026-01-06 1.2 start
            2026-01-17 2.1 start
            2026-01-21 2.2 start
            """)

        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(date(2026,1,1), project.tracker.actual_start("1"))
        self.assertEqual(date(2026,1,17), project.tracker.actual_start("2"))
        
    def test_summary_latest_finishes(self):
        plan = textwrap.dedent("""\
            project: Test
                start: 2026-01-01
                finish: 2027-01-01
    
            task 1 Summary
            task 1.1 First Task 5d
            task 1.2 Second Task 6d
                depends 1.1
            task 2 Summary(2)
            task 2.1 Third Task 7d
                depends 1.2 +5d
            task 2.2 Fourth Task 2d
                depends 2.1
    
            ;Tracking
            2026-01-01 1.1 start
            2026-01-06 1.2 start
            2026-01-17 2.1 start
            2026-01-21 2.2 start
            2026-01-05 1.1 complete
            2026-01-12 1.2 complete
            2026-01-21 2.1 complete
            2026-01-24 2.2 complete
            """)

        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(date(2026,1,12), project.tracker.actual_finish("1"))
        self.assertEqual(date(2026,1,24), project.tracker.actual_finish("2"))

    def test_nested_summary(self):
        plan = textwrap.dedent("""\
            project: Test
                start: 2026-01-01
                finish: 2027-01-01
    
            task 1 Summary
            task 1.1 Sub Summary
            task 1.1.1 First Task 5d
            task 1.1.2 Second Task 6d
                depends 1.1.1
            task 1.2 interim task 1d
            task 2 Summary(2)
            task 2.1 Third Task 7d
                depends 1.2 +5d
            task 2.2 Fourth Task 2d
                depends 2.1
    
            ;Tracking
            2026-01-03 1.1.1 start
            2026-01-06 1.1.2 start
            2026-01-08 1.2 start
            2026-01-17 2.1 start
            2026-01-21 2.2 start
            2026-01-05 1.1.1 complete
            2026-01-12 1.1.2 complete
            2026-01-15 1.2 complete
            2026-01-21 2.1 complete
            2026-01-24 2.2 complete
            """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(date(2026,1,3), project.tracker.actual_start("1"))
        self.assertEqual(date(2026,1,3), project.tracker.actual_start("1.1"))
        self.assertEqual(date(2026,1,15), project.tracker.actual_finish("1"))
        self.assertEqual(date(2026,1,12), project.tracker.actual_finish("1.1"))

    def test_summary_no_tracked_child(self):
        plan = textwrap.dedent("""\
            project: Test
                start: 2026-01-01
                finish: 2027-01-01
    
            task 1 Summary
            task 1.1 Sub Summary
            task 1.1.1 First Task 5d
            task 1.1.2 Second Task 6d
                depends 1.1.1
            task 1.2 interim task 1d
            task 2 Summary(2)
            task 2.1 Third Task 7d
                depends 1.2 +5d
            task 2.2 Fourth Task 2d
                depends 2.1
    
            ;Tracking
            2026-01-17 2.1 start
            2026-01-21 2.2 start
            2026-01-21 2.1 complete
            2026-01-24 2.2 complete
            """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertIsNone(project.tracker.actual_start("1"))
        
    def test_summary_partial_tracked_child(self):
        plan = textwrap.dedent("""\
            project: Test
                start: 2026-01-01
                finish: 2027-01-01
    
            task 1 Summary
            task 1.1 Sub Summary
            task 1.1.1 First Task 5d
            task 1.1.2 Second Task 6d
                depends 1.1.1
            task 1.2 interim task 1d
            task 2 Summary(2)
            task 2.1 Third Task 7d
                depends 1.2 +5d
            task 2.2 Fourth Task 2d
                depends 2.1
    
            ;Tracking
            2026-01-06 1.1.2 start
            2026-01-08 1.2 start
            2026-01-17 2.1 start
            2026-01-21 2.2 start
            2026-01-12 1.1.2 complete
            2026-01-21 2.1 complete
            2026-01-24 2.2 complete
            """)
        
        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(date(2026,1,6), project.tracker.actual_start("1"))

        self.assertIsNone(project.tracker.actual_finish("1"))

    def test_multi_tracked_project(self):
        plan = textwrap.dedent("""\
            project: Variance Test Project
                start: 2026-10-01
                finish: 2026-11-30

            task 1 Project Management
            task 1.1 Kickoff 0d
            task 1.2 Project Plan 5d
                depends 1.1

            task 2 Design
            task 2.1 Preliminary Design
            task 2.1.1 Site Layout 5d
                depends 1.2
            task 2.1.2 Utility Design 10d
                depends 2.1.1
            task 2.2 Final Design 5d
                depends 2.1.2

            task 3 Construction
            task 3.1 Mobilization 3d
                depends 2.2
            task 3.2 Installation 15d
                depends 3.1 FS 0d
            task 3.3 Inspection 0d
                depends 3.2 FS 0d
            task 3.4 Closeout 5d
                depends 3.3 FS 0d

            task 4 Untracked Work
            task 4.1 Future Task 10d
                depends 2.2

            ;Tracking:
            2026-10-01
                1.1 start
                1.1 complete

            2026-10-03 1.2 start
            2026-10-09 1.2 progress 60%
            2026-10-12 1.2 complete
            2026-10-13
                2.1.1 start
                2.1.1 complete

            2026-10-15 2.1.2 start
            2026-10-24 2.1.2 complete
            2026-10-25 2.2 start

            2026-10-31 2.2 complete
            2026-11-03 3.1 start
            2026-11-05
                3.1 complete
            2026-11-06 3.2 start
            2026-11-20
                3.2 progress 75%
            2026-11-25 3.2 complete

            2026-11-26
                3.3 start
                3.3 complete
            2026-11-27 3.4 start
        """)

        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)
        analysis = Analyzer(project)

        self.assertEqual(date(2026,10,1), project.tracker.actual_start("1.1"))
        self.assertEqual(0, analysis.start_variance("1.1").days)
        self.assertEqual(0, analysis.duration_variance("1.1").days)

        self.assertEqual(date(2026,10,3), project.tracker.actual_start("1.2"))
        self.assertEqual(2, analysis.start_variance("1.2").days)
        self.assertEqual(7, analysis.finish_variance("1.2").days)
        self.assertEqual(5, analysis.duration_variance("1.2").days)

        # On-time milestone
        self.assertEqual(analysis.start_variance("1.1").days, 0)
        self.assertEqual(analysis.finish_variance("1.1").days, 0) #fix

        # Late start and finish
        self.assertEqual(analysis.start_variance("1.2").days, 2)
        self.assertEqual(analysis.finish_variance("1.2").days, 7) # check

        # Nested leaf task — started/finished late
        self.assertEqual(analysis.start_variance("2.1.1").days, 7)
        self.assertEqual(analysis.finish_variance("2.1.1").days, 3)
        self.assertEqual(analysis.start_variance("2.1.2").days, 4)
        self.assertEqual(analysis.finish_variance("2.1.2").days, 4)

        # Summary task — derived actual dates
        self.assertEqual(analysis.start_variance("2.1").days, 7)
        self.assertEqual(analysis.finish_variance("2.1").days, 4)
        self.assertEqual(analysis.duration_variance("2.1").days, -3)

        # Started but not finished
        self.assertEqual(analysis.start_variance("3.4").days, 14)
        self.assertIsNone(analysis.finish_variance("3.4"))

        # Completely untracked
        self.assertIsNone(analysis.start_variance("4.1"))
        self.assertIsNone(analysis.finish_variance("4.1"))

    def test_actual_duration_incomplete_uses_current_date(self):
        plan = textwrap.dedent("""\
            project: Test Project
                start: 2026-10-01

            task 1 Task 1 5d

            ;Tracking
            2026-10-01 1 start
        """)

        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        duration = project.tracker.actual_duration("1", date(2026, 10, 4))

        self.assertEqual(duration, timedelta(days=4))


    def test_actual_duration_complete_uses_finish_date(self):
        plan = textwrap.dedent("""\
            project: Test Project
                start: 2026-10-01

            task 1 Task 1 5d

            ;Tracking
            2026-10-01 1 start
            2026-10-05 1 complete
        """)

        project = self.parser.parse(plan)
        project.schedule = Scheduler().calculate(project)

        duration = project.tracker.actual_duration("1", date(2026, 10, 10))

        self.assertEqual(duration, timedelta(days=5))

class ValidateCostVariance(unittest.TestCase):
    """Cost variance compares actual invoiced cost against the budget.

    Variance is actual minus budget, so positive means over budget. Both the
    per-task and total figures are measured as of a date; invoices after that
    date are excluded.
    """

    def setUp(self):
        self.parser = Parser()
        self.as_of = date(2026, 6, 30)

    def _budgeted(self, plan):
        project = self.parser.parse(plan)
        project.budget = Budgeter().calculate(project)
        return project

    def test_task_cost_variance_is_actual_minus_budget(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01

                task 1 Summary
                task 1.1 First 5d
                    budget $100
                task 1.2 Second 5d
                    budget $50

                ;Tracking
                2026-01-10 invoice $60
                    1.1 $60
                """)

        project = self._budgeted(plan)
        analysis = Analyzer(project, self.as_of)

        self.assertEqual(analysis.cost_variance("1.1"), Decimal("-40"))
        self.assertEqual(analysis.cost_variance("1.2"), Decimal("-50"))
        self.assertEqual(analysis.cost_variance("1"), Decimal("-90"))

    def test_total_cost_variance_is_actual_minus_budget(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01

                task 1 Summary
                task 1.1 First 5d
                    budget $100
                task 1.2 Second 5d
                    budget $50

                ;Tracking
                2026-01-10 invoice $60
                    1.1 $60
                """)

        project = self._budgeted(plan)
        analysis = Analyzer(project, self.as_of)

        self.assertEqual(analysis.total_cost_variance(), Decimal("-90"))

    def test_cost_variance_is_none_without_a_budget(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01

                task 1.1 First 5d

                ;Tracking
                2026-01-10 invoice $60
                    1.1 $60
                """)

        project = self._budgeted(plan)
        analysis = Analyzer(project, self.as_of)

        self.assertIsNone(analysis.cost_variance("1.1"))

    def test_cost_variance_excludes_invoices_after_as_of(self):
        plan = textwrap.dedent("""\
                project: Test
                    start: 2026-01-01

                task 1 Summary
                task 1.1 First 5d
                    budget $100

                ;Tracking
                2026-01-10 invoice $60
                    1.1 $60
                2026-07-15 invoice $40
                    1.1 $40
                """)

        project = self._budgeted(plan)

        june = Analyzer(project, date(2026, 6, 30))
        august = Analyzer(project, date(2026, 8, 1))

        self.assertEqual(june.cost_variance("1.1"), Decimal("-40"))
        self.assertEqual(august.cost_variance("1.1"), Decimal("0"))
        self.assertEqual(june.total_cost_variance(), Decimal("-40"))
        self.assertEqual(august.total_cost_variance(), Decimal("0"))
