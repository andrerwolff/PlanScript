from datetime import timedelta, date
from decimal import Decimal

from planscript.model.project import Project
from planscript.model.task import Task
from planscript.model.dependency import DependencyType


def simple_linear():
    """
    Test 1 - Simple Linear

    1.1 → 1.2 → 1.3 → 1.4

    Expected duration: 14 days
    Critical path: 1.1 → 1.2 → 1.3 → 1.4
    """

    project = Project("Test 1 - Simple Linear")

    task1 = Task("1.1", "Site Preparation", timedelta(days=2))
    task2 = Task("1.2", "Excavation", timedelta(days=3))
    task3 = Task("1.3", "Foundation", timedelta(days=4))
    task4 = Task("1.4", "Framing", timedelta(days=5))

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

    task1 = Task("1.1", "Mobilization", timedelta(days=2))
    task2 = Task("1.2", "Survey", timedelta(days=3))
    task3 = Task("1.3", "Geotechnical", timedelta(days=5))
    task4 = Task("1.4", "Design", timedelta(days=4))

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

    task1 = Task("1.1", "Start", timedelta(days=2))
    task2 = Task("1.2", "Survey", timedelta(days=3))
    task3 = Task("1.3", "Design", timedelta(days=5))
    task4 = Task("1.4", "Permitting", timedelta(days=2))
    task5 = Task("1.5", "Construction", timedelta(days=4))

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
    project.start_date = date(2026,8,1)

    task1 = Task("1.1", "Investigation", timedelta(days=3))
    task2 = Task("1.2", "Survey", timedelta(days=5))
    task3 = Task("1.3", "Analysis", timedelta(days=4))
    task4 = Task("1.4", "Design", timedelta(days=2))
    task5 = Task("1.5", "Report", timedelta(days=3))
    task6 = Task("1.6", "Plans", timedelta(days=4))

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

    task1 = Task("1.1", "Task A", timedelta(days=2))
    task2 = Task("1.2", "Task B", timedelta(days=3))
    task3 = Task("1.3", "Task C", timedelta(days=2))

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

    task1 = Task("1.1", "Design", timedelta(days=5))
    task2 = Task("1.2", "Approval", timedelta(days=0))
    task3 = Task("1.3", "Construction", timedelta(days=4))

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)

    project.add_dependency(task1, task2)
    project.add_dependency(task2, task3)

    return project

def mixed_dependency_types():
    """
    Test 8 - Mixed Dependencies
                    
        CP : 1.1 → 1.2 → 1.3 → 1.4
    
        Expected duration: 9 days
    """
    project = Project("Test 8 - Mixed Dependency Types")
    
    a = Task("8.1", "A", timedelta(days=4))
    b = Task("8.2", "B", timedelta(days=6))
    c = Task("8.3", "C", timedelta(days=5))
    d = Task("8.4", "D", timedelta(days=4))
    e = Task("8.5", "E", timedelta(days=3))

    for task in [a, b, c, d, e]:
        project.add_task(task)

    project.add_dependency(a, b, "FS")
    project.add_dependency(b, c, "SS")
    project.add_dependency(c, d, "FF")
    project.add_dependency(e, d, "SF")

    return project

def dependency_types_with_lag():
    """
    Test 9 - Mixed Dependencies With Lag
                    
        CP : 2.1 → 2.2 → 2.3 → 2.4
    
        Expected duration: 13 days
    """
    project = Project("Test 9 - Mixed Dependency With Lag")
    
    a = Task("9.1", "A", timedelta(days=5))
    b = Task("9.2", "B", timedelta(days=4))
    c = Task("9.3", "C", timedelta(days=3))
    d = Task("9.4", "D", timedelta(days=2))
    e = Task("9.5", "E", timedelta(days=1))

    for task in [a, b, c, d, e]:
        project.add_task(task)

    project.add_dependency(a, b, "FS", timedelta(days=2))
    project.add_dependency(b, c, "SS", timedelta(days=1))
    project.add_dependency(c, d, "FF", timedelta(days=2))
    project.add_dependency(d, e, "SF", timedelta(days=1))

    return project

def single_task():
    project = Project("Single Task")

    project.add_task(Task("10.1", "Only Task", timedelta(days=5)))

    return project


