from operator import attrgetter
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from planscript.model.task import Task
from planscript.model.project import Project
from planscript.engine.analyzer import Analyzer

CURRENCY = Decimal("0.01")
GREEN = "\033[32m"
RESET = "\033[0m"

class Table:
    def __init__(self, headers, rows):
        self.headers = headers
        self.rows = rows

    def render(self):
        pass
    def print(self):
        print(self.render())

def print_table(headers, rows, summary_row=None):
    widths = calculate_col_widths(headers, rows, summary_row)
    table_width = sum(widths)+len(widths)+1

    print("-"*table_width)
    print(format_row(headers, widths))
    print("-"*table_width)
    for row in rows:
        print(format_row(row, widths))
    
    if summary_row:
        print("="*table_width)
        print(format_row(summary_row, widths))
        
    print("-"*table_width)
    return table_width

def calculate_col_widths(headers, rows, summary_row):
    widths = []
    for col in range(len(headers)):
        width = len(str(headers[col]))+2

        for row in rows:
            width = max(width, len(str(row[col]))+2)

        if summary_row is not None:
            width = max(width, len(str(summary_row[col]))+2)

        widths.append(width)
    return widths

def format_row(row, widths):
    parts = []

    for value, width in zip(row, widths):
        parts.append(f"{str(value):<{width}}")

    return "|"+"|".join(parts)+"|"

def _format_currency(amount:Decimal | None) -> str:
    if amount is None or amount == Decimal("0"):
        return "-"
    amount = amount.quantize(CURRENCY, rounding=ROUND_HALF_UP)
    if amount.is_signed() and not amount.is_zero():
        return f"(${abs(amount):,})" # TODO add colors to tables, green good red bad
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

def view_cost_actuals(project:Project, as_of=None):
    tracker = project.tracker
    budget = project.budget
    analysis = Analyzer(project, as_of) 
    tree = tracker.hierarchy.get_tree()

    headers = ['ID','TASK','BUDGET', 'ACTUAL COST', 'COST VARIANCE']
    rows = []
    for task_id in tree:
        task_name = project.tasks[task_id].name
        
        plan = budget.get(task_id)
        tree_id = tree[task_id]
        level = (len(tree_id) - len(tree_id.lstrip(' ')))*2
        
        plan_value = _format_currency(plan)
        plan_value = f"{' '*level}" + plan_value

        cost_value = _format_currency(tracker.actual_cost(task_id, as_of))
        cost_value = f"{' '*level}" + cost_value

        variance_value = _format_currency(analysis.cost_variance(task_id))
        variance_value = f"{' '*level}" + variance_value

        rows.append([tree[task_id], task_name, plan_value, cost_value, variance_value])
    
    total_cost_value = _format_currency(tracker.total_actual_cost(as_of))
    total_budget_value = _format_currency(budget.total)
    total_variance_value = _format_currency(analysis.total_cost_variance())
    
    summary_row = ['','PROJECT TOTALS', total_budget_value, total_cost_value, total_variance_value]
    print_table(headers, rows, summary_row)

def render_log(project):
    print()
    print(f"    PROJECT: {project.name}")
    print("-" * 50)
    print("|| Begin Log ||")
    print("-" * 25)
    for event in project.tracker.get_all_task_events():
        print(event)
    print("-" * 25)
    print("|| End Log ||")
    print("-" * 50)
    print(project.tracker.get_task_state("1.1"))
    print(project.tracker.get_task_state("1.2"))
    print(project.tracker.get_task_state("3.1"))
    print(project.tracker.get_task_state("3.2"))
    print(project.tracker.get_task_state("4.2.2"))
    input("Press Enter to continue...")
    return f"-"* 69
    