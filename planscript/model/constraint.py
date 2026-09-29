from dataclasses import dataclass
from enum import Enum
from datetime import date

from planscript.model.task import Task

class ConstraintType(Enum):
    START_ON_OR_AFTER = "SOA"
    START_ON_OR_BEFORE = "SOB"
    FINISH_ON_OR_AFTER = "FOA"
    FINISH_ON_OR_BEFORE = "FOB"
    MANDATORY_START = "MSON"
    MANDATORY_FINISH = "MFON"


@dataclass
class Constraint:
    task: Task
    con_type: ConstraintType
    con_date: date