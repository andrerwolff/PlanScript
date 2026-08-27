# PlanScript Parser — Syntax Decisions & Design Context
 
This is the current design baseline for starting a new conversation. **Locked decisions should be treated as established unless explicitly reopened. Items marked open/deferred should not be assumed.**
  
## 1. Core philosophy
 
PlanScript is intended to be a **plaintext-first project scheduling language**, not a general-purpose configuration/data language.
 
Primary goals:
 
 
- Human-readable.
 
- Minimal syntax to remember.
 
- Low "how do I write this again?" friction.
 
- Visually understandable without requiring documentation.
 
- Avoid looking like JSON, YAML, or another structured data/configuration language.
 
- Syntax should communicate meaning rather than exist primarily to make parsing convenient.
 
- Keep the scheduling model clean and relatively small.
 
- Separate human/descriptive information from information that affects scheduling.
 

 
A major lesson from the design discussion:
 
 
**Don't add syntax merely because the parser can use it. Add syntax when it gives the user meaningful information or behavior.**
 
  
# LOCKED SYNTAX DECISIONS
 
## 2. Project declaration
 `project: Lafayette WRF ` 
The project name follows `project:`.
 
We initially considered more structured/project metadata syntax but intentionally avoided nesting.
  
## 3. Project metadata
 
Human/descriptive project information uses:
 `- Key: Value ` 
Example:
 `project: Lafayette WRF - Client: Lafayette - Project Number: 123456 - PM: Andre - Description: Does things ` 
### Important semantic distinction
 
Metadata is **not scheduler information**.
 
The parser can store it, but the scheduling engine doesn't need to understand fields such as:
 `- Client: - Project Number: - PM: - Description: ` 
Metadata keys do not need to be predefined by the scheduler.
 
This gives PlanScript useful extensibility without making the core language more complicated.
 
### Association rule
 
Metadata belongs to the **immediately preceding project/task entry**.
 
Example:
 `task 1.2 Preliminary Design 30d - Owner: Design Team - Description: 60% design package  task 1.3 Construction 20w - Owner: Contractor ` 
The first two metadata entries belong to `1.2`; the last belongs to `1.3`.
 
### Spacing
 
Use:
 `- Client: Lafayette ` 
rather than:
 `-Client: Lafayette ` 
The space improves readability and makes the `-` visually function as a metadata/list marker.
  
# 4. Task syntax
 
Basic task:
 `task 1.2 Preliminary Design 30w ` 
General concept:
 `task <ID> <description> <duration> ` 
Task definitions should remain focused on **what the task is**.
 
We deliberately moved away from putting every possible attribute onto the task line.
 
For example, dependencies should NOT be embedded in the task definition.
  
# 5. Task IDs
 
Task IDs are **hierarchical alphanumeric identifiers**, separated by periods.
 
Examples:
 `1 1.1 1.2 1.2.1 1.1.a 1.1.a.2 A.1 ` 
Invalid examples:
 `1..2 .1 1. 1-2 ` 
### Important conceptual decision
 
The hierarchy in the ID is **organizational**, not a scheduling relationship.
 
For example:
 `task 1 Design 30w task 1.1 Preliminary Design 10w task 1.2 Final Design 20w ` 
does NOT automatically create dependencies.
 
Dependencies remain explicit:
 `dependency 1.1 > 1.2 FS ` 
### Why we chose this
 
The initial thought was to make IDs completely flexible, e.g.:
 `survey design-01 site_prep ` 
but this was rejected because the actual intended use is hierarchical project/task numbering. Unlimited arbitrary identifiers would introduce flexibility without much practical value.
 
### Sorting
 
The scheduler currently sorts task IDs lexicographically for deterministic ordering, but **task ID ordering is not the basis of CPM scheduling**.
 
The dependency graph/topological sort determines calculation order.
 
This distinction should be preserved.
  
# 6. Duration syntax
 
