from datetime import date, timedelta
from pathlib import Path

from planscript.model import Project, Task, Dependency, DependencyType
from planscript.cli import display
from planscript.engine.scheduler import Scheduler
from planscript.tests import test_projects
from planscript.parser.parser import Parser, ParseError


# Menus
def main_menu():
    project = None

    while True:
        choice = display.show_main_menu()

        if choice == "n":
            project = new_project()
            if project:
                project_menu(project)
            else:
                print("No project created. Returning to main menu.")
                continue

        elif choice == "o":
            choice2 = input("Select test project: ")
            if choice2 == "f":
                file = Path("examples/simple.plan")
                text = file.read_text(encoding="utf-8")
                parser = Parser()
                try:
                    project = parser.parse(text)
                except ParseError as e:
                    print(f"Parse error: {e}")
                    input("\nPress Enter to return...")
                    continue

                print(f"Project: {project.name}")
                print(f"Tasks: {len(project.tasks)}")
                print(f"Dependencies: {len(project.dependencies)}")
                
            else:
                project_builder = test_projects.TEST_PROJECTS[choice2]
                project = project_builder()

            if project:
                project_menu(project)
            else:
                print("No project opened. Returning to main menu.")
                continue

        elif choice == "r":
            # Implement recent projects functionality here
            pass

        elif choice == "q":
            break

        else:
            print("Invalid Option.")
            continue

def project_menu(project):

    while True:
        choice = display.show_project_menu(project)

        if choice == "t":
            task_menu(project)

        elif choice == "d":
            dependency_menu(project)

        elif choice == "p":
            # Implement project properties functionality here
            print("Project Properties functionality is not yet implemented.")
            pass

        elif choice == "v":
            scheduler = Scheduler()
            try:
                schedule = scheduler.calculate(project)
            except ValueError as e:
                print(f"Scheduling error: {e}")
                return
            print(schedule)

        elif choice == "s":
            # Implement save project functionality here
            print("Save Project functionality is not yet implemented.")
            pass

        elif choice == "b":
            #project = None  <- May need this to reset the project variable when returning to main menu
            break

        elif choice == "q":
            print("Exiting the application.")
            exit()

def task_menu(project):
    while True:
        choice = display.show_task_menu(project)

        if choice == "n":
            new_task(project)

        elif choice == "e":
            print("\nEDIT TASK")
            print("-" * 50)
            print()
            task_to_edit = display.select_task(project, "Edit")
            if task_to_edit:
                edit_task_menu(project, task_to_edit)
            else:
                print("Invalid task index.")
                continue

        elif choice == "x":
            print("\nDELETE TASK")
            print("-" * 50)
            print()
            task_to_remove = display.select_task(project, "Delete")
            if task_to_remove:
                project.remove_task(task_to_remove.number)
            else:
                print("Task not found.")

        elif choice == "b":
            break

        else:
            print("Invalid Option t.")
            continue

def edit_task_menu(project, task):
    while True:
        choice = display.show_task_edit_menu(project, task)

        if choice == "#":
            new_number = input("Enter new task number: ")
            if new_number in project.tasks:
                print(f"Task number '{new_number}' already exists in the project. Please choose a different number.")
                continue
            project.renumber_task(task.number, new_number)
            print(f"Task number updated to '{new_number}'.")
            project.sort_tasks()  # Ensure tasks are sorted after renumbering
            continue  # Return to the edit menu after renumbering
            

        if choice == "n":
            new_name = input("Enter new task name: ")
            task.name = new_name
            print(f"Task name updated to '{new_name}'.")

        elif choice == "d":
            # Implement edit task duration functionality here
            print("Edit Task Duration functionality is not yet implemented.")
            pass

        elif choice == "b":
            break

        else:
            print("Invalid Option et.")
            continue

def dependency_menu(project):
    while True:
        choice = display.show_dependency_menu(project)

        if choice == "n":
            new_dependency(project)
        
        elif choice == "e":
            print("\nEDIT DEPENDENCY")
            print("-" * 50)
            print()
            dependency_to_edit = display.select_dependency(project, "Edit")
            if dependency_to_edit:
                edit_dependency_menu(project, dependency_to_edit)
            else:
                print("Invalid dependency index.")
                continue

        elif choice == "x":
            print("\nDELETE DEPENDENCY")
            print("-" * 50)
            print()
            dependency_to_remove = display.select_dependency(project, "Delete")
            if dependency_to_remove:
                project.remove_dependency(dependency_to_remove)
            else:
                print("Dependency not found.")

        elif choice == "b":
            break

        else:
            print("Invalid Option d.")
            continue

