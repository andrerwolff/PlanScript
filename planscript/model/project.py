from dataclasses import dataclass, field

from planscript.model import dependency
from planscript.model.calendar import Calendar
from planscript.model.dependency import Dependency, DependencyType
from planscript.model.task import Task


@dataclass
class Project:
    name: str

    start: str | None = None
    finish: str | None = None

    tasks: dict[str, Task] = field(default_factory=dict)
    dependencies: list[Dependency] = field(default_factory=list)
    calendars: dict[str, Calendar] = field(default_factory=dict)

    metadata: dict = field(default_factory=dict)

    def add_task(self, task: Task) -> None:
        if task.number in self.tasks:
            raise ValueError(f"Task with number '{task.number}' already exists in the project.")

        self.tasks[task.number] = task

    def remove_task(self, task_number: str) -> None:
        #TODO: Check if task is a predecessor or successor in any dependencies before removing
        if task_number not in self.tasks:
            raise ValueError(f"Task with number '{task_number}' does not exist in the project.")

        del self.tasks[task_number]

    def renumber_task(self, old_number: str, new_number: str) -> None:
        #TODO: Check if task is a predecessor or successor in any dependencies before renumbering
        if old_number not in self.tasks:
            raise ValueError(f"Task with number '{old_number}' does not exist in the project.")
        if new_number in self.tasks:
            raise ValueError(f"Task with number '{new_number}' already exists in the project.")

        task = self.tasks.pop(old_number)
        task.number = new_number
        self.tasks[new_number] = task

    def get_task(self, task_number: str) -> Task:
        try:
            return self.tasks[task_number]
        except KeyError:
            raise ValueError(f"Task with number '{task_number}' does not exist in the project.")

    def add_dependency(self, predecessor: str, successor: str, type: DependencyType = DependencyType.FINISH_START) -> None:
        if predecessor not in self.tasks:
            raise ValueError(f"Predecessor task with number '{predecessor}' does not exist in the project.")
        if successor not in self.tasks:
            raise ValueError(f"Successor task with number '{successor}' does not exist in the project.")

        dependency = Dependency(predecessor=predecessor, successor=successor, type=type)
        self.dependencies.append(dependency)

    def remove_dependency(self, dependency: Dependency) -> None:
        if dependency not in self.dependencies:
            raise ValueError("Dependency does not exist in the project.")

        self.dependencies.remove(dependency)