# PlanScript — Usage

```powershell
python -m planscript <command> <file_name.plan> [options]
```

PlanScript project planning and scheduling tool. The `.plan` file is read-only:
commands parse, validate, calculate, and report, but never modify the file.

## Commands

```text
usage: planscript [-h] {check,summary,schedule,status,budget} ...

positional arguments:
  {check,summary,schedule,status,budget}
    check               Validate a PlanScript file.
    summary             Display a project summary.
    schedule            Calculate and display the project schedule.
    status              Display current project status.
    budget              Display project financials.

options:
  -h, --help            show this help message and exit
```

### `check`

Parses and validates the file, then prints the project name and `Valid`.

```powershell
python -m planscript check Full_Plan.plan
```

```text
Project: DOTI LS6
Valid
```

### `summary`

Displays the project header (`PROJECT`, duration when scheduled, target start
and finish) plus task, dependency, and tracking event counts. It does not
calculate a schedule.

```powershell
python -m planscript summary Simple.plan
```

### `schedule`

```text
usage: planscript schedule [-h] [-d] [-c] [-g] file

options:
  -h, --help        show this help message and exit
  -d, --dates       Display Scheduled dates.
  -c, --calculated  Display calculated schedule values.
  -g, --gantt       Display the project Gantt chart.
```

With no display option, all three views plus the critical path(s) are shown.

* `-c` — ID, task, duration, ES, EF, LS, LF, float.
* `-d` — ID, task, start date, finish date, float.
* `-g` — textual Gantt bars, with critical tasks marked.

```powershell
python -m planscript schedule Simple.plan -d
python -m planscript schedule Detailed.plan
```

### `status`

```text
usage: planscript status [-h] [-ao AS_OF] [-la LOOK_AHEAD] file

options:
  -h, --help            show this help message and exit
  -ao AS_OF, --as-of AS_OF
                        Date for the status report (YYYY-MM-DD). Default Today
  -la LOOK_AHEAD, --look-ahead LOOK_AHEAD
                        Number of days to look ahead (0 or greater). Default 21
```

Reports project status, progress, overdue tasks, blocked tasks with their
blocking predecessors and root causes, late tasks, and the look-ahead windows.

```powershell
python -m planscript status Simple.plan -ao 2026-09-20 -la 14
```

### `budget`

```text
usage: planscript budget [-h] [-ao AS_OF] file

options:
  -h, --help            show this help message and exit
  -ao AS_OF, --as-of AS_OF
                        Date for the status report (YYYY-MM-DD). Default Today
```

Resolves explicit and weighted budgets and prints each task's amount with its
basis (`explicit`, weight, `rollup`, or `unallocated`), the project total, and
any unallocated tasks.

```powershell
python -m planscript budget Simple.plan
```

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | Expected failure: file not found, decode error, parse/validation/scheduling/budgeting error. The message is printed to stderr as `Parse error: …` or similar. |
| `2` | argparse usage error (unknown command or option). |

Unexpected exceptions are not caught and appear as tracebacks; treat one as a
bug and report it with the plan file. The known defects in this area are listed
in `ROADMAP.md` under P0.

## Sample plans

* `Simple.plan` — small project with budgets, invoices, and tracking events.
* `Detailed.plan` — a larger CPM network with partial tracking.
* `Full_Plan.plan` — metadata, calendars, lagged dependencies, and mixed
  tracking directives.
