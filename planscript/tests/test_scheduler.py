import unittest

from planscript.engine.scheduler import Scheduler
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


if __name__ == "__main__":
    unittest.main()