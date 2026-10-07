# PlanScript — Design

## Purpose

Plaintext-first project scheduling, inspired by Beancount and hledger.

The `.plan` file is the authoritative project definition. The system parses it
into a project model, validates it, derives a CPM schedule, tracking state,
costs, and reports, and exposes the results through a CLI. GUI and plugin
interfaces remain future work.

The central design rule:

> **Derived information must not become a second source of truth.**

Plan definition and tracking history are authoritative and live in the file.
Schedules, resolved budgets, variances, forecasts, and reports are derived and
never written back as authoritative data. (Serialization exists but is not yet
wired into the CLI; see `planscript/serializer/`.)

## Design Principles

1. Plaintext readability over structured-data convenience. Do not drift toward
   JSON/YAML.
2. Avoid quoting and unnecessary punctuation; punctuation must communicate
   meaning.
3. Keep task lines short. Dependencies, budgets, and metadata get their own
   indented lines.
4. Descriptive metadata is separate from scheduler input.
5. Hierarchy in a task number is organizational; it never implies a dependency.
6. CPM stays pure: the scheduler operates on duration/offset values and
   dependency relationships.
7. Dates are mapped to and from schedule offsets in a calendar layer.
8. Do not call something a constraint if it does not change the schedule.
9. Prefer a small number of powerful concepts (a zero-duration task *is* a
   milestone; there is no milestone class).
10. Resolve the semantic model before inventing syntax.
11. Invalid input fails explicitly with a line number; nothing is silently
    repaired.

## Architecture

```text
                        .plan FILE (authoritative)
                              │
                     ┌────────┴────────┐
                     │                 │
              plan definition     tracking history
                     │                 │
                     ▼                 ▼
                  Parser           (events)
                     │                 │
                     ▼                 │
              Project model ◄──────────┘
                     │
        ┌────────────┼────────────┬───────────┬──────────┐
        ▼            ▼            ▼           ▼          ▼
   Scheduler      Tracker      Analyzer    Budgeter   (Serializer)
        │            │            │           │          │
        ▼            ▼            ▼           ▼          ▼
    Schedule     actuals /     variance    Budget     .plan text
                 status       reports    (derived)
        └────────────┴────────────┴───────────┘
                     │
                     ▼
              CLI: display / gantt / reporter
```

## Package Layout

| Module | Responsibility |
| --- | --- |
| `planscript/__main__.py` | Module entry point for `python -m planscript`. |
| `planscript/app.py` | Argument parsing, subcommands, exit codes, error reporting. |
| `planscript/exceptions.py` | `ParseError`, `ValidationError`, `SchedulingError`, `BudgetingError`. |
| `planscript/engine/parser.py` | Line-oriented parser: `.plan` text → `Project`. |
| `planscript/model/project.py` | `Project` aggregate root and project-level validation. |
| `planscript/model/task.py` | `Task` (number, name, duration, budget, metadata). |
| `planscript/model/dependency.py` | `Dependency`, `DependencyType`, `DependencyGraph`. |
| `planscript/model/constraint.py` | `Constraint`, `ConstraintType`: task-level schedule constraints. |
| `planscript/model/hierarchy.py` | `TaskHierarchy` derived from task numbers. |
| `planscript/model/calendar.py` | `Calendar` (working days, holidays). Model only; not yet applied. |
| `planscript/model/budget.py` | `Budget` (resolved/derived budget). |
| `planscript/model/schedule.py` | `Schedule` (derived CPM results and dates). |
| `planscript/engine/scheduler.py` | `Scheduler`: CPM forward/backward pass, float, critical paths, dates. |
| `planscript/engine/tracker.py` | `Tracker`, `TaskEvent`, `TaskState`, `Invoice`, directives and statuses. |
| `planscript/engine/analyzer.py` | `Analyzer`, `TaskVariance`: planned vs. actual variance and progress. |
| `planscript/engine/budgeter.py` | `Budgeter`: resolves explicit and weighted budgets. |
| `planscript/engine/forecaster.py` | `Forecaster`: forecast schedule from actuals; finished work pinned to its actual finish, remaining work floored at the data date. |
| `planscript/engine/reporter.py` | `ReportBuilder` and report dataclasses for status reporting. |
| `planscript/cli/display.py` | Table rendering, schedule/budget views, legacy interactive menus. |
| `planscript/cli/gantt.py` | Textual Gantt rendering. |
| `planscript/serializer/plan_serializer.py` | `Project` → `.plan` text. Incomplete; not wired into the CLI. |
| `planscript/tests/` | `unittest` suite (274 tests) plus shared project fixtures. |
| `_archive/` | Superseded interactive CLI and the original standalone invoice model. |

