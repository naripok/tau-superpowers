# Spec: Plan checkbox progress tracking

<!-- Derived from the approved proposal docs/design/2026-09-02-plan-checkbox-tracking-proposal.md (commit d933a8d, sha256 177745324b4190a0e37eeaba365a56c6fc19dc8202dbd0aa53917bfe78cfab90). Delta against the living spec docs/specs/workflow-governance.md. -->

## Domain: workflow-governance

### ADDED Requirements

#### Requirement: Plan checkbox progress tracking
The plan document SHALL record execution progress through its task checkboxes. When a plan task completes its completion gate, the controller SHALL mark every checkbox of that task `[x]` in the plan document. In inline execution the completion gate is the task loop's completion step, reached after the task's implementation commit and verification pass. In dispatch execution the completion gate is the task's per-task review approving both review dimensions, Spec Compliance and Code Quality. The controller SHALL commit each flip immediately as exactly one tracking commit for that task; the tracking commit SHALL contain only that flip, and its message SHALL use the form `docs(plan): mark <plan-file-stem> Task N complete`, where `<plan-file-stem>` is the plan file's name without its extension. A flip changes only checkbox state: it changes no contract text, task text, interface, verification command, or requirement mapping. A task that has not cleared its completion gate SHALL keep unchecked checkboxes. A flipped checkbox SHALL NOT revert: it records that the task cleared its completion gate, and post-completion fix work SHALL NOT reopen that record. A progress-tracking flip SHALL NOT invalidate the plan's reviews or approvals and SHALL NOT create a new plan version or trigger a re-review. The plan's reviews and approvals SHALL attach to the plan's identity of record, the exact reviewed plan version.

##### Scenario: Inline execution flips at completion
- GIVEN inline execution runs a Bounded plan task
- WHEN the controller marks the task complete after its implementation commit and verification pass
- THEN every checkbox of that task reads `[x]` in the plan document
- AND the controller commits exactly one tracking commit for the task, immediately, with the message `docs(plan): mark <plan-file-stem> Task N complete`

##### Scenario: Dispatch execution flips after review
- GIVEN dispatch execution runs a plan task and its per-task review approves both the Spec Compliance and Code Quality dimensions
- WHEN the controller marks the task complete
- THEN every checkbox of that task reads `[x]` in the plan document
- AND the controller commits exactly one tracking commit for the task, immediately, with the message `docs(plan): mark <plan-file-stem> Task N complete`

##### Scenario: Failed review keeps boxes unchecked
- GIVEN a task's per-task review returns a needs-fixes verdict
- WHEN the controller handles the report
- THEN the task's checkboxes stay unchecked
- AND no tracking commit exists for that task

##### Scenario: Flipped boxes never revert
- GIVEN a task's checkboxes read `[x]`
- WHEN post-completion fix work changes the task's code
- THEN the task's checkboxes stay `[x]`

##### Scenario: Flip preserves plan approval
- GIVEN plan-review approval attaches to the exact reviewed plan version
- WHEN the controller flips a completed task's checkboxes during execution
- THEN the plan-review approval still attaches through the plan's identity of record
- AND no plan re-review starts

#### Requirement: Single plan writer during execution
The controller SHALL be the single writer of the plan document during execution. An implementer or reviewer subagent SHALL NOT read or edit the plan document. The controller SHALL supply the full task text in each implementer and reviewer dispatch, and the dispatch SHALL NOT direct the subagent to the plan document for task context.

##### Scenario: Subagents receive task text, not the plan
- GIVEN dispatch execution prepares an implementer or reviewer dispatch
- WHEN the controller constructs the dispatch
- THEN the dispatch supplies the full task text
- AND the subagent neither reads nor edits the plan document

##### Scenario: Controller is the only plan writer
- GIVEN execution is running
- WHEN the plan document changes
- THEN the change came from the controller

