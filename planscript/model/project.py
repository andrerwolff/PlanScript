from dataclasses import dataclass, field
from datetime import timedelta

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
        self.sort_tasks()

    def remove_task(self, task_number: str) -> None:
        if task_number not in self.tasks:
            raise ValueError(f"Task with number '{task_number}' does not exist in the project.")
        for dependency in self.dependencies:
            if dependency.predecessor == task_number or dependency.successor == task_number:
                try:
                    print(f"--Found related dependency '{dependency}', removing...")
                    self.remove_dependency(dependency)
                except ValueError:
                    print(f"Could not remove dependency '{dependency}' from project '{self.name}'.")
                
        try:
            del self.tasks[task_number]
            print(f"Task '{task_number}' removed from project '{self.name}'.")
        except KeyError:
            raise ValueError(f"Task with number '{task_number}' does not exist in the project.")
        self.sort_tasks()

    def renumber_task(self, old_number: str, new_number: str) -> None:
        #TODO: Check if task is a predecessor or successor in any dependencies before renumbering
        if old_number not in self.tasks:
            raise ValueError(f"Task with number '{old_number}' does not exist in the project.")
        if new_number in self.tasks:
            raise ValueError(f"Task with number '{new_number}' already exists in the project.")

        task = self.tasks.pop(old_number)
        task.number = new_number
        self.tasks[new_number] = task
        self.sort_tasks()

    def sort_tasks(self):
        self.tasks = dict(sorted(self.tasks.items(), key=lambda item: item[0]))
        print(f"Tasks in project '{self.name}' sorted by task number.")

    def list_tasks(self):
        return list(self.tasks.values())

    def add_dependency(self, predecessor: str, successor: str, type: DependencyType = DependencyType.FINISH_START, lag: timedelta = timedelta(days=0)) -> None:
        if predecessor not in self.tasks:
            raise ValueError(f"Predecessor task with number '{predecessor}' does not exist in the project.")
        if successor not in self.tasks:
            raise ValueError(f"Successor task with number '{successor}' does not exist in the project.")
        if predecessor == successor:
            raise ValueError("Predecessor and successor cannot be the same task.")

        dependency = Dependency(predecessor=predecessor, successor=successor, type=type, lag=lag)
        self.dependencies.append(dependency)
        print(f"Dependency added: {dependency}")

    def remove_dependency(self, dependency: Dependency) -> None:
        if dependency not in self.dependencies:
            raise ValueError("Dependency does not exist in the project.")

        try:
            self.dependencies.remove(dependency)
            print(f"Dependency '{dependency.predecessor} -> {dependency.successor}' removed from project '{self.name}'.")
        except ValueError:
            print(f"No dependency found from '{dependency.predecessor}' to '{dependency.successor}' in project '{self.name}'.")

    def get_predecessors(self, task: Task):
        predecessors = []
        for dependency in self.dependencies:
            if dependency.successor == task.number:
                predecessors.append(dependency.predecessor)
        return predecessors