def disconnected_networks():
    project = Project("Disconnected Networks")

    a = Task("11.1", "A", timedelta(days=5))
    b = Task("11.2", "B", timedelta(days=3))
    c = Task("11.3", "C", timedelta(days=10))
    d = Task("11.4", "D", timedelta(days=2))

    for task in [a, b, c, d]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)
    project.add_dependency(predecessor=c, successor=d)

    return project


def competing_constraints():
    project = Project("Competing Constraints")

    a = Task("12.1", "A", timedelta(days=5))
    b = Task("12.2", "B", timedelta(days=8))
    c = Task("12.3", "C", timedelta(days=3))

    for task in [a, b, c]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=c, dep_type="FS")
    project.add_dependency(predecessor=b, successor=c, dep_type="SS")

    return project


def negative_lag():
    project = Project("Negative Lag")

    a = Task("13.1", "A", timedelta(days=5))
    b = Task("13.2", "B", timedelta(days=4))

    project.add_task(a)
    project.add_task(b)

    project.add_dependency(predecessor=a, successor=b, dep_type="FS", lag=timedelta(days=-2))

    return project
    
def start_no_earlier_than():
    """
    Test 14 - Start No Earlier Than (soft)

    14.1 (5d) → 14.2 (3d) → 14.3 (4d)

    SNET on 14.2 at offset 2 is weaker than its dependency (offset 5),
    so the dependency wins.
    SNET on 14.3 at offset 14 is stronger than its dependency (offset 8),
    so the constraint wins and extends the project.

    Expected duration: 18 days
    Critical path: 14.3
    """

    project = Project("Test 14 - Start No Earlier Than", start_date=date(2026, 1, 5))

    a = Task("14.1", "A", timedelta(days=5))
    b = Task("14.2", "B", timedelta(days=3))
    c = Task("14.3", "C", timedelta(days=4))

    for task in [a, b, c]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)
    project.add_dependency(predecessor=b, successor=c)

    project.add_constraint(b, "SNET", date(2026, 1, 7))
    project.add_constraint(c, "SNET", date(2026, 1, 19))

    return project


def finish_no_earlier_than():
    """
    Test 15 - Finish No Earlier Than (soft)

    15.1 (4d) → 15.2 (2d) → 15.3 (3d)

    FNET on 15.2 (finish no earlier than 2026-01-08) is weaker than its
    dependency (finish 2026-01-10), so the dependency wins.
    FNET on 15.3 (finish no earlier than 2026-01-15) is stronger than its
    dependency (finish 2026-01-13), so the constraint wins and opens a
    two-day gap after 15.2.

    Expected duration: 11 days
    Critical path: 15.3
    """

    project = Project("Test 15 - Finish No Earlier Than", start_date=date(2026, 1, 5))

    a = Task("15.1", "A", timedelta(days=4))
    b = Task("15.2", "B", timedelta(days=2))
    c = Task("15.3", "C", timedelta(days=3))

    for task in [a, b, c]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)
    project.add_dependency(predecessor=b, successor=c)

    project.add_constraint(b, "FNET", date(2026, 1, 8))
    project.add_constraint(c, "FNET", date(2026, 1, 15))

    return project


def start_no_later_than():
    """
    Test 16 - Start No Later Than (soft)

    16.1 (3d) → 16.2 (4d)
    16.3 (10d)            (no dependencies)

    SNLT on 16.2 at offset 5 binds (its late start would otherwise be 6),
    consuming float from 16.2 and its predecessor 16.1.
    SNLT on 16.1 at offset 4 is weaker than its dependency-driven late
    start (2), so the dependency wins.

    Expected duration: 10 days (late-side constraint, early dates unchanged)
    Critical path: 16.3
    """

    project = Project("Test 16 - Start No Later Than", start_date=date(2026, 1, 5))

    a = Task("16.1", "A", timedelta(days=3))
    b = Task("16.2", "B", timedelta(days=4))
    c = Task("16.3", "C", timedelta(days=10))

    for task in [a, b, c]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)

    project.add_constraint(a, "SNLT", date(2026, 1, 9))
    project.add_constraint(b, "SNLT", date(2026, 1, 10))

    return project


