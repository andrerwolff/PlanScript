import shutil
import textwrap

from decimal import Decimal, ROUND_HALF_UP

from planscript.model.project import Project
from planscript.engine.analyzer import Analyzer

CURRENCY = Decimal("0.01")
GREEN = "\033[32m"
RESET = "\033[0m"

def print_table(headers, rows, summary_row=None):
    """
    Print a formatted table.

    Long cell values are wrapped to fit the available terminal width.
    The original API is preserved.
    """
    terminal_width = shutil.get_terminal_size(fallback=(120, 24)).columns

    widths = calculate_col_widths(
        headers,
        rows,
        summary_row,
        max_width=terminal_width
    )

    table_width = sum(widths) + len(widths) + 1

    print("-" * table_width)
    print(format_row(headers, widths))
    print("-" * table_width)

    for row in rows:
        for line in format_wrapped_row(row, widths):
            print(line)

    if summary_row is not None:
        print("=" * table_width)
        for line in format_wrapped_row(summary_row, widths):
            print(line)

    print("-" * table_width)

    return table_width


def calculate_col_widths(
    headers,
    rows,
    summary_row=None,
    max_width=None,
    min_width=3,
    depths=None,
    indent_column=1,
    indent=2
):
    """
    Calculate column widths, including two characters of padding.

    min_width: minimum content width, excluding padding.
    max_width: maximum overall table width.
    depths: optional hierarchy depths for each row.
    indent_column: column receiving hierarchy indentation.
    indent: spaces per hierarchy level.
    """
    widths = []

    max_depth = max(depths, default=0) if depths else 0

    for col in range(len(headers)):
        width = len(str(headers[col]))

        for row in rows:
            if col < len(row):
                width = max(width, len(str(row[col])))

        if summary_row is not None and col < len(summary_row):
            width = max(width, len(str(summary_row[col])))

        if col == indent_column:
            width += max_depth * indent

        widths.append(max(width, min_width) + 2)

    if max_width is None:
        return widths

    available_width = max_width - len(widths) - 1

    while sum(widths) > available_width:
        largest = max(range(len(widths)), key=lambda i: widths[i])

        if widths[largest] <= min_width + 2:
            break

        widths[largest] -= 1

    return widths

def format_row(row, widths):
    """Format a single, non-wrapped table row."""
    parts = []

    for value, width in zip(row, widths):
        parts.append(f" {str(value):<{width - 2}} ")

    return "|" + "|".join(parts) + "|"


def format_wrapped_row(row, widths):
    """
    Format a row into one or more lines.

    Each cell wraps independently. Shorter cells are padded
    with blank lines to maintain table alignment.
    """
    wrapped_cells = []

    for value, width in zip(row, widths):
        content_width = max(1, width - 2)

        wrapped = textwrap.wrap(
            str(value),
            width=content_width,
            break_long_words=True,
            break_on_hyphens=False
        )

        wrapped_cells.append(wrapped or [""])

    if not wrapped_cells:
        return ["||"]

    line_count = max(len(cell) for cell in wrapped_cells)

    lines = []

    for line_number in range(line_count):
        parts = []

        for cell, width in zip(wrapped_cells, widths):
            value = cell[line_number] if line_number < len(cell) else ""
            parts.append(f" {value:<{width - 2}} ")

        lines.append("|" + "|".join(parts) + "|")

    return lines


def format_row_with_indent(row, widths, column=1, depth=0, indent=2):
    """Format a row with hierarchy indentation and wrapped text."""
    cells = []

    for index, (value, width) in enumerate(zip(row, widths)):
        content_width = width - 2

        if index == column:
            prefix = " " * (depth * indent)

            available_width = max(1, content_width - len(prefix))

            wrapped = textwrap.wrap(
                str(value),
                width=available_width,
                break_long_words=True,
                break_on_hyphens=False
            )

            wrapped = wrapped or [""]
            wrapped = [
                prefix + line for line in wrapped
            ]

        else:
            wrapped = textwrap.wrap(
                str(value),
                width=content_width,
                break_long_words=True,
                break_on_hyphens=False
            )

            wrapped = wrapped or [""]

        cells.append(wrapped)

    line_count = max(len(cell) for cell in cells)

    lines = []

    for line_number in range(line_count):
        parts = []

        for cell, width in zip(cells, widths):
            value = cell[line_number] if line_number < len(cell) else ""
            parts.append(f" {value:<{width - 2}} ")

        lines.append("|" + "|".join(parts) + "|")

    return lines

def print_table_with_indents(
    headers,
    rows,
    depths,
    summary_row=None,
    indent_column=1
):
    """
    Print a table with hierarchy indentation on selected rows.

    rows: list of table rows
    depths: corresponding hierarchy depths
    """
    terminal_width = shutil.get_terminal_size(
        fallback=(120, 24)
    ).columns

    widths = calculate_col_widths(
        headers,
        rows,
        summary_row,
        max_width=terminal_width,
        depths=depths,
        indent_column=indent_column
    )

    table_width = sum(widths) + len(widths) + 1

    print("-" * table_width)
    print(format_row(headers, widths))
    print("-" * table_width)

    for row, depth in zip(rows, depths):
        for line in format_row_with_indent(
            row,
            widths,
            column=indent_column,
            depth=depth
        ):
            print(line)

    if summary_row is not None:
        print("=" * table_width)

        for line in format_wrapped_row(summary_row, widths):
            print(line)

    print("-" * table_width)

    return table_width

