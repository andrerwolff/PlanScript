"""Forecast schedules derived from a plan's tracking state.

The Forecaster builds a throwaway copy of the project in which each task's
remaining duration and constraints are derived from tracking at a single data
date (`as_of`):

* finished work is pinned to its actual finish with a mandatory-finish
  constraint, because history is a fact the network must accommodate;
* every unfinished task - started, in progress, or not started - keeps its
  remaining duration, `(1 - percent_complete / 100) * planned`, floored at
  the data date with start-no-earlier-than, so remaining work is projected
  forward from the data date and an open task never forecasts a finish
  before it;
* summary tasks take neither duration nor constraint.

The forecast is scheduled by the normal CPM Scheduler, so dependencies, lag,
milestones, and summary rollups behave exactly as they do for the plan, and
forecast float stays network-derived. The source project is never modified:
forecasts are derived information. When the network cannot accommodate a
finished task's actual finish, the scheduler raises `SchedulingError`.
"""

from datetime import timedelta

from planscript.engine.scheduler import Scheduler
from planscript.engine.analyzer import Analyzer
from planscript.engine.tracker import TaskState, TaskStatus
from planscript.model.project import Project
from planscript.model.schedule import Schedule
from planscript.model.task import Task
from planscript.model.dependency import Dependency
from planscript.model.constraint import ConstraintType

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
            if task.duration is None:
                forecast_duration = None
                con_type = None
                con_date = None
            
            else:
                task_state = project.tracker.get_task_state(task_id, as_of)

                if task_state.status == TaskStatus.COMPLETED:
                    # History is a fact: the network must accommodate the
                    # actual finish.
                    forecast_duration = timedelta(0)
                    con_date = project.tracker.actual_finish(task_id, as_of)
                    con_type = ConstraintType.MANDATORY_FINISH

                else:
                    # Everything unfinished - started, in progress, or not
                    # started - forecasts its remaining duration forward
                    # from the data date, so an open task never forecasts a
                    # finish before the data date and a bare `start` event
                    # behaves exactly like `progress 0%`.
                    forecast_duration = (1 - task_state.percent_complete / 100) * task.duration
                    con_type = ConstraintType.START_NO_EARLIER_THAN
                    con_date = as_of
                    
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
        return forecast_project
