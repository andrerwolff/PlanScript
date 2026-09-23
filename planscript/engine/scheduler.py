"""CPM scheduler for PlanScript projects.

Scheduler calculates a project's dependency-based schedule using a forward
pass and backward pass. It derives early and late dates, total float,
critical tasks, critical paths, and calendar dates.

Summary tasks are excluded from CPM calculations and receive derived dates
based on their descendant tasks.
"""

from datetime import timedelta, date
from dataclasses import dataclass

from planscript.exceptions import SchedulingError
from planscript.model.schedule import Schedule
from planscript.model.hierarchy import TaskHierarchy
from planscript.model.dependency import DependencyType, DependencyGraph
from collections import deque


class Scheduler:
    """Calculate a CPM schedule from a PlanScript project.

    Scheduler operates on the project's plan and produces a Schedule
    containing derived scheduling results. It does not modify the project's
    tasks, dependencies, or tracking history.

    Scheduling is performed in dependency order. Summary tasks are structural
    groupings and do not participate directly in CPM calculations.
    """
    
    def calculate(self, project) -> Schedule:
        """Calculate and return a schedule for the project.

        Scheduling proceeds through these stages:

        1. Build the task hierarchy.
        2. Topologically order tasks by dependency relationships.
        3. Perform the CPM forward pass.
        4. Perform the CPM backward pass.
        5. Calculate total float.
        6. Identify critical tasks and critical paths.
        7. Convert CPM offsets to calendar dates when a start date exists.

        Raises:
            ValueError: If the project contains a circular dependency.
            SchedulingError: If the project has no tasks to schedule.
        """
        if not project.tasks:
            raise SchedulingError("Project has no tasks to schedule.")

        graph = DependencyGraph(project)
        hierarchy = TaskHierarchy(project.tasks)
        ordered_task_ids = graph.topological_sort()
        early_start, early_finish = self._forward_pass(project, graph, ordered_task_ids)
        late_start, late_finish, duration = self._backward_pass(project, graph, ordered_task_ids, early_finish)
        total_float = self._float(hierarchy, early_start, late_start)
        critical_tasks = self._critical_tasks(total_float)
        critical_paths = self._find_critical_paths(project, critical_tasks, early_start, early_finish)
        start_dates, finish_dates = self._get_dates(project, hierarchy, ordered_task_ids, early_start, early_finish)

        return Schedule(hierarchy = hierarchy,
            ordered_task_ids = ordered_task_ids,
            early_start = early_start,
            early_finish = early_finish,
            late_start = late_start,
            late_finish = late_finish,
            total_float= total_float,
            critical_tasks = critical_tasks,
            critical_paths = critical_paths,
            duration = duration,
            start_dates= start_dates,
            finish_dates= finish_dates)


    def _forward_pass(self, project, graph, ordered_task_ids) -> tuple[dict[str, timedelta], dict[str, timedelta]]:
        """Calculate earliest start and finish times using CPM.

        Tasks are processed in dependency order. Each task's earliest start
        is determined by the constraints imposed by its predecessor
        dependencies. Summary tasks are excluded because their dates are
        derived from descendants after CPM calculations.

        Supports Finish-to-Start, Start-to-Start, Finish-to-Finish, and
        Start-to-Finish dependencies with optional lag.
        """

        early_start = {}
        early_finish = {}
        for task_id in ordered_task_ids:
            task = project.tasks[task_id]

            if task.duration is None:
                continue
            dependencies = graph.predecessors[task_id]

            if not dependencies:
                early_start[task_id] = timedelta(0)

            else:
                candidate_es_values = []
                for dependency in dependencies:
                    predecessor = dependency.predecessor
                    predecessor_id = predecessor.number
                    if dependency.dep_type == DependencyType.FINISH_START:
                        candidate_es = (early_finish[predecessor_id] + dependency.lag)
                        
                    elif dependency.dep_type == DependencyType.START_START:
                        candidate_es = (early_start[predecessor_id] + dependency.lag)

                    elif dependency.dep_type == DependencyType.FINISH_FINISH:
                        candidate_ef = (early_finish[predecessor_id] + dependency.lag)
                        candidate_es = (candidate_ef - task.duration)

                    elif dependency.dep_type == DependencyType.START_FINISH:
                        candidate_ef = (early_start[predecessor_id] + dependency.lag)
                        candidate_es = (candidate_ef - task.duration)

                    else:
                        raise ValueError("Looks like an issue with dependency type - Forward Pass")

                    candidate_es_values.append(candidate_es)
        
                early_start[task_id] = max(candidate_es_values)
            early_finish[task_id] = (early_start[task_id] + task.duration)

        return early_start, early_finish

    def _backward_pass(self, project, graph, ordered_task_ids, early_finish) -> tuple[dict[str, timedelta], dict[str, timedelta], timedelta,]:
        """Calculate latest start and finish times using CPM.

        Tasks are processed in reverse dependency order. The project
        duration from the forward pass establishes the initial latest
        finish constraint, and successor dependencies propagate allowable
        dates backward through the network.

        Summary tasks are excluded because their dates are derived from
        descendants after CPM calculations.
        """

        project_duration = max(early_finish.values())
        late_start = {}
        late_finish = {}
        for task_id in reversed(ordered_task_ids):
            task = project.tasks[task_id]
            # Pass on tasks that are summary
            if task.duration is None:
                continue
            #----------------------------
            dependencies = graph.successors[task_id]
            candidate_lf_values = [project_duration]
            for dependency in dependencies:
                successor = dependency.successor
                successor_id = successor.number

                if dependency.dep_type == DependencyType.FINISH_START:
                    candidate_lf = (late_start[successor.number] - dependency.lag)

                elif dependency.dep_type == DependencyType.START_START:
                    candidate_ls = (late_start[successor.number] - dependency.lag)
                    candidate_lf = (candidate_ls + task.duration)

                elif dependency.dep_type == DependencyType.FINISH_FINISH:
                    candidate_lf = (late_finish[successor_id] - dependency.lag)

                elif dependency.dep_type == DependencyType.START_FINISH:
                    candidate_ls = (late_finish[successor_id] - dependency.lag)
                    candidate_lf = (candidate_ls + task.duration)

                else:
                    raise ValueError("Looks like an issue with dependency type - Backward Pass")
                
                candidate_lf_values.append(candidate_lf)

            if task.duration is not None:
                late_finish[task_id] = min(candidate_lf_values)
                late_start[task_id] = (late_finish[task_id] - task.duration)

        return late_start, late_finish, project_duration

    def _float(self, hierarchy, early_start, late_start) -> dict[str, timedelta | None]:
        """Calculate total float from early and late start times.

        Summary tasks receive no CPM float because they do not participate
        directly in the CPM calculation.
        """

        total_float = {}

        for task_id in hierarchy.tasks:
            if hierarchy.is_summary(task_id):
                total_float[task_id] = None
            else:
                total_float[task_id] = late_start[task_id] - early_start[task_id]
        return total_float

    def _critical_tasks(self, total_float: dict[str, timedelta | None]) -> list[str]:
        """Return tasks with zero total float."""

        critical_tasks = []
        for task_id in total_float:
            if total_float[task_id] == timedelta(0):
                critical_tasks.append(task_id)
        return critical_tasks

    def _dependency_is_tight(self, project, dependency, early_start, early_finish) -> bool:
        """Return True if a dependency imposes the successor's early start."""

        predecessor = dependency.predecessor
        successor = dependency.successor

        lag = dependency.lag

        if dependency.dep_type == DependencyType.FINISH_START:
            imposed_start = early_finish[predecessor.number] + lag
        elif dependency.dep_type == DependencyType.START_START:
            imposed_start = early_start[predecessor.number] + lag
        elif dependency.dep_type == DependencyType.FINISH_FINISH:
            imposed_finish = early_finish[predecessor.number] + lag
            imposed_start = imposed_finish - successor.duration
        elif dependency.dep_type == DependencyType.START_FINISH:
            imposed_finish = early_start[predecessor.number] + lag
            imposed_start = imposed_finish - successor.duration

        else:
            raise ValueError(f"Unknown dependency type: {dependency.dep_type}")

        return early_start[successor.number] == imposed_start

    def _find_critical_paths(self, project, critical_tasks, early_start, early_finish) -> list[list[str]]:
        """Find complete paths through the critical-task network.

        A critical path begins with a critical task that has no critical
        predecessor and ends with a critical task that has no critical
        successor. Branching in the critical network may produce multiple
        critical paths.
        """

        critical = set(critical_tasks)
        critical_successors = {}
        for task_id in critical:
            critical_successors[task_id] = []

        # Build the graph of only tight critical dependencies.
        for dependency in project.dependencies:
            predecessor_id = dependency.predecessor.number
            successor_id = dependency.successor.number

            if predecessor_id not in critical:
                continue
            if successor_id not in critical:
                continue
            if not self._dependency_is_tight(project, dependency, early_start, early_finish):
                continue

            critical_successors[predecessor_id].append(successor_id)

        # Find critical tasks with no tight critical predecessors.
        has_critical_predecessor = set()

        for successors in critical_successors.values():
            has_critical_predecessor.update(successors)

        starts = []

        for task_id in critical:
            if task_id not in has_critical_predecessor:
                starts.append(task_id)

        paths = []
        # Walk forward from each critical starting task.
        def walk(task_id, path):
            path = path + [task_id]

            successors = critical_successors[task_id]

            if not successors:
                paths.append(path)
                return

            for successor_id in successors:
                walk(successor_id, path)
                
        for start_id in starts:
            walk(start_id, [])

        return paths

    def _get_dates(self, project, hierarchy, ordered_task_ids, early_start, early_finish) -> tuple[dict[str, date] | None, dict[str, date] | None]:
        """Convert CPM offsets into calendar start and finish dates.

        Task offsets are measured from the project's planned start date. When
        the project has no start date, the schedule is calculated-only and
        (None, None) is returned instead of inventing a calendar anchor.

        Summary-task dates are rolled up from the dates of their descendants.
        """

        if project.start_date is None:
            return None, None
        else:
            start_date = project.start_date
        start_dates = {}
        finish_dates = {}
        for task_id in early_start:
            task = project.tasks[task_id]
            start = start_date + early_start[task_id]
            start_dates[task_id] = start

            if task.is_milestone:
                finish_dates[task_id] = start
            else:
                finish_dates[task_id] = (start_date + early_finish[task_id] - timedelta(days=1))

        start_dates, finish_dates = self._rollup_summary_dates(hierarchy, ordered_task_ids, start_dates, finish_dates)
        return start_dates, finish_dates

    def _rollup_summary_dates(self, hierarchy, ordered_task_ids, start_dates, finish_dates) -> tuple[dict[str, date], dict[str, date]]:
        """Derive summary-task dates from their descendant task dates.

        A summary task starts on the earliest start date of its descendants
        and finishes on the latest finish date of its descendants.
        """

        for task_id in reversed(ordered_task_ids):
            if hierarchy.is_summary(task_id):
                decendant_starts = []
                decendant_finishes = []
                for child in hierarchy.get_descendants(task_id):
                    decendant_starts.append(start_dates[child])
                    decendant_finishes.append(finish_dates[child])

                start_dates[task_id] = min(decendant_starts)
                finish_dates[task_id] = max(decendant_finishes)
        return start_dates, finish_dates
    