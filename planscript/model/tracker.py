"""Tracking models and derived actuals for PlanScript projects.

Tracking records dated events against project tasks. Tracker provides access
to tracking history and derives actual task dates and durations. TaskState
derives the current tracking status and percent complete from a task's events.

Every derived value is measured to a single data date (`as_of`, defaulting to
today). Events and invoices dated after the data date are ignored, so
historical state can be derived deterministically and a future-dated entry
never makes a task look started or finished. `Tracker.future_dated_events()`
returns the entries a data date excluded so callers can report them rather
than silently drop them.

Tracking data is authoritative history; status, progress, and actual schedule
values are derived from that history.
"""

from operator import attrgetter
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum

from planscript.exceptions import ValidationError, ParseError
from planscript.model.hierarchy import TaskHierarchy

class EventDirective(Enum):
    """Supported tracking events recorded against a task."""

    START = "start"
    PROGRESS = "progress"
    COMPLETE = "complete"
    NOTE = "note"

#: Same-day lifecycle precedence: within one date, events are applied as
#: start -> progress -> complete regardless of file order. Notes rank last;
#: they never affect derived state.
DIRECTIVE_PRECEDENCE = {
    EventDirective.START: 0,
    EventDirective.PROGRESS: 1,
    EventDirective.COMPLETE: 2,
    EventDirective.NOTE: 3,
}

class TaskStatus(Enum):
    """Derived status of a task based on its tracking events."""

    NOT_STARTED = "Not Started"
    STARTED = "Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

@dataclass
class TaskEvent:
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
class Invoice:
    invoice_date: date
    invoice_amount: Decimal

    allocations: dict[str,Decimal] = field(default_factory=dict)

    def add_allocation(self, task_id, amount):
        if task_id not in self.allocations:
            self.allocations[task_id] = amount
        else:
            raise ValidationError(f"Amount already allocated to task")
    
    def validate(self):
        allocation_total = sum(self.allocations.values(), Decimal("0"))
        if allocation_total != self.invoice_amount:
            raise ValidationError(f"Invoice total does not match allocations:\n {self}")
        # TODO add credits/adjustments?
        if self.invoice_amount < 0:
            raise ValidationError(f"Invoice amount cannot be negative:\n {self}")

        for task_id, amount in self.allocations.items():
            if amount <=0:
                raise ValidationError(f"Allocation must be positive: {task_id}\n{Invoice}")
                

    def __str__(self):
        str = f"INVOICE [{self.invoice_date}] - ${self.invoice_amount}\n"
        for task_id in self.allocations:
            str += f"    {task_id} - ${self.allocations[task_id]}\n"
        return str


