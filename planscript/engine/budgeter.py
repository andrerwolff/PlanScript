
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
        2. Resolve explicit budgets and percentage weights top-down.
        3. Roll up summary tasks that have no budget of their own.

        Raises:
            BudgetingError: If the project has no tasks to budget, or if a
                weighted task has no budgeted ancestor to allocate from.
        """

        if not project.tasks:
            raise BudgetingError("Project has no tasks to budget.")

        hierarchy = TaskHierarchy(project.tasks)
        amounts = self._allocate(project, hierarchy, hierarchy.get_roots(), None, {})
        unallocated = self._roll_up(project, hierarchy, amounts)

        return Budget(
            hierarchy = hierarchy,
            amounts = amounts,
            explicit = {task_id: task.budget
                        for task_id, task in project.tasks.items()
                        if task.budget is not None},
            weights = {task_id: task.budget_wt
                       for task_id, task in project.tasks.items()
                       if task.budget_wt is not None},
            unallocated = unallocated)

    def _allocate(self, project, hierarchy, task_ids, base, amounts) -> dict[str, Decimal]:
        """Resolve one level of siblings against their parent's allocation base.

        A task's allocation base is the resolved amount of its nearest budgeted
        ancestor. Weighted siblings share that base by percentage, while an
        explicitly budgeted task keeps its authored amount and replaces the base
        for its own descendants.
        """

        for task_id in task_ids:
            task = project.tasks[task_id]
            if task.budget is not None:
                amounts[task_id] = task.budget

        weighted_ids = [task_id for task_id in task_ids
                        if project.tasks[task_id].budget_wt is not None]

        if weighted_ids:
            amounts.update(self._distribute(project, base, weighted_ids))

        for task_id in task_ids:
            child_base = amounts.get(task_id)
            if child_base is None:
                child_base = base

            self._allocate(project, hierarchy, hierarchy.get_children(task_id), child_base, amounts)

        return amounts

    def _distribute(self, project, base, task_ids) -> dict[str, Decimal]:
        """Share a parent's amount between weighted children, in whole cents.

        Each child receives its percentage of the base floored to cents, and the
        cents left over are awarded to the largest fractional shares, in task
        number order. The children therefore sum to exactly the parent's amount,
        which a share that does not divide into whole cents (such as 10% of
        $45000.25) would otherwise not do.

        Percentage weights are expected to total 100%, which Project validation
        enforces.

        Raises:
            BudgetingError: If the siblings have no budgeted ancestor to draw on.
        """

        if base is None:
            raise BudgetingError(
                f"Task '{task_ids[0]}' has a weighted budget allocation but "
                f"no budgeted ancestor to allocate from.")

        total = self._to_cents(base)
        shares = []
        allocated = 0

        for task_id in task_ids:
            weight = project.tasks[task_id].budget_wt
            exact = base * weight / Decimal("100")
            cents = self._to_cents(exact)
            allocated += cents

            shares.append([task_id, exact - Decimal(cents), cents])

        # Largest fractional share first, breaking ties by task number.
        shares.sort(key=lambda share: (-share[1], share[0]))

        for index in range(total - allocated):
            shares[index % len(shares)][2] += 1

        return {share[0]: Decimal(share[2]) / 100 for share in shares}

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
        