"""Core project model for PlanScript.

The Project is the central domain object representing a PlanScript project.
It owns the project's tasks, dependencies, calendar definitions, schedule,
tracking history, and metadata.

Project is responsible for maintaining basic model integrity and validating
relationships between its components. Scheduling, tracking, and analysis
logic are implemented by their respective engine classes.
"""

from dataclasses import dataclass, field
from datetime import timedelta, date
from decimal import Decimal

from planscript.exceptions import ValidationError
from planscript.model.calendar import Calendar
from planscript.model.dependency import Dependency, DependencyType, DependencyGraph
from planscript.model.task import Task
from planscript.model.hierarchy import TaskHierarchy
from planscript.model.budget import Budget
from planscript.engine.tracker import Tracker
from planscript.engine.scheduler import Schedule

@dataclass
class Project:
    """The complete in-memory representation of a PlanScript project.

    Project is the aggregate root for the project model. Tasks and
    dependencies are owned by the project, while scheduling and tracking
    state are represented by their respective engine objects.

    A Project may exist without a calculated schedule or tracking history.
    Schedule data is derived from the project plan, while tracking history
    is part of the project's recorded state.

    Validation is performed by the project after parsing or after direct
    model modifications to ensure that the project's tasks, hierarchy,
    dependencies, durations, dates, and tracking references are consistent.

    Attributes:
        name: Project name.
        start_date: Optional planned project start date.
        finish_date: Optional planned project finish date.
        tasks: Tasks keyed by their PlanScript task number.
        dependencies: Dependency relationships between tasks.
        calendar: Calendar name from the project's calendar attribute; stored
            but not yet interpreted.
        calendars: Calendar definitions available to the project (always
            empty today).
        schedule: Calculated schedule, if one has been generated.
        tracker: Tracking history and derived task states.
        metadata: Additional project-level metadata.
    """

    name: str

    start_date: date | None = None
    finish_date: date | None = None

    calendar: str | None = None

    tasks: dict[str, Task] = field(default_factory=dict)
    dependencies: list[Dependency] = field(default_factory=list)
    calendars: dict[str, Calendar] = field(default_factory=dict)

    budget: Budget = field(default_factory=Budget)

    schedule: Schedule | None = None
    tracker: Tracker = field(default_factory=Tracker)

    metadata: dict = field(default_factory=dict)


    def add_task(self, task: Task) -> None:
        """Add a task to the project.

        Raises:
            ValueError: If another task already uses the task number.
        """

        if task.number in self.tasks:
            raise ValueError(f"Task with number '{task.number}' already exists in the project.")

        self.tasks[task.number] = task
        self.sort_tasks()

    def remove_task(self, task_number: str) -> None:
        """Remove a task and all dependencies involving it.

        Args:
            task_number: Number of the task to remove.

        Raises:
            ValueError: If the task does not exist.
        """

        if task_number not in self.tasks:
            raise ValueError(f"Task with number '{task_number}' does not exist in the project.")
 # Remove related dependencies
        dependencies_to_remove = []
        for dependency in self.dependencies:
            if dependency.predecessor == self.tasks[task_number] or dependency.successor == self.tasks[task_number]:
                #print(f"--Found related dependency '{dependency}', removing...")
                dependencies_to_remove.append(dependency)
        for dependency in dependencies_to_remove:
            self.remove_dependency(dependency)
                
        try:
            del self.tasks[task_number]
            #print(f"Task '{task_number}' removed from project '{self.name}'.")
        except KeyError:
            raise ValueError(f"Task with number '{task_number}' does not exist in the project.")
        self.sort_tasks()

    def renumber_task(self, old_number: str, new_number: str) -> None:
        """Change a task's number.

        The Task object itself is retained; only its project key and task
        number are changed.

        Args:
            old_number: Existing task number.
            new_number: New task number.

        Raises:
            ValueError: If the old task does not exist or the new number
                is already in use.
        """
        # Task numbers are user-facing identifiers and may be changed.
        # Relationships stored as Task objects remain attached to the task.
        if old_number not in self.tasks:
            raise ValueError(f"Task with number '{old_number}' does not exist in the project.")
        if new_number in self.tasks:
            raise ValueError(f"Task with number '{new_number}' already exists in the project.")

        task = self.tasks.pop(old_number)
        task.number = new_number
        self.tasks[new_number] = task
        self.sort_tasks()

    def sort_tasks(self) -> None:
        """Keep tasks ordered by PlanScript task number."""

        self.tasks = dict(sorted(self.tasks.items(), key=lambda item: item[0]))
        #print(f"Tasks in project '{self.name}' sorted by task number.")

    def list_tasks(self) -> list[Task]:
        return list(self.tasks.values())

    def add_dependency(self, predecessor: Task, successor: Task, dep_type: DependencyType = DependencyType.FINISH_START, lag: timedelta = timedelta(days=0), lag_unit: str = "d") -> None:
        """Add a dependency between two project tasks.

        Dependencies default to Finish-to-Start with zero lag.

        Raises:
            ValueError: If either task is not in the project or if a task
                is made dependent on itself.
        """

        if predecessor not in self.tasks.values():
            raise ValueError(f"Predecessor task with number '{predecessor}' does not exist in the project.")
        if successor not in self.tasks.values():
            raise ValueError(f"Successor task with number '{successor}' does not exist in the project.")
        if predecessor == successor:
            raise ValueError("Predecessor and successor cannot be the same task.")

        if isinstance(dep_type, str):
            dep_type = DependencyType(dep_type)
        
        dependency = Dependency(predecessor=predecessor, successor=successor, dep_type=dep_type, lag=lag, lag_unit=lag_unit)
        self.dependencies.append(dependency)
        #print(f"Dependency added: {dependency}")

    def remove_dependency(self, dependency: Dependency) -> None:
        """Remove an existing dependency from the project.

        Raises:
            ValueError: If the dependency is not present.
        """

        if dependency not in self.dependencies:
            raise ValueError("Dependency does not exist in the project.")

        try:
            self.dependencies.remove(dependency)
            #print(f"Dependency '{dependency.predecessor} -> {dependency.successor}' removed from project '{self.name}'.")
        except ValueError:
            print(f"No dependency found from '{dependency.predecessor}' to '{dependency.successor}' in project '{self.name}'.")

    def get_predecessors(self, task: Task) -> list[Task]:
        """Return the tasks that directly precede the given task."""

        predecessors = []
        for dependency in self.dependencies:
            if dependency.successor == task:
                predecessors.append(dependency.predecessor)
        return predecessors

    def get_successors(self, task: Task) -> list[Task]:
        """Return the tasks that directly follow the given task."""

        successors = []
        for dependency in self.dependencies:
            if dependency.predecessor == task:
                successors.append(dependency.successor)
        return successors

    def get_incoming_dependencies(self, task:Task) -> list[Dependency]:
        """Return dependency objects entering the given task."""

        incoming_dependencies = []
        for dependency in self.dependencies:
            if dependency.successor == task:
                incoming_dependencies.append(dependency)
        return incoming_dependencies

    def get_outgoing_dependencies(self, task:Task) -> list[Dependency]:
        """Return dependency objects leaving the given task."""

        outgoing_dependencies = []
        for dependency in self.dependencies:
            if dependency.predecessor == task:
                outgoing_dependencies.append(dependency)
        return outgoing_dependencies

    def validate(self) -> None:
        """Validate the internal consistency of the project.

        Validation covers project dates, task hierarchy, summary-task rules,
        dependencies, task durations, and tracking references.

        Validation raises ValidationError on the first detected violation.
        """

        hierarchy = TaskHierarchy(self.tasks)
        
        self._validate_dates()
        self._validate_summaries(hierarchy)
        self._validate_dependencies(hierarchy)
        self._validate_budget(hierarchy)
        self._validate_task_durations()
        self._validate_tracker()

    def _validate_dates(self) -> None:
        """Validate project-level date constraints."""

        if (
            self.start_date is not None
            and self.finish_date is not None                
            and self.start_date > self.finish_date):
            raise ValidationError("Project start date cannot be after finish date.")

    def _validate_summaries(self, hierarchy) -> None:
        """Validate duration rules for summary and leaf tasks."""

        for task_id, task in self.tasks.items():
            if hierarchy.has_children(task_id):
                if task.duration is not None:
                    raise ValidationError(f"Summary task '{task_id}' cannot have a duration.")
            elif task.duration is None:
                raise ValidationError(f"Task '{task_id}' must have a duration.")

    def _validate_dependencies(self, hierarchy) -> None:
        """Validate that dependencies reference valid non-summary tasks."""

        for dependency in self.dependencies:
            predecessor_id = dependency.predecessor.number
            successor_id = dependency.successor.number
            if hierarchy.is_summary(predecessor_id):
                raise ValidationError(f"Task '{predecessor_id}' is a 'Summary Task' and cannot be a predecessor.")

            if hierarchy.is_summary(successor_id):
                raise ValidationError(f"Task '{successor_id}' is a 'Summary Task' and cannot be a succcessor.")

        try:
            DependencyGraph(self).topological_sort()
        except ValueError as e:
            raise ValidationError(str(e)) from e

    def _validate_budget(self, hierarchy:TaskHierarchy) -> None:
        for task_id in self.tasks:
            self._validate_budget_task(hierarchy, task_id)

        for task_id in self.tasks:
            children = hierarchy.get_children(task_id)
            if not children:
                continue

            self._validate_budget_children(task_id, children)

    def _validate_budget_task(self, hierarchy:TaskHierarchy, task_id:str) -> None:
        """Validate a task's own budget allocation.

        A task's budget is either explicit, weighted, or absent; it cannot be
        both explicit and weighted. A weighted task draws its share from the
        nearest explicitly budgeted ancestor, so one must exist.
        """

        task = self.tasks[task_id]

        if task.budget is not None and task.budget_wt is not None:
            raise ValidationError(f"Task '{task_id}' budget cannot be explicit AND derived.")

        if task.budget is not None and task.budget < 0:
            raise ValidationError(f"Task '{task_id}' budget cannot be negative.")

        if task.budget_wt is not None:
            if task.budget_wt < 0 or task.budget_wt > 100:
                raise ValidationError(f"Task '{task_id}' budget weight = {task.budget_wt}%, expected 0% to 100%.")

            if not self._has_explicit_budget_ancestor(hierarchy, task_id):
                raise ValidationError(f"Task '{task_id}' has a weighted budget allocation but no explicitly budgeted ancestor to draw from.")

    def _validate_budget_children(self, task_id, children):
        parent = self.tasks[task_id]

        explicit = []
        weighted = []

        for child_id in children:
            child = self.tasks[child_id]

            # A child's own allocation is validated by _validate_budget_task.
            if child.budget is not None:
                explicit.append(Decimal(child.budget))
            if child.budget_wt is not None:
                weighted.append(Decimal(child.budget_wt))

        if parent.budget_wt is not None and explicit:
                raise ValidationError(f"Task '{task_id}' is derived by % weight and cannot have explicitly budgeted children.")
        if weighted and explicit:
            raise ValidationError(f"Task '{task_id}' cannot mix explicit and derived child budgets.")

        if weighted:
            if len(weighted) != len(children):
                raise ValidationError(f"Task '{task_id}' children must all be weighted (use 0% if needed).")

            total = sum(weighted)
            if total != 100:
                raise ValidationError(f"Task '{task_id}' children budget weights = {total}, expected 100%.")

        if explicit:
            if parent.budget is not None:
                total = sum(explicit)
                if total != parent.budget:
                    raise ValidationError(f"Task '{task_id}' children budgets = ${total}, expected ${parent.budget}.")

    def _has_explicit_budget_ancestor(self, hierarchy: TaskHierarchy, task_id) -> bool:
        """Return True if the task or any of its ancestors has an explicit budget."""

        if self.tasks[task_id].budget is not None:
            return True

        for ancestor_id in hierarchy.get_ancestors(task_id):
            if self.tasks[ancestor_id].budget is not None:
                return True

        return False
                

    def _validate_task_durations(self) -> None:
        """Validate that defined task durations are non-negative."""

        for task_id, task in self.tasks.items():
            if task.duration is None:
                continue

            if task.duration.total_seconds() < 0:
                raise ValidationError(f"Task '{task_id}' cannot have a negative duration.")

    def _validate_tracker(self) -> None:
        """Validate that tracked task references still exist in the project."""

        for task_id in self.tasks:
            self.tracker.get_task_state(task_id)

        for invoice in self.tracker.invoice_events:
            invoice.validate()