---
name: executing-plans
description: Use when you have a written implementation plan to execute inline in the current session
---

# Executing Plans

Load the plan. Review it critically. Execute all tasks. When the work is complete, report.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

For plans with 3+ substantive tasks, use subagent-driven-development instead. Use this skill for simple plans (1-2 tasks or trivial changes).

## The Process

### Step 1: Load and Review the Plan

1. Read the plan file
2. Review critically — identify questions or concerns about the plan
3. If you have concerns, raise them with your human partner first
4. If you have no concerns, copy the plan checklist into your working notes. Then proceed

### Step 2: Verify the Workspace

Work on the feature branch or worktree created during brainstorming. Never work directly on the default branch.

```bash
git branch --show-current
```

If you are on the default branch, stop and set up the worktree first (using-git-worktrees).

### Step 3: Execute Tasks

For each task:

1. Mark the task as in_progress
2. Implement the task's contract with TDD. Write the failing tests for the task's "Tests must prove" list. Watch each test fail for the expected reason. Implement the interface and behavior. Refactor. You decide the exact implementation within the contract
3. Run the task's verification commands
4. Commit
5. Mark the task as completed

### Step 4: Checkpoint Reviews

After every 3 tasks (or at the plan's stated checkpoints), dispatch a `code-review` subagent over the accumulated diff. Use the template at `../subagent-driven-development/implementation-reviewer-prompt.md`. It checks spec compliance and code quality in one pass. Before continuing, fix all Critical and Important findings.

### Step 5: Complete Development

After you complete and check all tasks:

- Announce: "I'm using the finishing-a-development-branch skill to complete this work."
- **REQUIRED SUB-SKILL:** Use finishing-a-development-branch

## When to Stop and Ask for Help

Stop executing immediately when:

- You hit a blocker (missing dependency, failing test, unclear instruction)
- The plan has a critical gap
- Verification fails repeatedly

Ask for clarification rather than guessing. If the fundamental approach is wrong, return to Step 1 with your human partner.

## Integration

- **using-git-worktrees** — workspace setup (created during brainstorming)
- **writing-plans** — creates the plan this skill executes
- **subagent-driven-development** — alternative execution for substantive plans
- **finishing-a-development-branch** — completion after all tasks
