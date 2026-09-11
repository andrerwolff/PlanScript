# PlanScript Tracking — Design

## 1. Purpose and Architecture

The `.plan` file is the single authoritative project definition.

It contains both:

* **Plan** — what is intended to happen
* **Tracking history** — what has actually happened

There is no second authoritative tracking database, file, hidden ID, or immutable audit log.

Tracking is user-readable and user-editable. Users may edit the `.plan` file directly. Broken task references and contradictory tracking information are validation errors; PlanScript must not silently repair or reinterpret them.

Derived information is calculated from the authoritative plan and tracking history.

```text
                    AUTHORITATIVE
                      .plan FILE
                          │
             ┌────────────┴────────────┐
             │                         │
            PLAN                 TRACKING HISTORY
             │                         │
             │                         ▼
             │                    ACTUAL STATE
             │                         │
             └────────────┬────────────┘
                          ▼
                       VARIANCE
                          │
                          ▼
                       FORECAST
                          │
                          ▼
                        REPORT
```

The central principle is:

> **Derived information must not become a second source of truth.**

---

## 2. Tracking Model

Tracking consists of dated, task-level events.

An event records something that actually happened to a task. A task's state at any point in time is derived from its tracking history.

Current state and historical/as-of state are not stored separately.

Initial tracking is task-level only. Project-level tracking events may be added later.

### Project tracking status

Tracking is optional.

A project is:

* **Untracked** if it contains no tracking events.
* **Tracked** if it contains at least one valid tracking event.

A tracked project does not require every task to have tracking events.

A task with no tracking history is derived as **Not Started** with 0% progress.

There is no explicit project-level "tracking enabled" setting.

---

## 3. Tracking Section

Tracking is stored in a distinct `Tracking` section at the end of the `.plan` file.

Example:

```text
Project "Example"

1. Design
    3d

2. Build
    5d

Tracking

2026-09-10  1.1  start
2026-09-12  1.1  progress 50%
2026-09-15  1.1  complete
```

Current syntax rules:

* Tracking is optional.
* `Tracking` must be the final section.
* Nothing may follow the Tracking section.
* Tracking events are not currently intermixed with the project definition.
* Future syntax may relax this if there is a compelling reason.

---

## 4. Tracking Event Syntax

Basic syntax:

```text
<date> <task-number> <directive> [arguments]
```

Example:

```text
2026-09-10  1.1  start
2026-09-12  1.1  progress 50%
2026-09-15  1.1  complete
```

There are no independent event IDs.

The date is first because tracking represents historical events and chronological ordering is fundamental to interpretation.

### Grouped dates

A date may be specified once for multiple events:

```text
2026-09-10
    1.1  start
    1.2  start
    1.3  progress 50%
```

Each indented entry remains an independent event internally. Indentation is syntactic grouping only.

A date-only line with no events is invalid.

---

## 5. Time and Event Ordering

Tracking operates at day-level precision.

Events have dates, not timestamps.

File order does not determine chronological order. Events are processed according to their dates.

When multiple events for the same task occur on the same date, directive lifecycle precedence determines their order:

```text
start → progress → complete
```

For example:

```text
2026-09-10
    1.1  progress 50%
    1.1  start
```

is processed as:

```text
start
progress 50%
```

Future directives may be assigned an appropriate position in the lifecycle.

---

## 6. Tracking Represents History

Tracking records what has actually happened.

A tracking event may not have a future date.

Therefore:

* An event dated today or earlier may be valid.
* A future-dated tracking event is a validation error.
* Intended future activity belongs in the planning section.
* Forecasts may contain future dates, but forecasts are derived information rather than tracking events.

"Today" is not part of the stored tracking state. It is only an input when generating current reports such as variance, forecast, or staleness.

The same tracking history therefore produces the same historical state regardless of when the project is opened.

---

## 7. Task Lifecycle

The initial lifecycle is:

```text
Not Started
     │
     │ start
     ▼
Started / In Progress
     │
     ├── progress
     │
     │ complete
     ▼
Complete
```

### `start`

Records that work actually began.

Rules:

* Establishes the actual start date.
* Sets derived progress to 0%.
* May occur only once per task.
* A task must be started before `progress` or `complete`.

Once established, the actual start date does not change.

Progress may subsequently increase or decrease without affecting the actual start date.

### `progress`

Records explicitly reported completion.

Example:

```text
progress 60%
```

means:

> The task was reported as 60% complete as of this date.

Progress is absolute, not incremental.

Progress may increase or decrease:

```text
start
progress 60%
progress 40%
```

The derived progress is therefore piecewise constant:

```text
start       → 0%
progress 60 → 60%
progress 40 → 40%
```

A progress event requires a prior `start`.

`progress 100%` is valid and **does not complete the task**. It represents a task that has been reported as 100% complete but has not yet been formally closed.

This distinction is intentional:

* **100% progress** = reported completion level
* **Complete** = terminal task state

### `complete`

Records that the task has actually finished.

Rules:

* Requires a prior `start`.
* Establishes the actual finish date.
* Sets derived progress to 100%.
* Moves the task to the terminal `Complete` state.
* No tracking events may occur after completion.

`complete` is therefore sufficient to establish 100% progress; a separate `progress 100%` event is not required.

Completion currently cannot be reversed. A future `reopen` or similar directive may introduce a richer lifecycle.

---

## 8. Same-Day Events and Duplicates

Different lifecycle events may occur on the same date when their lifecycle ordering produces a valid history.

Valid:

