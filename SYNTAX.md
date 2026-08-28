# PlanScript — Syntax

## General
Planscript files use the .plan suffix and should be stored [tbd]

## Project Definition
General concept:
`project: <project name>`

Example:
```text
project: DOTI LS6
- Client: DOTI
- Project Number: TBA
- Description: Decommission LS6 and Install 18" Sewer
```

### Project Metadata
`- <key>: <value>`
- User defined and generated, these are not required for CPM scheduling
- Referred programattically like `project.metadata["Client"]`
- space required after `-` and after `:`

## Task Definition
General concept:
 `task <ID> <description> <duration> ` 

Examples:
```text
task 4.1.1 Alt Analysis 16w
task 4.1.2 Engineering Report 6w
 - Description: Prepare report with intent to submit to CDPHE
task 4.1.3 Submit Report 0d
```
### Task IDs
Task IDs are **hierarchical alphanumeric identifiers**, separated by periods.

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
### Task Names
Task names are user-defined strings, very flexible.

### Task Duration
The optional last entry on the task line, defines the length of the task. 

Supported units:
 `h = hours d = days w = weeks m = months `

Examples:

✔ `8h, 5d, 2w, 3m , 2.5d, 1.5w, ``, 7 `

✘ `5 d,  d4,  3days`

Default Behavior:
- If no duration is specified, the task will be marked as summary (no CPM impact)
- If no unit is specified, the default is [d]ay
- 0d tasks are considered milestones

### Task Metadata
`- <key>: <value>`
- User defined and generated, these are not required for CPM scheduling
- Referred programattically like `task.metadata["Description"]`
- space required after `-` and after `:`

## Dependencies
General concept:
`dependency <predecessor_id> > <successor_id> <relationship_type><lag> `

Examples:
```text
dependency 1.1 > 1.2
dependency 3.1 > 3.2 +14d
dependency 1.1 > 3.2 -7
```
### Predecessor / Successor
Use task ids for references. Tasks must be previously defined in the document. 

`>` notation indicates direction of the dependency *not necessarily* the flow of tasks. 

i.e. `dependency 1.1 > 1.2` should read "task 1.2 depends on 1.1" or "task 1.1 drives task 1.2"

### Relationships

#### Dependency Type
Supported relationship types:

* `FS` — Finish-to-Start
* `SS` — Start-to-Start
* `FF` — Finish-to-Finish
* `SF` — Start-to-Finish

Default Behavior
- If dependency type is ommitted, default is FS
#### Lag
Lag values can be `+` or `-`, and must follow the dependency type without space

Supported units:
 `h = hours d = days w = weeks m = months `

Examples:

✔ `8h, 5d, 2w, 3m , 2.5d, 1.5w, ``, 7 `

✘ `5 d,  d4,  3days`

Default Behavior:
- If no duration is specified, lag = 0
- If no unit is specified, the default is [d]ay
- if no sign specified, default is `+`

## Comments
Comments use `#`:

 `# Preliminary design estimate task 1.2 Preliminary Design 30d ` 

Inline comments such as:
 `task 1.2 Design 30d # preliminary estimate ` 
are intentionally not part of the current syntax.

## Parser Principles

* Human-readable plaintext is the source of truth.
* Syntax should favor readability over unnecessary punctuation.
* Invalid input should fail explicitly.
* Parser errors should identify the line whenever possible.