## Model

All model types are dataclasses. Identity is by task number; `Task` objects are
shared by reference between the project and its dependencies, so renaming a
task number keeps its dependencies attached.

### `Project` (aggregate root)

| Attribute | Type | Notes |
| --- | --- | --- |
| `name` | `str` | Project name from the `project:` line. |
| `start_date` | `date \| None` | Planned/target start. Soft; not a constraint. |
| `finish_date` | `date \| None` | Planned/target finish. Soft; not a constraint. |
| `calendar` | `str \| None` | Calendar name from the `calendar:` attribute; stored, not interpreted. |
| `tasks` | `dict[str, Task]` | Keyed by task number, kept sorted by number. |
| `dependencies` | `list[Dependency]` | All dependency relationships. |
| `constraints` | `list[Constraint]` | Task-level schedule constraints; dates are mapped to CPM offsets at schedule time. |
| `calendars` | `dict[str, Calendar]` | Declared calendars. Currently always empty. |
| `budget` | `Budget` | Derived; populated by `Budgeter`. |
| `schedule` | `Schedule \| None` | Derived; populated by `Scheduler`. |
| `tracker` | `Tracker` | Authoritative tracking history and derived state. |
| `metadata` | `dict` | Project-level descriptive metadata. |

Operations: `add_task`, `remove_task` (also removes its dependencies and
constraints), `renumber_task`, `sort_tasks`, `list_tasks`, `add_dependency`,
`remove_dependency`, `add_constraint`, `get_predecessors`, `get_successors`,
`get_incoming_dependencies`, `get_outgoing_dependencies`, `validate`.

`Project.validate()` is the single entry point for model validation and runs
date, summary, dependency, constraint, budget, duration, and tracking checks.

### `Task`

| Attribute | Type | Notes |
| --- | --- | --- |
| `number` | `str` | Hierarchical identifier such as `4.2.a`; the dictionary key. |
| `name` | `str` | Display name only. |
| `duration` | `timedelta \| None` | `None` = summary task; `0` = milestone. |
| `budget` | `Decimal \| None` | Explicit budget. |
| `budget_wt` | `Decimal \| None` | Percentage weight of the budgeted ancestor. |
| `metadata` | `dict` | Free-form task metadata. |

Also `Task.is_milestone`. A task-level `calendar` field is planned but not yet
implemented.

### `Dependency` and dependency types

| Attribute | Type | Notes |
| --- | --- | --- |
| `predecessor` | `Task` | Task that establishes the constraint. |
| `successor` | `Task` | Task whose schedule is constrained. |
| `dep_type` | `DependencyType` | `FS` (default), `SS`, `FF`, `SF`. |
| `lag` | `timedelta` | Signed offset; defaults to zero. |
| `lag_unit` | `str` | Unit the lag was authored in (`h`/`d`/`w`). |

`DependencyGraph` is a derived index of the project's `Dependency` objects
(`predecessors`/`successors` keyed by task ID). `topological_sort()` returns
task IDs in dependency order and raises `ValueError` if the graph contains a
cycle.

### `Constraint` and constraint types

| Attribute | Type | Notes |
| --- | --- | --- |
| `task` | `Task` | Task the constraint applies to. Leaf tasks only; summary tasks are rejected. |
| `con_type` | `ConstraintType` | Soft: `SNET`, `SNLT`, `FNET`, `FNLT`. Mandatory (hard): `MSON`, `MFON`. |
| `con_date` | `date` | Authoritative calendar anchor, stored as authored. |

Constraints require a project `start_date` to anchor them to. The scheduler
maps `con_date` to an offset from `start_date` before the passes, so no
offset is stored and reassigning `start_date` cannot leave stale derived
data behind. Start-side dates map directly (`con_date − start_date`);
finish-side dates map one day later for leaf tasks, because a leaf task's
calendar finish falls the day before its early-finish offset — a milestone
finishes on its start day, so no adjustment applies to it. Only leaf tasks
(including milestones) may carry a constraint — a summary task's dates are
derived from its children, so a constraint there would never change the
schedule.