Supported units:
 `h = hours d = days w = weeks m = months ` 
Examples:
 `8h 5d 2w 3m ` 
Decimal durations are allowed conceptually:
 `2.5d 1.5w ` 
Implementation of decimal durations can be deferred if it creates unnecessary complexity, but the language should accommodate them.
  
# 7. Dependencies
 
Standalone dependency entries:
 `dependency 1.1 > 1.2 SS+1w ` 
General structure:
 `dependency <predecessor> > <successor> <type><lag> ` 
Examples:
 `dependency 1.1 > 1.2 FS dependency 1.1 > 1.3 SS dependency 1.1 > 1.4 FF+2d dependency 1.1 > 1.5 SF-1w ` 
### Dependency direction
 
`>` means:
 `predecessor > successor ` 
This was deliberately chosen even though `>` can superficially look like "1.2 flows to 1.1" if written incorrectly.
 
The syntax itself establishes the direction:
 `dependency 1.1 > 1.2 ` 
meaning:
 
 
1.1 precedes/controls 1.2.
 
 
### Why dependencies are separate
 
We explicitly rejected embedding dependencies in task definitions, e.g.:
 `task 2.1 Design 30w >1.6FS+1w ` 
Reasons:
 
 
1. Task lines become too long once dates, calendars, resources, etc. are added.
 
2. Dependencies become visually buried.
 
3. `>` has a clear relationship-direction meaning and shouldn't be overloaded in a confusing task-line context.
 
4. Dependencies are important enough to deserve their own entries.
 
5. It preserves a clean distinction between task definition and task relationships.
 

  
# 8. Dependency types
 
The intended dependency types are:
 `FS SS FF SF ` 
with lag:
 `+1w -1d +2d ` 
Example:
 `dependency 1.1 > 1.2 SS+1w ` 
This is intentionally close to the user's existing MS Project mental model, e.g. `1.1FF+2`.
 
Exact defaults, such as whether omitted type means `FS`, remain to be finalized during parser design/review.
  
# 9. Comments
 
Comments use `#`:
 `# Preliminary design estimate task 1.2 Preliminary Design 30d ` 
For now:
 
 
**Whole-line comments only.**
 
 
Inline comments such as:
 `task 1.2 Design 30d # preliminary estimate ` 
are intentionally not part of the current syntax.
 
They can be reconsidered during final syntax review.
  
# 10. Calendar selection
 
Project-level calendar selection:
 `calendar: standard ` 
### Default
 
If the user doesn't specify a calendar, the scheduler assumes:
 `calendar: standard ` 
The concept of automatically writing that default into the file after the first calculation was discussed but is **not yet locked**.
 
### Custom calendars
 
Custom calendar definitions are deferred.
 
Eventually PlanScript may support something like:
 `calendar: construction ` 
with a corresponding calendar definition, but we deliberately are **not designing the custom calendar language yet**.
 
The immediate language only needs calendar selection.
  
# 11. Milestones
 
No separate milestone syntax.
 
A milestone is simply a zero-duration task:
 `task 2.3 Permit Approved 0d ` 
### Reasoning
 
A milestone is fundamentally a task with zero duration.
 
This keeps the scheduling model small:
 `Task ` 
rather than introducing:
 `Task Milestone ` 
The UI can recognize `duration == 0` and display it as a milestone.
 
Zero-duration tasks participate in dependencies normally:
 `dependency 2.2 > 2.3 FS dependency 2.3 > 3.1 FS ` 
### Important distinction
 
`0d` does **not** inherently mean a due date.
 
It means the activity has zero duration.
 
Its actual scheduled date comes from the network unless a later planning/constraint mechanism specifies otherwise.
  
# 12. Task metadata
 
The same metadata syntax applies to tasks:
 `task 1.2 Preliminary Design 30d - Owner: Design Team - Description: 60% design package - Deliverable: Design drawings ` 
This is intentionally the same mechanism used for project metadata.
 
