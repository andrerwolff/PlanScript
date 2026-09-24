from decimal import Decimal, ROUND_FLOOR

from planscript.exceptions import BudgetingError
from planscript.model.budget import Budget
from planscript.model.hierarchy import TaskHierarchy

class Budgeter:
    """Resolve explicit and weighted task budgets into a project budget.

    Budgeter reads the project's plan and produces a Budget containing
    resolved amounts. It does not modify the project's tasks. Plan-level
    budget legality is the responsibility of Project.validate().

    Allocation is performed in two passes: weights are resolved top-down from
    each task's parent, then unbudgeted summary tasks roll up bottom-up.

    Weighted shares are allocated in whole cents with the leftover cents given
    to the largest fractional shares, so the children of a weighted task always
    sum to the parent's amount.
    """

    def calculate(self, project) -> Budget:
        """Calculate and return the resolved budget for the project.

        Budgeting proceeds through these stages:

        1. Build the task hierarchy.
        2. Assign explicit budgets, then resolve percentage weights top-down.
        3. Roll up summary tasks that have no budget of their own.

        Raises:
            BudgetingError: If the project has no tasks to budget, or if a
                weighted task has no budgeted ancestor to allocate from.
        """

        if not project.tasks:
            raise BudgetingError("Project has no tasks to budget.")

        hierarchy = TaskHierarchy(project.tasks)
        amounts = {}
        self._calculate_explicits(project, hierarchy, amounts)
        self._calculate_weights(project, hierarchy, amounts)
        unallocated = self._roll_up(project, hierarchy, amounts)

        return Budget(
            hierarchy=hierarchy,
            amounts=amounts,
            explicit={task_id: task.budget
                      for task_id, task in project.tasks.items()
                      if task.budget is not None},
            weights={task_id: task.budget_wt
                     for task_id, task in project.tasks.items()
                     if task.budget_wt is not None},
            unallocated=unallocated)

    def _calculate_explicits(self, project, hierarchy, amounts) -> None:
        """Assign each task its authored explicit budget.

        Summary rollups and weighted shares are resolved by later passes.
        """

        for task_id in hierarchy.get_bottom_up_order():
            task = project.tasks[task_id]

            # An explicitly budgeted task keeps its authored budget.
            if task.budget is not None:
                amounts[task_id] = task.budget

    def _calculate_weights(self, project, hierarchy: TaskHierarchy, amounts) -> None:
        """Distribute weighted children from their level's allocation base.

        A level draws from its own resolved amount when it has one, otherwise
        from the nearest resolved ancestor's amount, so weighted tasks below
        an unbudgeted summary still draw from the nearest budgeted ancestor.

        Raises:
            BudgetingError: If weighted siblings have no budgeted ancestor to
                draw on, mix weighted and non-weighted children, or do not
                total 100%.
        """

        bases = {}
        for task_id in hierarchy.get_top_down_order():
            # This level's base: its own resolved amount, else the inherited one.
            base = amounts.get(task_id)
            if base is None:
                base = bases.get(hierarchy.get_parent(task_id))
            bases[task_id] = base

            task = project.tasks[task_id]

            if task.budget_wt is not None and task_id not in amounts:
                # A weighted root can never draw from an ancestor.
                raise BudgetingError(
                    f"Task '{task_id}' has a weighted budget allocation but "
                    f"no budgeted ancestor to allocate from.")

            children = hierarchy.get_children(task_id)

            weighted = []
            for child_id in children:
                child = project.tasks[child_id]
                if child.budget_wt is not None:
                    weighted.append((child_id, child.budget_wt))

            if not weighted:
                continue

            if len(weighted) != len(children):
                raise BudgetingError(
                    f"Task '{task_id}' mixes weighted and non-weighted children.")

            total_weight = Decimal("0")
            for child_id, child_wt in weighted:
                total_weight += child_wt

            if total_weight != Decimal("100"):
                raise BudgetingError(
                    f"Weighted children of '{task_id}' must total 100%.")

            if base is None:
                raise BudgetingError(
                    f"Task '{weighted[0][0]}' has a weighted budget allocation "
                    f"but no budgeted ancestor to allocate from.")

            allocated = self._allocate_weighted(base, weighted)
            for child_id, amount in allocated.items():
                amounts[child_id] = amount

    def _allocate_weighted(self, parent_budget, weighted) -> dict[str, Decimal]:
        total_cents = self._to_cents(parent_budget)

        shares = []
        allocated_cents = 0

        for task_id, weight in weighted:
            exact_amount = parent_budget * weight / Decimal("100")
            cents = self._to_cents(exact_amount)
            remainder = (exact_amount - Decimal(cents)/Decimal("100"))

            shares.append({"task_id": task_id,
                           "remainder": remainder,
                            "cents": cents})

            allocated_cents += cents

        remaining = total_cents - allocated_cents

        # Largest fractional share first, breaking ties by task number.
        shares.sort(key=lambda share: (-share["remainder"], share["task_id"]))

        for index in range(remaining):
            shares[index]["cents"] += 1

        amounts = {}
        for share in shares:
            amounts[share["task_id"]] = (Decimal(share["cents"]) / Decimal("100"))

        return amounts

    @staticmethod
    def _to_cents(amount: Decimal) -> int:
        """Return an amount as a whole number of cents, rounded down."""

        return int((amount * 100).to_integral_value(rounding=ROUND_FLOOR))

    def _roll_up(self, project, hierarchy, amounts) -> list[str]:
        """Derive summary amounts and collect tasks with no determined budget.

        Tasks are processed deepest first, so a summary task rolls up after its
        own descendants. A summary task with no budget of its own takes the sum
        of its resolvable children. A summary task whose children are only
        partly resolvable takes the sum of the children that are.

        Returns:
            Task IDs with no determinable budget, in task-number order.
        """

        unallocated = []
        depth_order = sorted(project.tasks, key=lambda task_id: task_id.count("."), reverse=True)

        for task_id in depth_order:
            if task_id in amounts:
                continue

            children = hierarchy.get_children(task_id)

            if not children:
                unallocated.append(task_id)
                continue

            child_amounts = [amounts[child_id] for child_id in children if child_id in amounts]

            if child_amounts:
                amounts[task_id] = sum(child_amounts)
            else:
                unallocated.append(task_id)

        unallocated.sort()
        return unallocated