Soft constraints resolve to the more restrictive of the network and the
constraint. Mandatory constraints pin the date exactly — in both the early
and the late dates, so a mandatory task always carries zero total float —
and raise `SchedulingError` when the network cannot accommodate the pin or
when two mandatory constraints on one task demand different pins. The
`Forecaster` pins completed tasks to their actual finish with a mandatory
constraint, and floors every unfinished task - started or not - at the data
date with a start-no-earlier-than constraint, so remaining work is projected
forward from the data date rather than replayed from the actual start.

### `TaskHierarchy`

Derived purely from task numbers: `1.2.3` belongs to `1.2` when that task
exists. When an implied parent does not exist, the task attaches to its
nearest existing ancestor — with `1` present but `1.2` absent, `1.2.3` is a
child of `1` — so projects need not declare every level; a task with no
existing ancestor is a root. This is separate from the dependency
graph. API: `get_parent`, `get_children`, `get_roots`, `get_leaves`,
`get_leaf_ids`, `has_children`, `is_summary`, `get_descendants`,
`get_ancestors`, `get_tree`.

### `Calendar`

`id`, `name`, `working_days` (0 = Monday), and `holidays`, with
`is_working_day`, `next_working_day`, `previous_working_day`,
`add_working_days`, and `working_days_between`.

**Status:** implemented as a model but not yet used by the scheduler, tracker,
or analyzer. Dates are currently scheduled on plain calendar days.

### `Schedule` (derived)

`hierarchy`, `ordered_task_ids`, `early_start`, `early_finish`, `late_start`,
`late_finish`, `total_float`, `critical_tasks`, `critical_paths`, `duration`,
`start_dates`, `finish_dates`.

CPM values are stored as `timedelta` offsets from the project's planned start
day; `start_dates`/`finish_dates` are the calendar-day projections of those
offsets when the project has a `start_date`, and `None` when it does not (a
calculated-only schedule). Summary tasks have `None` float because they do
not participate in CPM.

### `Tracker`, events, and invoices

* `TaskEvent(date, task_id, directive, info)` — one dated event.
* `EventDirective` — `START`, `PROGRESS`, `COMPLETE`, `NOTE`.
* `TaskStatus` — `NOT_STARTED`, `STARTED`, `IN_PROGRESS`, `COMPLETED`.
* `TaskState(task_id)` with `status` and `percent_complete`, derived by
  replaying the task's events in date order (`_derive`).
* `Invoice(invoice_date, invoice_amount, allocations)` with `add_allocation`
  and `validate` (allocations must equal the invoice amount).
* `Tracker(hierarchy, task_events, invoice_events)` derives `actual_start`,
  `actual_finish`, `actual_dates`, `actual_duration`, `actual_cost`, and
  `get_task_state`.

Actual dates for summary tasks are rolled up from descendants: earliest actual
start, latest actual finish (and a summary is only finished when all children
are).

### `Analyzer` (derived)

`Analyzer(project, as_of)` computes `start_variance`, `finish_variance`,
`duration_variance`, `task_variance`, `cost_variance` (actual cost minus
resolved budget for one task), `total_cost_variance` (project actual minus
budget total), `project_actual_start`, and `project_progress`
(duration-weighted percent complete across leaf tasks). Schedule variance is
positive when later than planned; cost variance is positive when over budget.

## Engines

### `Scheduler` — CPM

`Scheduler().calculate(project) -> Schedule` runs these stages:

1. Build a `TaskHierarchy` and a `DependencyGraph`.
2. Topologically sort tasks by dependency (cycle ⇒ `ValidationError` at
   validation time).
