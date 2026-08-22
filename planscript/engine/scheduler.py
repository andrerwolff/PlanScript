from planscript.model.project import Project

class Scheduler:
    
    def calculate(self, project):
            orderd_tasks = self._topological_sort(project)

    def _topological_sort(self, project):
        ordered_tasks = []
        dependency_count = {}
        for task in project.tasks.values():
            dependency_count[task.number] = len(project.get_predecessors(task))

        for task in in_degree:
             if in_degree[task] == 0
                ordered_tasks.append(task)
            
             in_degree[task] -= 1
        print(in_degree)


