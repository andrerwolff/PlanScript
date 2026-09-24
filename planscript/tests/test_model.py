import unittest
from datetime import date, timedelta
from decimal import Decimal

from planscript.model.hierarchy import TaskHierarchy
from planscript.model.project import Project, ValidationError
from planscript.model.dependency import Dependency, DependencyType
from planscript.model.schedule import Schedule
from planscript.model.task import Task

class TestTaskHierarchy(unittest.TestCase):

    def setUp(self):
        self.tasks = {
            "1": object(),
            "1.1": object(),
            "1.2": object(),
            "1.1.a": object(),
            "1.1.b": object(),
            "1.1.a.i": object(),
            "2": object(),
            "2.1": object(),
        }

        self.hierarchy = TaskHierarchy(self.tasks)

    def test_parents(self):
        self.assertIsNone(self.hierarchy.get_parent("1"))
        self.assertEqual(self.hierarchy.get_parent("1.1"), "1")
        self.assertEqual(self.hierarchy.get_parent("1.1.a"), "1.1")
        self.assertEqual(self.hierarchy.get_parent("1.1.a.i"), "1.1.a")
        self.assertEqual(self.hierarchy.get_parent("2.1"), "2")

    def test_children(self):
        self.assertEqual(
            self.hierarchy.get_children("1"),
            ["1.1", "1.2"]
        )

        self.assertEqual(
            self.hierarchy.get_children("1.1"),
            ["1.1.a", "1.1.b"]
        )

        self.assertEqual(
            self.hierarchy.get_children("1.1.a"),
            ["1.1.a.i"]
        )

        self.assertEqual(
            self.hierarchy.get_children("1.1.a.i"),
            []
        )

    def test_roots(self):
        self.assertEqual(
            self.hierarchy.get_roots(),
            ["1", "2"]
        )

    def test_missing_parent_attaches_to_nearest_existing_ancestor(self):
        tasks = {
            "1": object(),
            "1.2.3": object(),
            "1.2.3.4": object(),
        }
        hierarchy = TaskHierarchy(tasks)

        # 1.2 is absent, so 1.2.3 attaches to 1.
        self.assertEqual(hierarchy.get_parent("1.2.3"), "1")
        self.assertEqual(hierarchy.get_children("1"), ["1.2.3"])

        # 1.2.3 exists, so its child keeps its immediate parent.
        self.assertEqual(hierarchy.get_parent("1.2.3.4"), "1.2.3")

        self.assertEqual(hierarchy.get_roots(), ["1"])

    def test_task_without_any_existing_ancestor_is_a_root(self):
        tasks = {
            "1.1": object(),
            "9": object(),
        }
        hierarchy = TaskHierarchy(tasks)

        self.assertIsNone(hierarchy.get_parent("1.1"))
        self.assertEqual(hierarchy.get_roots(), ["1.1", "9"])

    def test_has_children(self):
        self.assertTrue(
            self.hierarchy.has_children("1")
        )

        self.assertTrue(
            self.hierarchy.has_children("1.1")
        )

        self.assertFalse(
            self.hierarchy.has_children("1.1.a.i")
        )

    def test_is_summary(self):
        self.assertTrue(
            self.hierarchy.is_summary("1")
        )

        self.assertTrue(
            self.hierarchy.is_summary("1.1")
        )

        self.assertFalse(
            self.hierarchy.is_summary("1.1.a.i")
        )

    def test_get_descendants(self):
        self.assertEqual(
            self.hierarchy.get_descendants("1"),
            [
                "1.1",
                "1.1.a",
                "1.1.a.i",
                "1.1.b",
                "1.2",
            ]
        )

        self.assertEqual(
            self.hierarchy.get_descendants("1.1"),
            [
                "1.1.a",
                "1.1.a.i",
                "1.1.b",
            ]
        )

        self.assertEqual(
            self.hierarchy.get_descendants("1.1.a.i"),
            []
        )

    def test_unknown_task(self):
        self.assertIsNone(
            self.hierarchy.get_parent("does.not.exist")
        )

        self.assertEqual(
            self.hierarchy.get_children("does.not.exist"),
            []
        )

        self.assertFalse(
            self.hierarchy.has_children("does.not.exist")
        )

    def test_rebuild_does_not_duplicate_children(self):
        self.hierarchy._build()
        self.hierarchy._build()

        self.assertEqual(
            self.hierarchy.get_children("1"),
            ["1.1", "1.2"]
        )

        self.assertEqual(
            self.hierarchy.get_children("1.1"),
            ["1.1.a", "1.1.b"]
        )
    def test_get_leaves(self):
        assert self.hierarchy.get_leaves("1") == [
            "1.1.a.i",
            "1.1.b",
            "1.2"
        ]

    def test_leaf_returns_itself(self):
        assert self.hierarchy.get_leaves("1.1.b") == ["1.1.b"]

    def test_validate_allows_skipped_parent_task(self):
        project = Project("Name")

        project.add_task(Task("2.1", "Design", timedelta(days=2)))
        project.add_task(Task("2.2", "Construction", timedelta(days=3)))

        project.validate()


    def test_validate_rejects_summary_with_duration(self):
        project = Project("Name")

        project.add_task(Task("1", "Summary", timedelta(days=5)))
        project.add_task(Task("1.1", "Task", timedelta(days=2)))

        with self.assertRaises(ValidationError):
            project.validate()


    def test_validate_rejects_leaf_without_duration(self):
        project = Project("Name")

        project.add_task(Task("1", "Task", None))

        with self.assertRaises(ValidationError):
            project.validate()


    def test_validate_rejects_summary_dependency(self):
        project = Project("Name")

        project.add_task(Task("1", "Summary", None))
        project.add_task(Task("1.1", "Task", timedelta(days=2)))
        project.add_task(Task("2", "Task", timedelta(days=1)))

        dependency = Dependency(
            project.tasks["1"],
            project.tasks["2"],
            DependencyType.FINISH_START
        )

        project.dependencies.append(dependency)

        with self.assertRaises(ValidationError):
            project.validate()


