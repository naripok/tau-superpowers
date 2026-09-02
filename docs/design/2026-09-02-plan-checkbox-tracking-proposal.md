# Proposal: Plan checkbox progress tracking

## Intent

Every implementation plan promises progress tracking. The `writing-plans` header template states "Steps use checkbox (`- [ ]`) syntax for tracking", and every task carries checkboxes for its TDD steps. Nothing in the workflow fulfills that promise: no skill instructs any agent to flip a checkbox, `executing-plans` moves the checklist into working notes, and `subagent-driven-development` forbids subagents from reading the plan file while naming no target for its own "Mark the task complete" step. The checkboxes stay `[ ]` forever, and an operator who opens a plan document mid-execution learns nothing about progress.

This change makes the plan document the progress record. The controller marks every checkbox of a task `[x]` when the task completes its gate, in both execution modes, and records each flip in a tracking commit. `finishing-a-development-branch` verifies that a finished plan shows every task complete before synchronization.

**Selected depth:** Bounded (operator-selected).

## Brownfield Baseline

Baseline branch: living-spec domain. The affected domain is `workflow-governance`, specified in `docs/specs/workflow-governance.md`. That living spec defines the review gates, the artifact-edit invalidation rule, the execution reviews, and the finishing flow. It says nothing about plan-internal progress tracking, so the current system and the living spec agree: no tracking exists.

Relevant current behavior, with evidence:

- `skills/writing-plans/SKILL.md`: the required plan header states "Steps use checkbox (`- [ ]`) syntax for tracking." Every task template ends with four checkboxes (failing tests, implementation, verification, commit). The plan is committed to the branch before execution. No instruction covers updating the checkboxes.
- `skills/executing-plans/SKILL.md`: Step 1 instructs the controller to "copy the plan checklist into your working notes." Step 3 instructs "Mark the task as in_progress" and "Mark the task as completed" with no target. The plan file is never edited after commit.
- `skills/subagent-driven-development/SKILL.md`: step 1 says "Create task tracking" and step 2f says "Mark the task complete", both without a target. The Red Flags section says "Make a subagent read the plan file" is never allowed, so implementer and reviewer subagents cannot update the document. The Review Accounting section states "An artifact or implementation change creates a new version and receives one new complete initial review."
- `skills/finishing-a-development-branch/SKILL.md`: Step 1 final acceptance checks approval identities, High-risk evidence, depth, acceptance examples, and fresh verification. It checks no plan progress state.
- `tests/test-plan-execution-guidance.sh` and `tests/test-finishing-workflow-guidance.sh`: guidance tests that assert cross-file contracts in these skill files and in the implementation dispatch and review prompt templates. They pass on the baseline and encode today's no-tracking behavior.
- `docs/specs/workflow-governance.md`, requirement "Ordered proposal-baseline state flow": "Any artifact edit MUST invalidate that artifact's prior review or approval." Taken literally, this rule invalidates plan-review approval the first time a checkbox flips during execution. Two further clauses repeat the conflict: the same requirement's "A changed upstream input MUST invalidate every affected downstream review and approval", and requirement "Single High-risk two-pass review": "An artifact edit MUST create a new artifact version. The new version MUST receive a new complete initial review." That reading makes any tracking mechanism self-defeating, so this proposal resolves it (see Required Outcomes and Approach).

Material discrepancies: none. The living spec is silent on tracking, and the skills implement no tracking.

## Required Outcomes

1. The plan document is the progress record for both execution modes: inline execution through `executing-plans` and dispatch execution through `subagent-driven-development`.
2. The controller flips all `- [ ]` checkboxes of a task to `- [x]` when that task completes its gate: in inline execution, at the completion step of the task loop; in dispatch execution, after both per-task review dimensions pass. A task that has not cleared its review gate keeps unchecked boxes. A flipped box never reverts.
3. The controller commits each flip immediately as one tracking commit for that task.
4. The controller is the single writer of the plan file during execution. Implementer and reviewer subagents neither read nor edit the plan file; they receive the task text in the dispatch.
5. A checkbox flip is a meaning-preserving tracking edit that the controller makes during execution: it changes no contract text, task text, verification command, or requirement mapping. The feature spec carves exactly one exemption for it, scoped to controller progress-tracking flips of the plan document's checkboxes: a flip invalidates no review or approval, creates no new plan version, and triggers no re-review, and the plan's identity of record stays the exact reviewed version. Every other artifact edit keeps current behavior: a meaning-changing edit invalidates reviews and approvals, a plan edit creates a new version that receives a new complete initial review, and a format-only proposal edit still goes through proposal change control.
6. The plan document carries exactly two checkbox states, `- [ ]` and `- [x]`. No in-progress marker exists in the document. In-progress state lives in the controller's own task tracking in both modes: inline execution retargets the executing-plans "Mark the task as in_progress" step to the controller's task tracking, and dispatch execution keeps the subagent-driven-development task tracking. The plan document records completion only.
7. Final acceptance in `finishing-a-development-branch` checks that the plan document shows every task's checkboxes complete. A plan with unchecked boxes blocks synchronization and integration.
8. New plan documents carry the operational tracking instruction in their header, so any executor that reads the plan sees the contract.

