from datetime import timedelta

from planscript.model.project import Project
from planscript.model.task import Task


def simple_linear():
    """
    Test 1 - Simple Linear

    1.1 → 1.2 → 1.3 → 1.4

    Expected duration: 14 days
    Critical path: 1.1 → 1.2 → 1.3 → 1.4
    """

    project = Project("Test 1 - Simple Linear")

    task1 = Task(
        "1.1",
        "Site Preparation",
        timedelta(days=2),
    )

    task2 = Task(
        "1.2",
        "Excavation",
        timedelta(days=3),
    )

    task3 = Task(
        "1.3",
        "Foundation",
        timedelta(days=4),
    )

    task4 = Task(
        "1.4",
        "Framing",
        timedelta(days=5),
    )

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)
    project.add_task(task4)

    project.add_dependency(task1, task2)
    project.add_dependency(task2, task3)
    project.add_dependency(task3, task4)

    return project


def parallel_work():
    """
    Test 2 - Parallel Work

    1.1
    1.2
    1.3
    1.4

    No dependencies.

    Expected duration: 5 days
    Critical path: 1.3
    """

    project = Project("Test 2 - Parallel Work")

    task1 = Task(
        "1.1",
        "Mobilization",
        timedelta(days=2),
    )

    task2 = Task(
        "1.2",
        "Survey",
        timedelta(days=3),
    )

    task3 = Task(
        "1.3",
        "Geotechnical",
        timedelta(days=5),
    )

    task4 = Task(
        "1.4",
        "Design",
        timedelta(days=4),
    )

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)
    project.add_task(task4)

    return project


def branch_and_merge():
    """
    Test 3 - Branch and Merge

              ┌→ 1.2 ─┐
    1.1 ──────┼→ 1.3 ─┼→ 1.5
              └→ 1.4 ─┘

    Expected duration: 11 days
    Critical path: 1.1 → 1.3 → 1.5
    """

    project = Project("Test 3 - Branch and Merge")

    task1 = Task(
        "1.1",
        "Start",
        timedelta(days=2),
    )

    task2 = Task(
        "1.2",
        "Survey",
        timedelta(days=3),
    )

    task3 = Task(
        "1.3",
        "Design",
        timedelta(days=5),
    )

    task4 = Task(
        "1.4",
        "Permitting",
        timedelta(days=2),
    )

    task5 = Task(
        "1.5",
        "Construction",
        timedelta(days=4),
    )

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)
    project.add_task(task4)
    project.add_task(task5)

    project.add_dependency(task1, task2)
    project.add_dependency(task1, task3)
    project.add_dependency(task1, task4)

    project.add_dependency(task2, task5)
    project.add_dependency(task3, task5)
    project.add_dependency(task4, task5)

    return project


def complex_network():
    """
    Test 4 - Complex Dependency Network

    1.1 → 1.2 ─────────┐
      │                │
      └→ 1.3 → 1.4 → 1.5 → 1.6
                       │
    1.2 ───────────────┘

    Expected duration: 15 days
    Critical path:
        1.1 → 1.3 → 1.4 → 1.5 → 1.6
    """

    project = Project("Test 4 - Complex Network")

    task1 = Task(
        "1.1",
        "Planning",
        timedelta(days=2),
    )

    task2 = Task(
        "1.2",
        "Survey",
        timedelta(days=4),
    )

    task3 = Task(
        "1.3",
        "Design",
        timedelta(days=3),
    )

    task4 = Task(
        "1.4",
        "Review",
        timedelta(days=2),
    )

    task5 = Task(
        "1.5",
        "Approval",
        timedelta(days=3),
    )

    task6 = Task(
        "1.6",
        "Construction",
        timedelta(days=5),
    )

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)
    project.add_task(task4)
    project.add_task(task5)
    project.add_task(task6)

    project.add_dependency(task1, task2)
    project.add_dependency(task1, task3)
    project.add_dependency(task3, task4)
    project.add_dependency(task4, task5)

    project.add_dependency(task2, task6)
    project.add_dependency(task5, task6)

    return project


def multiple_starts_and_ends():
    """
    Test 5 - Multiple Starts and Ends

    1.1 → 1.3 → 1.5
            │
    1.2 ────┴→ 1.6
              ↑
    1.4 ──────┘

    Multiple starting tasks:
        1.1, 1.2

    Multiple ending tasks:
        1.5, 1.6

    Expected duration: 11 days

    Two critical paths:
        1.1 → 1.3 → 1.6
        1.2 → 1.4 → 1.6
    """

    project = Project("Test 5 - Multiple Starts and Ends")

    task1 = Task(
        "1.1",
        "Investigation",
        timedelta(days=3),
    )

    task2 = Task(
        "1.2",
        "Survey",
        timedelta(days=5),
    )

    task3 = Task(
        "1.3",
        "Analysis",
        timedelta(days=4),
    )

    task4 = Task(
        "1.4",
        "Design",
        timedelta(days=2),
    )

    task5 = Task(
        "1.5",
        "Report",
        timedelta(days=3),
    )

    task6 = Task(
        "1.6",
        "Plans",
        timedelta(days=4),
    )

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)
    project.add_task(task4)
    project.add_task(task5)
    project.add_task(task6)

    project.add_dependency(task1, task3)
    project.add_dependency(task2, task4)

    project.add_dependency(task3, task5)

    project.add_dependency(task3, task6)
    project.add_dependency(task4, task6)

    return project


def circular_dependency():
    """
    Test 6 - Circular Dependency

    1.1 → 1.2 → 1.3
     ↑           │
     └───────────┘

    Expected:
        Topological sort raises a circular dependency error.
    """

    project = Project("Test 6 - Circular Dependency")

    task1 = Task(
        "1.1",
        "Task A",
        timedelta(days=2),
    )

    task2 = Task(
        "1.2",
        "Task B",
        timedelta(days=3),
    )

    task3 = Task(
        "1.3",
        "Task C",
        timedelta(days=2),
    )

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)

    project.add_dependency(task1, task2)
    project.add_dependency(task2, task3)
    project.add_dependency(task3, task1)

    return project


def zero_duration():
    """
    Test 7 - Zero Duration / Milestone

    1.1 → 1.2 → 1.3

    1.2 has zero duration.

    Expected duration: 9 days
    """

    project = Project("Test 7 - Zero Duration")

    task1 = Task(
        "1.1",
        "Design",
        timedelta(days=5),
    )

    task2 = Task(
        "1.2",
        "Approval",
        timedelta(days=0),
    )

    task3 = Task(
        "1.3",
        "Construction",
        timedelta(days=4),
    )

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)

    project.add_dependency(task1, task2)
    project.add_dependency(task2, task3)

    return project


TEST_PROJECTS = {
    "1": simple_linear,
    "2": parallel_work,
    "3": branch_and_merge,
    "4": complex_network,
    "5": multiple_starts_and_ends,
    "6": circular_dependency,
    "7": zero_duration,
}