3. **Forward pass** — for each leaf task, earliest start is the maximum imposed
   start across its predecessors:
   * `FS`: `ES(succ) = EF(pred) + lag`
   * `SS`: `ES(succ) = ES(pred) + lag`
   * `FF`: `EF(succ) = EF(pred) + lag`, then `ES = EF − duration`
   * `SF`: `EF(succ) = ES(pred) + lag`, then `ES = EF − duration`
   Tasks with no predecessors start at offset 0. `EF = ES + duration`.
   Soft constraints then raise the candidate: `SNET` with the constraint
   offset, `FNET` with the offset less the duration. Mandatory constraints
   are applied last: `MSON`/`MFON` pin the candidate exactly and raise
   `SchedulingError` when the network pushes past the pin, so the outcome
   does not depend on the order constraints were added.
4. **Backward pass** — project duration is the maximum early finish; latest
   finish starts there and propagates back through successors. Soft
   constraints then pull the candidates in: `SNLT` on the late start, `FNLT`
   on the late finish. Mandatory constraints then pin the late dates to the
   same pins (or raise), which is what leaves a mandatory task with zero
   float. In both passes the more restrictive of the network
   and the constraint wins.
5. **Float** — `total_float = LS − ES`. Summary tasks get `None`.
6. **Critical tasks** — total float zero or negative. Negative float means a
   soft constraint cannot be met without violating the network; those tasks
   are over-constrained and stay critical so they remain visible.
7. **Critical paths** — walks the sub-graph of critical tasks connected by
   *tight* dependencies (those that actually impose the successor's early
   start). Branches produce multiple paths.
8. **Dates** — offsets are projected onto calendar days from the project's
   `start_date`. A milestone finishes on its start day; other tasks finish one
   day before `EF`. Summary dates roll up: earliest descendant start, latest
   descendant finish.

Rules and current limits:

* Durations and offsets are treated as plain calendar days. The project's
  `calendar:` is not consulted yet.
* Without a project `start_date` the schedule is calculated-only:
  `start_dates`/`finish_dates` are `None`. The scheduled view and Gantt chart
  print a note, `Analyzer` variance and `ReportBuilder` raise
  `SchedulingError`, and the `status` command exits `1`.
* Summary tasks are excluded from CPM and only receive rolled-up dates.
* Constraint dates are converted to offsets from `start_date` before the
  passes (the calendar boundary), so a project with constraints but no
  `start_date` raises `SchedulingError`.
* Soft constraints take the more restrictive value; mandatory constraints
  pin both the early and the late dates, so a mandatory task always carries
  zero float, and raise `SchedulingError` when the network cannot
  accommodate the pin.

### `Tracker` — actuals

Records events and derives per-task actuals. Every derived value is measured to
a single **data date** (`as_of`), which is the report's reference date and
defaults to today. Events and invoices dated after the data date are ignored,
so historical state is deterministic and a future-dated entry never makes a
task look started or finished. `future_dated_events(as_of)` returns the entries
a data date excluded, so callers can report them instead of silently dropping
them.

* `actual_start` — the task's `start` event; for a summary, the earliest
  descendant actual start.
* `actual_finish` — the task's `complete` event; for a summary, the latest
  descendant finish, and only when every descendant is finished.
* `actual_duration` — inclusive calendar days: `finish − start + 1`, or
  `as_of − start + 1` while the task is open. Because the data date limits the
  events considered, an elapsed duration is never negative, and a task whose
  start is recorded after the data date has no actual duration yet.
* `actual_cost` — sum of invoice allocations to the task up to the data date,
  plus all descendant costs for a summary.
* `get_task_state` — replays events up to the data date to derive `TaskStatus`
  and `percent_complete`, raising `ValidationError`/`ParseError` for invalid
  sequences instead of repairing them.

### `Analyzer` — variance

Compares `Schedule` and task durations against `Tracker` actuals at the same
data date (`Analyzer(project, as_of)`, defaulting to today):

* `start_variance` / `finish_variance` — actual minus planned date, `None`
  until the corresponding actual exists; raises `SchedulingError` when the
  schedule has no calendar dates (no project `start_date`).
* `duration_variance` — actual (or elapsed, measured to `as_of`) duration minus
  planned duration. Summary planned duration comes from scheduled dates
  (raising `SchedulingError` when the schedule has none). A milestone that has
  happened has zero duration variance; one that has not reports `None`.
* `planned_progress` / `actual_progress` — 0..1 fractions for a task. Planned
  progress counts calendar days to `as_of`, inclusive of the planned start day
  and capped at the planned duration; a milestone counts as planned once its
  date is reached. Actual progress comes from the tracking events up to `as_of`;
  a milestone reports as complete or not complete, since it has no duration to
  measure.
