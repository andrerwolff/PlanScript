from datetime import timedelta

from planscript.engine.scheduler import Scheduler
from planscript.engine.analyzer import Analyzer
from planscript.engine.tracker import TaskState, TaskStatus
from planscript.model.project import Project
from planscript.model.schedule import Schedule
from planscript.model.task import Task
from planscript.model.dependency import Dependency
from planscript.model.constraint import Constraint, ConstraintType

class Forecaster:

    def forecast(self, project:Project, as_of=None) -> Schedule:
        forecast_project = self._build_forecast_project(project, as_of)
        return Scheduler().calculate(forecast_project)

    def _build_forecast_project(self, project:Project, as_of=None):
        forecast_project = Project(name=project.name,
                                   start_date=project.start_date,
                                   finish_date=project.finish_date,
                                   calendar=project.calendar)
        
        for task_id, task in project.tasks.items():
            
            task_state = project.tracker.get_task_state(task_id, as_of)
            if task_state.status == TaskStatus.COMPLETED:
                forecast_duration = timedelta(0)
                con_date = project.tracker.actual_finish(task_id)
                con_type = ConstraintType.MANDATORY_FINISH
            elif task_state.status == TaskStatus.IN_PROGRESS:
                forecast_duration = (1 - task_state.percent_complete / 100) * task.duration
                con_date = project.tracker.actual_start(task_id)
                con_type = ConstraintType.MANDATORY_START
            else:
                forecast_duration = task.duration
                con_type = None
                con_date = None
                
            forecast_task = Task(task_id, "f_" + task.name, forecast_duration)
            forecast_project.add_task(forecast_task)
            if con_date is not None and con_type is not None:
                forecast_project.add_constraint(forecast_task, con_type, con_date)

        for dep in project.dependencies:

            successor_id = dep.successor.number
            predecessor_id = dep.predecessor.number
            dep_type = dep.dep_type
            lag = dep.lag
            lag_unit = dep.lag_unit

            forecast_project.add_dependency(predecessor=forecast_project.tasks[predecessor_id], 
                                            successor=forecast_project.tasks[successor_id], 
                                            dep_type=dep_type, lag=lag, lag_unit=lag_unit)