## Acceptance Examples

1. Inline flip: GIVEN a Bounded plan executes through `executing-plans`, WHEN Task 1 passes its verification and the controller commits the implementation, THEN the controller marks every Task 1 checkbox `[x]` in the plan file and commits one tracking commit.
2. Dispatch flip: GIVEN a task's implementer reports DONE and its reviewer approves both dimensions, WHEN the controller marks the task complete, THEN the task's checkboxes read `[x]` in the plan file and one tracking commit records the flip. GIVEN the reviewer returns a Needs-fixes verdict for a task, THEN that task's checkboxes remain `[ ]`.
3. Approval survives flips: GIVEN a plan holds plan-review approval, and the controller flipped Task 1 and Task 2 checkboxes during execution, WHEN finishing checks approval identities, THEN the plan-review approval still attaches to the plan.
4. Final acceptance blocks on unchecked boxes: GIVEN execution completed a task but its checkboxes are unchecked, WHEN final acceptance runs, THEN synchronization and integration stay blocked until the plan document records the task complete.
5. Single writer: GIVEN a Standard plan executes through dispatch, WHEN an implementer or reviewer subagent runs, THEN the dispatch supplies the task text and the subagent neither reads nor edits the plan file.
6. Operational header: GIVEN the planner writes a new plan, THEN the plan header instructs the executor to mark each task's checkboxes `[x]` in the plan file when the task completes.

## Scope

**In scope:**

- `skills/writing-plans/SKILL.md`: the header template line becomes the operational tracking contract (outcome 8), and the overview line "One commit per task" is reworded to "one implementation commit per task" so the file stays consistent with the tracking-commit convention. No task-template structure change.
- `skills/executing-plans/SKILL.md`: Step 1 names the plan file as the progress record and drops the working-notes copy; Step 3 item 1 targets the controller's task tracking for the in-progress state; Step 3 defines the completion step as flip all of the task's checkboxes plus one tracking commit.
- `skills/subagent-driven-development/SKILL.md`: step 1 names the plan checkboxes as the tracking record; step 2f defines flip plus tracking commit; the Red Flags entry extends to "read or edit"; the Review Accounting section gains the explicit meaning-preserving exemption (outcome 5).
- `skills/finishing-a-development-branch/SKILL.md`: final acceptance gains the all-boxes-checked check (outcome 7), and the approval-identity check binds the plan's approval to the plan's identity of record, the exact reviewed version, rather than to the current file bytes, so a checkbox flip does not stale the plan approval (outcome 5, acceptance example 3).
- Guidance tests: update `tests/test-plan-execution-guidance.sh` and `tests/test-finishing-workflow-guidance.sh` to assert the new contracts and keep asserting the preserved ones.
- Feature-spec delta against `docs/specs/workflow-governance.md`, synchronized during finishing.

**Out of scope:**

- Any non-standard checkbox state or in-progress marker syntax (rejected decision).
- Progress tracking for Direct work, which creates no plan.
- Changes to plan review content, task sizing, or the task template's structure beyond the header line.
- Reordering or re-wiring any workflow gate, artifact, or handoff.
- Installer behavior (`install.sh` copies skill content verbatim; content-only changes need no installer work).

## Constraints

- Checkbox flips preserve plan meaning: no contract text, task text, interface, verification command, or requirement mapping changes. The flip edits only checkbox state.
- One tracking commit per completed task. The implementation commit stays one per task; the tracking commit is separate metadata.
- The flip happens only at the completion gate, never before the review passes in dispatch execution.
- The subagent plan-file prohibition stays intact and extends from reading to editing.
- The tracking commit convention names the plan and the task: `docs(plan): mark <plan-file-stem> Task N complete`, where `<plan-file-stem>` is the plan file's name without extension. The plan `docs/plans/2026-09-02-plan-checkbox-tracking.md` yields `docs(plan): mark 2026-09-02-plan-checkbox-tracking Task 2 complete`.

