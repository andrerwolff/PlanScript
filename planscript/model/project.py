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
 # Remove related dependencies
        dependencies_to_remove = []
        for dependency in self.dependencies:
            if dependency.predecessor == self.tasks[task_number] or dependency.successor == self.tasks[task_number]:
                print(f"--Found related dependency '{dependency}', removing...")
                dependencies_to_remove.append(dependency)
        for dependency in dependencies_to_remove:
            self.remove_dependency(dependency)
                
        try:
            del self.tasks[task_number]
            print(f"Task '{task_number}' removed from project '{self.name}'.")
        except KeyError:
            raise ValueError(f"Task with number '{task_number}' does not exist in the project.")
        self.sort_tasks()

    def renumber_task(self, old_number: str, new_number: str) -> None:
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

    def add_dependency(self, predecessor: Task, successor: Task, dependency_type: DependencyType = DependencyType.FINISH_START, lag: timedelta = timedelta(days=0)) -> None:
        if predecessor not in self.tasks.values():
            raise ValueError(f"Predecessor task with number '{predecessor}' does not exist in the project.")
        if successor not in self.tasks.values():
            raise ValueError(f"Successor task with number '{successor}' does not exist in the project.")
        if predecessor == successor:
            raise ValueError("Predecessor and successor cannot be the same task.")

        if isinstance(dependency_type, str):
            dependency_type = DependencyType(dependency_type)
        
        dependency = Dependency(predecessor=predecessor, successor=successor, dependency_type=dependency_type, lag=lag)
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
            if dependency.successor == task:
                predecessors.append(dependency.predecessor)
        return predecessors

    def get_successors(self, task: Task):
        successors = []
        for dependency in self.dependencies:
            if dependency.predecessor == task:
                successors.append(dependency.successor)
        return successors

    def get_incoming_dependencies(self, task:Task):
        incoming_dependencies = []
        for dependency in self.dependencies:
            if dependency.successor == task:
                incoming_dependencies.append(dependency)
        return incoming_dependencies

    def get_outgoing_dependencies(self, task:Task):
        outgoing_dependencies = []
        for dependency in self.dependencies:
            if dependency.predecessor == task:
                outgoing_dependencies.append(dependency)
        return outgoing_dependencies
