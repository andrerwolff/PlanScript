from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from planscript.exceptions import ValidationError


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
        if not sum(self.allocations.values()) == self.invoice_amount:
            raise ValidationError(f"Invoice total does not match allocations")
