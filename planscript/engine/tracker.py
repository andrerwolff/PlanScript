"""Tracking models and derived actuals for PlanScript projects.

Tracking records dated events against project tasks. Tracker provides access
to tracking history and derives actual task dates and durations. TaskState
derives the current tracking status and percent complete from a task's events.

Tracking data is authoritative history; status, progress, and actual schedule
values are derived from that history.
"""

from operator import attrgetter
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum

from planscript.exceptions import ValidationError, ParseError
from planscript.model.hierarchy import TaskHierarchy
from planscript.model.invoice import Invoice

class EventDirective(Enum):
    """Supported tracking events recorded against a task."""

    START = "start"
    PROGRESS = "progress"
    COMPLETE = "complete"
    NOTE = "note"

class TaskStatus(Enum):
    """Derived status of a task based on its tracking events."""

    NOT_STARTED = "Not Started"
    STARTED = "Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

@dataclass
class TrackingEvent:
    """A dated tracking event recorded against a project task.

    Tracking events form the authoritative tracking history from which
    task status, progress, and actual schedule values are derived.

    Attributes:
        date: Date on which the event occurred.
        task_id: ID of the task affected by the event.
        directive: Type of tracking event.
        info: Event-specific information, such as a progress value or note.
    """

    date: date
    task_id: str
    directive: EventDirective
    info: str | None

    def __str__(self):
        info = self.info
        if info is None:
            info = ""
            
        return f"{self.date.strftime('%#m/%#d/%y')} {self.task_id} {self.directive.value} {info}"

@dataclass
class Tracker:
    """Manage tracking history and derive actual task performance.

    Tracker stores TrackingEvent records and derives task-level actual
    starts, finishes, durations, and current states from those events.

    The tracker does not modify the project's planned task data.
    """

    hierarchy: TaskHierarchy | None = None
    events: list[TrackingEvent] = field(default_factory=list)
    invoices: list[Invoice] = field(default_factory=list)

    def actual_start(self, task_id):
        """Return the actual start date for a task.

        For leaf tasks, the date comes from the task's start event. For summary
        tasks, the date is derived as the earliest actual start among descendants.

        Returns:
            The actual start date, or None if the task has not started.
        """

        if self.hierarchy is None:
            raise ValidationError(f"Hierarchy not working")
        
        if self.hierarchy.is_summary(task_id):
            starts = []
            for child_id in self.hierarchy.children[task_id]:
                start = self.actual_start(child_id)

                if start is not None:
                    starts.append(start)

            if starts:
                return min(starts)
            return None

        for event in self.get_task_events(task_id):
            if event.directive == EventDirective.START:
                return event.date
        return None

    def actual_finish(self, task_id):
        """Return the actual finish date for a task.

        For leaf tasks, the date comes from the task's completion event. For
        summary tasks, the date is derived as the latest actual finish among
        descendants.

        Returns:
            The actual finish date, or None if the task is not completely finished.
        """

        if self.hierarchy is None:
            raise ValidationError(f"Hierarchy not working")

        if self.hierarchy.is_summary(task_id):
            finishes = []
            for child_id in self.hierarchy.children[task_id]:
                finish = self.actual_finish(child_id)

                if finish is not None:
                    finishes.append(finish)
                else:
                    return None

            if finishes:
                return max(finishes)
            return None

        for event in self.get_task_events(task_id):
            if event.directive == EventDirective.COMPLETE:
                return event.date
        return None

    def actual_dates(self, task_id):
        start = self.actual_start(task_id)
        finish = self.actual_finish(task_id)
        actual_dates = {
            "start" : start,
            "finish" : finish,
        }
        return actual_dates

    def actual_duration(self, task_id, current_date=None):
        """Return the actual or elapsed duration of a task.

        A completed task uses its actual start and finish dates. An active task
        uses its actual start and the supplied current date, or today's date when
        no current date is supplied.

        Durations are inclusive of both the start and end dates.
        """

        start = self.actual_start(task_id)
        finish = self.actual_finish(task_id)

        if start is None:
            return None
        
        #complete project
        if finish is not None:
            return finish - start + timedelta(days=1)

        if current_date is None:
            current_date = date.today()
        #elapsed duration
        return current_date - start + timedelta(days=1)

    def add_event(self, tracking_event: TrackingEvent):

        if tracking_event in self.events:
            raise ValidationError(f"Event '{tracking_event}' already exists in the project.")
        
        self.events.append(tracking_event)

    def add_invoice(self, invoice: Invoice):

        if invoice in self.invoices:
            raise ValidationError(f"Event '{invoice}' already exists in the project.")

        self.invoices.append(invoice)

    def get_events(self):
        return sorted(self.events, key=attrgetter("date"))

    def get_task_events(self, task_id):
        task_events = []
        for event in self.events:
            if event.task_id == task_id:
                task_events.append(event)
        return sorted(task_events,key=attrgetter('date'))

    def get_latest_event(self):
        events = self.get_events()
        if events:
            return events[-1]
        else:
            return None

    def get_task_state(self, task_id):
        task_state = TaskState(task_id)
        task_state._derive(self.get_task_events(task_id))
        return task_state

@dataclass
class TaskState:
    """Derived current tracking state for a task.

    TaskState is reconstructed from the task's tracking events rather than
    stored as independent authoritative data.
    """

    task_id: str
    status: TaskStatus = TaskStatus.NOT_STARTED
    percent_complete: float = 0

    def _derive(self, task_events):
        """Derive status and percent complete from chronological task events.

        Events are applied in order. Invalid event sequences raise a validation
        or parsing error rather than being silently corrected.
        """

        for event in task_events:
            if event.directive == EventDirective.NOTE:
                pass
            elif event.directive == EventDirective.START:
                if self.status != TaskStatus.NOT_STARTED:
                    raise ValidationError(f"Task '{self.task_id}' can only start once.")
                self.status = TaskStatus.STARTED
            elif event.directive == EventDirective.COMPLETE:
                if self.status == TaskStatus.COMPLETED:
                    raise ValidationError(f"Task '{self.task_id}' can only close once.")
                if self.status == TaskStatus.NOT_STARTED:
                    raise ValidationError(f"Task '{self.task_id}' must be started before it can be closed.")
                self.status = TaskStatus.COMPLETED
                self.percent_complete = 100
            elif event.directive == EventDirective.PROGRESS:
                if self.status == TaskStatus.NOT_STARTED:
                    raise ValidationError(f"Task '{self.task_id}' must be started before progress can be made.")
                elif self.status == TaskStatus.COMPLETED:
                    raise ValidationError(f"Task '{self.task_id}' is already completed, cant apply progress.")

                try:
                    value = int(event.info.strip()[:-1])
                except ValueError as e:
                    raise ParseError(f"Log entry: '{event}' not correct syntax")
                if any(char in event.info for char in ("+", "-")):
                    result = self.percent_complete + value
                    self.percent_complete = result
                else:
                    self.percent_complete = value

                if self.percent_complete >= 0:
                    self.status = TaskStatus.IN_PROGRESS
                if self.percent_complete > 100 or self.percent_complete < 0:
                    raise ValidationError(f"Log entry: '{event}' results in out of bounds percentage")

    def __str__(self):
        return f"{self.task_id} Status: {self.status.value}\n\tProgress: {self.percent_complete}%"