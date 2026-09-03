# Plan Checkbox Progress Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Mark every checkbox of a task `[x]` in this file when the task completes its gate, and record each flip in one tracking commit named `docs(plan): mark <plan-file-stem> Task N complete`.

**Goal:** Make the plan document the execution progress record: the controller marks each completed task's checkboxes `[x]` and records the flip in one tracking commit, in both execution modes, and final acceptance verifies the record before synchronization.

**Architecture:** Controller-owned checkbox flips at each task's completion gate, one immediate per-task tracking commit, a single-writer plan file during execution, and a meaning-preserving exemption so flips neither invalidate approvals nor create plan versions. `finishing-a-development-branch` gains an all-boxes-checked acceptance check and binds the plan approval to the plan's identity of record.

**Tech Stack:** Bash guidance tests (grep-based cross-file contract assertions over the skill files); Markdown skill documents. No runtime code changes.

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-developer-facing-text prose.

**Feature spec:** `docs/design/2026-09-02-plan-checkbox-tracking-spec.md` (the behavioral contract)

**Approved proposal:** `docs/design/2026-09-02-plan-checkbox-tracking-proposal.md` (intent, scope, binding architecture, constraints, non-goals, acceptance, and risk treatment; the exact operator-approved version: commit `d933a8d`, sha256 `177745324b4190a0e37eeaba365a56c6fc19dc8202dbd0aa53917bfe78cfab90`)

---

## Commands

Run from the repository root (the worktree):

```bash
bash tests/test-plan-execution-guidance.sh
bash tests/test-finishing-workflow-guidance.sh
bash tests/test-proposal-baseline-guidance.sh
bash tests/test-install.sh
bash tests/test-references.sh
```

The first two suites carry the new contracts. The last three are preservation suites: they must stay green throughout.

## Shared Proposal Constraints (apply to every task)

- A checkbox flip changes only checkbox state: no contract text, task text, interface, verification command, or requirement mapping changes.
- The tracking commit convention is `docs(plan): mark <plan-file-stem> Task N complete`, where `<plan-file-stem>` is the plan file's name without extension; the tracking commit contains only that flip, and the implementation commit stays one per task.
- The flip happens only at the completion gate, never before the review passes in dispatch execution; a flipped box never reverts.
- The subagent plan-file prohibition stays intact and extends from reading to editing; the controller is the single plan writer.
- Exactly two checkbox states (`- [ ]`, `- [x]`); no in-progress marker in the plan document; in-progress state lives in the controller's task tracking.
- No workflow gate reordering; no installer changes; no new checkbox syntax.
- Skill text follows writing-developer-facing-text, pragmatic mode: short sentences, imperative, no banned modals (should, would, may, might, could), "check" as the only verification verb.

### Task 1: Execution-mode plan tracking (executing-plans and subagent-driven-development)

**Files:**
- Modify: `skills/executing-plans/SKILL.md` — the plan file becomes the progress record; the in-progress step targets the controller's task tracking; the completion step flips the task's checkboxes and commits one tracking commit
- Modify: `skills/subagent-driven-development/SKILL.md` — step 1 names the plan checkboxes as the tracking record; step 2f defines the flip plus tracking commit; the Red Flags entry extends to read-or-edit; Review Accounting gains the flip exemption
- Test: `tests/test-plan-execution-guidance.sh` — new assertions for both skills in their existing sections; every existing assertion stays

**Spec requirement:** ADDED "Plan checkbox progress tracking" (both completion gates, tracking-commit convention, never-revert, failed-review, flip-preserves-approval), ADDED "Single plan writer during execution" (subagent read/edit prohibition; dispatch supplies task text), ADDED "Two-state plan progress record" (inline in-progress target), and the skill-side surface of MODIFIED "Ordered proposal-baseline state flow" and "Single High-risk two-pass review" (the Review Accounting exemption).

**Proposal constraints:** the Shared Proposal Constraints above all bind this task.

**Interface:**