* `planned_project_progress` / `actual_project_progress` — duration-weighted
  averages over leaf tasks with a positive duration, so milestones and summary
  tasks do not weight the project figure.
* `project_actual_start` — earliest actual start across tasks.
* `cost_variance` / `total_cost_variance` — actual minus budget, where a
  positive value is over budget.
* `project_consumed_cost` — actual cost divided by the planned budget, or
  `None` when the project has no planned budget.

### `Budgeter` — budget resolution

`Budgeter().calculate(project) -> Budget` performs two passes:

1. **Allocate top-down.** Each task keeps its explicit amount (which becomes
   the base for its own children). Weighted siblings split their nearest
   budgeted ancestor's amount by percentage. Shares are allocated in whole
   cents, with leftover cents awarded to the largest fractional shares (ties
   broken by task number), so weighted children always sum exactly to the
   parent.
2. **Roll up bottom-up.** A summary task without its own budget takes the sum
   of its resolvable children (partially resolvable summaries sum what is
   known). Leaf tasks with no determinable budget are reported in
   `Budget.unallocated` rather than guessed.

`Budget.total` sums only root tasks, so summaries are not double counted.

Legality of an authored budget (explicit vs. weighted, sibling consistency,
weight totals) is enforced by `Project.validate()`, not by the `Budgeter`.

### `ReportBuilder` — status reporting

`ReportBuilder(project, as_of, look_ahead).build() -> ProjectReport` composes
the analyzer and tracker into a status report:

* Project status: `Not Started` (no leaf has begun), `Started` (work has begun
  but nothing is finished or progressing), `In Progress`, `Completed` (every
  leaf is complete).
* Per-task `ScheduleCondition`: `Blocked` (planned start passed, a predecessor
  is incomplete), `Late` (planned start passed, predecessors complete, not
  started), `Overdue` (started but planned finish passed), otherwise
  `On Schedule`. Unstarted conditions are evaluated before overdue so
  un-actioned work surfaces first, and completion is judged at the data date.
* For blocked tasks, `blocked_by` lists incomplete predecessors and
  `root_causes` walks the dependency chain to the terminal blockers that must
  actually be actioned. (Both are computed but not yet rendered: see
  `ROADMAP.md` P1-3.)
* `ProjectBudgetReport` and `TaskBudgetReport` carry only the planned and actual
  amounts; `remaining` (`budget − actual`) and `cost_variance`
  (`actual − budget`) are derived from them, so the two can never disagree.
* Forecast figures (`Forecast Finish`, `Schedule Variance`, and each task's
  forecast start, finish, and duration) come from `Forecaster` at the same
  data date: finished work is pinned to its actual finish, each unfinished
  task's remaining duration is floored at the data date, the forecast network
  runs through the normal CPM pass, and the project's schedule variance
  measures the forecast finish against the project's target finish (`n/a`
  when the project sets no target).
* A value that cannot be derived at the data date is reported as `n/a`, never as
  a zero: a zero row means a real zero. A `Data Notices` section lists tracking
  entries dated after the report date, so a truncated figure is explained rather
  than silently dropped.
* Milestones report no duration (no duration variance, no inclusive one-day
  span), and per-task `budget_consumed` is `n/a` for a task with no budget.

Example (`python -m planscript status Simple.plan -ao 2026-10-05`):

```text
Status Report as-of 2026-10-05
=======================================
Project Name: Variance Test Project
    Status: In Progress

--------------------------------------
Project Schedule Report
--------------------------------------
    Planned Start: 2026-08-01
    Planned Finish: 2026-11-30
    Planned Duration: 68d
    Actual Start: 2026-08-01
    Forecast Finish: 2026-10-30
    Schedule Variance: -31d

--------------------------------------
Project Budget Report
--------------------------------------
    Planned Budget: $304,650.50
    Actual Cost: $55,862.24
    Remaining Budget: $248,788.26
    Cost Variance (actual - budget): ($248,788.26)

--------------------------------------
Project Progress Report
--------------------------------------
    Planned Progress: 100.0%
    Actual Progress: 74.1%
    Budget Consumed: 18.3%

1.1 - Kickoff
--------------------------------------
Schedule Report    Status: On Schedule
--------------------------------------
    Planned Milestone Date: 2026-08-01
    Actual Milestone Date: 2026-08-01
    Schedule Variance: 0d

--------------------------------------
Budget Report
--------------------------------------
    Planned Budget: $3,400.00
    Actual Cost: $2,500.00
    Remaining Budget: $900.00

--------------------------------------
Progress Report
--------------------------------------
    Planned Progress: 100.0%
    Actual Progress: 100.0%
    Budget Consumed: 73.5%
```