Again:
 
 
Metadata is descriptive information, not inherently scheduling information.
 
  
# IMPORTANT ARCHITECTURAL DECISIONS
 
# 13. Separate human information from scheduler information
 
A major design principle established during the discussion:
 
### Human/project detail
 `- Client: Lafayette - Project Number: 123456 - PM: Andre - Description: Does things ` 
The scheduler doesn't care about these.
 
### Scheduler-relevant information
 
Uses dedicated PlanScript constructs:
 `start: ... finish: ... calendar: ... task ... dependency ... ` 
The goal is to prevent the scheduler from needing to interpret arbitrary project metadata.
  
# 14. Dates: previous `s:` / `e:` decision was reopened
 
We initially considered:
 `task 1.2 Survey 5d s: 2026-09-01 ` 
and:
 `e: 2026-09-15 ` 
with `s:` and `e:` meaning defined start/end dates.
 
This was **explicitly reopened and should NOT currently be treated as locked syntax**.
 
The reason is that "task date" can mean several different things:
 
 
1. A scheduling constraint.
 
2. A planned/target date.
 
3. A baseline date.
 
4. An actual date.
 
5. A calculated date.
 

 
Those should not necessarily be represented by the same mechanism.
 
For now, task definitions remain clean:
 `task 1.2 Preliminary Design 30d `  
# 15. Project start/finish targets
 
We developed a more useful concept for project-level dates.
 
Potential syntax:
 `start: 2026-09-01 finish: 2027-10-01 ` 
These are **planning targets**, not necessarily constraints.
 
The purpose is to answer questions such as:
 
 
"I want to finish in October. What does my network actually produce?"
 
 
Example:
 `finish: 2027-10-01 ` 
Calculated network:
 `Calculated finish: 2027-10-31 Target finish:     2027-10-01 Variance:           +30d ` 
Interpretation:
 `+30d = calculated schedule is 30 days later than target -30d = calculated schedule is 30 days earlier than target ` 
Recommended variance convention:
 
 
**Calculated date − target date**
 
 
So positive means later than target; negative means earlier.
  
# 16. No firm/soft target symbols
 
We discussed symbols such as:
 `@ = firm ~ = soft ` 
but decided this distinction isn't useful if both dates have **no different impact on CPM**.
 
Therefore the preferred model is simply:
 `start: 2026-09-01 finish: 2027-10-01 ` 
Both are targets.
 
No `@`/`~` distinction unless future functionality gives those symbols genuinely different semantics.
  
# 17. Forward/backward target analysis
 
A particularly important planning use case was identified.
 
### Known start
 
If:
 `start: 2026-09-01 ` 
the network can be evaluated forward from that target to determine expected finish.
 
### Known finish
 
If:
 `finish: 2027-10-01 ` 
the network can be analyzed backward to determine the start required to hit that target.
 
Example:
 `Target finish:     2027-10-01 Required start:    2026-08-02 Natural start:     2026-09-01 ` 
This tells the user:
 
 
The current network would need to start 30 days earlier to hit the target finish.
 
 
The existing backward-pass implementation provides much of the mathematical foundation for this type of analysis.
 
### Both dates
 
If both are supplied:
 `start: 2026-09-01 finish: 2027-10-01 ` 
the system can compare:
 `target window vs. network duration ` 
and identify whether the network fits within the desired window.
  
# 18. CPM should remain independent of target dates
 
This is the current architectural preference:
 
 
**The core CPM calculation should remain unconstrained by project targets.**
 
 
The scheduler answers:
 
 
"What does the dependency network produce?"
 
 
The planning analysis answers:
 
 
"How does that result compare with the target?"
 
 
This preserves deterministic CPM.
 
If a target finish is earlier than the calculated finish, the scheduler should not artificially change the network simply because a target exists.
 
Instead:
 `CPM  ↓ natural schedule  ↓ compare against target  ↓ variance `  
