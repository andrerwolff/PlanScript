import unittest
from datetime import timedelta
from decimal import Decimal

from planscript.engine.budgeter import Budgeter
from planscript.exceptions import BudgetingError
from planscript.model.project import Project
from planscript.model.task import Task
from planscript.tests import test_projects


class TestBudgeterExamples(unittest.TestCase):

    def test_explicit_children_roll_up_to_summary(self):
        project = test_projects.simple_budget()

        budget = Budgeter().calculate(project)

        self.assertEqual(budget.amounts["1"], Decimal("9650.25"))

    def test_weighted_children_split_parent_budget(self):
        project = test_projects.simple_budget()

        budget = Budgeter().calculate(project)

        self.assertEqual(budget.amounts["2.1"], Decimal("25000"))
        self.assertEqual(budget.amounts["2.2"], Decimal("225000"))

    def test_nested_weights_use_parent_amount(self):
        project = test_projects.simple_budget()

        budget = Budgeter().calculate(project)

        self.assertEqual(budget.amounts["2.1.1"], Decimal("10000"))
        self.assertEqual(budget.amounts["2.1.2"], Decimal("15000"))

    def test_summary_amount_equals_sum_of_children(self):
        project = test_projects.simple_budget()

        budget = Budgeter().calculate(project)

        self.assertEqual(
            budget.amounts["2.1"],
            budget.amounts["2.1.1"] + budget.amounts["2.1.2"])

        self.assertEqual(
            budget.amounts["2"],
            budget.amounts["2.1"] + budget.amounts["2.2"])

    def test_weighted_shares_are_allocated_in_whole_cents(self):
        project = test_projects.simple_budget()

        budget = Budgeter().calculate(project)

        # 10% of $45000.25 is $4500.025. The leftover cent goes to the largest
        # fractional share, which ties 3.1 and 3.4, so 3.1 wins on task number
        # and the children still sum to the parent.
        self.assertEqual(budget.amounts["3.1"], Decimal("4500.03"))
        self.assertEqual(budget.amounts["3.2"], Decimal("18000.10"))
        self.assertEqual(budget.amounts["3.3"], Decimal("18000.10"))
        self.assertEqual(budget.amounts["3.4"], Decimal("4500.02"))

        self.assertEqual(
            budget.amounts["3"],
            sum(budget.amounts[task_id] for task_id in ("3.1", "3.2", "3.3", "3.4")))

    def test_leftover_cent_goes_to_largest_share(self):
        project = Project("Remainder")
        project.add_task(Task("1", "Summary", None, budget=Decimal("10")))
        project.add_task(Task("1.1", "Smallest", timedelta(days=1), budget_wt=Decimal("33.33")))
        project.add_task(Task("1.2", "Middle", timedelta(days=1), budget_wt=Decimal("33.33")))
        project.add_task(Task("1.3", "Largest", timedelta(days=1), budget_wt=Decimal("33.34")))

        budget = Budgeter().calculate(project)

        self.assertEqual(budget.amounts["1.1"], Decimal("3.33"))
        self.assertEqual(budget.amounts["1.2"], Decimal("3.33"))
        self.assertEqual(budget.amounts["1.3"], Decimal("3.34"))

    def test_all_allocations_are_whole_cents(self):
        project = test_projects.simple_budget()

        budget = Budgeter().calculate(project)

        for task_id, amount in budget.amounts.items():
            self.assertEqual(amount, amount.quantize(Decimal("0.01")), task_id)

    def test_project_total_sums_root_tasks_only(self):
        project = test_projects.simple_budget()

        budget = Budgeter().calculate(project)

        self.assertEqual(budget.total, Decimal("304650.50"))

    def test_unallocated_tasks_are_reported(self):
        project = test_projects.simple_budget()

        budget = Budgeter().calculate(project)

        self.assertEqual(budget.unallocated, ["4", "4.1"])
        self.assertNotIn("4", budget.amounts)
        self.assertNotIn("4.1", budget.amounts)

    def test_authored_values_are_retained(self):
        project = test_projects.simple_budget()

        budget = Budgeter().calculate(project)

        self.assertEqual(budget.explicit["2"], Decimal("250000"))
        self.assertEqual(budget.weights["2.2"], Decimal("90"))
        self.assertNotIn("2.1.1", budget.explicit)

    def test_hierarchy_is_included(self):
        project = test_projects.simple_budget()

        budget = Budgeter().calculate(project)

        self.assertEqual(budget.hierarchy.get_roots(), ["1", "2", "3", "4"])

    def test_fixture_is_a_valid_plan(self):
        test_projects.simple_budget().validate()


class TestBudgeterEdges(unittest.TestCase):

    def test_empty_project_has_no_budget(self):
        project = Project("Empty")

        with self.assertRaises(BudgetingError):
            Budgeter().calculate(project)

    def test_partial_summary_rolls_up_resolvable_children(self):
        project = Project("Partial")
        project.add_task(Task("1", "Summary"))
        project.add_task(Task("1.1", "Budgeted", timedelta(days=1), budget=Decimal("100")))
        project.add_task(Task("1.2", "Unbudgeted", timedelta(days=1)))

        budget = Budgeter().calculate(project)

        self.assertEqual(budget.amounts["1"], Decimal("100"))
        self.assertEqual(budget.unallocated, ["1.2"])

    def test_unbudgeted_project_totals_zero(self):
        project = Project("Unbudgeted")
        project.add_task(Task("1", "Summary"))
        project.add_task(Task("1.1", "Task", timedelta(days=1)))

        budget = Budgeter().calculate(project)

        self.assertEqual(budget.amounts, {})
        self.assertEqual(budget.unallocated, ["1", "1.1"])
        self.assertEqual(budget.total, Decimal("0"))

    def test_weighted_task_without_budgeted_ancestor(self):
        project = Project("Weighted Root")
        project.add_task(Task("1", "Task", timedelta(days=1), budget_wt=Decimal("50")))

        with self.assertRaises(BudgetingError):
            Budgeter().calculate(project)

    def test_budget_does_not_modify_the_project(self):
        project = test_projects.simple_budget()

        Budgeter().calculate(project)

        self.assertEqual(project.tasks["2"].budget, Decimal("250000"))
        self.assertIsNone(project.tasks["2.1.1"].budget)
        self.assertEqual(project.tasks["2.1.1"].budget_wt, Decimal("40"))


if __name__ == "__main__":
    unittest.main()