Forecast fields are derived by `Forecaster` at the report's data date: each
unfinished task's remaining duration is scheduled through the normal CPM pass
with a floor at the data date, while finished work is pinned to its actual
finish, so `Forecast Finish` is the forecast network's latest date (never
earlier than the data date while work remains) and `Schedule Variance`
measures it against the project's target finish. A project with no target
finish reports `n/a` variance rather than inventing a comparison date.

`python -m planscript status Simple.plan -ao 2026-09-26` (the real data date at
the time of writing) additionally prints a `Data Notices` section, because
`Simple.plan` records a `3.4 start` entry dated 2026-09-27 - after the report
date. That entry is excluded from every figure and announced instead.

## CLI

Entry point: `python -m planscript <command> <file.plan>` (`planscript/app.py`).

| Command | Options | Behavior |
| --- | --- | --- |
| `check` | — | Parses and validates; prints the project name and `Valid`. |
| `summary` | — | Project header (name, duration when scheduled, target dates) plus task, dependency, and tracking counts. Does not schedule. |
| `schedule` | `-d/--dates`, `-c/--calculated`, `-g/--gantt` | Calculates the schedule. With no flags all three views plus critical paths are shown. Without a project `start_date`, the dates view and Gantt chart print a note instead of calendar output. |
| `status` | `-ao/--as-of YYYY-MM-DD` (default today), `-la/--look-ahead DAYS` (default 21) | Builds and renders a status report. Requires a project `start_date`; without one it fails with `SchedulingError` (exit 1). |
| `budget` | `-ao/--as-of YYYY-MM-DD` (default today) | Resolves the budget and prints the budget table. |

Exit codes: `0` success, `1` expected failure (missing file, decode error,
`ParseError`, `ValidationError`, `SchedulingError`, `BudgetingError`), `2`
argparse usage errors. Expected failures print a one-line message to stderr;
unexpected exceptions are deliberately not caught and surface as tracebacks.

Views:

* `display.view_project_summary` / `view_project_header`.
* `display.view_schedule_calculated` — ID, task, duration, ES, EF, LS, LF,
  float.
* `display.view_schedule_scheduled` — start/finish dates and float; prints a note when the schedule is calculated-only (no `start_date`).
* `display.view_budget` — resolved amount and basis (`explicit`, weight,
  `rollup`, `unallocated`).
* `display.view_critical_paths`.
* `cli/gantt.render_gantt` — textual bar chart scaled by project duration; prints a note when the project has no `start_date`.
* `display` also still contains the earlier interactive menu functions. They are
  only referenced by `_archive/app.py` and are not part of the current CLI.

Known CLI defects (tracked in `ROADMAP.md`):

* `schedule` prints an arrow character (`→`) that raises `UnicodeEncodeError`
  when stdout is redirected or piped on a Windows ANSI code page.

## Serializer

`PlanSerializer.serialize(project)` writes a `.plan` document. It is a skeleton:
project metadata, calendars, budgets, invoice/tracking events, and metadata are
not yet emitted, lag formatting is approximate, and it writes
`dependency <predecessor> > <successor> …` lines rather than the `depends`
syntax the parser accepts. It is not referenced by the CLI, so the CLI is
currently read-only.

## Tracking design

Tracking history lives in the same authoritative `.plan` file as the plan
(see Purpose). Event syntax, directives, and lifecycle rules are enforced by
the parser and `TaskState._derive` and are documented in `SYNTAX.md`; this
section records the design decisions behind them.

* Tracking is optional. A project with no events is **untracked**; one with
  at least one valid event is **tracked**. A tracked project does not need
  every task covered: a task with no history derives as **Not Started** at
  0%, and there is no project-level "tracking enabled" flag.
