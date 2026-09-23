# PlanScript — Syntax

This document describes the syntax the **current parser actually implements**
(`planscript/parser/parser.py`). Anything not described here is not accepted
today. See [Not yet supported](#not-yet-supported) and
[Known sharp edges](#known-sharp-edges) before reaching for a feature.

## General

* PlanScript files use the `.plan` suffix and are UTF-8 plaintext.
* One project per file.
* The plan file is the single source of truth. It holds the project definition
  and, optionally, the tracking history after it.
* A nested line is indented with **either a tab or exactly four spaces**.
* Blank lines are ignored. Whole-line comments start with `;`.
* Unrecognized input fails with a `ParseError` that names the line.

### File layout

```text
project declaration        required, exactly once, first content line
    project attributes     calendar / start / finish / metadata
task definitions           each followed by its own indented lines
    depends / budget / - metadata
tracking events            optional, dated, after the project definition
invoices                   optional, dated, after the project definition
```

Attributes apply to the **immediately preceding entry**, so an indented line
always attaches to the line above it.

### Minimal example

```text
project: Example

task 1 Design 5d
task 2 Build 10d
    depends 1
```

## Project Definition

General concept:

```text
project: <project name>
```

Example:

```text
project: DOTI LS6
    - Client: DOTI
    - Project Number: TBA
    - Description: Decommission LS6 and Install 18" Sewer
```

* The project name is the remainder of the line and is not quoted.
* Exactly one project declaration is allowed, and it must appear before any
  other content. A second declaration, or content before it, is a parse error.

### Project Attributes

The following indented lines are recognized on the project itself:

| Line | Meaning |
| --- | --- |
| `    start: YYYY-MM-DD` | Planned/target project start date. Soft; does not constrain CPM. |
| `    finish: YYYY-MM-DD` | Planned/target project finish date. Soft; does not constrain CPM. |
| `    calendar: <name>` | Calendar selection. Stored on the project, not yet applied by the scheduler. |
| `    - <Key>: <Value>` | Project metadata. |

Rules:

* `calendar`, `start`, and `finish` may each appear only once, and only in the
  indented project-attribute position. A duplicate is a parse error.
* `start` and `finish` must be exact `YYYY-MM-DD` dates.
* `start` must not be later than `finish` (validation error).
* Any calendar name is accepted today; the name is stored but not interpreted.

### Project Metadata

`<tab>- <key>: <value>` or `    - <key>: <value>`

* User defined and generated; not required for CPM scheduling.
* Referenced programmatically as `project.metadata["Client"]`.
* A tab or four spaces is required before `-`, a space is required after `-`,
  and a space is required after `:`.
* Keys are free-form and are not predefined by the scheduler.
* Repeating a key silently overwrites the earlier value (last one wins).

## Task Definition

General concept:

```text
task <ID> <description> [duration]
```

Examples:

```text
task 1 Project Management
task 1.1 Kickoff 0d
task 1.2 Project Plan 5d
    - Description: Prepare report with intent to submit to CDPHE
task 4.2.1 30% 98d
```

### Task IDs

Task IDs are **hierarchical alphanumeric identifiers**, separated by periods.
Each segment is one or more letters or digits.

Examples:

```text
1
1.1
1.2
1.2.1
1.1.a
1.1.a.2
A.1
```

Invalid examples:

```text
1..2
.1
1.
1-2
DESIGN-01
```

A duplicate task ID is a parse error.

### Task Names

Task names are user-defined strings and are otherwise unconstrained. A name may
contain spaces, digits, and symbols such as `%`. The name ends before the final
duration token when one is present.

### Task Duration

The optional last entry on the task line defines the length of the task.

Supported units on the task line: `h = hours`, `d = days`, `w = weeks`.

Examples:

✔ `8h`, `5d`, `2w`, `2.5d`, `1.5w`

✘ `5 d`, `d4`, `3days`, `-2d`, `+2d`

Rules:

* The unit is required when a duration is present.
* A duration must be separated from the name by whitespace.
* Signed or negative durations are rejected with an explicit error.
* A trailing token that is not a valid duration is folded into the name rather
  than rejected; see [Known sharp edges](#known-sharp-edges).

Default behavior:

* No duration ⇒ **summary task**. Its schedule is derived from its descendants.
* `0d` ⇒ **milestone**.
* A summary task may not have a duration, and a task without children (a leaf)
  must have a duration. Both are validation errors.

### Task Metadata

`<tab>- <key>: <value>` or `    - <key>: <value>`

Same rules as project metadata, but attached to the preceding task. Referenced
programmatically as `task.metadata["Owner"]`.

## Dependencies

General concept:

```text
<tab>depends <predecessor_id> [relationship_type] [lag]
```

A `depends` line attaches to the task above it. The task above is the
**successor**; the referenced task is the **predecessor**.

```text
task 1.1 Kickoff 0d
task 1.2 Project Plan 5d
    depends 1.1
task 1.3 Review 2d
    depends 1.2 SS +3d
```

### Predecessor

Task IDs are used for references, so the example above reads "task 1.3 depends
on 1.2". The referenced task must exist in the project.

### Dependency Type

Supported relationship types:

* `FS` — Finish-to-Start
* `SS` — Start-to-Start
* `FF` — Finish-to-Finish
* `SF` — Start-to-Finish

Default behavior:

* If the type is omitted, the default is `FS`.
* The type must be separated from the predecessor ID by whitespace. `depends
  1.1FS` is rejected with an explicit error rather than parsed.

### Lag

Lag follows the dependency type.

Supported units: `h = hours`, `d = days`, `w = weeks`.

Examples:

✔ `FS`, `FS 0d`, `FS +2w`, `SS -1d`, `+2w`, `3d`

✘ `FS+2w`, `FS 2 w`, `FS +2`

Default behavior:

* An omitted lag is `0`.
* An omitted sign defaults to `+`.

### Dependency Validation

* The predecessor and successor must both exist.
* A task may not depend on itself.
* Summary tasks may not be a predecessor or a successor. Dependencies attach to
  leaf tasks only.
* An identical dependency (same pair, type, and lag) may not be repeated.
* Circular dependencies are rejected during validation.

## Budgets

Budget lines are indented under the task.

```text
task 1.1 Kickoff 0d
    budget $3400
task 2 Design
    budget $250000
task 2.1 Preliminary Design
    budget 10%
task 2.1.1 Site Layout 5d
    budget 40%
```

### Explicit budget

```text
<tab>budget $<amount>
```

* The amount is in dollars, as a plain number such as `$250000` or `$6250.25`.
  Zero, one, or two decimal places are accepted and mean the same amount:
  `$10` is `$10.00` and `$10.5` is `$10.50`. Three or more decimal places is a
  parse error.
* An explicit budget may not be negative.

### Weighted budget

```text
<tab>budget <percent>%
```

* The percentage is a share of the nearest explicitly budgeted ancestor.
* Weights are `0`–`100`.
* A weighted task must have an explicitly budgeted ancestor.

### Budget rules enforced by validation

* A task's budget is explicit **or** weighted, never both.
* Siblings must not mix explicit and weighted allocations.
* If siblings are explicit, their amounts must sum exactly to the parent's
  explicit budget.
* If siblings are weighted, every sibling must carry a weight and the weights
  must sum to exactly `100%`.
* A task derived by weight may not have explicitly budgeted children.

Unallocated budgets are reported rather than guessed: a summary task with no
budget of its own rolls up only the children that resolve.

## Invoices

Invoices record money already billed. An invoice line is **not indented**; its
allocations are.

```text
2026-09-30 invoice $45362.24
    1.1 $2500
    2.1.2 $2500.24
    3.1 $40000
    3.2 $362
```

* The invoice date is `YYYY-MM-DD`.
* Invoice and allocation amounts follow the same rule as budget amounts: zero,
  one, or two decimal places (`$2500` means `$2500.00`).
* Each allocation references an existing task.
* Allocations must sum exactly to the invoice amount or validation fails.
* A task may be allocated at most once per invoice.
* An allocation line before any invoice is a parse error.

## Tracking

Tracking records what actually happened. Events are dated, task-level records
placed after the project definition.

```text
;Tracking
2026-08-01
    1.1 start
    1.1 complete

2026-08-03 1.2 start
2026-08-09 1.2 progress 60%
2026-08-12 1.2 complete
2026-08-15 2.1.2 start
2026-08-24 2.1.2 progress +20%
```

### Event syntax

```text
<date> <task_id> <directive> [argument]
```

* The date comes first because tracking is historical and chronological.
* A date-only line begins a group: the following indented lines inherit that
  date.
* A `;Tracking` comment before the events is a convention only. There is no
  `Tracking` section keyword; events are recognized after the project
  definition wherever they appear.

### Directives

| Directive | Argument | Meaning |
| --- | --- | --- |
| `start` | none | Work actually began. Sets the actual start date and 0% progress. |
| `progress <n>%` | percentage | Absolute reported completion. |
| `progress +<n>%` | signed percentage | Incremental change (`-<n>%` reduces). |
| `complete` | none | The task finished. Sets the actual finish date and 100% progress. |
| `note <text>` | free text | A remark; no effect on derived state. |

Anything else, including `progress 50` without `%`, is a parse error.

### Lifecycle rules (validated per task, in date order)

* `start` may occur only once.
* `progress` requires a prior `start`.
* `progress` may not follow `complete`.
* `complete` may occur only once and only after `start`.
* Resulting progress must stay within `0%`–`100%`.
* `progress 100%` does **not** complete a task; only `complete` does.
* The referenced task must exist.
* Tracking is currently accepted on any task, including summary tasks.

## Comments

Comments use `;` and occupy a whole line:

```text
; Preliminary design estimate
task 1.2 Preliminary Design 30d
```

Inline comments such as:

```text
task 1.2 Design 30d ; preliminary estimate
```

are intentionally not part of the syntax.

## Parser Principles

* Human-readable plaintext is the source of truth.
* Syntax should favor readability over unnecessary punctuation.
* Invalid input should fail explicitly.
* Parser errors should identify the line whenever possible.

## Not yet supported

These exist in design notes but are **not implemented** in the parser,
scheduler, or CLI today:

* Inline comments.
* `dependency <predecessor> > <successor> <type><lag>` as a standalone entry
  line. Dependencies are written as indented `depends` lines instead.
* Constraints of any kind, and task-level dates.
* Task-level calendars, working hours, holidays, and calendar-aware
  scheduling. A `calendar:` name is parsed and stored but never applied.
* Month (`m`) durations. `parse_duration` understands `m` as 30 days, but no
  syntax pattern reaches it, so `5m` on a task line is not a duration.
* Baselines, revised plans, and plan version history.
* Multiple projects per file.
* Quoted or escaped strings.
* A literal `Tracking` section keyword.

## Known sharp edges

These behave in ways that are surprising for hand-written plans. They are
tracked in `ROADMAP.md`.

1. **A token that is not a valid duration becomes part of the name.**
   `task 1.2 Design 5m` parses as a task named `Design 5m` with no duration, and
   then fails validation because a task without children must have a duration.
   The same happens for typos such as `task 1.2 Design 5 d`.
2. **Inline comments are absorbed into names.** `task 1.2 Design 5d ; rush`
   produces a name of `Design 5d ; rush` and an undated task rather than a
   clear comment error.
3. **A malformed budget is reported as a tracking error.** An indented
   `<word> $<amount>` line that is not a valid budget, such as
   `budget $10.555` (three decimal places), falls through to the tracking-entry
   branch and fails with `Tracking entry has no date.` instead of a
   budget-specific error.
4. **Same-day event order is file order.** `progress` written before `start` on
   the same date is rejected rather than reordered by lifecycle precedence.
5. **Future-dated tracking events are accepted.** A tracking date later than
   today is not currently rejected.
6. **A date-only tracking line with no entries is accepted and ignored.**

