import unittest
from datetime import date, timedelta

from planscript.engine.analyzer import Analyzer
from planscript.engine.reporter import ReportBuilder
from planscript.engine.scheduler import Scheduler
from planscript.exceptions import SchedulingError
from planscript.model.project import Project
from planscript.model.task import Task
from planscript.tests import test_projects


class TestSchedulerExamples(unittest.TestCase):

    def test_simple_linear(self):
        project = test_projects.simple_linear()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.duration.days, 14)
        self.assertEqual(schedule.critical_paths, [["1.1", "1.2", "1.3", "1.4"]])

    def test_parallel_work(self):
        project = test_projects.parallel_work()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.duration.days, 5)
        self.assertEqual(schedule.critical_paths, [["1.3"]])
         
    def test_branch_and_merge(self):
        project = test_projects.branch_and_merge()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.duration.days, 11)
        self.assertEqual(schedule.critical_paths, [["1.1", "1.3", "1.5"]])

    def test_complex_network(self):
        project = test_projects.complex_network()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.duration.days, 15)
        self.assertEqual(schedule.critical_paths, [["1.1", "1.3", "1.4", "1.5", "1.6"]])

    def test_multiple_starts_and_ends(self):
        project = test_projects.multiple_starts_and_ends()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.duration.days, 11)
        actual = sorted(schedule.critical_paths)
        expected = sorted([["1.1", "1.3", "1.6"],["1.2", "1.4", "1.6"]])
        self.assertEqual(actual, expected )

    def test_circular_dependency(self):
        project = test_projects.circular_dependency()

        with self.assertRaises(ValueError):
            Scheduler().calculate(project)

    def test_zero_duration(self):
        project = test_projects.zero_duration()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.duration.days, 9)
        self.assertEqual(schedule.critical_paths, [["1.1", "1.2", "1.3"]])

    def test_mixed_dependency(self):
        project = test_projects.mixed_dependency_types()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.duration.days, 10)
        self.assertEqual(schedule.early_start["8.1"].days, 0)
        self.assertEqual(schedule.early_finish["8.1"].days, 4)

        self.assertEqual(schedule.early_start["8.2"].days, 4)
        self.assertEqual(schedule.early_finish["8.2"].days, 10)

        self.assertEqual(schedule.early_start["8.3"].days, 4)
        self.assertEqual(schedule.early_finish["8.3"].days, 9)

        self.assertEqual(schedule.early_start["8.4"].days, 5)
        self.assertEqual(schedule.early_finish["8.4"].days, 9)

        self.assertEqual(schedule.early_start["8.5"].days, 0)
        self.assertEqual(schedule.early_finish["8.5"].days, 3)

    def test_dependency_with_lag(self):
        project = test_projects.dependency_types_with_lag()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.duration.days, 13)
        self.assertEqual(schedule.early_start["9.1"].days, 0)
        self.assertEqual(schedule.early_finish["9.1"].days, 5)

        self.assertEqual(schedule.early_start["9.2"].days, 7)
        self.assertEqual(schedule.early_finish["9.2"].days, 11)

        self.assertEqual(schedule.early_start["9.3"].days, 8)
        self.assertEqual(schedule.early_finish["9.3"].days, 11)

        self.assertEqual(schedule.early_start["9.4"].days, 11)
        self.assertEqual(schedule.early_finish["9.4"].days, 13)

    def test_disconnected_networks(self):
        project = test_projects.disconnected_networks()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.duration.days, 12)
        self.assertEqual(schedule.critical_paths, [["11.3", "11.4"]])

    def test_single_task(self):
        project = test_projects.single_task()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.duration.days, 5)
        self.assertEqual(schedule.critical_paths, [["10.1"]])

    def test_competing_constraints(self):
        project = test_projects.competing_constraints()

        schedule = Scheduler().calculate(project)

        # B's SS relationship:
        # C cannot start before B starts.
        #
        # A's FS relationship:
        # C cannot start before A finishes.
        #
        # The scheduler must use the more restrictive constraint.

        self.assertEqual(schedule.early_start["12.3"].days, 5)
    def test_negative_lag(self):
        project = test_projects.negative_lag()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.early_start["13.2"].days, 3)
        self.assertEqual(schedule.early_finish["13.2"].days, 7)

