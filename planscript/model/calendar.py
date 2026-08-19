from dataclasses import dataclass, field
from datetime import timedelta, date

@dataclass
class Calendar:
    id: str
    name: str

    working_days: set[int] # 0=Monday, 6=Sunday

    holidays: set[date] = field(default_factory=set)

    def is_working_day(self, day: date) -> bool:
        if day in self.holidays:
            return False
        
        return day.weekday() in self.working_days

    def next_working_day(self, day: date) -> date:
        current = day

        while not self.is_working_day(current):
            current += timedelta(days=1)

        return current

    def previous_working_day(self, day: date) -> date:
        current = day

        while not self.is_working_day(current):
            current -= timedelta(days=1)

        return current

    def add_working_days(self, start: date, days: int) -> date:
        current = start
        remaining = days

        while remaining > 0:
            current += timedelta(days=1)

            if self.is_working_day(current):
                remaining -= 1

        return current

    def working_days_between(self, start: date, finish: date) -> int:
        current = start
        count = 0

        while current < finish:
            if self.is_working_day(current):
                count += 1

            current += timedelta(days=1)

        return count