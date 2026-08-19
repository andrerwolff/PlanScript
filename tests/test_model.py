from datetime import timedelta

from planscript.model.project import Project
from planscript.model.task import Task


def test_create_project():
    project = Project(name="Test Project")

    project.add_task(
        Task(
            id="design",
            name="Design",
            duration=timedelta(days=20),
        )
    )

    assert project.name == "Test Project"
    assert project.tasks["design"].duration == timedelta(days=20)