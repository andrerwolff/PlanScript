from dataclasses import dataclass, field
from datetime import date, timedelta

@dataclass
class Task:
    number: str
    name: str

    duration: timedelta | None = None

    #calendar: str | None = None

    metadata: dict = field(default_factory=dict)

    @property
    def is_milestone(self) -> bool: 
        return self.duration == timedelta(0)

    def __str__(self):
        duration = "Summary"
        if self.duration:
            duration = str(self.duration.days) +"d"
        return f"{self.number} - {self.name} {duration}"    