def finish_no_later_than():
    """
    Test 17 - Finish No Later Than (soft)

    17.1 (3d) → 17.2 (4d)
    17.3 (10d)            (no dependencies)

    FNLT on 17.2 (finish no later than 2026-01-13) binds; its late finish
    would otherwise be the project duration (finish 2026-01-15),
    consuming float from 17.2 and its predecessor 17.1.
    FNLT on 17.1 (finish no later than 2026-01-11) is weaker than the late
    finish its dependency now imposes (2026-01-09), so the dependency wins.

    Expected duration: 10 days (late-side constraint, early dates unchanged)
    Critical path: 17.3
    """

    project = Project("Test 17 - Finish No Later Than", start_date=date(2026, 1, 5))

    a = Task("17.1", "A", timedelta(days=3))
    b = Task("17.2", "B", timedelta(days=4))
    c = Task("17.3", "C", timedelta(days=10))

    for task in [a, b, c]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)

    project.add_constraint(a, "FNLT", date(2026, 1, 11))
    project.add_constraint(b, "FNLT", date(2026, 1, 13))

    return project

def infeasible_finish_no_later_than():
    """
    Test 18 - Infeasible Finish No Later Than (soft)

    18.1 (5d) → 18.2 (5d)

    FNLT on 18.2 (finish no later than 2026-01-10) cannot be met: 18.2
    cannot finish before 2026-01-14. The constraint is soft, so early
    dates hold and the unsatisfiable constraint surfaces as negative
    total float.

    Expected duration: 10 days
    Critical path: 18.1 → 18.2 (both negative float)
    """

    project = Project("Test 18 - Infeasible Finish No Later Than", start_date=date(2026, 1, 5))

    a = Task("18.1", "A", timedelta(days=5))
    b = Task("18.2", "B", timedelta(days=5))

    for task in [a, b]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)

    project.add_constraint(b, "FNLT", date(2026, 1, 10))

    return project

def mandatory_start():
    """
    Test 19 - Mandatory Start

    19.1 (5d) → 19.2 (3d)

    MSON on 19.1 at the project start is the boundary case: the network
    already starts it there, so nothing raises.
    MSON on 19.2 on 2026-01-13 pins it to start later (offset 8) than its
    dependency allows (offset 5).

    Expected duration: 11 days
    Critical paths: 19.1 and 19.2 (mandatory dates leave no float)
    """

    project = Project("Test 19 - Mandatory Start", start_date=date(2026, 1, 5))

    a = Task("19.1", "A", timedelta(days=5))
    b = Task("19.2", "B", timedelta(days=3))

    for task in [a, b]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)

    project.add_constraint(a, "MSON", date(2026, 1, 5))
    project.add_constraint(b, "MSON", date(2026, 1, 13))

    return project


def mandatory_finish():
    """
    Test 20 - Mandatory Finish

    20.1 (4d) → 20.2 (6d)

    MFON on 20.1 on 2026-01-14 pins its finish later than its own start
    would place it; the whole chain shifts with it.

    Expected duration: 16 days
    Critical path: 20.1 → 20.2
    """

    project = Project("Test 20 - Mandatory Finish", start_date=date(2026, 1, 5))

    a = Task("20.1", "A", timedelta(days=4))
    b = Task("20.2", "B", timedelta(days=6))

    for task in [a, b]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)

    project.add_constraint(a, "MFON", date(2026, 1, 14))

    return project


def mandatory_start_conflict():
    """
    Test 21 - Mandatory Start Conflict

    21.1 (10d) → 21.2 (5d)

    MSON on 21.2 on 2026-01-09 demands a start earlier than its
    dependency permits, so scheduling must fail.
    """

    project = Project("Test 21 - Mandatory Start Conflict", start_date=date(2026, 1, 5))

    a = Task("21.1", "A", timedelta(days=10))
    b = Task("21.2", "B", timedelta(days=5))

    for task in [a, b]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)

    project.add_constraint(b, "MSON", date(2026, 1, 9))

    return project


def mandatory_finish_conflict():
    """
    Test 22 - Mandatory Finish Conflict

    22.1 (10d) → 22.2 (5d)

    MFON on 22.2 on 2026-01-12 demands a finish its dependency cannot
    allow (22.2 cannot even start until offset 10), so scheduling must
    fail.
    """

    project = Project("Test 22 - Mandatory Finish Conflict", start_date=date(2026, 1, 5))

    a = Task("22.1", "A", timedelta(days=10))
    b = Task("22.2", "B", timedelta(days=5))

    for task in [a, b]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)

    project.add_constraint(b, "MFON", date(2026, 1, 12))

    return project


