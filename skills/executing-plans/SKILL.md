---
name: executing-plans
description: Use when you have a written implementation plan to execute inline in the current session
---

# Executing Plans

Load the plan. Review it critically. Execute all tasks. When the work is complete, report.

**Announce at start:** "Using executing-plans to implement this plan."

If the plan has 3 or more substantive tasks, use subagent-driven-development instead. If the plan is simple (1-2 tasks or trivial changes), use this skill.

## The Process

### Step 1: Load and Review the Plan

1. Read the plan file
2. Review the plan critically to identify questions or concerns
3. If you have concerns, raise them with your human partner first
4. If you have no concerns, copy the plan checklist into your working notes. Then proceed

### Step 2: Check the Workspace

Work on the feature branch or worktree that you created during brainstorming. Never work directly on the default branch.

```bash
git branch --show-current
```

If you are on the default branch, stop. Create the worktree with using-git-worktrees first.

### Step 3: Execute Tasks

For each task:

1. Mark the task as in_progress
2. Implement the contract of the task with TDD. Write the failing tests for the "Tests must prove" list of the task. Watch each test fail for the expected reason. Implement the interface and the behavior. Refactor. You decide the exact implementation within the contract
3. Run the verification commands of the task
4. Commit
5. Mark the task as completed

### Step 4: Checkpoint Reviews

After every 3 tasks (or at the stated checkpoints of the plan), dispatch a `code-review` subagent over the accumulated diff. Use the template at `../subagent-driven-development/implementation-reviewer-prompt.md`. The template checks spec compliance and code quality in one pass.

Before you act on any finding, adjudicate every finding per `receiving-code-review`. You are the implementer at this checkpoint. Apply endorsed Critical and Important fixes yourself. Apply endorsed Minor findings yourself, or defer them and record each deferral. If adjudication rejects findings, re-dispatch the reviewer with the fixes, the rejected findings, and the rejection reasons. The gate does not continue while endorsed Critical or Important fixes remain unapplied. A maintained Critical finding stops the gate per the escalation section of `receiving-code-review`.

### Step 5: Complete Development

After you complete and check all tasks:

- Announce: "Using finishing-a-development-branch to complete this work."
- **REQUIRED SUB-SKILL:** Use finishing-a-development-branch
- **Report deviations:** in the final implementation summary, report every place where execution changed course from the plan. State the flaw, why the change was needed, and its implications

## When to Stop and Ask for Help

Stop executing immediately when:

- You hit a blocker (missing dependency, failing test, unclear instruction)
- The plan has a critical gap
- Verification fails repeatedly

Ask for clarification rather than guessing. If the fundamental approach is wrong, return to Step 1 with your human partner.

## Integration

- **using-git-worktrees**: workspace setup (created during brainstorming)
- **writing-plans**: creates the plan this skill executes
- **subagent-driven-development**: alternative execution for substantive plans
- **finishing-a-development-branch**: completion after all tasks.
