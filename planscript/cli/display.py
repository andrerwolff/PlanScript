from operator import attrgetter
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from planscript.model.task import Task
from planscript.model.project import Project

CURRENCY = Decimal("0.01")


class Table:
    def __init__(self, headers, rows):
        self.headers = headers
        self.rows = rows

    def render(self):
        pass
    def print(self):
        print(self.render())

def print_table(headers, rows):
    widths = calculate_col_widths(headers, rows)
    table_width = sum(widths)+len(widths)+1

    print("-"*table_width)
    print(format_row(headers, widths))
    print("-"*table_width)
    for row in rows:
        print(format_row(row, widths))
    print("-"*table_width)
    return table_width

def calculate_col_widths(headers, rows):
    widths = []
    for col in range(len(headers)):
        width = len(str(headers[col]))+2

        for row in rows:
            width = max(width, len(str(row[col]))+2)

        widths.append(width)
    return widths

def format_row(row, widths):
    parts = []

    for value, width in zip(row, widths):
        parts.append(f"{str(value):<{width}}")

    return "|"+"|".join(parts)+"|"


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
        amount = budget.amounts.get(task_id)

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

def view_cost_actuals(project:Project):
    tracker = project.tracker
    tree = tracker.hierarchy.get_tree()
    total_cost = 0

    headers = ['ID','TASK','ACTUAL COST']
    rows = []
    for task_id in tree:
        task = project.tasks[task_id]
        cost = tracker.actual_cost(task_id)
        if task_id in tracker.hierarchy.get_roots():
            total_cost += cost

        tree_id = tree[task_id]
        level = (len(tree_id) - len(tree_id.lstrip(' ')))*2

        if cost is None or cost == Decimal("0"):
            value = "-"
        else:
            value = f"${cost.quantize(CURRENCY, rounding=ROUND_HALF_UP):,}"
        value = f"{' '*level}" + value
        rows.append([tree[task_id], task.name, value])

    width = print_table(headers, rows)
    str = f"Project Total Cost: ${total_cost}"
    leading_space = width - len(str)-5
    print(f"|{' '*leading_space}{str}   |")
    print(f"-"*width)
    print()

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
    