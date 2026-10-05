"""CPM scheduler for PlanScript projects.

Scheduler calculates a project's dependency-based schedule using a forward
pass and backward pass. It derives early and late dates, total float,
critical tasks, critical paths, and calendar dates.

Summary tasks are excluded from CPM calculations and receive derived dates
based on their descendant tasks.
"""

from datetime import timedelta, date

from planscript.exceptions import SchedulingError
from planscript.model.task import Task
from planscript.model.schedule import Schedule
from planscript.model.hierarchy import TaskHierarchy
from planscript.model.dependency import DependencyType, DependencyGraph
from planscript.model.constraint import ConstraintType


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
        3. Map constraint dates to CPM offsets keyed by task number.
        4. Perform the CPM forward pass.
        5. Perform the CPM backward pass.
        6. Calculate total float.
        7. Identify critical tasks and critical paths.
        8. Convert CPM offsets to calendar dates when a start date exists.

        Raises:
            ValueError: If the project contains a circular dependency.
            SchedulingError: If the project has no tasks to schedule, has
                constraints but no start date to anchor them to, or a
                mandatory constraint the network cannot accommodate.
        """
        if not project.tasks:
            raise SchedulingError("Project has no tasks to schedule.")

        graph = DependencyGraph(project)
        hierarchy = TaskHierarchy(project.tasks)
        ordered_task_ids = graph.topological_sort()
        constraint_index = self._constraint_index(project)
        early_start, early_finish = self._forward_pass(project, graph, ordered_task_ids, constraint_index)
        late_start, late_finish, duration = self._backward_pass(project, graph, ordered_task_ids, early_finish, constraint_index)
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


    def _constraint_index(self, project) -> dict[str, list[tuple[ConstraintType, timedelta]]]:
        """Convert constraint dates to CPM offsets keyed by task number.

        This is the calendar boundary: constraint dates are mapped to
        offsets from the project's planned start once, so both passes
        operate only on offsets. Start-side dates map directly
        (`con_date − start_date`); finish-side dates map one day later for
        leaf tasks, because a leaf task's calendar finish falls the day
        before its early-finish offset. A milestone finishes on its start
        day, so no adjustment applies to it. Keying by task number
        attaches a constraint to its task the same way the rest of the
        scheduler does, regardless of object identity.

        Raises:
            SchedulingError: If the project has constraints but no
                project start date to anchor them to.
        """

        index: dict[str, list[tuple[ConstraintType, timedelta]]] = {}

        if not project.constraints:
            return index
        if project.start_date is None:
            raise SchedulingError("Project has constraints but no start date to anchor them to.")

        for constraint in project.constraints:
            offset = constraint.con_date - project.start_date
            if constraint.con_type.constrains_finish and not constraint.task.is_milestone:
                offset += timedelta(days=1)
            index.setdefault(constraint.task.number, []).append((constraint.con_type, offset))
        return index

    def _forward_pass(self, project, graph, ordered_task_ids, constraint_index) -> tuple[dict[str, timedelta], dict[str, timedelta]]:
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

            # 1. Calculate dependency-driven earliest start
            if not dependencies:
                candidate_es = timedelta(0)

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
                # 2. Apply start/finish constraints
                candidate_es = max(candidate_es_values)
            candidate_es = self._apply_forward_constraints(constraint_index.get(task_id, []), task, candidate_es)
            early_start[task_id] = candidate_es
            early_finish[task_id] = (early_start[task_id] + task.duration)

        return early_start, early_finish

    def _apply_forward_constraints(self, constraints: list[tuple[ConstraintType, timedelta]], task: Task, candidate_es: timedelta) -> timedelta:
        """Move a candidate early start to satisfy this task's constraints.

        Soft constraints (Start-No-Earlier-Than, Finish-No-Earlier-Than)
        raise the candidate to the more restrictive of the network and the
        constraint. Mandatory constraints (Mandatory Start, Mandatory
        Finish) then pin the candidate exactly and raise SchedulingError
        when the network cannot accommodate the pin. Mandatory constraints
        are applied last so the outcome does not depend on the order the
        constraints were added.
        """
        for con_type, offset in constraints:
            if con_type == ConstraintType.START_NO_EARLIER_THAN:
                candidate_es = max(candidate_es, offset)
            elif con_type == ConstraintType.FINISH_NO_EARLIER_THAN:
                candidate_es = max(candidate_es, offset - task.duration)

        pinned_es = None
        for con_type, offset in constraints:
            if con_type == ConstraintType.MANDATORY_START:
                pin = offset
                boundary = "start"
            elif con_type == ConstraintType.MANDATORY_FINISH:
                pin = offset - task.duration
                boundary = "finish"
            else:
                continue

            if pinned_es is None:
                if candidate_es > pin:
                    raise SchedulingError(
                        f"Task '{task.number}' violates mandatory {boundary} constraint.")
                pinned_es = pin
            elif pinned_es != pin:
                raise SchedulingError(
                    f"Task '{task.number}' has conflicting mandatory constraints.")

        if pinned_es is not None:
            candidate_es = pinned_es
        return candidate_es


    def _backward_pass(self, project, graph, ordered_task_ids, early_finish, constraint_index) -> tuple[dict[str, timedelta], dict[str, timedelta], timedelta,]:
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

                late_start[task_id], late_finish[task_id] = (
                    self._apply_backward_constraints(constraint_index.get(task_id, []), task, late_start[task_id], late_finish[task_id]))

        return late_start, late_finish, project_duration

    def _apply_backward_constraints(self, constraints: list[tuple[ConstraintType, timedelta]], task: Task, late_start: timedelta, late_finish: timedelta) -> tuple[timedelta, timedelta]:
        """Pull candidate late dates in to satisfy this task's constraints.

        Soft constraints (Start-No-Later-Than, Finish-No-Later-Than) pull
        the candidates in to the more restrictive of the network and the
        constraint. Mandatory constraints then pin the dates exactly and
        raise SchedulingError when the network cannot accommodate the pin,
        applied last so the outcome does not depend on the order the
        constraints were added. A task pinned by a mandatory constraint
        therefore carries zero total float.
        """
        for con_type, offset in constraints:
            if con_type == ConstraintType.START_NO_LATER_THAN:
                late_start = min(late_start, offset)
                late_finish = late_start + task.duration
            elif con_type == ConstraintType.FINISH_NO_LATER_THAN:
                late_finish = min(late_finish, offset)
                late_start = late_finish - task.duration

        pinned_lf = None
        for con_type, offset in constraints:
            if con_type == ConstraintType.MANDATORY_START:
                pin = offset + task.duration
                boundary = "start"
            elif con_type == ConstraintType.MANDATORY_FINISH:
                pin = offset
                boundary = "finish"
            else:
                continue

            if pinned_lf is None:
                if late_finish < pin:
                    raise SchedulingError(
                        f"Task '{task.number}' violates mandatory {boundary} constraint.")
                pinned_lf = pin
            elif pinned_lf != pin:
                raise SchedulingError(
                    f"Task '{task.number}' has conflicting mandatory constraints.")

        if pinned_lf is not None:
            late_finish = pinned_lf
            late_start = late_finish - task.duration

        return late_start, late_finish

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
        """Return tasks with zero or negative total float.

        Negative total float appears when a soft constraint cannot be met
        without pushing a task past dates the network forbids. Those tasks
        are over-constrained and stay critical so they remain visible in
        critical paths and the Gantt.
        """

        critical_tasks = []
        for task_id in total_float:
            if total_float[task_id] is not None and total_float[task_id] <= timedelta(0):
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
    