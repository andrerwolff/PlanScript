# PlanScript — Roadmap

This roadmap is the working plan for the project. It is organised by priority
rather than by date, and every item is written so it can be turned into a task
or a test without further design discussion.

**How to use it**

* `P0` items are defects or gaps that block reliable use of the current feature
  set. Do these first.
* `P1` items complete or harden something that is already designed.
* `P2` items add a designed-but-unbuilt capability.
* `P3` items are larger or deliberately later; they should not start before the
  items they depend on.
* When an item is done, move its acceptance criteria into
  `planscript/tests/` and update `SYNTAX.md` / `DESIGN.md` in the same change.
* Anything in [Explicitly deferred decisions](#explicitly-deferred-decisions)
  is not settled and must not be assumed by new code.

Work items are tagged with the modules they touch.

---

## Status: what already works

**Parser and model**

* Line-oriented `.plan` parser with line-numbered errors: project declaration,
  project attributes (`calendar`, `start`, `finish`), metadata, tasks, task
  metadata, dependencies, budgets, invoices, and tracking events.
* Hierarchical alphanumeric task IDs, summary tasks (no duration), milestones
  (`0d`), decimal durations, `h`/`d`/`w` units.
* `FS`/`SS`/`FF`/`SF` dependencies with signed lag and the default `FS`/`+0`
  behaviour.
* `Project.validate()` enforcing dates, summary rules, dependency endpoints and
  cycles, budget legality, duration sign, tracking references, and invoice
  allocation totals.

**Scheduling**

* Full CPM: topological order, forward pass, backward pass, total float,
  critical tasks, multiple critical paths, and calendar-day projections
  when a project start date is set (calculated-only otherwise).
* Summary date rollup from descendants.

**Tracking, cost, and status**

* Event model (`start`, `progress` absolute and incremental, `complete`,
  `note`), lifecycle validation, and derived `TaskState` (status + percent
  complete).
* Derived actual start/finish/duration (inclusive) and actual cost rolled
  through summaries.
* Invoices with per-task allocations that must reconcile to the invoice total.
* `Analyzer` variance (start/finish/duration), per-task and total cost
  variance (actual vs. resolved budget), project actual start, and
  duration-weighted project progress.
* `ReportBuilder` status report: project status, overdues, blocked tasks with
  blockers and root causes, late tasks, and look-ahead windows.

**Budgets**

* Explicit (`$`) and weighted (`%`) allocations, nested weighting, bottom-up
  rollup, whole-cent allocation with largest-remainder rounding, and
  unallocated reporting.

**CLI**

* `check`, `summary`, `schedule` (`-c`, `-d`, `-g`), `status`
  (`-ao`, `-la`), and `budget` (`-ao`) with documented exit codes.
* Calculated schedule table, date table, budget table, critical paths, and a
  textual Gantt chart.

**Quality baseline**

* 180 `unittest` tests covering parser errors, CPM examples,
  dependency types, tracking, budgets, variance, reports, and CLI behavior.

---

## P0 — Correctness and CLI defects

These are confirmed defects in the current build. Each one is small.

## P1 — Harden existing behaviour

### P1-1 Make task-line typos fail clearly

A trailing token that is not a valid duration is currently folded into the task
name (`task 1.2 Design 5m` becomes the name `Design 5m`), and inline comments
(`task 1.2 Design 5d ; rush`) are absorbed the same way. The user then gets a
"task must have a duration" validation error that does not point at the real
problem.

* Detect a trailing token that looks like a duration attempt but is invalid
  (no unit, unknown unit, embedded space, signed value) and raise a
  `ParseError` naming the line and token.
* Give inline comments their own explicit error, or decide to support them.
* Reconcile the `m` (month) unit: either accept `5m` on task lines with a
  documented 30-day definition, or reject it explicitly.
* Acceptance: parser tests for each rejected shape, plus `SYNTAX.md` updated to
  remove the corresponding "sharp edge".

### P1-2 Bring tracking behaviour in line with the tracking design (`DESIGN.md`)

The tracking design is written; five rules are not yet enforced:

1. **Same-day lifecycle precedence** — within one date, events should be
   applied as `start → progress → complete` regardless of file order. Today
   same-date order is file order, so `progress` written above `start` is
   rejected.
2. **Future-dated events** — a tracking date after "today" should be a
   validation error. `Full_Plan.plan` currently contains an event dated
   `2026-10-11` that parses cleanly whenever the current date is earlier. Decide
   whether the comparison uses the real current date or an explicit data date,
   then document it.
3. **Duplicate same-day events** — two `progress` events for one task on one
   date must be rejected rather than resolved by file order.
4. **Tracking on summary tasks** — currently accepted silently. Decide: reject,
   derive from leaves, or allow with rollup, then enforce and document.
5. **Date-only line with no entries** — should be invalid.
* Provide an `as_of`/data-date parameter so historical state can be derived
  deterministically and tested without depending on the wall clock.
* Acceptance: tests per rule; `DESIGN.md`, `SYNTAX.md`, and the
  deferred list below updated to match the decision.

### P1-3 Reporting completeness

* Populate `ProjectBudgetReport` in `ReportBuilder` (budget, invoiced, paid,
  remaining, variance, invoice list) and render the budget section in
  `ProjectReport.render_text`.
* Expose the variance values already computed by `Analyzer` (start/finish/
  duration) in the status report so slips are visible, not just recomputed.
* Turn `test_reporter.py` from a print-and-hope test into assertions on project
  status, overdue/blocked/late lists, look-ahead windows, and root causes.
* Acceptance: `python -m planscript status <file>` shows budget vs. invoiced and
  variance; reporter tests assert values.

## P2 — Calendars (working time)

Calendars are modelled (`planscript/model/calendar.py`) but nothing uses them,
so schedules and actual durations are plain calendar days, and `5d` spans a
weekend.

Design questions to settle first:

* Is the CPM offset unit a *calendar day* or a *working day*?
* How is `calendar: <name>` resolved to a `Calendar` object, and how are custom
  work weeks and holidays expressed in a `.plan` file?
* Is there a project default calendar plus optional per-task calendars?

Suggested sequence:

1. **P2-1** Resolve the `calendar:` name to a `Calendar` at parse time and
   validate the name. Registry of built-ins (`standard`, `7day`) plus declared
   custom calendars.
2. **P2-2** Define and parse custom calendar syntax (work week, holidays).
3. **P2-3** Make the scheduler working-time aware: convert durations and offsets
   to working-time units and project calendar dates through the calendar, keeping
   summary rollup and lag semantics intact. Pin weekend/holiday behaviour with a
   regression suite.
4. **P2-4** Make `Tracker.actual_duration` obey the task's planning calendar.
   The inclusive `finish − start + 1` convention is already documented.
5. **P2-5** Expose the inclusive/exclusive duration convention as a documented
   project setting.

Acceptance: a Friday-to-Monday one-day task and a holiday-spanning task produce
documented, tested dates; `Calendar.working_days_between` semantics (currently
excluding the finish day) are either fixed or documented and tested.

## P2 — Plan persistence and editing

The CLI is read-only today and `PlanSerializer` is a skeleton that does not even
emit syntax the parser accepts.

* **P2-6** Complete `PlanSerializer`: project declaration and attributes,
  metadata, calendars, tasks with budgets and metadata, `depends` lines with
  correct type and lag (no trailing `FS 0d` noise), invoices, and tracking
  events.
* **P2-7** Guarantee round-trip: parse → serialize → parse must be an identity
  on the model, with byte-stable output for an unchanged project. Add a
  round-trip test over `Simple.plan`, `Detailed.plan`, and `Full_Plan.plan`.
* **P2-8** Add CLI write commands (`format`, `save`) that write back to the
  authoritative file and preserve comments where practical.
* **P2-9** Settle how a library of `.plan` files is organised (where projects
  live, naming, and how "recent projects" is tracked) so project storage is no
  longer an open question.

## P3 — Model and repository hygiene

* **P3-5** Add a `pyproject.toml` (packaging, console script entry point,
  Python version, dev extras) so the tool installs as `planscript` rather than
  requiring `python -m planscript` from the repository root.
* **P3-6** Performance: scheduling and reporting currently iterate the full task
  and dependency lists repeatedly. Check scaling on a few thousand tasks and
  introduce indexes only where measurement justifies them.

## P3 — Baselines, forecasting, and reporting depth

These require the prior decisions in
[Explicitly deferred decisions](#explicitly-deferred-decisions).

* **P3-7** Baselines and plan revisions: decide representation (snapshot section
  in the file, separate baseline file, or derived from tracking history) before
  writing any code. This is the largest open architectural question.
* **P3-8** Forecast: forecast finish from actuals, remaining duration, and
  dependencies, and report forecast-vs-target. Forecasts are derived and must
  never be written back as authoritative data.
* **P3-9** Staleness reporting: "task has been at 40% for 14 days", driven by
  tracking cadence configuration.
* **P3-10** Derived/calculated progress, kept conceptually distinct from
  explicitly reported progress (`DESIGN.md`, Tracking design).
* **P3-11** Additional lifecycle events (`reopen`, pause/resume), once the
  tracking model is stable.
* **P3-12** Task-level constraints (start-no-earlier-than, finish-no-later-than)
  with the target-vs-constraint distinction preserved, evaluated against
  portfolio targets such as `Project.finish_date`.

## P3 — Interfaces and interoperability

* **P3-13** Decide the GUI direction (the original notes mention Godot) and
  whether it consumes the model in-process or through a stable command
  interface.
* **P3-14** A Logseq-style integration, consuming and writing `.plan` files.
* **P3-15** Import/export paths that would make the tool adoptable: MS Project /
  CSV / Excel interchange, and an explicit note on what round-trip fidelity is
  acceptable.
* **P3-16** Reporting outputs beyond the console: Markdown or HTML status
  reports, and a rendered Gantt worthy of sending to a client.

## Explicitly deferred decisions

These were deliberately left unresolved. They must not be assumed by new code;
each one is a decision waiting to be made, not an oversight.

| Decision | State | Where it lands |
| --- | --- | --- |
| Event representation in the model | **Settled.** `TaskEvent(date, task_id, directive, info)`; events carry no independent IDs. | `planscript/engine/tracker.py` |
| Tracking validation architecture (parser vs. project validation) | **Partly settled.** Syntax and references fail in the parser; lifecycle rules fail during state derivation. Revisit when tracking is data-date aware. | P1-2 |
| Incremental progress syntax (`+10%`, `-20%`) | **Implemented** in `TaskState._derive`. | `planscript/engine/tracker.py` |
| Late / Blocked / Overdue task status | **Implemented** as `ScheduleCondition` in the reporter. | `planscript/engine/reporter.py` |
| Variance calculations | **Partly settled.** Planned-vs-actual variance is implemented against the calculated schedule. Whether variance should be measured against a *revised* plan or a *baseline* is still open. | P3-7, P3-8 |
| How tracking interacts with task hierarchy | **Open.** Tracking a summary task is currently accepted with no defined semantics. | P1-2 |
| Calendar semantics | **Open.** Working days, work week, holidays, hours, per-task calendars, and the inclusive/exclusive duration convention are undesigned. | P2 |
| Plan revisions / baselines | **Open and the largest architectural question.** If a planned start changes from 9/10 to 9/15, historical reports become ambiguous without baselines or plan versions. Do not introduce versioning until a concrete use case forces it. | P3-7 |
| Project-level tracking events and actual project start/finish directives | **Open.** Tracking is task-level only. | P3-7 |
| Reopening or restarting completed tasks, pause/resume | **Open.** `complete` is currently irreversible. | P3-11 |
| Derived/calculated progress | **Open.** Must stay conceptually distinct from explicitly reported progress. | P3-10 |
| Staleness ("at 40% for 14 days") and tracking cadence | **Open.** Reporting logic, not tracking-model logic. | P3-9 |
| Forecasting | **Open.** Get reliable actual history first; forecasts consume state rather than influence the tracking model. | P3-8 |
| Resource modelling and resource-constrained scheduling / leveling | **Open.** `resource.py` exists only as a sketch in the model TODO list. Would be a major scope decision. | P3-2 |
| Whether tracking events may be intermixed with the project definition | **Settled for now.** Events are recognised wherever they appear; the convention is to place them last (`SYNTAX.md`). Reopen only if placement needs enforcement. | `planscript/parser/parser.py` |
| `Project.start_date` / `finish_date` semantics | **Partly settled.** Both are soft targets and do not constrain CPM. How target analysis is surfaced is still open. | P3-12 |
| Exact duration configuration and calendar settings | **Open.** | P2-5 |
| Cost scope and currency | **Settled.** Cost is in scope; the model is dollars-only with no currency abstraction. | P2-12 |

## Non-goals

* Becoming a general-purpose configuration or data language. No drift toward
  JSON/YAML, no required quoting, no punctuation added purely for parser
  convenience.
* A database, server, multi-user backend, hidden identifiers, or an immutable
  audit log. The `.plan` file remains the single source of truth.
* Silently repairing, reinterpreting, or "best-guessing" invalid or
  contradictory input. It fails explicitly.
* Being a full MS Project replacement. The value here is readability, CPM
  correctness, and honest reporting, not feature parity.
* Multi-currency support. Cost is in scope but the model is dollars-only:
  amounts are plain dollar figures rendered with a leading `$`.

## Working agreement

* **Tests first for defects.** Every P0/P1 item lands with a test that fails
  before the change.
* **Keep the suite green.** `python -m unittest discover -s planscript/tests -t .`
  must pass before a commit; the current baseline is 180 tests.
* **No new runtime dependencies** without an explicit decision; `unittest` is
  the test framework.
* **Validation ownership.** Syntax and structure in the parser, model legality
  in `Project.validate()`, derived-state legality where the state is derived.
* **Docs move with code.** Update `SYNTAX.md` for syntax, `DESIGN.md` for
  structure, and this roadmap when an item is completed (remove it and mention
  the docs in the commit message).
* **Preserve the central rule:** derived information never becomes a second
  source of truth.

## Suggested sequence

| Milestone | Contents | Exit criteria |
| --- | --- | --- |
| **M1 — Reliable current build** | P0-1 … P0-3, P1-3, P1-4, P1-5 | Every CLI command works for tracked and untracked plans on Windows; no internal errors escape as tracebacks for malformed input. Redirected-output hardening is parked (see [Parked](#parked)). |
| **M2 — Trustworthy tracking** | P1-2 | Tracking conforms to the tracking design in `DESIGN.md` for ordering, dates, duplicates, and summary tasks, with a data-date parameter for deterministic tests. |
| **M3 — Working time** | P2-1 … P2-5 | Calendars drive scheduling and actual durations; weekend/holiday behaviour is pinned by tests and documented. |
| **M4 — Writable plans** | P2-6 … P2-9 | `format`/`save` round-trip the sample plans without loss; edits can be made safely from the CLI. |
| **M5 — Reporting depth** | P2-10 … P2-12, P3-8, P3-9 | Status reports show cost and schedule variance, forecast finish, and staleness with tests. |
| **M6 — Baselines and interfaces** | P3-7, P3-11 … P3-16 | Baseline/version strategy decided and implemented; an interface beyond the CLI consumes the model. |

## Summary of the plan

`P0` items are defects to fix now, `P1` completes what is already designed,
`P2` adds the next designed capabilities, and `P3` holds the larger questions.
The status section above describes what the code does today, and the milestone
table gives the order to work in. When in doubt, trust the code and the tests,
then correct this file.

# Parked Items

Items taken off the active lists on purpose. They are not abandoned, but they
are not being worked on right now.

### P0-4 Redirected `schedule` output crashes on Windows [PARKED]

`display.view_critical_paths` prints `→`, which raises `UnicodeEncodeError`
when stdout is redirected or piped on a cp1252 console (this is why the test
suite forces `PYTHONIOENCODING=utf-8`).

* Encoding work is intentionally deferred for now; the
  `PYTHONIOENCODING=utf-8` override in `planscript/tests/test_cli.py` remains
  the interim mitigation.
* When this is picked up: use an ASCII separator (for example `->`) or make the
  renderer encoding-safe, reconfigure stdout encoding in `main()`, and remove
  the override from the CLI tests.
* Acceptance (future): `python -m planscript schedule Simple.plan | Out-File
  ...` succeeds on Windows without an explicit `PYTHONIOENCODING`; CLI tests
  pass with the override removed.

# Completed Items
### P0-1 `summary` crashes on tracked projects [COMPLETED]

`planscript/cli/display.py` reads `project.tracker.events`, which does not
exist (`Tracker` stores `task_events`).

* Fix the attribute, or expose `Tracker.get_events()` as the single accessor
  and use it everywhere.
* Acceptance: `python -m planscript summary Simple.plan` exits `0` and reports
  a tracking event count; add a CLI regression test.

### P0-2 Broken and dead `Tracker` accessors [COMPLETED]

`Tracker.get_all_task_events` and `Tracker.get_latest_task_event` reference
`self.events` / `self.get_events()`, and `display.render_log` calls
`project.tracker.get_events()`.

* Decide on one event accessor API (`get_events`, `get_tasks_events`,
  `get_latest_task_event`) and implement it against `task_events`.
* Acceptance: unit tests exercise each accessor and event ordering by date.

### P0-3 Malformed indented `$` line raises an internal error [COMPLETED]

In `planscript/parser/parser.py`, an indented `<word> $<amount>` line that is
not a valid budget used to reach the invoice-entry branch before
`invoice_date` was assigned, raising `UnboundLocalError` instead of a
`ParseError`. Invoice state is now tracked through the current invoice object,
so internal errors no longer escape.

* Budget and invoice amounts accept zero, one, or two decimal places: `$10` is
  `$10.00` and `$10.5` is `$10.50`. This is documented in `SYNTAX.md`.
* Acceptance: parser tests assert that `budget $10.5` parses as
  `Decimal("10.5")`, that a malformed amount such as `budget $10.555` raises a
  `ParseError` (not `UnboundLocalError`), and that `main()` reports a
  `ParseError` as `Parse error:` with exit code 1.

  ### P1-4 Reconcile model annotations with reality [COMPLETED]

* `planscript/model/schedule.py` annotates CPM values as `int` while the
  scheduler stores `timedelta`; `duration` is annotated `int` and holds a
  `timedelta`.
* `planscript/model/project.py` carries a standing `TODO` to replace `float`
  with `Decimal`.
* The parser assigns `project.calendar` (a `str`) although `Project` declares
  `calendars: dict[str, Calendar]`. Decide which is the real field and align the
  model, parser, serializer, and tests.
* Acceptance: annotations match runtime types, tests assert the calendar
  representation, and no stale `TODO` remains for these items.

### P1-5 Reconcile the design notes with the implemented syntax [COMPLETED]

`planscript/parser/DESIGN.md` and `planscript/engine/TRACKING_DESIGN.md` contain
decisions that the implementation has since moved past — for example comments
are `;` rather than `#`, dependencies are indented `depends` lines rather than
`dependency 1.1 > 1.2 FS`, month durations are unreachable, and budgets,
invoices, and the `start:`/`finish:`/`calendar:` attributes are not documented
there at all.

* Split each note document into **current behaviour** and **deferred design**, or
  fold the current parts into `SYNTAX.md` / `DESIGN.md` and keep the notes purely
  as open questions.
* Acceptance: no top-level document states a syntax rule that the parser
  rejects.

## P2 — Cost and invoicing follow-ups
* **P2-10** Cost variance: compare actual cost (`Tracker.actual_cost`) against the
  resolved `Budget` per task and in total, and report it. [COMPLETED]
* **P2-11** Invoice validation beyond totals: decide whether allocations to
  summary tasks are legal, and detect invoices dated after the data date or
  before project start. [COMPLETED]
* **P2-12** Decide whether cost belongs in this tool's scope at all (see
  [Non-goals](#non-goals)) and, if so, whether currency or a dollars-only model
  is intended. [CONFIRMED/PARKED($)]

## P3 — Model and repository hygiene (completed)

* **P3-3** Implied-parent semantics decided — keep the tolerance and document
  it: when a task's implied parent is absent, it attaches to its nearest
  existing ancestor, so with `1` present and `1.2` absent, `1.2.3` is a child
  of `1`; a task with no existing ancestor is a root
  (`planscript/model/hierarchy.py`, documented in `DESIGN.md`, tested in
  `test_model.py`). [COMPLETED]
* **P3-4** Replace the hard-coded `2026-01-01` fallback in
  `Scheduler._get_dates` with a calculated-only schedule: when no project
  start date exists, `start_dates`/`finish_dates` are `None`, date views
  print a note, and variance/status fail with `SchedulingError`. [COMPLETED]