def mandatory_start_backward_conflict():
    """
    Test 23 - Mandatory Start vs a Successor Constraint

    23.1 (5d) → 23.2 (5d)

    MSON on 23.1 on 2026-01-10 pins it to finish at offset 10, but SNLT
    on 23.2 on 2026-01-12 forces 23.2 to start by offset 7, so 23.1 must
    finish by then. The forward pass is happy; the backward pass must
    fail.
    """

    project = Project("Test 23 - Mandatory Start Backward Conflict", start_date=date(2026, 1, 5))

    a = Task("23.1", "A", timedelta(days=5))
    b = Task("23.2", "B", timedelta(days=5))

    for task in [a, b]:
        project.add_task(task)

    project.add_dependency(predecessor=a, successor=b)

    project.add_constraint(a, "MSON", date(2026, 1, 10))
    project.add_constraint(b, "SNLT", date(2026, 1, 12))

    return project

TEST_PROJECTS = {
    "1": simple_linear,
    "2": parallel_work,
    "3": branch_and_merge,
    "4": complex_network,
    "5": multiple_starts_and_ends,
    "6": circular_dependency,
    "7": zero_duration,
    "8": mixed_dependency_types,
    "9": dependency_types_with_lag,
    "10": single_task,
    "11": disconnected_networks,
    "12": competing_constraints,
    "13": negative_lag,
    "14": start_no_earlier_than,
    "15": finish_no_earlier_than,
    "16": start_no_later_than,
    "17": finish_no_later_than,
    "18": infeasible_finish_no_later_than,
    "19": mandatory_start,
    "20": mandatory_finish,
    "21": mandatory_start_conflict,
    "22": mandatory_finish_conflict,
    "23": mandatory_start_backward_conflict,
}

def finish_start():
    project = Project("FS")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=3))
    c = Task("D.3", "C", timedelta(days=4))

    project.add_task(a)
    project.add_task(b)
    project.add_task(c)

    project.add_dependency(predecessor=a, successor=b, dep_type="FS")
    project.add_dependency(predecessor=b, successor=c, dep_type="FS")

    return project


def start_start():
    project = Project("SS")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=3))

    project.add_task(a)
    project.add_task(b)

    project.add_dependency(predecessor=a, successor=b, dep_type="SS")

    return project


def finish_finish():
    project = Project("FF")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=3))

    project.add_task(a)
    project.add_task(b)

    project.add_dependency(predecessor=a, successor=b, dep_type=DependencyType.FINISH_FINISH)

    return project


def start_finish():
    project = Project("SF")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=3))

    project.add_task(a)
    project.add_task(b)

    project.add_dependency(predecessor=a, successor=b, dep_type=DependencyType.START_FINISH)

    return project



def tight_redundant():
    """
        Test - Redundant FS Dependency

        1.1 → 1.2 → 1.3
        └──────────→ 1.3

        Expected duration: 10 days

        Critical path: 1.1 → 1.2 → 1.3

        The direct 1.1 → 1.3 dependency is non-tight because
        1.2 → 1.3 already determines the start of 1.3.
        """

    project = Project("Test - Redundant FS Dependency")

    task1 = Task("1.1", "Task A", timedelta(days=5))
    task2 = Task("1.2", "Task B", timedelta(days=5))
    task3 = Task("1.3", "Task C", timedelta(days=5))

    project.add_task(task1)
    project.add_task(task2)
    project.add_task(task3)

    project.add_dependency(task1, task2)
    project.add_dependency(task2, task3)
    project.add_dependency(task1, task3)

    return project


def tight_FS():
    project = Project("Tight FS")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=5))

    project.add_task(a)
    project.add_task(b)

    project.add_dependency(predecessor=a, successor=b, dep_type=DependencyType.FINISH_START)

    return project

def non_tight_FS():
    project = Project("Non Tight FS")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=5))
    c = Task("D.3", "C", timedelta(days=5))

    project.add_task(a)
    project.add_task(b)
    project.add_task(c)

    project.add_dependency(predecessor=a, successor=b, dep_type=DependencyType.FINISH_START)
    project.add_dependency(predecessor=b, successor=c, dep_type=DependencyType.FINISH_START)
    project.add_dependency(predecessor=a, successor=c, dep_type=DependencyType.FINISH_START, lag=timedelta(days=1))

    return project

def tight_SS():
    project = Project("Tight SS")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=5))

    project.add_task(a)
    project.add_task(b)

    project.add_dependency(predecessor=a, successor=b, dep_type=DependencyType.START_START)

    return project

