from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

from planscript.model.task import Task


class DependencyType(Enum):
    FINISH_START = "FS"
    START_START = "SS"
    FINISH_FINISH = "FF"
    START_FINISH = "SF"

@dataclass(frozen=True)
class Dependency:
    predecessor: str
    successor: str
    type: DependencyType = DependencyType.FINISH_START
    lag: timedelta = timedelta(0)

    def __str__(self):
        return f"{self.predecessor} -> {self.successor} ({self.type.value}, Lag: {self.lag.days}d)"