- `skills/executing-plans/SKILL.md`, Step 1 ("Load and Review the Plan"): the instruction to "copy the plan checklist into your working notes" is removed. In its place the step states that the plan file's checkboxes are the progress record and that the controller marks them there. No other Step 1 content changes.
- `skills/executing-plans/SKILL.md`, Step 3 item 1: "Mark the task as in_progress" now targets the controller's own task tracking, and the plan document records completion only.
- `skills/executing-plans/SKILL.md`, Step 3: a completion step after the commit step defines "mark the task as completed": mark every checkbox of the task `[x]` in the plan file and commit exactly one tracking commit, immediately, with the message `docs(plan): mark <plan-file-stem> Task N complete`, containing only that flip. A flipped box never reverts. The existing items (TDD, verification, one implementation commit per task, commit step) stay.
- `skills/executing-plans/SKILL.md`, Step 4: one added sentence: the dispatched final reviewer receives the feature spec, the approved proposal, the evidence, and the diff in its dispatch, and neither reads nor edits the plan file.
- `skills/subagent-driven-development/SKILL.md`, step 1: after the task-extraction sentence, the step states that the plan file's checkboxes are the progress record (completion only), that the controller's own task tracking keeps in-progress state, and that the controller flips a completed task's checkboxes in the plan file (see step 2f).
- `skills/subagent-driven-development/SKILL.md`, step 2f: "Mark the task complete" is expanded to: check every checkbox of the task `[x]` in the plan file and commit exactly one tracking commit, immediately, with the message `docs(plan): mark <plan-file-stem> Task N complete`, containing only that flip. A flipped box never reverts. A task whose reviewer returns a needs-fixes verdict keeps unchecked checkboxes and gets no tracking commit until the review passes.
- `skills/subagent-driven-development/SKILL.md`, Red Flags: "Make a subagent read the plan file. Provide the full task text instead" extends to read **or edit**, keeping the provide-full-task-text remedy and adding that the controller is the only plan-file writer during execution.
- `skills/subagent-driven-development/SKILL.md`, Review Accounting: one added bullet: a plan-file checkbox flip that records a completed task is a meaning-preserving tracking edit — it is not a new plan version, triggers no new complete initial review, does not invalidate plan approvals, and is not a changed upstream input: downstream reviews that already approved keep their approvals and no downstream re-review starts. Every other plan edit keeps the full version and re-review rules above.
- `tests/test-plan-execution-guidance.sh`: new assertions in the existing `--- executing-plans` and `--- subagent-driven-development` sections (see "Tests must prove"); the variable set and every existing assertion stay unchanged.

**Behavior:**
- Inline execution: after a Bounded task's implementation commit and verification pass, the plan file shows every checkbox of that task `[x]`, and git history shows exactly one tracking commit for the task with the convention message.
- Dispatch execution: after a task's reviewer approves both dimensions, the controller produces the same flip and tracking commit; a needs-fixes verdict leaves the task's checkboxes unchecked with no tracking commit.
- Subagents never read or edit the plan file; dispatches carry the full task text.
- In-progress state never appears in the plan document.

