import unittest
from datetime import timedelta

from planscript.model.hierarchy import TaskHierarchy
from planscript.model.project import Project, ValidationError
from planscript.model.dependency import Dependency, DependencyType
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
        self.hierarchy.build()
        self.hierarchy.build()

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