class TestDependencyTypes(unittest.TestCase):

    def test_finish_start(self):
        project = test_projects.finish_start()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.early_start["D.1"].days, 0)
        self.assertEqual(schedule.early_finish["D.1"].days, 5)

        self.assertEqual(schedule.early_start["D.2"].days, 5)
        self.assertEqual(schedule.early_finish["D.2"].days, 8)

        self.assertEqual(schedule.early_start["D.2"].days, 5)
        self.assertEqual(schedule.early_finish["D.2"].days, 8)

    def test_start_start(self):
        project = test_projects.start_start()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.early_start["D.1"].days, 0)
        self.assertEqual(schedule.early_finish["D.1"].days, 5)

        self.assertEqual(schedule.early_start["D.2"].days, 0)
        self.assertEqual(schedule.early_finish["D.2"].days, 3)

    def test_finish_finish(self):
        project = test_projects.finish_finish()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.early_start["D.1"].days, 0)
        self.assertEqual(schedule.early_finish["D.1"].days, 5)

        self.assertEqual(schedule.early_finish["D.2"].days, 5)
        self.assertEqual(schedule.early_start["D.2"].days, 2)

    def test_start_finish(self):
        project = test_projects.start_finish()

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.early_start["D.1"].days, 0)
        self.assertEqual(schedule.early_finish["D.1"].days, 5)

        self.assertEqual(schedule.early_finish["D.2"].days, 0)
        self.assertEqual(schedule.early_start["D.2"].days, -3)

    def test_redundant(self):
        project = test_projects.tight_redundant()

        result = Scheduler().calculate(project)

        self.assertEqual(result.duration, timedelta(days=15))

        self.assertEqual(result.early_start["1.1"], timedelta(days=0))
        self.assertEqual(result.early_finish["1.1"], timedelta(days=5))

        self.assertEqual(result.early_start["1.2"], timedelta(days=5))
        self.assertEqual(result.early_finish["1.2"], timedelta(days=10))

        self.assertEqual(result.early_start["1.3"], timedelta(days=10))
        self.assertEqual(result.early_finish["1.3"], timedelta(days=15))

        self.assertEqual(result.total_float["1.1"], timedelta(0))
        self.assertEqual(result.total_float["1.2"], timedelta(0))
        self.assertEqual(result.total_float["1.3"], timedelta(0))

        self.assertEqual(result.critical_paths,[["1.1", "1.2", "1.3"]])

    def test_tight_FS(self):
        project = test_projects.tight_FS()

        result = Scheduler().calculate(project)

        self.assertEqual(result.duration, timedelta(days=10))

        self.assertEqual(result.early_start["D.1"], timedelta(days=0))
        self.assertEqual(result.early_finish["D.1"], timedelta(days=5))

        self.assertEqual(result.early_start["D.2"], timedelta(days=5))
        self.assertEqual(result.early_finish["D.2"], timedelta(days=10))

        self.assertEqual(result.total_float["D.1"], timedelta(0))
        self.assertEqual(result.total_float["D.2"], timedelta(0))

        self.assertEqual(result.critical_paths, [["D.1", "D.2"]])

    def test_tight_SS(self):
        project = test_projects.tight_SS()

        result = Scheduler().calculate(project)

        self.assertEqual(result.duration, timedelta(days=5))

        self.assertEqual(result.early_start["D.1"], timedelta(days=0))
        self.assertEqual(result.early_finish["D.1"], timedelta(days=5))

        self.assertEqual(result.early_start["D.2"], timedelta(days=0))
        self.assertEqual(result.early_finish["D.2"], timedelta(days=5))

        self.assertEqual(result.total_float["D.1"], timedelta(0))
        self.assertEqual(result.total_float["D.2"], timedelta(0))

        self.assertEqual(result.critical_paths, [["D.1", "D.2"]])

    def test_tight_FF(self):
        project = test_projects.tight_FF()

        result = Scheduler().calculate(project)

        self.assertEqual(result.duration, timedelta(days=5))

        self.assertEqual(result.early_start["D.1"], timedelta(days=0))
        self.assertEqual(result.early_finish["D.1"], timedelta(days=5))

        self.assertEqual(result.early_start["D.2"], timedelta(days=0))
        self.assertEqual(result.early_finish["D.2"], timedelta(days=5))

        self.assertEqual(result.total_float["D.1"], timedelta(0))
        self.assertEqual(result.total_float["D.2"], timedelta(0))

        self.assertEqual(result.critical_paths, [["D.1", "D.2"]])

    def test_tight_SF(self):
        project = test_projects.tight_SF()

        result = Scheduler().calculate(project)

        self.assertEqual(result.duration, timedelta(days=5))

        self.assertEqual(result.early_start["D.1"], timedelta(days=0))
        self.assertEqual(result.early_finish["D.1"], timedelta(days=5))

        self.assertEqual(result.early_start["D.2"], timedelta(days=-5))
        self.assertEqual(result.early_finish["D.2"], timedelta(days=0))

        self.assertEqual(result.total_float["D.1"], timedelta(0))
        self.assertEqual(result.total_float["D.2"], timedelta(5))

        self.assertEqual(result.critical_paths, [["D.1"]])

    def test_competing_SS(self):
        project = test_projects.competing_SS()

        scheduler = Scheduler()
        
        schedule = scheduler.calculate(project)
        a_to_c = project.dependencies[0]
        b_to_c = project.dependencies[1]


        self.assertTrue(scheduler._dependency_is_tight(project, b_to_c, schedule.early_start, schedule.early_finish))
        self.assertFalse(scheduler._dependency_is_tight(project, a_to_c, schedule.early_start, schedule.early_finish))

        self.assertEqual(schedule.early_start["D.1"], timedelta(days=0))
        self.assertEqual(schedule.early_finish["D.1"], timedelta(days=5))

        self.assertEqual(schedule.early_start["D.2"], timedelta(days=0))
        self.assertEqual(schedule.early_finish["D.2"], timedelta(days=10))

        self.assertEqual(schedule.early_start["D.3"], timedelta(days=5))
        self.assertEqual(schedule.early_finish["D.3"], timedelta(days=10))

        self.assertEqual(schedule.total_float["D.1"], timedelta(days=5))
        self.assertEqual(schedule.total_float["D.2"], timedelta(days=0))
        self.assertEqual(schedule.total_float["D.3"], timedelta(days=0))

        self.assertEqual(schedule.critical_paths, [["D.2", "D.3"]])

    def test_competing_FF(self):
        project = test_projects.competing_FF()
        
        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.early_start["D.1"], timedelta(days=0))
        self.assertEqual(schedule.early_finish["D.1"], timedelta(days=5))

        self.assertEqual(schedule.early_start["D.2"], timedelta(days=0))
        self.assertEqual(schedule.early_finish["D.2"], timedelta(days=10))

        self.assertEqual(schedule.early_start["D.3"], timedelta(days=10))
        self.assertEqual(schedule.early_finish["D.3"], timedelta(days=15))

        self.assertEqual(schedule.total_float["D.1"], timedelta(days=10))
        self.assertEqual(schedule.total_float["D.2"], timedelta(days=0))
        self.assertEqual(schedule.total_float["D.3"], timedelta(days=0))

        self.assertEqual(schedule.critical_paths, [["D.2", "D.3"]])

    def test_competing_SF(self):
        project = test_projects.competing_SF()
        
        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.early_start["D.1"], timedelta(days=0))
        self.assertEqual(schedule.early_finish["D.1"], timedelta(days=5))

        self.assertEqual(schedule.early_start["D.2"], timedelta(days=0))
        self.assertEqual(schedule.early_finish["D.2"], timedelta(days=10))

        self.assertEqual(schedule.early_start["D.3"], timedelta(days=0))
        self.assertEqual(schedule.early_finish["D.3"], timedelta(days=5))

        self.assertEqual(schedule.total_float["D.1"], timedelta(days=5))
        self.assertEqual(schedule.total_float["D.2"], timedelta(days=0))
        self.assertEqual(schedule.total_float["D.3"], timedelta(days=5))

        self.assertEqual(schedule.critical_paths, [["D.2"]])

    def test_dateless_project_is_calculated_only(self):
        project = test_projects.simple_linear()

        schedule = Scheduler().calculate(project)

        self.assertIsNone(schedule.start_dates)
        self.assertIsNone(schedule.finish_dates)
        self.assertEqual(schedule.duration.days, 14)
        self.assertEqual(schedule.critical_paths, [["1.1", "1.2", "1.3", "1.4"]])

    def test_dateless_schedule_rejects_date_consumers(self):
        linear = test_projects.simple_linear()
        linear.schedule = Scheduler().calculate(linear)

        with self.assertRaisesRegex(SchedulingError, "No project start date"):
            ReportBuilder(linear, date(2026, 1, 1), timedelta(days=21)).build()

        budgeted = test_projects.simple_budget()
        budgeted.schedule = Scheduler().calculate(budgeted)

        with self.assertRaisesRegex(SchedulingError, "No project start date"):
            Analyzer(budgeted).duration_variance("1")


