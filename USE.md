python -m planscript <arg> <file_name.plan> [--options, -o]
PlanScript project planning and scheduling tool.

positional arguments:
  {check,summary,schedule,status}
    check               Validate a PlanScript file.
    summary             Display a project summary.
    schedule            Calculate and display the project schedule.
    status              Display current project status.

options:
  -h, --help            show this help message and exit


usage: planscript schedule [-h] [-d] [-c] [-g] file

positional arguments:
  file

options:
  -h, --help        show this help message and exit
  -d, --dates       Display Scheduled dates.
  -c, --calculated  Display calculated schedule values.
  -g, --gantt       Display the project Gantt chart.