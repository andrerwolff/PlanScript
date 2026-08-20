def main_menu():
    print()
    print("=" * 50)
    print("                     PlanScript")
    print("=" * 50)
    print()
    print("  [N] New Project")
    print("  [O] Open Project")
    print("  [Q] Quit")
    print()

    return input("  Select an option: ").strip().lower()


def project_menu(project):
    print()
    print("=" * 50)
    print(f"  Project: {project.name}")
    print("=" * 50)
    print()
    print("  [T] Add Task")
    print("  [D] Add Dependency")
    print("  [L] List Tasks")
    print("  [E] List Dependencies")
    print("  [S] Schedule Project")
    print("  [V] View Project")
    print("  [B] Back to Main Menu")
    print()

    return input("  Select an option: ").strip().lower()
