from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

from planscript.model.task import Task


class DependencyType(Enum):
    FINISH_START = "FS"
    START_START = "SS"
    FINISH_FINISH = "FF"
    START_FINISH = "SF"

@dataclass
class Dependency:
    predecessor: Task
    successor: Task
    dependency_type: DependencyType = DependencyType.FINISH_START
    lag: timedelta = timedelta(0)
    lag_unit: str = "d"

    def __str__(self):
        return f"{self.predecessor.number} -> {self.successor.number} ({self.dependency_type.value}, Lag: {self.lag.days}d)"
