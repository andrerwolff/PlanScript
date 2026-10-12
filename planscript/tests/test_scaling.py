"""Scaling tests for plans of a few thousand tasks (ROADMAP P3-6).

These pin what `scale_bench.py` measures: the pipeline stays correct on a
generated plan of a few thousand tasks, a long dependency chain schedules
without hitting Python's recursion limit, and the whole status pipeline
completes within a generous ceiling so a return of superlinear behaviour
is caught without making the suite flaky on slow machines.

Run the per-stage timing table directly with:

    python -m planscript.tests.scale_bench [leaf_count ...]
"""

import unittest
from decimal import Decimal
from time import perf_counter

from planscript.engine.budgeter import Budgeter
from planscript.engine.parser import Parser
from planscript.engine.reporter import ReportBuilder
from planscript.engine.scheduler import Scheduler
from planscript.engine.tracker import TaskStatus
from planscript.tests.scale_bench import AS_OF, build_plan_text

#: Generous wall-clock ceiling for the whole 3,000-leaf pipeline. Measured
#: locally at roughly 1.5s; the ceiling only exists to catch a return of
#: behaviour measured in minutes, not to benchmark the machine.
PIPELINE_CEILING_SECONDS = 30

#: Hierarchy shape for the "few thousand tasks" plan: 3,000 leaves plus
#: 150 stage summaries and 10 group summaries.
GROUPS = 10
STAGES = 5
LEAVES_PER_STAGE = 60


class TestLargePlanScaling(unittest.TestCase):
    """The generated few-thousand-task plan parses, schedules, and reports."""

    @classmethod
    def setUpClass(cls):
        cls.text = build_plan_text(GROUPS, STAGES, LEAVES_PER_STAGE)
        cls.total_leaves = GROUPS * STAGES * LEAVES_PER_STAGE
        cls.total_tasks = cls.total_leaves + GROUPS * STAGES + GROUPS

    def test_generated_plan_parses_with_expected_shape(self):
        project = Parser().parse(self.text)

        self.assertEqual(len(project.tasks), self.total_tasks)
        self.assertEqual(len(project.dependencies), self.total_leaves - 1)
        self.assertEqual(len(project.tracker.task_events), int(self.total_leaves * 0.6))
        self.assertEqual(len(project.tracker.invoice_events), int(self.total_leaves * 0.4) // 25)

    def test_long_dependency_chain_schedules_as_one_critical_path(self):
        # A chain longer than Python's recursion limit used to crash
        # critical-path enumeration with RecursionError.
        project = Parser().parse(self.text)
        project.schedule = Scheduler().calculate(project)

        self.assertEqual(len(project.schedule.critical_paths), 1)
        self.assertEqual(len(project.schedule.critical_paths[0]), self.total_leaves)

    def test_tracking_state_and_costs_at_scale(self):
        project = Parser().parse(self.text)
        project.schedule = Scheduler().calculate(project)
        project.budget = Budgeter().calculate(project)
        tracker = project.tracker

        # The generator tracks leaves in dependency-chain order, which is
        # not the string-sorted order the hierarchy returns.
        chain = [f"{group}.{stage}.{leaf}"
                 for group in range(1, GROUPS + 1)
                 for stage in range(1, STAGES + 1)
                 for leaf in range(1, LEAVES_PER_STAGE + 1)]

        completed, tracked = int(self.total_leaves * 0.2), int(self.total_leaves * 0.4)

        self.assertEqual(tracker.get_task_state(chain[0], AS_OF).status,
                         TaskStatus.COMPLETED)
        self.assertEqual(tracker.get_task_state(chain[completed], AS_OF).status,
                         TaskStatus.STARTED)
        self.assertEqual(tracker.get_task_state(chain[tracked], AS_OF).status,
                         TaskStatus.NOT_STARTED)

        self.assertEqual(tracker.actual_cost(chain[0], AS_OF), Decimal("10"))
        self.assertEqual(tracker.actual_cost(chain[tracked], AS_OF), Decimal("0"))
        self.assertEqual(tracker.total_actual_cost(AS_OF), Decimal(tracked * 10))
        self.assertEqual(project.budget.total, Decimal(self.total_leaves * 100))

    def test_status_pipeline_stays_within_ceiling(self):
        start = perf_counter()
        project = Parser().parse(self.text)
        project.schedule = Scheduler().calculate(project)
        project.budget = Budgeter().calculate(project)
        report = ReportBuilder(project, AS_OF).build()
        rendered = report.render_text()
        elapsed = perf_counter() - start

        self.assertEqual(report.name, "Scale Bench")
        # The report lists one entry per leaf task (summaries are rolled up).
        self.assertEqual(len(report.all_tasks), self.total_leaves)
        self.assertIn("Status Report", rendered)
        self.assertLess(elapsed, PIPELINE_CEILING_SECONDS,
                        f"3,000-leaf pipeline took {elapsed:.1f}s "
                        f"(ceiling {PIPELINE_CEILING_SECONDS}s); profile with "
                        "python -m planscript.tests.scale_bench")
