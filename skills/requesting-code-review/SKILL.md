---
name: requesting-code-review
description: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
---

# Requesting Code Review

Dispatch read-only subagent to catch issues before they cascade. The reviewer gets precisely crafted context for evaluation — never your session's history. This keeps the reviewer focused on the work product, not your thought process, and preserves your own context for continued work.

**Core principle:** Review early, review often.

See the [Tau `Task` tool reference](../using-superpowers/references/tau-tools.md) for the complete argument, isolation, approval, and result contract.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development
- After completing major feature
- Before merge to main

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing complex bug

## How to Request

**1. Get the git diff (the read-only agent cannot run commands):**

```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main
HEAD_SHA=$(git rev-parse HEAD)
DIFF_OUTPUT=$(git diff "$BASE_SHA".."$HEAD_SHA")
```

**2. Dispatch the code reviewer:**

Read `code-reviewer.md`, fill its placeholders, and embed the complete diff, verification output, and paths of modified files in the delegated prompt. Then call the capitalized Tau `Task` tool with this argument shape:

```json
{
  "agent": "read-only",
  "task": "Review the named modified files for code quality.\n\n## Modified Files\n[LIST EVERY FILE THE REVIEWER MAY NEED TO READ]\n\n## Git Diff\n[PASTE DIFF_OUTPUT]\n\n## Verification Output\n[PASTE TEST, LINT, AND TYPE-CHECK OUTPUT]\n\n## Context\nWHAT_WAS_IMPLEMENTED: [WHAT YOU BUILT]\nPLAN_OR_REQUIREMENTS: [WHAT IT SHOULD DO]\nDESCRIPTION: [BRIEF SUMMARY]\n\nRead the named files for full context, then return the required review format."
}
```

Replace every bracketed placeholder before dispatch. Do not ask the child to run commands or discover paths: the enforced read-only profile permits only Tau's `read` tool. The policy blocks state-changing Tau tools but is not an OS, filesystem, network, credential, model, or provider sandbox.

**3. Act on feedback:**
- Fix Critical issues immediately
- Fix Important issues before proceeding
- Note Minor issues for later
- Push back if reviewer is wrong (with reasoning)

## Example

```
[Just completed Task 2: Add verification function]

You: Let me request code review before proceeding.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)
DIFF_OUTPUT=$(git diff "$BASE_SHA".."$HEAD_SHA")

[Call `Task` with `agent: "read-only"`; include the complete diff, verification output, requirements, and modified-file paths in `task`]
  WHAT_WAS_IMPLEMENTED: Verification and repair functions for conversation index
  PLAN_OR_REQUIREMENTS: Task 2 from docs/plans/deployment-plan.md
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types

[Subagent returns]:
  Strengths: Clean architecture, real tests
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

You: [Fix progress indicators]
[Continue to Task 3]
```

## Integration with Workflows

**Subagent-Driven Development:**
- Review after EACH task
- Catch issues before they compound
- Fix before moving to next task

**Executing Plans:**
- Review after each batch (3 tasks)
- Get feedback, apply, continue

**Ad-Hoc Development:**
- Review before merge
- Review when stuck

## Red Flags

**Never:**
- Skip review because "it's simple"
- Ignore Critical issues
- Proceed with unfixed Important issues
- Argue with valid technical feedback

**If reviewer wrong:**
- Push back with technical reasoning
- Show code/tests that prove it works
- Request clarification

See template: [`code-reviewer.md`](code-reviewer.md)
