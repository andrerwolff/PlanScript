# PlanScript — Design

## Purpose

Plaintext-first project scheduling system inspired by Beancount & hledger.

The PlanScript file is the authoritative project definition. The system parses it into a project model, validates it, calculates a schedule, and exposes results through CLI and future GUI/plugin interfaces.

## Architecture

```text
PlanScript file
      ↓
    Parser
      ↓
 Project Model
      ↓
 Scheduler
      ↓
 CLI / GUI / Plugins
```

## Core Components

* **Parser** — Reads and validates PlanScript files.
* **Model** — Represents projects, tasks, and dependencies.
* **Scheduler** — Performs CPM scheduling.
* **CLI** — Initial user interface.
* **TBD - Godot?** — Future interface.
* **TBD - Logseq?** — Future integration.

## Model

* `Project`
    * `name`: str, Project name
    * `start`: date, Target start date (soft for planning only, not for CPM scheduling)
    * `finish`: date, Target finish date (soft for planning only, not for CPM scheduling)
    * `tasks`: dict, [task_id, Task] dictionary of all task objects for the project (summary type tasks not yet in this list).
    * `dependencies`: list, (Dependency) list of all dependency objects for the project.
    * `calendar`: dict, [calendar name, Calendar] Dictionary of calendars for the project (not yet implemented)
    * `metadata`: dict, [key, value], project information not related to scheduling or other critical calculations
* `Task` 
    * `number`: str, user defined alphanumerical heierarchy such as `1.1` or `4.2.a`.
        * Used for key reference internally 
    * `name`: str, user defined task name, used for display, not used elsewhere
    * `duration`: timedelta, duration of the task
        * defaults to 0 if nothing entered
        * defaults to days if no unit entered.
        * 0 duration tasks are treated as milestones. 
    * `calendar`: str, (not yet implemented)
    * `constraints`: list (), (not yet implemented)
    * `metadata`: dict, [key, value], task information not related to scheduling or other critical calculations
* `Dependency`
    * `predecessor`: Task, task object that drives the successor
    * `successor`: Task, task object that is driven by the dependency
    * `dependency_type`: DependencyType, FS, SS, FF, SF enum
        * defaults to FS if not specified 
    * `lag`: timedelta, + or - 
        * defaults to 0 if not specified
* `Calendar` (not yet implemented)

## Engine / Scheduler

* `Schedule`
    * `project`: Project
    * `ordered_task_ids`: 1d array, [task_id] in topological order
    * `early_start`: dict, [task_id, timedelta] representing list of all tasks early starts
    * `early_finish`: dict, [task_id, timedelta] representing list of all tasks early finishes
    * `late_start`: dict, [task_id, timedelta] representing list of all tasks late starts
    * `late_finish`: dict, [task_id, timedelta] representing list of all tasks late finishes
    * `total_float`: dict, [task_id, timedelta] representing list of all tasks float
    * `critical_tasks`: 1d array, [task_id] that are identified as critical tasks (float = 0)
    * `critical_paths`: 2d array, [[path-1], [path-2], [path-n]] of ordered task_ids that represent critical paths
    * `duration`: timedelta: total project duration (maximum EF)

* `Scheduler.calculate()`: returns a Schedule object
    * `_topological_sort()`: returns `ordered_task_ids`
    * `_forward_pass()`: returns `early_start`, `early_finish`
    * `_backward_pass()`: returns `late_start`, `late_finish`, `duration`
    * `_float()`: returns `total_float`
    * `_critical_tasks()`: returns `critical_tasks`
    * `_find_critical_paths()`: returns `critical_paths` using recursive `walk()` method

## CLI

The CLI runs from the app.py file and generally has the below structure:
* `Main Menu`
    * `New Project`
    * `Open Project` : `o` `f` opens simple.plan file in the parser, `o` `#` opens a test project by number
    * `Recent Projects`
    * `Quit`
* `Project Menu`
    * `Tasks`
    * `Dependencies`
    * `Project Properties`
    * `View Schedule`
    * `Save Project`
    * `Back to Main Menu`
    * `Quit`
* `Task Menu`
    * List of tasks
    * `New Task`
    * `Edit Task`
    * `Delete Task`
    * `Back to Project Menu`
* `Dependency Menu`
    * List of dependencies
    * new, edit, delete, back to project menu
* `View Schedule`
    * Project info (name, calculated duration)
    * Table showing Task List table with each task duration, ES, EF, LS, LF, Float
    * Critical path(s)



## Validation

Invalid project definitions should produce clear errors rather than crashes or silently incorrect schedules.

Parser validation includes malformed syntax, unknown tasks, and invalid dependencies.

## Testing

Use Python `unittest`.

Tests should cover:

* Valid parsing
* Invalid/malformed input
* Dependency types
* Branching and merging
* Multiple starts/finishes
* Circular dependencies
* CPM calculations
* Critical path
* Edge cases
