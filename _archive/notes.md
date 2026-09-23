've now reviewed the full budget/cost/invoice landscape. Here's my analysis and a draft plan.

# Current state (what exists today)

__Budgets__ — fully working:

- `budget $X` (explicit) and `budget N%` (weighted) syntax; `Budgeter` resolves top-down, rolls summaries up, whole-cent largest-remainder allocation → derived `Budget` (`amounts`, `explicit`, `weights`, `unallocated`, `total`).
- `budget` CLI prints __one__ table (`ID, TASK, BUDGET, BASIS`) + project total.

__Cost/actuals__ — derived but invisible in the CLI:

- Invoices parse as top-level dated lines (`2026-09-30 invoice $45362.24` + indented per-task allocations; allocations must equal the total).
- `Tracker.actual_cost(task_id, as_of)` sums invoice allocations up to a date and rolls up through summaries (tested in `test_tracking.py`).
- __No command displays actuals or variance anywhere.__

__Variance__ — only schedule variance exists (`Analyzer`: start/finish/duration). Cost variance is open as __ROADMAP P2-10__, invoice validation as __P2-11__, cost-scope/currency decision as __P2-12__, and __P1-3__ (populate `ProjectBudgetReport`, render budget section in `status`) is still open — `test_reporter.py` doesn't exist yet.

__Defects/gaps found while reading:__

- `budget -ao/--as-of` is parsed but __silently ignored__ by `budget_command` — actuals would always be "as of today".
- `ProjectBudgetReport.project_paid` references a `paid` concept that __has no model or syntax anywhere__ (only mentioned in P1-3).
- SYNTAX.md doesn't document budgets or invoices at all (known ROADMAP doc gap).
- `Schedule` is never computed for the `budget` command today (fine — cost variance doesn't need it).

# Proposed plan

### Phase 0 — Settle scope decisions (docs-only, closes P2-12)

- Cost __is__ in scope (this request). Currency: __dollars-only__ (matches hardcoded `CURRENCY` quantizer and `$` formatting); document it and close P2-12.
- __Actuals = invoice allocations to date__ — that is the only cost source in the model. Define variance as __`budget − actual`__ (positive = under budget), documented in DESIGN.md.

### Phase 1 — Cost report derivation (core of P2-10)

- New derived data (never written back): per-task rows in hierarchy tree order — `ID, name, budget, actual(as_of), variance` — plus project totals (root-summed, mirroring `Budget.total` to avoid double-counting summaries) and the as-of date.
- Builder reads `Budget.amounts` + `Tracker.actual_cost(id, as_of)`; unallocated-budget tasks show actual but `"-"` variance; summary rows roll up naturally on both sides.
- Placement (my recommendation): derived model in `planscript/model/` + builder function in `planscript/engine/reporter.py`, so `budget` tables and P1-3's `status` section share one derivation. Alternative: a dedicated engine module — happy to go either way.
- Tests: new fixture in `test_projects.py` (per convention) + new test module covering over/under/zero variance, as-of cutoff excluding later invoices, summary rollups, direct charge-to-summary, totals reconciling to the invoiced total.

### Phase 2 — `budget` command → series of tables (the end goal)

Mirror the `schedule` command's exact pattern (`-c/-d/-g`, no flags = everything):

- `view_budget` (existing): `ID, TASK, BUDGET, BASIS`
- `view_budget_actuals` (new): `ID, TASK, ACTUAL`
- `view_budget_variance` (new): `ID, TASK, BUDGET, ACTUAL, VARIANCE`
- `view_invoices` (new): date, amount (+ allocation count)
- Totals footer: Budget / Invoiced to date / Remaining / Variance, with the as-of date; header shown when no flags given (same as `schedule`).
- New flags `-b/-a/-v/-i`; __wire `-ao` through__ (fixes the ignored-flag defect; test proves invoices after as-of drop out).
- CLI tests via the fast in-process `run_cli`.

### Phase 3 — P1-3 `status` integration

- Populate `ProjectBudgetReport` from the shared cost report; render the budget section in `render_text`; add `test_reporter.py` with value assertions (P1-3's acceptance criterion).
- `project_paid`: resolve per your answer below (drop/N/A, or new syntax later).

### Phase 4 — Invoice hardening (P2-11)

- Summary-task allocations: currently allowed and tested ("direct charge to summary is additional") → keep legal, document it.
- Invoice __before project start__ (when `start:` known): validation error. Invoice __after as-of__: excluded from actuals (already the semantics) rather than an error, since as-of is a run parameter, not file truth.

### Phase 5 — Docs & roadmap

- SYNTAX.md: add Budgets + Invoices sections (fixes the documented gap). DESIGN.md: cost-derivation section, new tables, remove the `ProjectBudgetReport` gap bullet. ROADMAP.md: mark P1-3/P2-10/P2-11/P2-12 completed, update status bullets and the test-count baseline; run full suite (must stay green, currently 170 @ ~0.9s).

__Out of scope:__ forecasts/EAC (P3-8), resource costs (P3-2), serializer budget/invoice support (P2-6), currency abstraction.

One scope decision determines Phases 3–4:

Cline has a question:

What should "invoicing features" include in this effort?

Display + validate only — show invoice tables and do P2-11 validation (dates, summary allocations) using existing syntax; no new syntaxAdd payments — also design new payment syntax so project_paid / paid-vs-invoiced becomes real (larger scope, new model + parser + validation work)Defer invoicing — build budget/actual/variance tables now from existing invoice data; handle invoice validation and payments in a later pass
