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