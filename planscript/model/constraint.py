from dataclasses import dataclass
from enum import Enum
from datetime import date

from planscript.model.task import Task

class ConstraintType(Enum):
    START_NO_EARLIER_THAN = "SNET"
    START_NO_LATER_THAN = "SNLT"
    FINISH_NO_EARLIER_THAN = "FNET"
    FINISH_NO_LATER_THAN = "FNLT"
    MANDATORY_START = "MSON"
    MANDATORY_FINISH = "MFON"

    @property
    def constrains_finish(self) -> bool:
        """Return True for constraint types that anchor a task's finish."""
        return self in (
            ConstraintType.FINISH_NO_EARLIER_THAN,
            ConstraintType.FINISH_NO_LATER_THAN,
            ConstraintType.MANDATORY_FINISH,
        )

@dataclass
class Constraint:
    """A task-level schedule constraint anchored to a calendar date.

    `con_date` is the authoritative value. The scheduler maps it to an
    offset from the project's start date before the CPM passes, so the
    offset is never stored and cannot go stale.

    Attributes:
        task: Task the constraint applies to.
        con_type: Which schedule boundary the constraint moves.
        con_date: Calendar date the constraint is anchored to.
    """
    task: Task
    con_type: ConstraintType
    con_date: date