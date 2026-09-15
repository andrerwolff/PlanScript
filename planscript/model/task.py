"""Core task model for PlanScript.

A Task represents a single item in a PlanScript project. Its task number
identifies its position in the project hierarchy, while its duration
distinguishes leaf tasks from summary tasks.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

@dataclass
class Task:
    """A single task in a PlanScript project.

    A task with a defined duration is a leaf task. A task with no duration
    is a summary task whose schedule is derived from its child tasks.

    A zero-duration task is a milestone.

    Attributes:
        number: PlanScript task number and hierarchical identifier.
        name: Human-readable task name.
        duration: Planned duration. None indicates a summary task; zero
            indicates a milestone.
        metadata: Additional task-level metadata parsed from the plan.
    """

    number: str
    name: str

    duration: timedelta | None = None

    #calendar: str | None = None

    metadata: dict = field(default_factory=dict)

    @property
    def is_milestone(self) -> bool: 
        """Return True when the task has a zero planned duration."""

        return self.duration == timedelta(0)

    def __str__(self) -> str:
        """Return a concise human-readable representation of the task."""

        if self.duration == None:
            duration = "Summary"
        elif self.is_milestone:
            duration = "Milestone"
        else:
            duration = str(self.duration.days) +"d"
        return f"{self.number} - {self.name} {duration}"    