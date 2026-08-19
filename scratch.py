from datetime import timedelta

from planscript.model.project import Project
from planscript.model.task import Task
from planscript.model.dependency import Dependency


project = Project(name="Test Project")

project.add_task(
    Task(
        number="1",
        name="Design",
        duration=timedelta(days=20),
    )
)

project.add_task(
    Task(
        number="2.1",
        name="Bidding",
        duration=timedelta(days=10),
    )
)
project.add_dependency(
        predecessor="1",
        successor="2.1",
)

print(project)
print(project.tasks)
print(project.dependencies)