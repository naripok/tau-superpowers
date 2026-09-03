---
name: executing-plans
description: Use when executing an approved Bounded implementation plan inline in the current session
---

# Executing Plans

Execute an approved Bounded workflow inline: one or two cohesive plan tasks, executed by the controller, with one final whole-change review.

**Announce at start:** "Using executing-plans to implement this plan."

## When This Skill Applies

This skill executes only a Bounded workflow: the approved proposal and depth classification selected Bounded, and the reviewed plan contains one or two cohesive tasks. Standard and High-risk work routes to subagent-driven-development, regardless of task count.

Check before you start:

- The proposal holds cold-review and operator approval for its current version.
- The feature spec holds spec-review approval for its current version.
- The plan holds plan-review approval and contains one or two tasks.

If any check fails, or the work is Standard or High-risk, stop and route per the using-superpowers gate matrix.

## The Process

### Step 1: Load and Review the Plan

1. Read the plan file
2. Review the plan critically to identify questions or concerns
3. If you have concerns, raise them with your human partner first
4. If you have no concerns, start execution. The plan file's checkboxes are the progress record: the controller marks them there as tasks complete. Do not copy the checklist into working notes

### Step 2: Check the Workspace

Work on the feature branch or worktree that you created during brainstorming. Never work directly on the default branch.

```bash
git branch --show-current
```

If you are on the default branch, stop. Create the worktree with using-git-worktrees first.

### Step 3: Execute Tasks

For each task:

1. Mark the task as in_progress in your task tracking. The plan document records completion only
2. Implement the contract of the task with TDD. Write the failing tests for the "Tests must prove" list of the task. Watch each test fail for the expected reason. Implement the interface and the behavior. Refactor. You decide the exact implementation within the contract
3. Run the verification commands of the task
4. Commit
5. Mark the task as completed: check every checkbox of the task `[x]` in the plan file, then commit exactly one tracking commit, immediately, with the message `docs(plan): mark <plan-file-stem> Task N complete` that contains only that flip. A flipped box never reverts

### Step 4: Final Whole-Change Review

After the last task and its fresh checks, dispatch one `code-review` subagent over the complete change. Use the template at `../subagent-driven-development/implementation-reviewer-prompt.md` in its **Standard final** scope mode: the full feature spec and the approved proposal are the governing contracts. This skill does not dispatch per-task reviewers; the final whole-change review is the only implementation review. The dispatch supplies the feature spec, the living-spec text for every MODIFIED requirement, the approved proposal, the full task list, the evidence, and the diff; the reviewer subagent neither reads nor edits the plan file.

Before you act on any finding, adjudicate every finding per `receiving-code-review`. You are the implementer at this gate. Apply endorsed Critical and Important fixes yourself. Apply endorsed Minor findings yourself, or defer them and record each deferral. If adjudication rejects findings, re-dispatch the reviewer with the fixes, the rejected findings, and the rejection reasons. The gate does not continue while endorsed Critical or Important fixes remain unapplied. A maintained Critical finding stops the gate per the escalation section of `receiving-code-review`.

### Step 5: Complete Development

After the final review passes:

- Announce: "Using finishing-a-development-branch to complete this work."
- **REQUIRED SUB-SKILL:** Use finishing-a-development-branch
- **Report deviations:** in the final implementation summary, report every place where execution changed course from the plan. State the flaw, why the change was needed, and its implications

## Depth Boundaries

- A required third cohesive task, or planning or implementation evidence of a higher trigger (cross-boundary coordination, migration, security, and similar), stops execution before it starts or continues. Invoke proposal change control: revise, cold-review, and reapprove the proposal, then re-derive the affected artifacts.
- A missing controlled decision during a task follows the proposal change control path: repair the owning upstream artifact. Never answer it only in working notes.

## When to Stop and Ask for Help

Stop executing immediately when:

- You hit a blocker (missing dependency, failing test, unclear instruction)
- The plan has a critical gap
- Verification fails repeatedly

Ask for clarification rather than guessing. If the fundamental approach is wrong, return to Step 1 with your human partner.

## Integration

- **using-git-worktrees**: workspace setup (created during brainstorming)
- **writing-plans**: creates the plan this skill executes; routes Bounded work here
- **subagent-driven-development**: the execution path for Standard and High-risk work
- **finishing-a-development-branch**: completion after the final review.
