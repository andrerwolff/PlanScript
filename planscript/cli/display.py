from operator import attrgetter

from planscript.model.task import Task


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

    


def show_main_menu():
    print()
    print("=" * 50)
    print("                     PlanScript")
    print("=" * 50)
    print()
    print("  [N] New Project")
    print("  [O] Open Project")
    print("  [R] Recent Projects")
    print("  [Q] Quit")
    print()

    return input("  Select an option: ").strip().lower()


def show_project_menu(project):
    print()
    print("=" * 50)
    print(f"  Project: {project.name}")
    print("=" * 50)
    print()
    print("  [T] Tasks")
    print("  [D] Dependencies")
    print("  [P] Project Properties")
    print("  [V] View Schedule")
    print("  [L] Inspect Log")
    print("  [S] Save Project")
    print("  [B] Back to Main Menu")
    print("  [Q] Quit")
    print()

    return input("  Select an option: ").strip().lower()


def show_task_menu(project):
    tasks = project.list_tasks()

    print()
    print("=" * 50)
    print(f"{project.name}: Tasks")
    print("=" * 50)
    print()
    if tasks:
        for task in tasks:
            print(display_task_with_dependencies(project, task))
    else:
        print("  No Tasks Found.")
    print()
    print("  [N] New Task")
    print("  [E] Edit Task")
    print("  [X] Delete Task")
    print("  [B] Back to Project Menu")
    print()

    return input("  Select an option: ").strip().lower()


def show_task_edit_menu(project, task):
    print()
    print("-" * 50)
    print(f"  Edit Task: {display_task_with_dependencies(project, task)}")
    print("-" * 50)
    print()
    print("  [#] Edit Task Number")
    print("  [N] Edit Name")
    print("  [D] Edit Duration")
    print("  [S] Edit Start Date")
    print("  [F] Edit Finish Date")
    print("  [P] Edit Predecessors")
    print("  [B] Back to Task Menu")
    print()

    return input("  Select an option: ").strip().lower()


def show_dependency_menu(project):
    dependencies = project.dependencies

    print()
    print("=" * 50)
    print(f"{project.name}: Dependencies")
    print("=" * 50)
    print()
    if dependencies:
        for dependency in dependencies:
            print(f"  {dependency}")
    else:
        print("  No Dependencies Found.")
    print()
    print("  [N] New Dependency")
    print("  [E] Edit Dependency")
    print("  [X] Delete Dependency")
    print("  [B] Back to Project Menu")
    print()

    return input("  Select an option: ").strip().lower()

def show_depend_edit_menu(project, dependency):
    print()
    print("-" * 50)
    print(f"  Edit Dependency: {dependency}")
    print("-" * 50)
    print()
    print("  [P] Edit Predecessor")
    print("  [S] Edit Successor")
    print("  [T] Edit Type")
    print("  [L] Edit Lag")
    print("  [B] Back to Dependency Menu")
    print()

    return input("  Select an option: ").strip().lower()

def display_task_with_dependencies(project, task):
    predecessors = project.get_predecessors(task)

    if predecessors:
        #TODO add type and lag values here        
        dependency_info = ", ".join(predecessor.number for predecessor in predecessors)
    else:
        dependency_info = "-"

    return f" {task} ({dependency_info})"

def select_task(project, action: str) -> Task:
    for task in project.list_tasks():
            task_info = display_task_with_dependencies(project, task)
            print(f"[{project.list_tasks().index(task)}] {task_info}")

    task_index = input(f"Select Task to {action}: ")

    if not task_index.isdigit():
            print("Invalid selection.")
            return
        
    task_index = int(task_index)

    if 0 <= task_index < len(project.list_tasks()):
            return project.list_tasks()[task_index]
    else:
        print("Invalid task index.")
        return

def select_dependency(project, action: str):
    for dep in project.dependencies:
        print(f"[{project.dependencies.index(dep)}]  {dep}")

    dependency_index = input(f"Select Dependency to {action}: ")

    if not dependency_index.isdigit():
        print("Invalid selection.")
        return
    
    dependency_index = int(dependency_index)

    if 0 <= dependency_index < len(project.dependencies):
        return project.dependencies[dependency_index]
    else:
        print("Invalid dependency index.")
        return

def show_schedule_menu(project):
    print()
    print("=" * 50)
    print(f"  Project: {project.name}")
    print("=" * 50)
    print()
    print("  [C] View Schedule Calculated Values")
    print("  [D] View Schedule Dates")
    print("  [G] View Gantt Chart")
    print("  [B] Back to Main Menu")
    print()
    
    return input("  Select an option: ").strip().lower()
    
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

    if project.tracker.events:
        print(f"Tracking events: {len(project.tracker.events)}")
    else:
        print("Tracking:      Not started")

def view_critical_paths(project):
    print("Critical Path(s):")
    for path in project.schedule.critical_paths:
        print(" → ".join(str(task) for task in path))
    
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

def render_log(project):
    print()
    print(f"    PROJECT: {project.name}")
    print("-" * 50)
    print("|| Begin Log ||")
    print("-" * 25)
    for event in project.tracker.get_events():
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
    