# PlanScript — Roadmap
There are a few major decisions I would explicitly mark as deferred, because they will become important once you build the first tracking implementation:

Event representation in the model
Probably a TrackingEvent object with date, task reference, directive, and optional argument.
Worth deciding before coding the parser/model interface, but not before the broader design is settled.
Tracking validation architecture
Which checks belong in the parser versus project-level validation.
Given your recent direction, I'd probably parse valid syntax first and have project validation enforce chronological/lifecycle rules.
How tracking interacts with task hierarchy
You have already constrained dependencies toward leaves.
You should eventually decide whether tracking is allowed on summary tasks. I would defer this until the basic task-level tracking works.
Calendar semantics
We have established that actual duration uses the task's planning calendar.
The exact inclusive/exclusive convention and user-configurable setting can wait.
Variance calculations
Planned vs. actual start/finish/duration.
Especially whether variance is measured against the original plan or a revised plan. This is where baselines eventually become important, so I would not design deeply into it yet.
Forecasting
Definitely defer. Get reliable actual history first. Forecasting can consume the resulting state rather than influence the tracking model.
Staleness
Eventually useful: "Task has been at 40% for 14 days."
But this is reporting logic, not tracking-model logic.
Plan revisions / baselines
Probably the biggest eventual architectural issue.
If the user changes a planned start from 9/10 to 9/15, historical reports can become ambiguous unless you eventually have baselines or historical plan versions.
I would explicitly leave this unresolved rather than prematurely introducing versioning.