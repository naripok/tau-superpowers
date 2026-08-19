---
name: executing-plans
description: Use when you have a written implementation plan to execute inline in the current session
---

# Executing Plans

Load the plan, review it critically, execute all tasks, report when complete.

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

For plans with 3+ substantive tasks, use subagent-driven-development instead. Use this skill for simple plans (1-2 tasks or trivial changes).

## The Process

### Step 1: Load and Review the Plan

1. Read the plan file
2. Review critically — identify questions or concerns about the plan
3. If concerns: raise them with your human partner before starting
4. If no concerns: copy the plan checklist into your working notes and proceed

### Step 2: Verify the Workspace

Implementation happens on the feature branch or worktree created during brainstorming — never directly on the default branch.

```bash
git branch --show-current
```

If you are on the default branch, stop and set up the worktree first (using-git-worktrees).

### Step 3: Execute Tasks

For each task:

1. Mark as in_progress
2. Implement the task's contract with TDD: write the failing tests for the task's "Tests must prove" list, watch each fail for the expected reason, implement the interface and behavior, refactor. The exact implementation within the contract is your decision
3. Run the task's verification commands
4. Commit
5. Mark as completed

### Step 4: Checkpoint Reviews

After every 3 tasks (or at the plan's stated checkpoints), dispatch a `code-review` subagent over the accumulated diff using the template at `../subagent-driven-development/implementation-reviewer-prompt.md` — it checks spec compliance and code quality in one pass. Fix all Critical and Important findings before continuing.

### Step 5: Complete Development

After all tasks complete and verified:

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