```text
2026-09-10
    1.1  start
    1.1  progress 50%
```

Valid:

```text
2026-09-10
    1.1  start
    1.1  complete
```

Invalid:

```text
2026-09-10
    1.1  progress 40%
    1.1  progress 60%
```

A task may not have more than one event of the same directive type on the same date.

PlanScript must not infer user intent by choosing the greatest percentage, latest textual entry, or any other heuristic.

Ambiguous or contradictory tracking information produces a validation error.

---

## 9. Tracking Validation

Initial validation includes:

* Referenced task must exist.
* Tracking event date may not be in the future.
* `start` may occur only once per task.
* `progress` requires a prior `start`.
* `complete` requires a prior `start`.
* No event may occur after `complete`.
* Progress may increase or decrease.
* Same-day `start → progress` is valid.
* Same-day `start → complete` is valid.
* Same-day events are interpreted according to lifecycle precedence.
* File ordering does not determine chronological ordering.
* Duplicate events of the same directive type for the same task/date are invalid.
* Invalid or ambiguous tracking information is a validation error.
* PlanScript does not silently repair or reinterpret tracking history.

---

## 10. State as of a Date

A task's state at an arbitrary date is derived by processing all tracking events dated on or before that date.

For example:

```text
2026-09-10  1.1  start
2026-09-12  1.1  progress 60%
2026-09-15  1.1  progress 40%
2026-09-18  1.1  complete
```

Produces:

| As of | State       | Progress |
| ----- | ----------- | -------: |
| 9/9   | Not Started |       0% |
| 9/10  | Started     |       0% |
| 9/12  | Started     |      60% |
| 9/15  | Started     |      40% |
| 9/18  | Complete    |     100% |

Current state is simply the state evaluated through the current date.

No separate historical snapshots are required.

---

## 11. Plan, Actual, and Forecast

These are three distinct concepts.

### Plan

Defined by the project definition:

* Planned start
* Planned duration
* Planned finish
* Dependencies
* Calendars
* Other scheduling information

Tracking does not modify the plan.

### Actual

Derived exclusively from tracking history:

* Actual start
* Actual progress
* Actual finish
* Actual state
* Actual duration

A task does not acquire an actual start or finish merely because its planned dates have passed.

### Forecast

Calculated from the plan and actual history.

Examples:

```text
Plan:
    Start:    Jan 5
    Duration: 5d

Actual:
    Start:    Jan 8

Variance:
    +3d

Forecast:
    Expected finish: Jan 12
```

Forecasts are derived information, not tracking events and not another source of truth.

---

## 12. Actual Dates and Duration

### Actual start

`start` permanently establishes the actual start date.

Actual start is derived exclusively from tracking.

Progress changes do not affect actual start.

### Actual finish

`complete` permanently establishes the actual finish date.

Actual finish is derived exclusively from tracking.

A task without a `complete` event has no actual finish, regardless of its planned finish date or reported progress.

### Actual duration

Actual duration is calculated from actual start and actual finish using the task's applicable planning calendar.

The calculation includes both the actual start and actual finish dates.

For a Monday–Friday calendar:

```text
Start:    Monday 9/14
Complete: Friday 9/18
```

produces:

```text
Actual duration: 5 working days
```

The exact duration convention may eventually become a user-configurable project/calendar setting.

---

## 13. Explicit vs. Derived Progress

Explicit and calculated progress must remain conceptually distinct.

An explicit progress event means:

> "The user reported this task as X% complete."

A future calculated-progress mechanism may instead mean:

> "The system estimates this task as X% complete."

PlanScript must not represent calculated progress as though the user explicitly reported it.

Currently, progress is only explicitly reported through tracking events, with `complete` deriving 100% progress.

---

## 14. Reporting and Variance

Tracking exists not merely for historical recordkeeping but to make discrepancies between the plan and reality useful and visible.

The system should eventually support reports such as:

* Not Started
* Started
* Progress behind plan
* 100% reported but not completed
* Completed early
* Completed late
* Stale tracking
* Forecast finish
* Forecast dependency conflicts

The core questions are:

1. What did we plan?
2. What has actually happened?
3. Given what has happened, what do we now expect?

---

## 15. Deferred / Future Decisions

The following are intentionally unresolved:

* Project-level tracking events.
* Actual project start/finish directives.
* Baselines and historical plan versions.
* Reopening/restarting completed tasks.
* Incremental progress syntax (`+10%`, `-20%`).
* Derived/calculated progress mechanisms.
* Tracking cadence and staleness configuration.
* Pause/resume or richer lifecycle states.
* Tracking on summary tasks and interaction with task hierarchy.
* Forecast calculation rules.
* Variance calculation details, particularly with revised plans.
* Exact duration configuration and calendar settings.
* Whether tracking events should eventually be permitted alongside the project definition.
* Exact syntax refinements beyond the rules established above.

These should be addressed only when implementation or a concrete use case requires them.

---

## 16. Initial Implementation Scope

The first implementation should remain deliberately small.

Implement:

1. Tracking section parsing.
2. `TrackingEvent` model.
3. `start`, `progress`, and `complete`.
4. Tracking validation.
5. Chronological/lifecycle event processing.
6. Current task state.
7. Task state as of an arbitrary date.
8. Actual start.
9. Actual finish.
10. Actual duration using the planning calendar.

Do not implement forecasting, baselines, plan revision history, or richer lifecycle behavior yet.

The tracking events remain the authoritative historical data; task state, actual duration, variance, forecasts, and reports remain derived.