def _format_currency(amount: Decimal | None) -> str:
    if amount is None or amount == Decimal("0"):
        return "-"
    amount = amount.quantize(CURRENCY, rounding=ROUND_HALF_UP)
    if amount < 0:
        return f"(${abs(amount):,})"

    return f"${amount:,}"
    
def display_task_with_dependencies(project, task):
    predecessors = project.get_predecessors(task)

    if predecessors:
        #TODO add type and lag values here        
        dependency_info = ", ".join(predecessor.number for predecessor in predecessors)
    else:
        dependency_info = "-"

    return f" {task} ({dependency_info})"
    
def view_project_header(project):
    print()
    print(f"    PROJECT: {project.name}")
    if project.schedule is not None:
        print(f"    Duration: {project.schedule.duration}")
    print(f"    Target Start: {project.start_date}")
    print(f"    Target Finish: {project.finish_date}")
    print("~" * 69)
    print()

def view_project_summary(project):
    view_project_header(project)
    print(f"Tasks:         {len(project.tasks)}")
    print(f"Dependencies:  {len(project.dependencies)}")

    if project.tracker.task_events:
        print(f"Tracking events: {len(project.tracker.task_events)}")
    else:
        print("Tracking:      Not started")

def view_critical_paths(project):
    print("Critical Path(s):")
    for path in project.schedule.critical_paths:
        print(" -> ".join(str(task) for task in path))
    
def view_schedule_calculated(project):
    schedule = project.schedule
    tree = schedule.hierarchy.get_tree()
    headers = ['ID','TASK','DUR','ES','EF','LS','LF','FLOAT']
    rows = []
    for task_id in tree:
        task = project.tasks[task_id]
        if schedule.hierarchy.is_summary(task_id):
            d,es,ef,ls,lf,f = ("-","-","-","-","-","-")
        else:
            d = task.duration.days
            es = schedule.early_start[task_id].days
            ef = schedule.early_finish[task_id].days
            ls = schedule.late_start[task_id].days
            lf = schedule.late_finish[task_id].days
            f = schedule.total_float[task_id].days

        rows.append([task_id,task.name,d,es,ef,ls,lf,f])
    print_table(headers, rows)
    print()

def view_schedule_scheduled(project):
    schedule = project.schedule
    if schedule.start_dates is None:
        print("Calculated schedule only: the project has no start date.")
        print("Add a 'start: YYYY-MM-DD' line to project dates onto a calendar.")
        print()
        return
    tree = schedule.hierarchy.get_tree()

    headers = ['ID','TASK','START','END','FLOAT']
    rows = []
    for task_id in tree:
        task = project.tasks[task_id]
        start = schedule.start_dates[task_id]
        end = schedule.finish_dates[task_id]
        total_float = schedule.total_float[task_id]
        if total_float is None:
            f = "-"
        else:
            f = total_float.days

        rows.append([tree[task_id], task.name, start.strftime('%#m/%#d/%y'), end.strftime('%#m/%#d/%y'), f])
    print_table(headers, rows)
    print()

def view_budget(project):
    budget = project.budget
    tree = budget.hierarchy.get_tree()

    headers = ['ID','TASK','BUDGET','BASIS']
    rows = []
    for task_id in tree:
        task = project.tasks[task_id]
        amount = budget.get(task_id)

        if amount is None:
            value = "-"
        else:
            value = f"${amount.quantize(CURRENCY, rounding=ROUND_HALF_UP):,}"

        if task_id in budget.explicit:
            basis = "explicit"
        elif task_id in budget.weights:
            basis = f"{budget.weights[task_id]}%"
        elif budget.hierarchy.is_summary(task_id):
            basis = "rollup"
        else:
            basis = "unallocated"

        rows.append([tree[task_id], task.name, value, basis])

    print_table(headers, rows)
    print(f"    Project Total: ${budget.total.quantize(CURRENCY, rounding=ROUND_HALF_UP):,}")
    if budget.unallocated:
        print(f"    Unallocated: {', '.join(budget.unallocated)}")
    print()

def view_cost_actuals(project: Project, as_of=None):
    tracker = project.tracker
    budget = project.budget
    analysis = Analyzer(project, as_of)

    tree = tracker.hierarchy.get_tree()

    headers = [
        'ID',
        'TASK',
        'BUDGET',
        'ACTUAL COST',
        'COST VARIANCE'
    ]

    rows_with_depth = []

    for task_id, tree_id in tree.items():
        task = project.tasks[task_id]

        depth = len(tree_id) - len(tree_id.lstrip(' '))

        row = [
            tree_id.strip(),
            task.name,
            _format_currency(budget.get(task_id)),
            _format_currency(tracker.actual_cost(task_id, as_of)),
            _format_currency(analysis.cost_variance(task_id))
        ]

        rows_with_depth.append((row, depth))

    total_cost_value = _format_currency(
        tracker.total_actual_cost(as_of)
    )
    total_budget_value = _format_currency(budget.total)
    total_variance_value = _format_currency(
        analysis.total_cost_variance()
    )

    summary_row = [
        '',
        'PROJECT TOTALS',
        total_budget_value,
        total_cost_value,
        total_variance_value
    ]

    rows = []

    depths = []

    for row, depth in rows_with_depth:
        adjusted_row = list(row)

        adjusted_row[1] = (
            " " * (depth * 2) + adjusted_row[1]
        )

        rows.append(adjusted_row)
        depths.append(depth)

    print_table_with_indents(
        headers,
        rows,
        depths,
        summary_row
    )

    print()