**Tests must prove:** (one named assertion group per behavior; add to `tests/test-plan-execution-guidance.sh`)
- executing-plans names the plan file as the progress record: `has_all` on `$EP` with patterns for `plan file` + `checkbox` + `progress record|tracking`
- executing-plans dropped the working-notes copy: `lacks` on `$EP` for `copy the plan checklist into your working notes`
- executing-plans completion step flips and commits: `has_all` on `$EP` with patterns for `\[x\]` + `tracking commit` + `docs\(plan\): mark`
- executing-plans in-progress targets task tracking: `has_all` on `$EP` with patterns for `in_progress|in-progress` + `task tracking`
- executing-plans final reviewer plan-file prohibition: `has_all` on `$EP` with patterns for `neither reads nor edits|read or edit` + `plan file`
- executing-plans flip never reverts: `has_all` on `$EP` with patterns for `never` + `revert|un-check|uncheck`
- executing-plans and subagent-driven-development introduce no non-standard checkbox syntax: `lacks` on `$EP` and on `$SDD` for `\[-\]|\[~\]|\[\/\]`
- subagent-driven-development names the plan checkboxes as its tracking record: `has_all` on `$SDD` with patterns for `checkbox` + `tracking`
- subagent-driven-development step 2f flips and commits: `has_all` on `$SDD` with patterns for `\[x\]` + `tracking commit` + `docs\(plan\): mark`
- subagent-driven-development Review Accounting exemption: `has_all` on `$SDD` with patterns for `meaning-preserving` + `re-review|new version|initial review` + `upstream input`
- subagent-driven-development failed review keeps boxes unchecked: `has_all` on `$SDD` with patterns for `needs-fixes|Needs-fixes` + `unchecked|no tracking commit`
- subagent-driven-development flip never reverts: `has_all` on `$SDD` with patterns for `never` + `revert|un-check|uncheck`
- subagent-driven-development single-writer and read-or-edit prohibition: `has_all` on `$SDD` with patterns for `read or edit` + `single writer|only.*writer|only agent`
- Preserved baseline: every pre-existing assertion in the file passes unchanged (the suite exits 0)

**Check:** `bash tests/test-plan-execution-guidance.sh && bash tests/test-proposal-baseline-guidance.sh && bash tests/test-references.sh && bash tests/test-install.sh` — expected: all pass

- [x] Write the failing test assertions above. Run the suite and check each new assertion fails for the expected reason (the skill text does not yet carry the contracts)
- [x] Implement the `executing-plans` and `subagent-driven-development` changes within the contracts above
- [x] Run verification: all four Check commands pass
- [x] Commit: `git add skills/executing-plans/SKILL.md skills/subagent-driven-development/SKILL.md tests/test-plan-execution-guidance.sh && git commit -m "skills: plan checkbox tracking in execution skills"`

### Task 2: Planning and finishing tracking contracts (writing-plans and finishing-a-development-branch)

**Files:**
- Modify: `skills/writing-plans/SKILL.md` — the header template line becomes the operational tracking instruction; the overview line "One commit per task" is reworded to "one implementation commit per task"
- Modify: `skills/finishing-a-development-branch/SKILL.md` — final acceptance gains the all-boxes-checked check and the plan-approval identity-of-record binding
- Test: `tests/test-finishing-workflow-guidance.sh` — new assertions; every existing assertion stays
- Test: `tests/test-plan-execution-guidance.sh` — new assertions in the existing `--- writing-plans` section; every existing assertion stays

