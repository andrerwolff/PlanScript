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
`<tab>- <key>: <value>`
- User defined and generated, these are not required for CPM scheduling
- Referred programattically like `project.metadata["Client"]`
- tab or 4 spaces required before `-`
- space required after `-` and after `:`

## Task Definition
General concept:
 `task <ID> <description> [duration] ` 

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

Supported units (required if duration is listed):
 `h = hours d = days w = weeks`

Examples:

✔ `8h, 5d, 2w, 2.5d, 1.5w`

✘ `5 d,  d4,  3days`

Default Behavior:
- If no duration is specified, the task will be marked as summary (no CPM impact)
- 0d tasks are considered milestones

### Task Metadata
`<tab>- <key>: <value>`
- User defined and generated, these are not required for CPM scheduling
- Referred programattically like `task.metadata["Description"]`
- tab or 4 spaces required before `-`
- space required after `-` and after `:`

## Dependencies
General concept:
`<tab>depends <predecessor_id> <relationship_type> [lag] `

Examples:
```text
task 1.3 3w
    depends 1.1 FF +2W
```
### Predecessor
Use task ids for references. 

i.e. the above example should read "task 1.3 depends on 1.1"

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
Lag values can be `+` or `-`, and must follow the dependency type after a space

Supported units (required if lag listed):
 `h = hours d = days w = weeks`

Examples:

✔ `8h, 5d, 2w, 2.5d, 1.5w`

✘ `5 d,  d4,  3days, 7`

Default Behavior:
- If no duration is specified, lag = 0
- if no sign specified, default is `+`

## Comments
Comments use `;`:

 `; Preliminary design estimate task 1.2 Preliminary Design 30d ` 

Inline comments such as:
 `task 1.2 Design 30d ; preliminary estimate ` 
are intentionally not part of the current syntax.

## Parser Principles

* Human-readable plaintext is the source of truth.
* Syntax should favor readability over unnecessary punctuation.
* Invalid input should fail explicitly.
* Parser errors should identify the line whenever possible.
