"""Synthetic large-plan generator and stage benchmark (ROADMAP P3-6).

`build_plan_text` produces a valid `.plan` document of a requested shape: a
three-level task hierarchy (group summary -> stage summary -> leaf tasks),
a single dependency chain across every leaf (so the whole network is one
critical path and critical-path enumeration stays linear), explicit budgets
on the leaves, tracking events on a fraction of the leaves, and invoices
allocating to the tracked leaves.

`benchmark` times each pipeline stage separately on generated plans so
scaling behaviour can be measured rather than guessed:

    parse (includes validate) -> schedule -> budget -> status build -> render

Run it directly for the measurement table:

    python -m planscript.tests.scale_bench [leaf_count ...]

With no arguments it measures roughly 300, 1,000, and 3,000 leaves. The
generator is shared with `test_scaling.py`.
"""

import sys
from datetime import date, timedelta
from decimal import Decimal
from time import perf_counter

from planscript.engine.budgeter import Budgeter
from planscript.engine.parser import Parser
from planscript.engine.reporter import ReportBuilder
from planscript.engine.scheduler import Scheduler

#: All generated events and invoices fall before this date, so a status
#: report taken here never truncates tracking data.
AS_OF = date(2026, 12, 31)

#: Fraction of leaves that carry a `start` event, and fraction of all
#: leaves that are also `complete`.
TRACKED_FRACTION = 0.4
COMPLETED_FRACTION = 0.2

#: Dollars allocated per task by each invoice, and tracked tasks per invoice.
INVOICE_UNIT = Decimal("10")
INVOICE_BATCH = 25


def build_plan_text(groups=30, stages=5, leaves_per_stage=20) -> str:
    """Return `.plan` text for a plan with the requested hierarchy shape.

    Total leaf tasks are `groups * stages * leaves_per_stage`; total tasks
    add the group and stage summaries. Every leaf is 5d with an explicit
    `$100` budget and (except the very first) a `FS` dependency on the
    previous leaf, forming one chain. The first 40% of leaves (in chain
    order) are started, the first 20% are also completed, and every 25
    tracked leaves are billed by one invoice that reconciles to its total.
    """
    total_leaves = groups * stages * leaves_per_stage
    tracked = int(total_leaves * TRACKED_FRACTION)
    completed = int(total_leaves * COMPLETED_FRACTION)

    lines = ["project: Scale Bench", "    start: 2026-01-01", ""]

    leaves = []
    previous_leaf = None
    for group in range(1, groups + 1):
        lines.append(f"task {group} Group {group}")
        for stage in range(1, stages + 1):
            lines.append(f"task {group}.{stage} Stage {group}.{stage}")
            for leaf in range(1, leaves_per_stage + 1):
                task_id = f"{group}.{stage}.{leaf}"
                leaves.append(task_id)
                lines.append(f"task {task_id} Task {task_id} 5d")
                if previous_leaf is not None:
                    lines.append(f"    depends {previous_leaf}")
                lines.append("    budget $100")
                previous_leaf = task_id
        lines.append("")

    lines.append(";Tracking")
    for index, task_id in enumerate(leaves):
        if index < completed:
            start = date(2026, 1, 1) + timedelta(days=index // 10)
            lines.append(f"{start} {task_id} start")
            lines.append(f"{start + timedelta(days=2)} {task_id} complete")
        elif index < tracked:
            start = date(2026, 1, 1) + timedelta(days=index // 10)
            lines.append(f"{start} {task_id} start")
    lines.append("")

    for first in range(0, tracked, INVOICE_BATCH):
        batch = leaves[first:min(first + INVOICE_BATCH, tracked)]
        invoice_date = date(2026, 1, 5) + timedelta(days=first // INVOICE_BATCH)
        total = INVOICE_UNIT * len(batch)
        lines.append(f"{invoice_date} invoice ${total}")
        for task_id in batch:
            lines.append(f"    {task_id} ${INVOICE_UNIT}")
        lines.append("")

    return "\n".join(lines) + "\n"


def benchmark(sizes, as_of=AS_OF):
    """Time each pipeline stage for every size and return the result rows.

    Each size is a target leaf count; it is split across 10 groups of 5
    stages so the hierarchy shape stays constant while the plan grows.
    Returns a list of dicts with the plan shape, stage seconds, and the
    rendered report length.
    """

    rows = []
    for target_leaves in sizes:
        groups = 10
        stages = 5
        leaves_per_stage = max(1, target_leaves // (groups * stages))
        text = build_plan_text(groups, stages, leaves_per_stage)

        start = perf_counter()
        project = Parser().parse(text)
        row = {"leaves": groups * stages * leaves_per_stage,
               "tasks": len(project.tasks),
               "events": len(project.tracker.task_events),
               "invoices": len(project.tracker.invoice_events),
               "parse": perf_counter() - start}

        start = perf_counter()
        project.schedule = Scheduler().calculate(project)
        row["schedule"] = perf_counter() - start

        start = perf_counter()
        project.budget = Budgeter().calculate(project)
        row["budget"] = perf_counter() - start

        start = perf_counter()
        report = ReportBuilder(project, as_of, timedelta(days=21)).build()
        row["status_build"] = perf_counter() - start

        start = perf_counter()
        row["render_chars"] = len(report.render_text())
        row["render"] = perf_counter() - start

        rows.append(row)
    return rows


def _format_seconds(value):
    """Format seconds compactly for the benchmark table."""

    if value < 0.001:
        return f"{value * 1e6:.0f}us"
    if value < 1:
        return f"{value * 1e3:.1f}ms"
    return f"{value:.2f}s"


_TIMED_COLUMNS = ("parse", "schedule", "budget", "status_build", "render")
_COLUMNS = ("leaves", "tasks", "events", "invoices") + _TIMED_COLUMNS


def main(argv=None):
    """Print the per-stage timing table for the requested leaf counts."""

    argv = list(sys.argv[1:] if argv is None else argv)
    sizes = [int(arg) for arg in argv] or [300, 1000, 3000]

    print("  ".join(f"{name:>12}" for name in _COLUMNS))
    for row in benchmark(sizes):
        cells = []
        for name in _COLUMNS:
            value = row[name]
            if name in _TIMED_COLUMNS:
                cells.append(f"{_format_seconds(value):>12}")
            else:
                cells.append(f"{value:>12,}")
        print("  ".join(cells))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


