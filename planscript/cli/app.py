from datetime import date, timedelta

from planscript.model.project import Project
from planscript.cli.display import *



def main():
    project = None

    while True:
        choice = main_menu()

        if choice == "n":
            project = new_project()
            project_directory(project)

        elif choice == "o":
            project = open_project()
            project_directory(project)

        elif choice == "q":
            break

        else:
            print("Invalid Option.")
            continue


def project_directory(project):

    while True:
        choice = project_menu(project)

        if choice == "t":
            add_task(project)

        elif choice == "d":
            add_dependency(project)

        elif choice == "l":
            list_tasks(project)

        elif choice == "e":
            list_dependencies(project)

        elif choice == "s":
            project.schedule()

        elif choice == "v":
            view_project(project)

        elif choice == "b":
            #project = None  <- May need this to reset the project variable when returning to main menu
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