#### Requirement: Two-state plan progress record
The plan document SHALL carry exactly two checkbox states, `- [ ]` and `- [x]`, and SHALL NOT carry an in-progress marker. In-progress state SHALL live in the controller's own task tracking in both execution modes: inline execution targets the controller's task tracking with its in-progress step, and dispatch execution keeps its task tracking. The plan document SHALL record completion only. A new plan document's header SHALL instruct the executor to mark each task's checkboxes `[x]` in the plan file when the task completes, so an executor that reads the plan sees the tracking contract.

##### Scenario: No in-progress marker in the plan
- GIVEN execution has started tasks that are not complete
- WHEN a reader opens the plan document
- THEN the document shows only `- [ ]` and `- [x]` checkbox states
- AND no in-progress marker appears
- AND in-progress state lives in the controller's task tracking

##### Scenario: Plan header instructs executors
- GIVEN the planner writes a plan header
- WHEN an executor reads the plan
- THEN the header instructs the executor to mark each task's checkboxes `[x]` in the plan file when the task completes

### MODIFIED Requirements

#### Requirement: Ordered proposal-baseline state flow
<!-- Only the changed parts. The sync preserves existing content not mentioned. Within the paragraph that begins "Artifact existence MUST NOT establish completion of a state.", the following two sentences are replaced: "Any artifact edit MUST invalidate that artifact's prior review or approval. A changed upstream input MUST invalidate every affected downstream review and approval." The replacement sentences follow. Every other sentence of the paragraph, including "The workflow MUST NOT enter planning until all unresolved controlled decisions and blocking spec-review dispositions are resolved.", stays unchanged. -->

Any artifact edit MUST invalidate that artifact's prior review or approval. A changed upstream input MUST invalidate every affected downstream review and approval. A progress-tracking flip of a plan document's checkboxes, performed by the controller during execution as defined by the Plan checkbox progress tracking requirement, MUST NOT invalidate the plan's reviews or approvals and MUST NOT count as a changed upstream input; every other artifact edit remains fully governed by the preceding sentences.

##### Scenario: Flip is not a changed upstream input
- GIVEN the plan is an upstream input for per-task implementation reviews
- WHEN the controller flips a completed task's checkboxes
- THEN the downstream reviews that already approved keep their approvals
- AND no downstream re-review starts

#### Requirement: Single High-risk two-pass review
<!-- Only the changed parts. The sync preserves existing content not mentioned. The following sentences are appended after "An artifact edit MUST create a new artifact version. The new version MUST receive a new complete initial review.", which stay unchanged. Every other part of the requirement stays unchanged. -->

A progress-tracking flip of a plan document's checkboxes, performed by the controller during execution as defined by the Plan checkbox progress tracking requirement, MUST NOT create a new artifact version and MUST NOT trigger a new initial review; every other artifact edit remains fully governed by the preceding sentences.

##### Scenario: Flip creates no plan version
- GIVEN a plan holds plan-review approval
- WHEN the controller records a completed task by flipping its checkboxes
- THEN the plan keeps the exact reviewed version as its identity of record
- AND no new initial review starts

#### Requirement: Implementation reviews and final acceptance
<!-- Only the changed parts. The sync preserves existing content not mentioned. The paragraph below replaces "Before living-spec synchronization, the workflow MUST check every proposal acceptance example and run fresh repository verification. A failed required review, acceptance example, or verification command MUST block finishing." -->

Before living-spec synchronization, the workflow MUST check every proposal acceptance example, check that the plan document shows every task's checkboxes complete, and run fresh repository verification. A failed required review, acceptance example, verification command, or an incomplete plan progress record MUST block finishing. When final acceptance checks the plan approval identity, the plan's approval SHALL attach through the plan's identity of record, the exact reviewed version, so progress-tracking flips do not stale it.

##### Scenario: Unchecked plan boxes block finishing
- GIVEN execution completed but the plan document shows an unchecked checkbox for a completed task
- WHEN final acceptance runs
- THEN synchronization and integration stay blocked until the plan document records every task complete

##### Scenario: Plan approval binds to the reviewed version
- GIVEN the plan file bytes changed only by progress-tracking flips
- WHEN final acceptance checks the plan approval identity
- THEN the plan approval attaches through the plan's identity of record, the exact reviewed version
- AND final acceptance does not report a stale plan approval