## Approach

The controller owns all checkbox updates, at task completion, with a per-task tracking commit.

- **Controller-owned flips.** In inline execution the controller performs the steps itself and marks the task complete at the end of the task loop. In dispatch execution the controller alone holds the evidence (implementer report, reviewer verdict) and is the only agent permitted to touch the plan file. Single-writer semantics eliminate concurrent-edit hazards and follow from the existing prohibition on subagents reading the plan.
- **Flip at the completion gate.** Boxes flip once, after the task clears its gate, and a flipped box never reverts. A task that fails review stays unchecked. The checkbox records that the task cleared its gate; post-completion fix work does not reopen the record. This matches the accepted granularity decision: all of a task's boxes flip together at completion.
- **Immediate per-task tracking commit.** Uncommitted plan edits pollute the diff evidence that every later reviewer receives and leave a dirty tree for the rest of the run. One small commit per task keeps reviewer evidence clean and persists progress across a session loss.
- **Meaning-preserving exemption.** The feature spec carves exactly one exemption into the `workflow-governance` rules: a controller progress-tracking flip of the plan document's checkboxes during execution. The exemption amends exactly three clauses. In "Ordered proposal-baseline state flow", "Any artifact edit MUST invalidate that artifact's prior review or approval" and "A changed upstream input MUST invalidate every affected downstream review and approval" gain a meaning-based limit: a meaning-preserving flip is neither an invalidating edit nor a changed input. In "Single High-risk two-pass review", "An artifact edit MUST create a new artifact version" gains the same limit: a flip creates no version and no new initial review. The plan's identity of record stays the exact reviewed version; reviews and approvals bind to that identity. Every other edit keeps current behavior: a plan edit that can change meaning invalidates plan-review approval and creates a new reviewed version, and format-only proposal edits still repeat cold review and operator approval under "Approved proposal change control", which the exemption does not touch. This resolves the literal-reading conflict in the baseline and keeps finishing's approval-identity check satisfiable.
- **Final-acceptance check.** Finishing verifies that the plan document shows every task complete. This closes the loop: a controller that forgets to flip boxes gets stopped at the last gate instead of shipping a stale record.

Alternatives considered:

- Per-step flips during inline execution. Rejected: two different mechanisms across the two execution modes, and boxes that regress when verification fails.
- One consolidated tracking commit before finishing. Rejected: dirty plan edits pollute reviewer diffs across the whole run, and a session loss loses all progress state.
- An in-progress marker state in the document. Rejected: non-standard markdown, and the two-state model keeps the document honest about completion only.
- Implementer subagents flip their own task's boxes. Rejected: contradicts the plan-file prohibition, and the flip precedes the review gate.
- A separate progress file or PR-body tracking. Rejected: the operator selected the plan document itself as the record.

## Impact

- Skill text: the four SKILL.md files listed in scope. No skill outside the plan lifecycle changes.
- Future plan documents: every plan gains live progress state during execution.
- Living spec: `docs/specs/workflow-governance.md` gains the plan-progress-tracking behavior and the meaning-based invalidation amendment during synchronization.
- Guidance tests: two test files updated; reference checks (`tests/test-references.sh`) stay green as a preservation check.
- Installer: no change. The installer copies skill content verbatim.
- Rollback: a single revert of the merge commit restores prior behavior. Plans created meanwhile keep their checked boxes, which is harmless history.

## Risks

- **Stale record:** a controller forgets to flip boxes while work proceeds. Treatment: the final-acceptance check blocks synchronization and integration until the record is reconciled.
- **Reviewer-evidence pollution:** plan edits land uncommitted and enter reviewer diffs. Treatment: the per-task tracking commit lands immediately at the completion gate.
- **Approval-invalidation ambiguity:** the invalidation and version-creation rules read literally against any edit. Treatment: the exemption is explicit in the feature spec and in the Review Accounting section, scoped to controller progress-tracking flips only, and names every clause it amends.
- **Commit noise:** one extra small commit per task. Accepted by operator decision; the commit message convention keeps the history self-describing.

## Assumptions

- Plan documents keep standard markdown task-list syntax, `- [ ]` and `- [x]`.
- The controller runs in a context that can edit and commit the plan file inside the execution worktree.

## Unresolved Decisions

None.
