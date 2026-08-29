from datetime import timedelta
# TODO finish this
def render(project, schedule):
    gantt_start = project.start_date
    gantt_end = gantt_start + schedule.duration
    factor = 1

    if gantt_end.day - gantt_start.day > 100:
        factor = 7
    elif gantt_end.day - gantt_start.day < 15:
        factor = 0.1

    for task_id in schedule.ordered_task_ids:
        offset = int(schedule.early_start[task_id].days/factor)
        length = int(project.tasks[task_id].duration.days/factor)
        if length == 0:
            l_str = "*" #"◆"
        elif task_id in schedule.critical_tasks:
            l_str = "{"+("$"* (length - 2))+"}" #'█'*length
        else:
            l_str = "["+("|"* (length - 2))+"]" #'█'*length
        print(f"{task_id:^7}| "
            f"{' '*offset}"
            f"{l_str}")
    input("Press Enter to continue...")
    return f"-"* 69