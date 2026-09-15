    
from datetime import timedelta

class Analyzer:
    def __init__(self, project):
        self.project = project

    def start_variance(self, task_id):
        actual = self.project.tracker.actual_start(task_id)
        if actual is None:
            return None
        return actual - self.project.schedule.start_dates[task_id]
    
    def finish_variance(self, task_id):
        actual = self.project.tracker.actual_finish(task_id)
        if actual is None:
            return None
        return  actual - self.project.schedule.finish_dates[task_id]

    def duration_variance(self, task_id):
        
        planned = self.project.tasks[task_id].duration
        if planned == timedelta(0):
            return timedelta(0)
        elif planned == None:
            planned = self.project.schedule.finish_dates[task_id] - self.project.schedule.start_dates[task_id] + timedelta(days=1)

        actual = self.project.tracker.actual_duration(task_id)

        if actual is None:
            return None

        return actual - planned