# 19. Target-anchored analysis is separate from normal CPM
 
If only a target finish is provided, the system can additionally ask:
 
 
"What start would be required to hit this finish?"
 
 
That is a **secondary target analysis**, not a modification of the primary CPM calculation.
 
Conceptually:
 `                    ┌── Normal CPM Project definition ─┤                     ├── Target variance                     │                     └── Target-anchored analysis ` 
This distinction is important and should be preserved.
  
# 20. Days vs. dates separation
 
This is one of the most important architectural decisions.
 
### Scheduler domain
 
The scheduling engine operates in **project-day units**, not calendar dates.
 
For example:
 `Project day 0 Project day 5 Project day 15 ` 
The engine calculates:
 
 
- Early Start
 
- Early Finish
 
- Late Start
 
- Late Finish
 
- Float
 
- Critical Path
 
- dependency relationships
 

 
without needing to know whether day 0 is September 1, January 15, etc.
 
### Date/calendar domain
 
A separate date/calendar layer handles:
 `2026-09-01 2026-09-15 weekends holidays working hours ` 
and maps between dates and project-day positions.
 
Conceptually:
 `Calendar/date domain         ↓ project-day values         ↓ Scheduler         ↓ project-day results         ↓ Calendar/date domain         ↓ reported dates `  
# 21. Why this separation matters
 
It keeps CPM calculations easy to test.
 
Example scheduler test:
 `A = 5d B = 10d A → B FS ` 
Expected:
 `A ES = 0 A EF = 5 B ES = 5 B EF = 15 ` 
No calendar involved.
 
Then separately test:
 `2026-09-01 + 5 working days ` 
This prevents calendar complexity from contaminating the core CPM engine.
  
# 22. Date-based constraints
 
Constraints will eventually complicate the days/dates boundary, but the intended architecture is:
 `PlanScript     ↓ Parser     ↓ Date / Calendar Layer     ↓ project-day constraint     ↓ Scheduler ` 
For example:
 `constraint 1.2 start >= 2026-09-15 ` 
could eventually become internally:
 `Task 1.2 ES >= project day 10 ` 
The scheduler still doesn't need to know that project day 10 corresponds to September 15.
  
# 23. Constraints vs. targets
 
This distinction is important.
 
### Target
 
 
"Tell me how far my schedule is from this date."
 
 
Example:
 `finish: 2027-10-01 ` 
Does not necessarily alter CPM.
 
### Constraint
 
 
"Do not allow the schedule to violate this condition."
 
 
A constraint becomes an **input to the scheduling calculation** and can cause cascading changes.
 
For example:
 `1.1 → 1.2 → 1.3 ` 
If 1.2 has a start constraint that pushes it five days later, 1.3 may move five days later too.
 
This is fundamentally different from a target.
  
# 24. Calendar/date constraints
 
Simple date constraints can be converted into project-day constraints by the date/calendar layer.
 
However, constraints involving calendar semantics such as:
 
 
- must start on Monday
 
- must finish on last working day of month
 
- specific holiday rules
 

 
may eventually require tighter interaction between calendar and scheduler.
 
These are intentionally **not designed yet**.
  
# 25. Project tracking architecture is intentionally open
 
Two possible future directions were identified:
 
### One file
 
A single PlanScript file containing project definition and current tracking state.
 
### Two files
 
For example:
 `project.plan project.log ` 
where:
 
 
- `.plan` = intended project definition
 
- `.log` = historical/current project events
 

 
The two-file/event-log model has conceptual advantages, especially for preserving history, but introduces significant complexity.
 
### Current decision
 
**Do not decide this yet.**
 
Tracking is a later feature.
 
Do not introduce `% complete`, actual start, actual finish, etc. into the core syntax until the tracking architecture is designed.
  
# 26. Baselines are deferred
 
Baseline dates are another distinct concept from:
 
 
- calculated dates
 
- target dates
 