* State is derived, never stored. `TaskState` replays a task's events in
  date order; events carry dates, not timestamps (day-level precision), and
  no historical snapshots are kept. The same history always derives the same
  state — "today" only enters when a report or analysis is given an `as_of`
  date.
* Plan, actual, and forecast stay distinct. The plan is what was intended;
  actuals derive only from tracking, so a planned date passing never creates
  an actual start or finish; forecasts combine plan and actuals and are
  derived information that is never written back.
* Explicit versus calculated progress stays a real distinction: `progress`
  means the user reported it, and `complete` implies 100%. Any future
  calculated-progress mechanism must never be presented as though the user
  reported it (`ROADMAP.md` P3-10).
* Designed but not yet enforced — same-day lifecycle precedence, rejecting
  future-dated events, duplicate same-day detection, and tracking on summary
  tasks — are listed under Current Gaps and tracked as `ROADMAP.md` P1-2.

## Validation

Validation is layered so that each failure is reported by the layer that owns
the rule:

1. **Parser** (`ParseError`) — line-level syntax and structure: missing or
   duplicate `project:`, content before the project, unindented attributes,
   duplicate attributes, invalid dates, invalid durations, unknown task
   references in `depends`/tracking/allocation lines, self-dependencies,
   duplicate dependencies, malformed directive arguments, and unrecognized
   lines.
2. **Model** (`ValidationError`, via `Project.validate()`) — project start
   after finish, summary tasks with durations, leaf tasks without durations,
   dependencies touching summary tasks, cycles, negative durations, constraints
   on summary tasks or unknown tasks, budget
   legality (explicit vs. weighted, sibling consistency, weight totals,
   percentage bounds, budgeted ancestor required), and tracking references and
   invoice allocation totals.
3. **State derivation** (`ValidationError` / `ParseError`) — event lifecycle
   rules when a `TaskState` is derived (start once, no progress before start,
   no progress after complete, complete once, 0–100%).
4. **Engines** (`SchedulingError`, `BudgetingError`) — nothing to schedule or
   budget, weighted budgets with no allocatable ancestor, and mandatory
   constraints the network cannot accommodate.

## Testing

The suite uses Python's built-in `unittest`; there is no third-party test
dependency. Currently **274 tests**; all pass.

```powershell
python -m unittest discover -s planscript/tests -t .
```

| Test module | Focus |
| --- | --- |
| `test_parser.py` | Project/task/metadata/budget/dependency syntax, error messages, line references. |
| `test_model.py` | `TaskHierarchy` behavior, budget validation, and constraint validation rules. |
| `test_scheduler.py` | CPM examples across dependency types, branching, merging, float, critical paths, and soft and mandatory constraints. |
| `test_tracking.py` | Event parsing, lifecycle/derivation rules, actual dates and costs. |
| `test_budgeter.py` | Explicit, weighted, nested, rollup, remainder-cent, and unallocated cases. |
| `test_performance.py` | Variance calculations against tracked plans. |
| `test_reporter.py` | Status report figures, budget/progress invariants, data notices, and forecast fields. |
| `test_forecaster.py` | Forecast durations and pins per tracking status, data-date edge cases, failure modes. |
| `test_cli.py` | Subcommand behavior and exit codes through subprocesses. |
| `test_projects.py` | Shared in-memory project fixtures for the scheduler tests. |

Test conventions: fixtures live in `test_projects.py`; CLI tests call
`app.main` in-process with one subprocess smoke run; tests assert on messages
rather than tracebacks.

## Current Gaps

The design intent and the implementation are not yet aligned in these areas.
`ROADMAP.md` tracks them with priorities:

* Calendars exist as a model but are unused, so schedules and actual durations
  ignore working days, holidays, and working hours.
* `_archive/` holds superseded code, and `display.py` retains unused menu
  functions.
* The serializer is incomplete and not wired to the CLI, so plans can be read
  but not written back.
* The status report lists every task but not the summary sections (overdue,
  blocked, late, upcoming deadlines/starts) that `ROADMAP.md` P1-3 still asks
  for.
* Tracking design decisions that are not yet implemented: same-day lifecycle
  precedence, rejection of future-dated events, duplicate same-day detection,
  and a decision on tracking summary tasks.