@dataclass
class Tracker:
    """Manage tracking history and derive actual task performance.

    Tracker stores TrackingEvent records and derives task-level actual
    starts, finishes, durations, and current states from those events.

    The tracker does not modify the project's planned task data.
    """

    hierarchy: TaskHierarchy | None = None
    task_events: list[TaskEvent] = field(default_factory=list)
    invoice_events: list[Invoice] = field(default_factory=list)

    # Derived indexes over the authoritative lists above. They are rebuilt
    # lazily whenever a list's length changes, so they can never disagree
    # with the history even if a caller mutates a list directly.
    _event_index: dict[str, list[TaskEvent]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _event_index_size: int = field(default=0, init=False, repr=False, compare=False)
    _allocation_index: dict[str, list[tuple[date, Decimal]]] = field(default_factory=dict, init=False, repr=False, compare=False)
    _allocation_index_size: int = field(default=0, init=False, repr=False, compare=False)

    def _events_by_task(self) -> dict[str, list[TaskEvent]]:
        """Return this tracker's task events indexed by task ID.

        Deriving state for one task should cost time proportional to that
        task's own events, not to the whole history, so repeated calls scan
        an index instead of the full event list.
        """
        if self._event_index_size != len(self.task_events):
            index = {}
            for event in self.task_events:
                index.setdefault(event.task_id, []).append(event)
            self._event_index = index
            self._event_index_size = len(self.task_events)
        return self._event_index

    def _allocations_by_task(self) -> dict[str, list[tuple[date, Decimal]]]:
        """Return invoice allocations indexed by task ID.

        Each entry is an `(invoice_date, amount)` pair in invoice order, so
        a task's actual cost costs time proportional to its own allocations
        rather than to every invoice in the project.
        """
        if self._allocation_index_size != len(self.invoice_events):
            index = {}
            for invoice in self.invoice_events:
                for task_id, amount in invoice.allocations.items():
                    index.setdefault(task_id, []).append((invoice.invoice_date, amount))
            self._allocation_index = index
            self._allocation_index_size = len(self.invoice_events)
        return self._allocation_index

    @staticmethod
    def _data_date(as_of):
        """Return the data date used to derive actual values.

        The data date limits which tracking events are considered, so historical
        state can be derived deterministically. Today is used when no date is
        supplied, matching the other date-consuming methods.
        """
        return as_of if as_of is not None else date.today()

    def actual_start(self, task_id, as_of=None):
        """Return the actual start date for a task.

        For leaf tasks, the date comes from the task's start event. For summary
        tasks, the date is derived as the earliest actual start among descendants.

        Events after the data date are ignored, so a start recorded in the future
        does not make a task look started.

        Returns:
            The actual start date, or None if the task has not started.
        """

        if self.hierarchy is None:
            raise ValidationError(f"Hierarchy not working")

        as_of = self._data_date(as_of)

        if self.hierarchy.is_summary(task_id):
            starts = []
            for child_id in self.hierarchy.children[task_id]:
                start = self.actual_start(child_id, as_of)

                if start is not None:
                    starts.append(start)

            if starts:
                return min(starts)
            return None

        for event in self.get_tasks_events(task_id, as_of):
            if event.directive == EventDirective.START:
                return event.date
        return None

    def actual_finish(self, task_id, as_of=None):
        """Return the actual finish date for a task.

        For leaf tasks, the date comes from the task's completion event. For
        summary tasks, the date is derived as the latest actual finish among
        descendants.

        Events after the data date are ignored, so work completed later is not
        reported as finished.

        Returns:
            The actual finish date, or None if the task is not completely finished.
        """

        if self.hierarchy is None:
            raise ValidationError("Hierarchy not working")

        as_of = self._data_date(as_of)

        if self.hierarchy.is_summary(task_id):
            finishes = []
            for child_id in self.hierarchy.children[task_id]:
                finish = self.actual_finish(child_id, as_of)

                if finish is not None:
                    finishes.append(finish)
                else:
                    return None

            if finishes:
                return max(finishes)
            return None

        for event in self.get_tasks_events(task_id, as_of):
            if event.directive == EventDirective.COMPLETE:
                return event.date
        return None

    def actual_dates(self, task_id, as_of=None):
        start = self.actual_start(task_id, as_of)
        finish = self.actual_finish(task_id, as_of)
        actual_dates = {
            "start" : start,
            "finish" : finish,
        }
        return actual_dates

    def actual_duration(self, task_id, as_of=None):
        """Return the actual or elapsed duration of a task.

        A completed task uses its actual start and finish dates. An active task
        uses its actual start and the data date, which defaults to today.

        Durations are inclusive of both the start and end dates. Because the
        data date also limits the events considered, an elapsed duration is
        never negative and a task whose start is recorded after the data date
        has no actual duration at all.
        """

        as_of = self._data_date(as_of)
        

        start = self.actual_start(task_id, as_of)
        finish = self.actual_finish(task_id, as_of)

        if start is None:
            return None

        #complete project
        if finish is not None:
            return finish - start + timedelta(days=1)

        #elapsed duration
        return as_of - start + timedelta(days=1)

    def actual_cost(self, task_id, as_of=None):
        """Return the actual cost for a task.

        A task's cost is the sum of the invoice amounts allocated to it,
        including amounts allocated directly to a summary task. For summary
        tasks, the cost also includes the costs of all descendants, so a charge
        made directly to a summary is additional to the charges beneath it.

        Returns:
            The actual cost incurred up to the data date.
        """

        if self.hierarchy is None:
            raise ValidationError("Hierarchy not working")

        as_of = self._data_date(as_of)

        cost = Decimal("0")

        for invoice_date, amount in self._allocations_by_task().get(task_id, ()):
            if invoice_date <= as_of:
                cost += amount

        if self.hierarchy.is_summary(task_id):
            for child_id in self.hierarchy.get_children(task_id):
                cost += self.actual_cost(child_id, as_of)

        return cost

    def total_actual_cost(self, as_of=None) -> Decimal:
        as_of = self._data_date(as_of)

        total_cost = Decimal("0")
        for task_id in self.hierarchy.get_roots():
            cost = self.actual_cost(task_id, as_of)
            if cost is not None:
                total_cost += cost
        return total_cost

    def add_task_event(self, task_event:TaskEvent):
        """Append a task event, combining notes and rejecting duplicates.

        A `note` may repeat for one task on one date; repeat notes are
        combined into the existing note, separated by ` | `. Any other
        directive may appear at most once per task per date, so duplicates
        are rejected rather than resolved by file order.
        """
        own_events = self._events_by_task().setdefault(task_event.task_id, [])

        if task_event.directive == EventDirective.NOTE:
            for existing in own_events:
                if (existing.directive == EventDirective.NOTE
                        and existing.date == task_event.date):
                    parts = [part for part in (existing.info, task_event.info) if part]
                    existing.info = " | ".join(parts)
                    return
        else:
            for existing in own_events:
                if (existing.directive == task_event.directive
                        and existing.date == task_event.date):
                    raise ValidationError(
                        f"Duplicate {task_event.directive.value} event for task "
                        f"'{task_event.task_id}' on {task_event.date}."
                    )

        self.task_events.append(task_event)
        own_events.append(task_event)
        self._event_index_size = len(self.task_events)

    def add_invoice_event(self, invoice:Invoice):

        if invoice in self.invoice_events:
            raise ValidationError(f"Event '{invoice}' already exists in the project.")

        self.invoice_events.append(invoice)

    def get_all_task_events(self, as_of=None):
        """Return every task event up to the data date, in chronological order.

        Same-day events are ordered by lifecycle precedence (start, progress,
        complete, note) rather than file order.
        """

        as_of = self._data_date(as_of)
        events = sorted(self.task_events, key=lambda e: (e.date, DIRECTIVE_PRECEDENCE[e.directive]))
        return [event for event in events if event.date <= as_of]

    def get_tasks_events(self, task_id, as_of=None):
        """Return a task's events up to the data date, in chronological order.

        Same-day events are ordered by lifecycle precedence (start, progress,
        complete, note) rather than file order.
        """

        as_of = self._data_date(as_of)
        task_events = self._events_by_task().get(task_id, ())
        events = sorted(task_events, key=lambda e: (e.date, DIRECTIVE_PRECEDENCE[e.directive]))
        return [event for event in events if event.date <= as_of]

    def get_latest_task_event(self, as_of=None):
        events = self.get_all_task_events(as_of)
        if events:
            return events[-1]
        else:
            return None

    def future_dated_events(self, as_of=None):
        """Return task events dated after the data date, in chronological order.

        The data date never silently drops tracking data: callers can report
        these events so a truncated figure is explained rather than hidden.
        """

        as_of = self._data_date(as_of)
        events = sorted(self.task_events, key=attrgetter("date"))
        return [event for event in events if event.date > as_of]

    def get_task_state(self, task_id, as_of=None):
        task_state = TaskState(task_id)
        task_state._derive(self.get_tasks_events(task_id, as_of))
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