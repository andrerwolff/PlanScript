from datetime import timedelta
# TODO finish this
def render(project, schedule):
    gantt_start = project.start_date
    gantt_end = gantt_start + schedule.duration
    factor = 1

    if (gantt_end - gantt_start).days > 100:
        factor = 7
    elif (gantt_end - gantt_start).days < 15:
        factor = 0.1

    for task_id in schedule.hierarchy.get_tree():
        if schedule.hierarchy.is_summary(task_id):
            offset = int(((schedule.start_dates[task_id] - project.start_date).days)/factor)
            length = int(((schedule.finish_dates[task_id] - schedule.start_dates[task_id]).days)/factor)
        else:
            offset = int(schedule.early_start[task_id].days/factor)
            length = int(project.tasks[task_id].duration.days/factor)

        if length == 0:
            l_str = "@" #"◆"
        elif task_id in schedule.critical_tasks:
            l_str = "!"+("≡"* (length - 2))+"¡" #'$'*length
        elif schedule.hierarchy.is_summary(task_id):
            l_str = "{"+("-"* (length - 2))+"}" #'-'*length
        else:
            l_str = ('='* (length)) #'█'*length
        print(f"{task_id:^7}| "
            f"{' '*offset}"
            f"{l_str}")
    input("Press Enter to continue...")
    return f"-"* 69