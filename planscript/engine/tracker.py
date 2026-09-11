from operator import attrgetter
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum

from planscript.cli.exceptions import ValidationError, ParseError

class EventDirective(Enum):
    START = "start"
    PROGRESS = "progress"
    COMPLETE = "complete"
    NOTE = "note"

class TaskStatus(Enum):
    NOT_STARTED = "Not Started"
    STARTED = "Started"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

@dataclass
class TrackingEvent:
    date: date
    task_id: str
    directive: EventDirective
    info: str

    def __str__(self):
        info = self.info
        if info is None:
            info = ""
            
        return f"{self.date.strftime('%#m/%#d/%y')} {self.task_id} {self.directive.value} {info}"

@dataclass
class Tracker:
    events: list[TrackingEvent] = field(default_factory=list)

    def add_event(self, tracking_event: TrackingEvent):
        if tracking_event in self.events:
            raise ValidationError(f"Event '{tracking_event}' already exists in the project.")
        
        self.events.append(tracking_event)

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
    task_id: str
    status: TaskStatus = TaskStatus.NOT_STARTED
    percent_complete: float = 0

    def _derive(self, task_events):
        for event in task_events:
            if event.directive == EventDirective.START:
                if self.status != TaskStatus.NOT_STARTED:
                    raise ValidationError(f"Task '{self.task_id}' can only start once.")
                self.status = TaskStatus.STARTED
            elif event.directive == EventDirective.COMPLETE:
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
                    if result > 100 or result < 0:
                        raise ValidationError(f"Log entry: '{event}' results in out of bounds percentage")
                    self.percent_complete = result
                else:
                    self.percent_complete = value

                if self.percent_complete >= 0:
                    self.status = TaskStatus.IN_PROGRESS

    def __str__(self):
        return f"{self.task_id} Status: {self.status.value}\n\tProgress: {self.percent_complete}%"