class TestSoftConstraints(unittest.TestCase):
    """The four soft constraint types move dates only when they are the
    more restrictive of the constraint and the dependency network."""

    def test_start_no_earlier_than(self):
        project = test_projects.start_no_earlier_than()

        schedule = Scheduler().calculate(project)

        # 14.2's constraint (offset 2) is weaker than its dependency
        # (offset 5), so the dependency wins.
        self.assertEqual(schedule.early_start["14.2"], timedelta(days=5))
        self.assertEqual(schedule.early_finish["14.2"], timedelta(days=8))

        # 14.3's constraint (offset 14) is stronger than its dependency
        # (offset 8), so the constraint wins.
        self.assertEqual(schedule.early_start["14.3"], timedelta(days=14))
        self.assertEqual(schedule.early_finish["14.3"], timedelta(days=18))

        # A binding constraint extends the project duration.
        self.assertEqual(schedule.duration, timedelta(days=18))

        # Offsets project back onto the constraint date.
        self.assertEqual(schedule.start_dates["14.3"], date(2026, 1, 19))
        self.assertEqual(schedule.finish_dates["14.3"], date(2026, 1, 22))

        # The constraint pushes float onto the predecessor chain.
        self.assertEqual(schedule.total_float["14.2"], timedelta(days=6))
        self.assertEqual(schedule.total_float["14.3"], timedelta(days=0))
        self.assertEqual(schedule.critical_paths, [["14.3"]])

    def test_finish_no_earlier_than(self):
        project = test_projects.finish_no_earlier_than()

        schedule = Scheduler().calculate(project)

        # 15.2's constraint (finish no earlier than 2026-01-08) is weaker
        # than its dependency (finish 2026-01-10), so the dependency wins.
        self.assertEqual(schedule.early_start["15.2"], timedelta(days=4))
        self.assertEqual(schedule.early_finish["15.2"], timedelta(days=6))

        # 15.3's constraint (finish no earlier than 2026-01-15) is
        # stronger than its dependency (finish 2026-01-13), so the
        # constraint wins.
        self.assertEqual(schedule.early_start["15.3"], timedelta(days=8))
        self.assertEqual(schedule.early_finish["15.3"], timedelta(days=11))

        # A binding constraint extends the project duration.
        self.assertEqual(schedule.duration, timedelta(days=11))

        # The finish-side date lands exactly on the constraint date.
        self.assertEqual(schedule.start_dates["15.3"], date(2026, 1, 13))
        self.assertEqual(schedule.finish_dates["15.3"], date(2026, 1, 15))

        # The two-day gap after 15.2 leaves it two days of float.
        self.assertEqual(schedule.total_float["15.2"], timedelta(days=2))
        self.assertEqual(schedule.total_float["15.3"], timedelta(days=0))
        self.assertEqual(schedule.critical_paths, [["15.3"]])

    def test_start_no_later_than(self):
        project = test_projects.start_no_later_than()

        schedule = Scheduler().calculate(project)

        # Late-side only: early dates and duration are untouched.
        self.assertEqual(schedule.early_start["16.2"], timedelta(days=3))
        self.assertEqual(schedule.early_finish["16.2"], timedelta(days=7))
        self.assertEqual(schedule.duration, timedelta(days=10))

        # 16.2's constraint (offset 5) binds; its late start would
        # otherwise be the project duration less its duration (6).
        self.assertEqual(schedule.late_start["16.2"], timedelta(days=5))
        self.assertEqual(schedule.late_finish["16.2"], timedelta(days=9))
        self.assertEqual(schedule.total_float["16.2"], timedelta(days=2))

        # 16.1's constraint (offset 4) is weaker than the late start its
        # dependency now imposes (2), so the dependency wins.
        self.assertEqual(schedule.late_start["16.1"], timedelta(days=2))
        self.assertEqual(schedule.late_finish["16.1"], timedelta(days=5))
        self.assertEqual(schedule.total_float["16.1"], timedelta(days=2))

        self.assertEqual(schedule.total_float["16.3"], timedelta(days=0))
        self.assertEqual(schedule.critical_paths, [["16.3"]])

    def test_finish_no_later_than(self):
        project = test_projects.finish_no_later_than()

        schedule = Scheduler().calculate(project)

        # Late-side only: early dates and duration are untouched.
        self.assertEqual(schedule.early_start["17.2"], timedelta(days=3))
        self.assertEqual(schedule.early_finish["17.2"], timedelta(days=7))
        self.assertEqual(schedule.duration, timedelta(days=10))

        # 17.2's constraint (finish no later than 2026-01-13) binds; its
        # late finish would otherwise be the project duration
        # (finish 2026-01-15).
        self.assertEqual(schedule.late_finish["17.2"], timedelta(days=9))
        self.assertEqual(schedule.late_start["17.2"], timedelta(days=5))
        self.assertEqual(schedule.total_float["17.2"], timedelta(days=2))

        # 17.1's constraint (finish no later than 2026-01-11) is weaker
        # than the late finish its dependency now imposes
        # (finish 2026-01-09), so the dependency wins.
        self.assertEqual(schedule.late_finish["17.1"], timedelta(days=5))
        self.assertEqual(schedule.late_start["17.1"], timedelta(days=2))
        self.assertEqual(schedule.total_float["17.1"], timedelta(days=2))

        self.assertEqual(schedule.total_float["17.3"], timedelta(days=0))
        self.assertEqual(schedule.critical_paths, [["17.3"]])

    def test_infeasible_soft_constraint_stays_critical(self):
        project = test_projects.infeasible_finish_no_later_than()

        schedule = Scheduler().calculate(project)

        # The constraint is soft: early dates and duration hold.
        self.assertEqual(schedule.early_start["18.2"], timedelta(days=5))
        self.assertEqual(schedule.early_finish["18.2"], timedelta(days=10))
        self.assertEqual(schedule.duration, timedelta(days=10))

        # The unsatisfiable constraint pulls late dates in and shows up
        # as negative total float on the constrained task and, through
        # the dependency, its predecessor.
        self.assertEqual(schedule.late_finish["18.2"], timedelta(days=6))
        self.assertEqual(schedule.late_start["18.2"], timedelta(days=1))
        self.assertEqual(schedule.total_float["18.2"], timedelta(days=-4))
        self.assertEqual(schedule.total_float["18.1"], timedelta(days=-4))

        # Over-constrained tasks remain critical so they stay visible.
        self.assertEqual(schedule.critical_tasks, ["18.1", "18.2"])
        self.assertEqual(schedule.critical_paths, [["18.1", "18.2"]])

    def test_constraint_added_with_equal_task_copy_still_applies(self):
        project = Project("Constraint Identity", start_date=date(2026, 1, 5))
        project.add_task(Task("1", "A", timedelta(days=3)))

        # An equal-but-distinct Task passes add_constraint's membership
        # check; constraints must attach by task number to apply.
        project.add_constraint(Task("1", "A", timedelta(days=3)), "SNET", date(2026, 1, 10))

        schedule = Scheduler().calculate(project)

        self.assertEqual(schedule.early_start["1"], timedelta(days=5))
        self.assertEqual(schedule.early_finish["1"], timedelta(days=8))


