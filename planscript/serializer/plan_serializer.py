


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
        dependency_and_lag = ""
        sign = ""
        # TODO this is very incomplete this is where i left off - giving 2.0 instead of 2 maybe use rstrip
        lag = dependency.lag.days
        lag_unit = dependency.lag_unit
        if lag_unit == "m":
            lag = lag / 30
        elif lag_unit == "w":
            lag = lag / 7
        elif lag_unit == "d":
            lag = lag
        elif lag_unit == "h":
            lag = lag / 24

        if dependency_type != "FS":
            if lag != 0:
                if lag > 0:
                    sign = "+"
                elif lag < 0:
                    sign = "-"
            dependency_and_lag = f"{dependency_type} {sign}{lag:.2f}".rstrip("0").rstrip(".")
            #else:
                #sign = ""
        else:
            dependency_and_lag = f"{dependency_type} {sign}{lag:.2f}".rstrip("0").rstrip(".")

        line = str(f"dependency {predecessor_id} > {successor_id} {dependency_and_lag}{lag_unit}")
        return line