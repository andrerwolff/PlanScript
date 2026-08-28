from datetime import timedelta
# TODO finish this
def render(project, schedule):
    gantt_start = project.start_date
    gantt_end = gantt_start + schedule.duration

    for task_id in schedule.ordered_task_ids:
        print(task_id, project.tasks[task_id].name)