def edit_dependency_menu(project, dependency):
    while True:
        choice = display.show_depend_edit_menu(project, dependency)

        if choice == "p":
            # TODO add check if task is the same as successor
            new_number = input("Enter new predecessor task number: ").strip()
            if new_number not in project.tasks:
                print(f"Task number '{new_number}' does not exist in the project. Please choose a different number.")
                continue
            dependency.predecessor = project.tasks[new_number]
            
        if choice == "s":
            #TODO add check if task is the same as successor
            new_number = input("Enter new successor task number: ").strip()
            if new_number not in project.tasks:
                print(f"Task number '{new_number}' does not exist in the project. Please choose a different number.")
                continue
            dependency.successor = project.tasks[new_number]

        elif choice == "t":
            print("Edit dependency type functionality is not yet implemented.")
            pass

        elif choice == "l":
            print("Edit dependency lag functionality is not yet implemented.")

        elif choice == "b":
            break

        else:
            print("Invalid Option et.")
            continue    

#Project Functions
def new_project():
    print("\nNEW PROJECT")
    print("-" * 50)
    print()
    proj_name = input("Project Name: ")

    create = input(f"Create project '{proj_name}'? (y/n): ").strip().lower()
    if create != 'y':
        print("Project creation cancelled.")
        return None
    project = Project(name=proj_name)

    print("\nProject created!\n")
    print(f"Project Name: {project.name}")
    print("Location: File system (not yet implemented)")
    print("File: (not yet implemented)")
    print()
    input("Press Enter to continue...")
    return project

def open_project():
    project = Project("Test Project")

    project.add_task(Task("1.1", "PM", timedelta(days=100)))
    project.add_task(Task("2.1", "Design", timedelta(days=200)))
    project.add_task(Task("3.1", "Construction", timedelta(days=300)))
    project.add_task(Task("4.1", "Closeout", timedelta(days=20)))

    project.add_dependency(project.tasks["2.1"], project.tasks["3.1"], lag=timedelta(days=10))
    project.add_dependency(project.tasks["3.1"], project.tasks["4.1"])
    project.add_dependency(project.tasks["1.1"], project.tasks["4.1"], DependencyType.FINISH_FINISH, timedelta(days=14))

    return project

#Task Functions
def new_task(project):
    print("\nNEW TASK")
    print("-" * 50)
    print()
    task_number = input("Task Number: ")
    task_name = input("Task Name: ")
    task_duration = int(input("Duration (days): "))

    predecessors = []
    while True:
        predecessor = input("Enter a predecessor task number (or press Enter to finish): ").strip()
        if not predecessor:
            break
        if predecessor not in project.tasks:
            print(f"Task with number '{predecessor}' does not exist in the project. Please enter a valid task number.")
            continue
        predecessors.append(predecessor)
    if predecessors:
        print(f"Predecessors: {', '.join(predecessors)}")

    create = input(f"Create Task? (y/n): ").strip().lower()
    if create != 'y':
        print("Task creation cancelled.")
        return None

    new_task = Task(
            number=task_number,
            name=task_name,
            duration=timedelta(days=task_duration),
        )

    project.add_task(new_task)
    print(f"\nTask '{new_task.number} - {new_task.name}' added to project '{project.name}'.\n")

    for predecessor in predecessors:
        successor = new_task
        project.add_dependency(project.tasks[predecessor], successor)



#Dependency Functions
def new_dependency(project):
    # TODO: control for predecessor and successor being the same number
    print("\nNEW DEPENDENCY")
    print("-" * 50)
    print()

    predecessor_number = input("Predecessor Task Number: ").strip()
    try:
        predecessor = project.tasks[predecessor_number]
    except KeyError:
        print(f"Predecessor task with number '{predecessor_number}' does not exist in the project.")
        return
    successor_number = input("Successor Task Number: ").strip()
    try:
        successor = project.tasks[successor_number]
    except KeyError:
        print(f"Successor task with number '{successor_number}' does not exist in the project.")
        return
    
    dep_type_input = input("Dependency Type (FS, SS, FF, SF) [default FS]: ").strip().upper()
    dep_type = DependencyType.FINISH_START  # Default
    if dep_type_input:
        try:
            dep_type = DependencyType(dep_type_input)
        except ValueError:
            print(f"Invalid dependency type '{dep_type_input}'. Using default 'FS'.")

    lag_days_input = input("Lag (days) [default 0]: ").strip()
    lag_days = 0
    if lag_days_input:
        try:
            lag_days = int(lag_days_input)
        except ValueError:
            print(f"Invalid lag value '{lag_days_input}'. Using default 0.")

    project.add_dependency(predecessor, successor, dep_type, timedelta(days=lag_days))

def delete_dependency(project):
    print("\nDELETE DEPENDENCY")
    print("-" * 50)
    print()
   
    if dependency_to_remove:
        project.remove_dependency(dependency_to_remove)
    else:
        print("Dependency not found.")