- constraints
 
- actual dates
 

 
Do not force baseline behavior into the current date syntax.
 
Likely future possibilities include snapshots or baseline data, but this is intentionally open.
  
# 27. Actual dates are deferred
 
Actual dates belong conceptually to the future tracking system:
 `actual start actual finish actual progress ` 
They should not currently be added to the basic task syntax.
  
# CURRENT REPRESENTATIVE FILE
 
The current concepts could produce something like:
 `# Lafayette WRF schedule  project: Lafayette WRF - Client: Lafayette - Project Number: 123456 - PM: Andre - Description: Does things  calendar: standard  start: 2026-09-01 finish: 2027-10-01  task 1 Design 30w - Owner: Design Team  task 1.1 Preliminary Design 10w - Description: 30% design package  task 1.2 Final Design 20w - Description: 60% design package  task 2 Construction 40w  dependency 1.1 > 1.2 FS dependency 1.2 > 2 FS ` 
**Caveat:** The exact final syntax/semantics of `start:` and `finish:` is still under discussion, particularly how target analysis is exposed.
  
# CURRENT OPEN/DEFERRED ITEMS
 
Do **not** accidentally treat these as settled:
 
### Dates
 
 
- Exact semantics of project `start:` and `finish:`
 
- Whether project dates are optional targets
 
- How target-anchored analysis is exposed
 
- Task-level dates
 
- Date constraints
 

 
### Constraints
 
 
- Exact syntax
 
- Constraint types
 
- How hard constraints interact with CPM
 
- Calendar-specific constraints
 

 
### Calendars
 
 
- Custom calendar definition syntax
 
- Working hours
 
- Holidays
 
- Multiple calendars
 
- Task-specific calendars
 

 
### Tracking
 
 
- One-file vs. two-file architecture
 
- Actual dates
 
- Percent complete
 
- Remaining duration
 
- Status/data date
 
- Event log
 

 
### Baselines
 
 
- Representation
 
- Storage
 
- Comparison
 

 
### Parser conveniences
 
 
- Whether `FS` is the default dependency type
 
- Whether inline comments are eventually supported
 
- Validation/error messages
 
- Whether default `calendar: standard` is automatically written into the file after first calculation
 

  
# DESIGN LESSONS TO PRESERVE
 
These are probably the most important things to carry into the next conversation.
 
 
1.  
**Don't turn PlanScript into YAML/JSON.** Plaintext readability is a core goal.
 
 
2.  
**Avoid quotes whenever possible.** They create unnecessary "opening/closing" syntax and increase friction.
 
 
3.  
**Don't put everything on a task line.** Task lines should remain short and readable.
 
 
4.  
**Dependencies are first-class entries.** They deserve their own lines.
 
 
5.  
**Use punctuation only when it communicates meaning.** Don't add punctuation solely for parser convenience.
 
 
6.  
**Separate descriptive metadata from scheduler inputs.** `- Key: Value` is for human information.
 
 
7.  
**Don't encode hierarchy into scheduling logic.** `1.1` being under `1` is organizational; it does not imply dependency.
 
 
8.  
**Keep CPM pure.** The scheduler should primarily operate on project-day values and dependency relationships.
 
 
9.  
**Separate dates from scheduling calculations.** Dates are mapped to/from project-day values through the calendar/date layer.
 
 
10.  
**Don't call something a constraint if it doesn't constrain the schedule.** A target is a target; a constraint changes scheduling behavior.
 
 
11.  
**Don't design future features prematurely.** Tracking, baselines, custom calendars, and complex constraints can wait.
 
 
12.  
**Prefer a small number of powerful concepts.** A zero-duration task is a milestone; don't create a separate milestone object unless actual behavior eventually requires it.
 
 
13.  
**When syntax is ambiguous, resolve the semantic model first.** Especially for dates, constraints, baselines, and tracking. Syntax should follow the model rather than define it accidentally.