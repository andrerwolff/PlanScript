


class PlanSerializer():
    def serialize(self, project) -> str:
        lines = []

        lines.append(f"project: {project.name}")
        # TODO add metadata
        lines.append("")
        # TODO add calendar
        lines.append(f"start: {project.start_date}")
        lines.append(f"finish: {project.finish_date}")
        lines.append("")
        
        for task in project.tasks.values():
            lines.append(self._serialize_task(task))

        lines.append("")

        for dependency in project.dependencies:
            lines.append(self._serialize_dependency(dependency))

        return "\n".join(lines)

    def _serialize_task(self, task):
        line = str(f"task {task.number} {task.name} {task.duration.days}d")
        return line
    
    def _serialize_dependency(self, dependency):
        predecessor_id = dependency.predecessor.number
        successor_id = dependency.successor.number
        dependency_type = dependency.dependency_type.value
        
        lag = dependency.lag.days
        if dependency_type != "FS":
            if lag != 0:
                if lag > 0:
                    sign = "+"
                elif lag < 0:
                    sign = "-"
            else:
                sign = ""
        else:
            dependency_type = ""
                

        
        elif lag == 0:
            sign = ""
            lag = ""
        lag = sign + str(lag)
        line = str(f"{predecessor_id} > {successor_id} {dependency_type} {lag}")
        return line