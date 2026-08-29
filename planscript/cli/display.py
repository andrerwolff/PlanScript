from planscript.model.task import Task


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

def show_schedule_menu(project, schedule):
    print()
    print("=" * 50)
    print(f"  Project: {project.name}")
    print("=" * 50)
    print()
    print("  [C] View Schedule Calculated Values")
    print("  [D] View Schedule Dates")
    print("  [G] View Gantt Chart")
    print("  [B] Back to Main Menu")
    print("  [Q] Quit")
    print()
    
    return input("  Select an option: ").strip().lower()
    

def view_schedule_calculated(project, schedule):
    print()
    print(f"    PROJECT: {project.name}")
    print(f"    Duration: {schedule.duration}")
    print(f"    Target Start: {schedule.project.start_date}")
    print(f"    Target Finish: {schedule.project.finish_date}")
    print("~" * 69)
    print()
    print(f"|{'ID':<5}|{'TASK':<25}|{'DUR':^5}|{'ES':^5}|{'EF':^5}|{'LS':^5}|{'LF':^5}|{'FLOAT':^5}|")
    print("-" *69)

    for task_id in schedule.ordered_task_ids:
        task = schedule.project.tasks[task_id]

        d = task.duration.days
        es = schedule.early_start[task_id].days
        ef = schedule.early_finish[task_id].days
        ls = schedule.late_start[task_id].days
        lf = schedule.late_finish[task_id].days
        f = schedule.total_float[task_id].days

        print(f" {task_id:<5} {task.name:<25} {d:^5} {es:^5} {ef:^5} {ls:^5} {lf:^5} {f:^5} ")
    print(f"-"* 69)
    print()
    print("Critical Path(s):")
    for path in schedule.critical_paths:
        print(" → ".join(str(task) for task in path))
    input("Press Enter to continue...")

def view_schedule_scheduled(project, schedule):
    print()
    print(f"    PROJECT: {project.name}")
    print(f"    Duration: {schedule.duration}")
    print(f"    Target Start: {schedule.project.start_date}")
    print(f"    Target Finish: {schedule.project.finish_date}")
    print("~" * 69)
    print()
    print(f"|{'ID':<5}|{'TASK':<25}|{'START':^10}|{'END':^10}|{'FLOAT':^7}|")
    print("-" *69)

    for task_id in schedule.ordered_task_ids:
        task = schedule.project.tasks[task_id]
        start = schedule.start_dates[task_id]
        end = schedule.finish_dates[task_id]
        f = schedule.total_float[task_id].days

        print(f" {task_id:<5} {task.name:<25} {start.strftime('%#m/%#d/%y'):^10} {end.strftime('%#m/%#d/%y'):^10} {f:^7} ")
    print(f"-"* 69)
    print()
    print("Critical Path(s):")
    for path in schedule.critical_paths:
        print(" → ".join(str(task) for task in path))
    input("Press Enter to continue...")
    return f"-"* 69