def tight_FF():
    project = Project("Tight FF")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=5))

    project.add_task(a)
    project.add_task(b)

    project.add_dependency(predecessor=a, successor=b, dep_type=DependencyType.FINISH_FINISH)

    return project

def tight_SF():
    project = Project("Tight SF")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=5))

    project.add_task(a)
    project.add_task(b)

    project.add_dependency(predecessor=a, successor=b, dep_type=DependencyType.START_FINISH)

    return project

def competing_SS():
    project = Project("Competing SS")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=10))
    c = Task("D.3", "C", timedelta(days=5))

    project.add_task(a)
    project.add_task(b)
    project.add_task(c)

    project.add_dependency(predecessor=a, successor=c, dep_type=DependencyType.START_START)
    project.add_dependency(predecessor=b, successor=c, dep_type=DependencyType.START_START, lag=timedelta(days=5))

    return project

def competing_FF():
    project = Project("Competing FF")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=10))
    c = Task("D.3", "C", timedelta(days=5))

    project.add_task(a)
    project.add_task(b)
    project.add_task(c)

    project.add_dependency(predecessor=a, successor=c, dep_type=DependencyType.FINISH_FINISH)
    project.add_dependency(predecessor=b, successor=c, dep_type=DependencyType.FINISH_FINISH, lag=timedelta(days=5))

    return project

def competing_SF():
    project = Project("Competing SF")

    a = Task("D.1", "A", timedelta(days=5))
    b = Task("D.2", "B", timedelta(days=10))
    c = Task("D.3", "C", timedelta(days=5))

    project.add_task(a)
    project.add_task(b)
    project.add_task(c)

    project.add_dependency(predecessor=a, successor=c, dep_type=DependencyType.START_FINISH)
    project.add_dependency(predecessor=b, successor=c, dep_type=DependencyType.START_FINISH, lag=timedelta(days=5))

    return project

def simple_budget():
    """
    Budget Test - Explicit and Weighted Allocations

    1 Summary                        no budget, rolls up from its children
      1.1 explicit $3400
      1.2 explicit $6250.25
    2 Design                         explicit $250000
      2.1 weighted 10%
        2.1.1 weighted 40%
        2.1.2 weighted 60%
      2.2 weighted 90%
    3 Construction                   explicit $45000.25
      3.1 weighted 10%
      3.2 weighted 40%
      3.3 weighted 40%
      3.4 weighted 10%
    4 Untracked Work                 no budget at all

    A weight is a share of the parent's resolved amount, so 2.1.1 takes 40%
    of 2.1's $25000 rather than 40% of 2's $250000.

    Expected amounts: 1=$9650.25, 1.1=$3400, 1.2=$6250.25, 2=$250000,
    2.1=$25000, 2.1.1=$10000, 2.1.2=$15000, 2.2=$225000, 3=$45000.25,
    3.1=$4500.03, 3.2=$18000.10, 3.3=$18000.10, 3.4=$4500.02
    Expected total: $304650.50
    Expected unallocated: 4, 4.1
    """

    project = Project("Budget Test - Explicit and Weighted Allocations")

    tasks = [
        Task("1", "Summary"),
        Task("1.1", "Kickoff", timedelta(days=0), budget=Decimal("3400")),
        Task("1.2", "Project Plan", timedelta(days=5), budget=Decimal("6250.25")),

        Task("2", "Design", budget=Decimal("250000")),
        Task("2.1", "Preliminary Design", budget_wt=Decimal("10")),
        Task("2.1.1", "Site Layout", timedelta(days=5), budget_wt=Decimal("40")),
        Task("2.1.2", "Utility Design", timedelta(days=10), budget_wt=Decimal("60")),
        Task("2.2", "Final Design", timedelta(days=5), budget_wt=Decimal("90")),

        Task("3", "Construction", budget=Decimal("45000.25")),
        Task("3.1", "Mobilization", timedelta(days=3), budget_wt=Decimal("10")),
        Task("3.2", "Installation", timedelta(days=15), budget_wt=Decimal("40")),
        Task("3.3", "Inspection", timedelta(days=0), budget_wt=Decimal("40")),
        Task("3.4", "Closeout", timedelta(days=5), budget_wt=Decimal("10")),

        Task("4", "Untracked Work"),
        Task("4.1", "Future Task", timedelta(days=10)),
    ]

    for task in tasks:
        project.add_task(task)

    return project
