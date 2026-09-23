"""Derived budget model for PlanScript.

A Budget contains the results of resolving a Project's task budgets. Budget
data is derived and is not authoritative project data.
"""

from dataclasses import dataclass, field
from planscript.model.hierarchy import TaskHierarchy
from decimal import Decimal

@dataclass
class Budget:
    """Resolved budget allocation for a PlanScript project.

    Scope is excluded; only *precise* allocations roll up. A task's amount is
    its explicit budget when authored, its percentage share of the parent's
    resolved amount when weighted, and the sum of its children when a summary.

    An empty Budget has no hierarchy and no amounts. This is the state of a
    Project before its budget has been calculated.

    Attributes:
        hierarchy: Task hierarchy used to interpret summary relationships, or
            None when no budget has been calculated.
        amounts: Resolved budget for each task with a determinable amount, in
            whole cents. A summary task's amount equals the sum of its children.
        explicit: Authored explicit budgets, keyed by task ID.
        weights: Authored percentage weights, keyed by task ID.
        unallocated: Task IDs whose budget cannot be determined, by task number.
    """

    hierarchy: TaskHierarchy | None = None
    amounts: dict[str, Decimal] = field(default_factory=dict)
    explicit: dict[str, Decimal] = field(default_factory=dict)
    weights: dict[str, Decimal] = field(default_factory=dict)
    unallocated: list[str] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        """Return the project's total budget.

        Only root tasks are summed. Summing every entry would double-count
        summaries against their own children.
        """

        if self.hierarchy is None:
            # Without a hierarchy the amounts cannot be rolled up, so they are
            # treated as top level.
            return sum(self.amounts.values(), Decimal("0"))

        total = Decimal("0")
        for task_id in self.hierarchy.get_roots():
            amount = self.amounts.get(task_id)
            if amount is not None:
                total += amount
        return total