from dataclasses import dataclass, field
from datetime import date, timedelta

@dataclass
class Task:
    number: str
    name: str

    duration: timedelta | None = None

    start: date | None = None
    finish: date | None = None

    calendar: str | None = None

    constraints: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __str__(self):
        return f"{self.number} - {self.name} {self.duration.days}d"    