from dataclasses import dataclass
from enum import Enum
from datetime import date, timedelta

from planscript.model.task import Task

class ConstraintType(Enum):
    START_NO_EARLIER_THAN = "SNET"
    START_NO_LATER_THAN = "SNLT"
    FINISH_NO_EARLIER_THAN = "FNET"
    FINISH_NO_LATER_THAN = "FNLT"
    MANDATORY_START = "MSON"
    MANDATORY_FINISH = "MFON"

@dataclass
class Constraint:
    task: Task
    con_type: ConstraintType
    con_date: date
    con_offset: timedelta