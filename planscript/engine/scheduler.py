from datetime import timedelta
from planscript.model.project import Project
from planscript.model.dependency import DependencyType
from collections import deque


class Schedule:
    def __init__(self, project, ordered_task_ids, early_start, early_finish,
        late_start, late_finish, total_float, critical_tasks, critical_paths, duration):

        self.project = project
        self.ordered_task_ids = ordered_task_ids
        self.early_start = early_start
        self.early_finish = early_finish
        self.late_start = late_start
        self.late_finish = late_finish
        self.total_float = total_float
        self.critical_tasks = critical_tasks
        self.critical_paths = critical_paths
        self.duration = duration

    def __str__(self):
        print()
        print(f"    PROJECT: {self.project.name}")
        print(f"    Duration: {self.duration}")
        print("~" * 69)
        print()
        print(f"|{'ID':<5}|{'TASK':<25}|{'DUR':^5}|{'ES':^5}|{'EF':^5}|{'LS':^5}|{'LF':^5}|{'FLOAT':^5}|")
        print("-" *69)

        for task_id in self.ordered_task_ids:
            task = self.project.tasks[task_id]

            d = task.duration.days
            es = self.early_start[task_id].days
            ef = self.early_finish[task_id].days
            ls = self.late_start[task_id].days
            lf = self.late_finish[task_id].days
            f = self.total_float[task_id].days

            print(f" {task_id:<5} {task.name:<25} {d:^5} {es:^5} {ef:^5} {ls:^5} {lf:^5} {f:^5} ")
        print(f"-"* 69)
        print()
        print("Critical Path(s):")
        for path in self.critical_paths:
            print(" → ".join(str(task) for task in path))
        input("Press Enter to continue...")
        return f"-"* 69

class Scheduler:
    
    def calculate(self, project):
        ordered_task_ids = self._topological_sort(project)
        early_start, early_finish = self._forward_pass(project, ordered_task_ids)
        late_start, late_finish, duration = self._backward_pass(project, ordered_task_ids, early_finish)
        total_float = self._float(ordered_task_ids, early_start, late_start)
        critical_tasks = self._critical_tasks(ordered_task_ids, total_float)
        critical_paths = self._find_critical_paths(project, critical_tasks)

        return Schedule(project = project,
            ordered_task_ids = ordered_task_ids,
            early_start = early_start,
            early_finish = early_finish,
            late_start = late_start,
            late_finish = late_finish,
            total_float= total_float,
            critical_tasks = critical_tasks,
            critical_paths = critical_paths,
            duration = duration)
       

    def _topological_sort(self, project):
        ordered_task_ids = []
        dependency_count = {}

        for task_id, task in project.tasks.items():
            dependency_count[task_id] = len(project.get_predecessors(task))

        queue = deque()

        for task_id, count in dependency_count.items():
             if count == 0:
                queue.append(task_id)

        while queue:
             task_id = queue.popleft()
             ordered_task_ids.append(task_id)

             for dependent_id, dependent in project.tasks.items():
                if project.tasks[task_id] in project.get_predecessors(dependent):
                    dependency_count[dependent_id] -= 1

                    if dependency_count[dependent_id] == 0:
                        queue.append(dependent_id)

        if len(ordered_task_ids) != len(project.tasks):
            raise ValueError("Circular dependency detected")
        return ordered_task_ids

    def _forward_pass(self, project, ordered_task_ids):
        early_start = {}
        early_finish = {}

        for task_id in ordered_task_ids:
            task = project.tasks[task_id]
            dependencies = project.get_incoming_dependencies(task)

            if not dependencies:
                early_start[task_id] = timedelta(0)

            else:
                candidate_es_values = []
                for dependency in dependencies:
                    predecessor = dependency.predecessor
                    predecessor_id = predecessor.number
                    if dependency.dependency_type == DependencyType.FINISH_START:
                        candidate_es = (early_finish[predecessor_id] + dependency.lag)
                        
                    elif dependency.dependency_type == DependencyType.START_START:
                        candidate_es = (early_start[predecessor_id] + dependency.lag)

                    elif dependency.dependency_type == DependencyType.FINISH_FINISH:
                        candidate_ef = (early_finish[predecessor_id] + dependency.lag)
                        candidate_es = (candidate_ef - task.duration)

                    elif dependency.dependency_type == DependencyType.START_FINISH:
                        candidate_ef = (early_start[predecessor_id] + dependency.lag)
                        candidate_es = (candidate_ef - task.duration)

                    else:
                        raise ValueError("Looks like an issue with dependency type - Forward Pass")

                    candidate_es_values.append(candidate_es)
                #early_start[task_id] = max(timedelta(0), max(candidate_es_values)) for clamp to 0
                early_start[task_id] = max(candidate_es_values)

            early_finish[task_id] = (early_start[task_id] + task.duration)

        return early_start, early_finish

    def _backward_pass(self, project, ordered_task_ids, early_finish):
        project_duration = max(early_finish.values())
        late_start = {}
        late_finish = {}
        for task_id in reversed(ordered_task_ids):
            task = project.tasks[task_id]
            #----------------------------
            dependencies = project.get_outgoing_dependencies(task)
            candidate_lf_values = [project_duration]
            for dependency in dependencies:
                successor = dependency.successor
                successor_id = successor.number

                if dependency.dependency_type == DependencyType.FINISH_START:
                    candidate_lf = (late_start[successor.number] - dependency.lag)

                elif dependency.dependency_type == DependencyType.START_START:
                    candidate_ls = (late_start[successor.number] - dependency.lag)
                    candidate_lf = (candidate_ls + task.duration)

                elif dependency.dependency_type == DependencyType.FINISH_FINISH:
                    candidate_lf = (late_finish[successor_id] - dependency.lag)

                elif dependency.dependency_type == DependencyType.START_FINISH:
                    candidate_ls = (late_finish[successor_id] - dependency.lag)
                    candidate_lf = (candidate_ls + task.duration)

                else:
                    raise ValueError("Looks like an issue with dependency type - Backward Pass")
                
                candidate_lf_values.append(candidate_lf)
            late_finish[task_id] = min(candidate_lf_values)
            late_start[task_id] = (late_finish[task_id] - task.duration)

        return late_start, late_finish, project_duration

    def _float(self, ordered_task_ids, early_start, late_start):
        total_float = {}

        for task_id in ordered_task_ids:
            total_float[task_id] = late_start[task_id] - early_start[task_id]
        return total_float

    def _critical_tasks(self, ordered_task_ids, total_float):
        critical_tasks = []
        for task_id in ordered_task_ids:
            if total_float[task_id] == timedelta(0):
                critical_tasks.append(task_id)
        return critical_tasks

    def _find_critical_paths(self, project, critical_tasks):
        critical = set(critical_tasks)

        paths = []

        # Find critical tasks with no critical predecessors.
        starts = []

        for task_id in critical:
            task = project.tasks[task_id]

            has_critical_predecessor = False
            for pred in project.get_predecessors(task):
                if pred.number in critical:
                    has_critical_predecessor = True
                    break

            if not has_critical_predecessor:
                starts.append(task_id)

        # Walk forward from each critical starting task.
        def walk(task_id, path):
            path = path + [task_id]

            task = project.tasks[task_id]

            critical_successors = []
            for succ in project.get_successors(task):
                if succ.number in critical:
                    critical_successors.append(succ.number)

            if not critical_successors:
                paths.append(path)
                return

            for successor_id in critical_successors:
                walk(successor_id, path)

        for start_id in starts:
            walk(start_id, [])

        return paths
    