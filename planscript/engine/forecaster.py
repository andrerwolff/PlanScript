

from planscript.engine.scheduler import Scheduler
from planscript.engine.analyzer import Analyzer
from planscript.engine.tracker import TaskState, TaskStatus
from planscript.model.project import Project
from planscript.model.schedule import Schedule
from planscript.model.task import Task

class Forecaster:

    def forecast(self, project:Project, as_of=None) -> Schedule:
        forecast_project = self._build_forecast_project(project, as_of)
        return Scheduler.calculate(forecast_project)

    def _build_forecast_project(self, project:Project, as_of=None):
        forecast_project = Project(name=project.name,
                                   start_date=project.start_date,
                                   finish_date=project.finish_date,
                                   calendar=project.calendar,
                                   metadata=project.metadata,)
        for task_id, task in project.tasks.items():
            task_state = project.tracker.get_task_state(task_id, as_of)
            if task_state.status == TaskStatus.COMPLETED:
                #if task is complete no need to forecast, but need to check dependencies
                continue
            elif task_state.status == TaskStatus.NOT_STARTED:
                f_duration = task.duration
            elif task_state.t####################################################HHHHHHERRRRRRRRRRRREEEEEEEEEEEEE
                f_task = Task(task_id, task.name, task.duration)
                forecast_project.add_task(f_task)

            if project.tracker.ge   