class TestMandatoryConstraints(unittest.TestCase):
    """Mandatory constraints pin dates exactly and fail loudly when the
    network cannot accommodate them."""

    def test_mandatory_start_pins_dates_and_leaves_no_float(self):
        project = test_projects.mandatory_start()

        schedule = Scheduler().calculate(project)

        # The boundary constraint on 19.1 (the network already starts it
        # there) raises nothing.
        self.assertEqual(schedule.early_start["19.1"], timedelta(days=0))
        self.assertEqual(schedule.early_finish["19.1"], timedelta(days=5))

        # 19.2 is pinned two days later than its dependency allows.
        self.assertEqual(schedule.early_start["19.2"], timedelta(days=8))
        self.assertEqual(schedule.early_finish["19.2"], timedelta(days=11))
        self.assertEqual(schedule.duration, timedelta(days=11))
        self.assertEqual(schedule.start_dates["19.2"], date(2026, 1, 13))

        # Mandatory dates leave no usable float on either task: the
        # backward pass pins the late dates to the same pins.
        self.assertEqual(schedule.late_start["19.1"], timedelta(days=0))
        self.assertEqual(schedule.late_start["19.2"], timedelta(days=8))
        self.assertEqual(schedule.total_float["19.1"], timedelta(days=0))
        self.assertEqual(schedule.total_float["19.2"], timedelta(days=0))
        self.assertEqual(schedule.critical_tasks, ["19.1", "19.2"])

        # The pinned gap means the dependency is not tight, so each task
        # is its own critical path.
        self.assertEqual(sorted(schedule.critical_paths), [["19.1"], ["19.2"]])

    def test_mandatory_finish_pins_dates_and_makes_chain_critical(self):
        project = test_projects.mandatory_finish()

        schedule = Scheduler().calculate(project)

        # 20.1 is pinned to finish on the constraint date...
        self.assertEqual(schedule.early_start["20.1"], timedelta(days=6))
        self.assertEqual(schedule.early_finish["20.1"], timedelta(days=10))
        self.assertEqual(schedule.finish_dates["20.1"], date(2026, 1, 14))

        # ...and 20.2 shifts with it.
        self.assertEqual(schedule.early_start["20.2"], timedelta(days=10))
        self.assertEqual(schedule.early_finish["20.2"], timedelta(days=16))
        self.assertEqual(schedule.duration, timedelta(days=16))

        # The backward pass pins the same dates, leaving no float.
        self.assertEqual(schedule.late_finish["20.1"], timedelta(days=10))
        self.assertEqual(schedule.late_start["20.1"], timedelta(days=6))
        self.assertEqual(schedule.total_float["20.1"], timedelta(days=0))
        self.assertEqual(schedule.total_float["20.2"], timedelta(days=0))
        self.assertEqual(schedule.critical_paths, [["20.1", "20.2"]])

    def test_mandatory_start_conflict_raises(self):
        project = test_projects.mandatory_start_conflict()

        # The dependency cannot deliver a start at or before the
        # mandatory date.
        with self.assertRaisesRegex(SchedulingError, "violates mandatory start constraint"):
            Scheduler().calculate(project)


    def test_mandatory_finish_conflict_raises(self):
        project = test_projects.mandatory_finish_conflict()

        # The dependency cannot deliver a finish at or before the
        # mandatory date.
        with self.assertRaisesRegex(SchedulingError, "violates mandatory finish constraint"):
            Scheduler().calculate(project)

    def test_mandatory_start_conflicts_with_successor_constraint(self):
        project = test_projects.mandatory_start_backward_conflict()

        # The forward pass accommodates the pin, but the successor's
        # late-side constraint makes the pinned late dates impossible.
        with self.assertRaisesRegex(SchedulingError, "violates mandatory start constraint"):
            Scheduler().calculate(project)

    def test_mandatory_and_soft_conflict_regardless_of_order(self):
        soft = ("SNET", date(2026, 1, 15))   # start no earlier than day 10
        hard = ("MSON", date(2026, 1, 7))    # must start on day 2

        for constraints in ([soft, hard], [hard, soft]):
            project = Project("Conflicting Constraints", start_date=date(2026, 1, 5))
            project.add_task(Task("1", "A", timedelta(days=3)))

            for con_type, con_date in constraints:
                project.add_constraint(project.tasks["1"], con_type, con_date)

            # The mandatory pin is applied after the soft constraints, so
            # both orders must fail rather than silently let the soft
            # constraint override the pin.
            with self.assertRaisesRegex(SchedulingError, "violates mandatory start"):
                Scheduler().calculate(project)

    def test_conflicting_mandatory_constraints_rejected(self):
        start = ("MSON", date(2026, 1, 7))    # must start on 2026-01-07
        finish = ("MFON", date(2026, 1, 15))  # must finish on 2026-01-15 (3d task)

        for constraints in ([start, finish], [finish, start]):
            project = Project("Conflicting Mandatories", start_date=date(2026, 1, 5))
            project.add_task(Task("1", "A", timedelta(days=3)))

            for con_type, con_date in constraints:
                project.add_constraint(project.tasks["1"], con_type, con_date)

            with self.assertRaisesRegex(SchedulingError, "conflicting mandatory"):
                Scheduler().calculate(project)

    def test_mandatory_finish_on_milestone_pins_its_day(self):
        project = Project("Milestone Mandatory Finish", start_date=date(2026, 1, 5))
        project.add_task(Task("1", "Gate", timedelta(days=0)))
        project.add_constraint(project.tasks["1"], "MFON", date(2026, 1, 15))

        schedule = Scheduler().calculate(project)

        # A milestone finishes on its start day, so its constraint date
        # needs no finish-side adjustment: day 10 IS 2026-01-15.
        self.assertEqual(schedule.early_start["1"], timedelta(days=10))
        self.assertEqual(schedule.early_finish["1"], timedelta(days=10))
        self.assertEqual(schedule.finish_dates["1"], date(2026, 1, 15))
        self.assertEqual(schedule.total_float["1"], timedelta(days=0))


if __name__ == "__main__":
    unittest.main()