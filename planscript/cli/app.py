from datetime import date, timedelta

from planscript.model.project import Project
from planscript.cli.display import *



def main():
    print("PlanScript")
    print("==========")
    project = None

    actions = {
                "n": new_project,
                "o": open_project,
                "q": quit,
            }
    
    while True:
        choice = main_menu()

        action = actions.get(choice)

        if action is None:
            print("Invalid Option.")
            continue

        action()


def project_menu(project):

    while True:
        choice = project_menu()

        if choice == "1":
            add_task(project)

        elif choice == "2":
            add_dependency(project)

        elif choice == "3":
            list_tasks(project)

        elif choice == "5":
            project.schedule()

        elif choice == "7":
            break

def new_project():
    print("Creating new project...")
    proj_name = input("Project Name: ")

    proj_start = input("Defined Start Date: ")
    project = Project(name=proj_name, start=proj_start)
    return project

def open_project():
    pass

def quit():
    pass
    


def add_task(project):
    task_number = input("Task Number: ")
    task_name = input("Task Name: ")
    task_duration = int(input("Duration (days): "))

    project.add_task(
        number = task_number,
        name = task_name,
        duration = timedelta(days=task_duration),
    )