class TestProjectBudgetValidation(unittest.TestCase):

    def test_validate_rejects_explicit_and_weighted_budget(self):
        project = Project("Name")
        project.add_task(Task("1", "Task", timedelta(days=1),
                              budget=Decimal("100"), budget_wt=Decimal("50")))

        with self.assertRaisesRegex(ValidationError, "cannot be explicit AND derived"):
            project.validate()


class TestProjectCalendarField(unittest.TestCase):

    def test_calendar_field_is_declared_and_defaults_to_none(self):
        project = Project("No Calendar")

        self.assertIsNone(project.calendar)


class TestScheduleAnnotations(unittest.TestCase):

    def test_cpm_annotations_match_runtime_types(self):
        annotations = Schedule.__annotations__

        self.assertEqual(annotations["early_start"], dict[str, timedelta])
        self.assertEqual(annotations["early_finish"], dict[str, timedelta])
        self.assertEqual(annotations["late_start"], dict[str, timedelta])
        self.assertEqual(annotations["late_finish"], dict[str, timedelta])
        self.assertEqual(annotations["total_float"], dict[str, timedelta | None])
        self.assertEqual(annotations["duration"], timedelta)
        self.assertEqual(annotations["start_dates"], dict[str, date] | None)
        self.assertEqual(annotations["finish_dates"], dict[str, date] | None)

    def test_validate_rejects_negative_budget(self):
        project = Project("Name")
        project.add_task(Task("1", "Task", timedelta(days=1), budget=Decimal("-100")))

        with self.assertRaisesRegex(ValidationError, "budget cannot be negative"):
            project.validate()

    def test_validate_rejects_weight_above_100(self):
        project = Project("Name")
        project.add_task(Task("1", "Summary"))
        project.add_task(Task("1.1", "Task", timedelta(days=1), budget_wt=Decimal("150")))

        with self.assertRaisesRegex(ValidationError, "expected 0% to 100%"):
            project.validate()

    def test_validate_rejects_weighted_task_without_budgeted_ancestor(self):
        project = Project("Name")
        project.add_task(Task("1", "Task", timedelta(days=1), budget_wt=Decimal("50")))

        with self.assertRaisesRegex(ValidationError, "no explicitly budgeted ancestor"):
            project.validate()

    def test_validate_rejects_mixed_child_budgets(self):
        project = Project("Name")
        project.add_task(Task("1", "Summary", None, budget=Decimal("100")))
        project.add_task(Task("1.1", "Explicit", timedelta(days=1), budget=Decimal("100")))
        project.add_task(Task("1.2", "Weighted", timedelta(days=1), budget_wt=Decimal("50")))

        with self.assertRaisesRegex(ValidationError, "cannot mix explicit and derived"):
            project.validate()

    def test_validate_rejects_weights_not_totalling_100(self):
        project = Project("Name")
        project.add_task(Task("1", "Summary", None, budget=Decimal("100")))
        project.add_task(Task("1.1", "First", timedelta(days=1), budget_wt=Decimal("40")))
        project.add_task(Task("1.2", "Second", timedelta(days=1), budget_wt=Decimal("40")))

        with self.assertRaisesRegex(ValidationError, "expected 100%"):
            project.validate()

    def test_validate_rejects_explicit_children_not_matching_parent(self):
        project = Project("Name")
        project.add_task(Task("1", "Summary", None, budget=Decimal("100")))
        project.add_task(Task("1.1", "First", timedelta(days=1), budget=Decimal("60")))
        project.add_task(Task("1.2", "Second", timedelta(days=1), budget=Decimal("30")))

        with self.assertRaisesRegex(ValidationError, "expected \\$100"):
            project.validate()

    def test_validate_allows_summary_without_budget(self):
        project = Project("Name")
        project.add_task(Task("1", "Summary"))
        project.add_task(Task("1.1", "First", timedelta(days=1), budget=Decimal("60")))
        project.add_task(Task("1.2", "Second", timedelta(days=1), budget=Decimal("30")))

        project.validate()

    def test_validate_treats_zero_budget_as_explicit(self):
        project = Project("Name")
        project.add_task(Task("1", "Summary", None, budget=Decimal("0")))
        project.add_task(Task("1.1", "Free", timedelta(days=1), budget=Decimal("0")))

        project.validate()