**Spec requirement:** ADDED "Two-state plan progress record" (new-plan-header instruction) and MODIFIED "Implementation reviews and final acceptance" (all-boxes-checked check blocks synchronization and integration; plan approval binds to the plan's identity of record).

**Proposal constraints:** the Shared Proposal Constraints above all bind this task.

**Interface:**

- `skills/writing-plans/SKILL.md`, header template blockquote: the sentence "Steps use checkbox (`- [ ]`) syntax for tracking." is replaced by the operational contract: the executor marks every checkbox of a task `[x]` in the plan file when the task completes its gate, and records each flip in one tracking commit named `docs(plan): mark <plan-file-stem> Task N complete`. The rest of the blockquote (the REQUIRED SUB-SKILL line) stays.
- `skills/writing-plans/SKILL.md`, overview paragraph: "One commit per task." becomes "One implementation commit per task." with a short clause that the executor's plan-checkbox tracking commit is separate metadata. Nothing else in the paragraph changes.
- `skills/finishing-a-development-branch/SKILL.md`, Step 1 item 1 (approval identities): the plan's approval attaches to the plan's identity of record, the exact reviewed version — progress-tracking checkbox flips do not stale it. The existing identity checks for the other artifacts stay verbatim.
- `skills/finishing-a-development-branch/SKILL.md`, Step 1: a new check (with the acceptance-examples check, before fresh verification) that the plan document shows every task's checkboxes complete; a plan with unchecked boxes blocks synchronization and integration until the record is reconciled.
- `skills/finishing-a-development-branch/SKILL.md`, Step 1 closing line: "If any required review, acceptance example, or verification command fails" extends to include an incomplete plan progress record.
- `tests/test-finishing-workflow-guidance.sh`: new assertions in the existing sections (see "Tests must prove").
- `tests/test-plan-execution-guidance.sh`: new assertions in the existing `--- writing-plans` section (see "Tests must prove").

**Behavior:**
- A newly written plan's header instructs the executor to mark each task's checkboxes `[x]` in the plan file at task completion and to use the tracking-commit convention.
- Final acceptance verifies the plan record: every task's checkboxes complete; unchecked boxes block synchronization and integration.
- Final acceptance's identity check tolerates progress-tracking flips: the plan approval binds to the exact reviewed version.

**Tests must prove:** (one named assertion group per behavior)
- writing-plans header is operational: `has_all` on `$WP` with patterns for `header|blockquote` context plus `mark` + `\[x\]` + `plan file` + `docs\(plan\): mark` (the template sentence itself satisfies this)
- writing-plans separates the implementation commit from tracking commits: `has` on `$WP` for `[Oo]ne implementation commit per task`
- finishing checks plan checkbox completeness and blocks: `has_all` on `$FIN` with patterns for `checkbox` + `complete|every task` + `block|synchron`
- finishing binds the plan approval to the identity of record: `has_all` on `$FIN` with patterns for `identity of record` + `flip|progress-tracking`
- writing-plans old tracking sentence removed: `lacks` on `$WP` for `Steps use checkbox`
- writing-plans introduces no non-standard checkbox syntax: `lacks` on `$WP` for `\[-\]|\[~\]|\[\/\]`
- Preserved baseline: every pre-existing assertion in both test files passes unchanged (both suites exit 0)

**Check:** `bash tests/test-plan-execution-guidance.sh && bash tests/test-finishing-workflow-guidance.sh && bash tests/test-proposal-baseline-guidance.sh && bash tests/test-references.sh && bash tests/test-install.sh` — expected: all pass

- [x] Write the failing test assertions above. Run both suites and check each new assertion fails for the expected reason
- [x] Implement the `writing-plans` and `finishing-a-development-branch` changes within the contracts above
- [x] Run verification: all five Check commands pass
- [x] Commit: `git add skills/writing-plans/SKILL.md skills/finishing-a-development-branch/SKILL.md tests/test-finishing-workflow-guidance.sh tests/test-plan-execution-guidance.sh && git commit -m "skills: plan checkbox tracking in planning and finishing"`

## Preservation Mapping (unchanged baseline)

- All pre-existing assertions in `tests/test-plan-execution-guidance.sh` and `tests/test-finishing-workflow-guidance.sh` stay and pass (preservation checks; executing-plans keeps its `'commit'`-pattern assertion, and the reworded writing-plans line "One implementation commit per task." still satisfies every writing-plans assertion that checks commit-bearing contract text).
- `tests/test-install.sh`, `tests/test-references.sh`, and `tests/test-proposal-baseline-guidance.sh` stay green (installer, reference scan, and proposal-baseline guidance untouched).
- The dispatch/review prompt templates (`implementer-prompt.md`, `implementation-reviewer-prompt.md`, `plan-document-reviewer-prompt.md`, `living-spec-document-reviewer-prompt.md`) change nothing: dispatches already carry the full task text, and no template directs a subagent to the plan file.
- Living-spec synchronization happens in finishing, not in these tasks: the feature spec is the delta; `docs/specs/workflow-governance.md` is untouched by Tasks 1–2.

## Depth and Task Count

Bounded workflow: two cohesive tasks, executed inline per executing-plans. A required third task stops planning and invokes proposal change control.
