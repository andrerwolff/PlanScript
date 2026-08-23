from datetime import timedelta
from planscript.model.project import Project
from collections import deque

class Scheduler:
    
    def calculate(self, project):
        orderd_task_ids = self._topological_sort(project)
        early_start, early_finish = self._forward_pass(project, orderd_task_ids)
        late_start, late_finish = self._backward_pass(project, orderd_task_ids, early_finish)

        return early_start, early_finish, late_start, late_finish

            

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
            preds = project.get_predecessors(task)
            if not preds:
                early_start[task_id] = timedelta(0)
            else:
                max_pef = timedelta(0)
                for pred in preds:
                    if early_finish[pred.number] > max_pef:
                        max_pef = early_finish[pred.number]
                early_start[task_id] = max_pef

            early_finish[task_id] = early_start[task_id] + task.duration

        return early_start, early_finish

    def _backward_pass(self, project, ordered_task_ids, early_finish):
        project_duration = max(early_finish.values())
        late_start = {}
        late_finish = {}

        for task_id in reversed(ordered_task_ids):
            task = project.tasks[task_id]
            succs = project.get_successors(task)
            if not succs:
                finish = project_duration
            else:
                min_sls = project_duration
                for succ in succs:
                    if late_start[succ.number] < min_sls:
                        min_sls = finish
                finish = min_sls

            start = finish - task.duration

            late_start[task_id] = start
            late_finish[task_id] = finish

        return late_start, late_finish
