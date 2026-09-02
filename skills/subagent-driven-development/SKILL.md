---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

Execute the plan by dispatching a fresh implementer subagent per task. Then dispatch a single review subagent per task that checks spec compliance and code quality in one pass.

**Announce at start:** "Using subagent-driven-development to execute this plan."

**Operating rules:**

- Subagents do not inherit this conversation. Every dispatch must be self-contained: full task text, file paths, context, expected report format
- There is no mid-task conversation. A subagent reports DONE, DONE_WITH_CONCERNS, BLOCKED, or NEEDS_CONTEXT. You re-dispatch with a new complete prompt
- Dispatch with the `task` tool: the `implementation` agent for implementers, the `code-review` agent for reviewers. Unless the user requests an override, omit `provider`, `model`, and `reasoningEffort`
- Call schema and result contract: [`../using-superpowers/references/tau-tools.md`](../using-superpowers/references/tau-tools.md)

## When to Use

```
IF the workflow depth is Bounded (one or two cohesive tasks, approved at that depth):
    executing-plans (inline execution)
ELSE IF the workflow depth is Standard or High-risk:
    subagent-driven-development, regardless of task count
ELSE IF no implementation plan exists:
    brainstorm first, or execute manually
ELSE IF tasks are tightly coupled:
    manual execution
```

Route by workflow depth, never by task count. The selected depth comes from the approved proposal and the using-superpowers depth procedure.

## Artifact-Derived Dispatches

Every implementer dispatch derives controlled design context only from the exact approved proposal, the reviewed feature spec, and the reviewed plan task. The dispatch carries the artifact identities (commit hash or content digest) and may add repository facts, file paths, diffs, command output, and logs — labeled as evidence that cannot select a controlled decision.

A controller never introduces or resolves intent, behavior, scope, binding architecture, thresholds, exceptions, constraints, assumptions, risk treatment, or operator-visible outcomes only inside a child prompt:

- If an implementer reports a missing or conflicting controlled decision, stop implementation. Repair the owning upstream artifact through proposal change control, then re-derive the affected artifacts and re-dispatch.
- If the missing information is operational evidence (test output, log lines, file locations) that selects no controlled outcome, include it in a new complete dispatch. No approval cycle is required.
- When in doubt about whether evidence selects a controlled outcome, treat it as controlling and return it upstream.

## The Process

1. Read the plan once. Extract every task with its full text and its proposal constraints. Create task tracking.
2. Per task:
   a. Dispatch the implementer (`./implementer-prompt.md`) with the approved proposal identity and content, the reviewed feature spec, the full plan-task text, and the artifact identities
   b. Handle the reported status (below)
   c. Check the implementer report: tests ran and pass, work committed, self-review done
   d. Dispatch the implementation reviewer (`./implementation-reviewer-prompt.md`). Give it the full feature-spec text, the approved proposal content, the task text, and the implementer report. Also give it every relevant file path, the artifact identities, the diff, and the verification output
   e. The reviewer reports on two dimensions: **Spec Compliance** and **Code Quality**. Before you act on any finding, adjudicate every finding per `receiving-code-review`. If adjudication endorses findings, re-dispatch the implementer. The re-dispatch carries the original task, the current state, and only the endorsed findings. Then re-dispatch the reviewer with the updated evidence, the rejected findings, and the rejection reasons. Repeat until both pass
   f. Mark the task complete
3. After the last task: dispatch the implementation reviewer over the entire change. The final review checks the FULL feature spec AND the approved proposal: observable behavior against the spec; scope, binding architecture, constraints, non-goals, acceptance, and risk treatment against the proposal. For High-risk work, the final reviewer performs a contract pass and a risk pass and reports one verdict. Missing mapped High-risk evidence blocks final approval. Per-task reviews check only their own task. Before you act on any finding, adjudicate every finding per `receiving-code-review`. Endorsed findings go to dispatched fix subagents
4. Invoke finishing-a-development-branch

## Handling Implementer Status

**DONE:** Proceed to review.

**DONE_WITH_CONCERNS:** Read the concerns. If they affect correctness or scope, resolve them before review. If they are observations, note them. Then proceed.

**NEEDS_CONTEXT:** First classify what is missing:

- A controlled decision (behavior, threshold, exception, constraint, architecture) is absent from or conflicts with the approved artifacts → stop implementation. Repair the owning upstream artifact through proposal change control, then re-derive and re-dispatch. Do not answer the decision in the redispatch.
- Operational evidence (command output, file locations, log lines) that selects no controlled outcome is missing → obtain it and re-dispatch with a complete prompt. No approval cycle is required.

**BLOCKED:** Assess the blocker. If context is missing, apply the NEEDS_CONTEXT rule above. If the task is oversized, split it. If the plan itself is wrong, escalate to the user.

Never re-dispatch a stuck implementer with no changes, because a plain restart is not a fix.

## Review Inputs

| Input | Role |
|-------|------|
| **Feature spec** (full text, REQUIRED) | The behavioral contract: is every relevant ADDED requirement present, every MODIFIED reflected, every REMOVED gone, and nothing extra built |
| **Approved proposal** (content + identity, REQUIRED) | Design and scope contract: intent, binding architecture, constraints, non-goals, acceptance, risk treatment |
| **Reviewed plan** (task text per task; full task list for the final review) | What this task was asked to do, with its proposal constraints |
| **Artifact identities** (REQUIRED) | Commit hash or digest binding each review to its exact inputs |
| **Implementer report + file paths + diff + verification output** | Evidence |

**Per-task scope:** A single spec requirement can span several tasks. The per-task reviewer checks "did this task implement what was asked", not "is the full requirement satisfied". The final review checks full-spec and proposal compliance.

## Review Accounting

- One initial reviewer dispatch covers one implementation version against one complete input set and one review task. Do not dispatch duplicate initial reviews with identical inputs.
- An artifact or implementation change creates a new version and receives one new complete initial review.
- Added context after `BLOCKED` or `NEEDS_CONTEXT` changes the inputs and permits one new complete initial review.
- An unchanged rejected-finding confirmation is a targeted adjudication redispatch to the same reviewer profile. It carries only the rejected findings and their reasons. It does not repeat a complete review.
- A format-only correction to a derived artifact stays in its automated review loop when it cannot change meaning. A correction that can change meaning, or any approved-proposal edit, goes through proposal change control.

**Spec discrepancies:** If the reviewer reports a mismatch between code and feature spec, decide:

- (a) Fix the code: the spec is correct but the implementation is wrong
- (b) Update the feature spec: the implementation is correct but the spec was incomplete or wrong. After a spec update, re-check that every requirement still has a task with tests. Then re-review

If the mismatch involves a controlled decision (behavior, constraint, architecture), apply proposal change control instead of choosing locally.

## Example Task Cycle

```
[Dispatch task with agent: 'implementation' and the filled implementer prompt]
Implementer: DONE — implemented X, 5/5 tests passing, committed

[Dispatch task with agent: 'code-review' and the filled implementation reviewer prompt]
Reviewer:
  ## Code Review
  Verdict: Needs fixes
  ### Spec Compliance — ❌ missing progress reporting (spec requires it)
  ### Code Quality — Important: magic number at reporter.py:42
  **Status: DONE_WITH_CONCERNS**

[Adjudicate the findings per receiving-code-review: both endorsed]

[Re-dispatch implementer with the original task, current state, and endorsed findings]
Implementer: DONE — added progress reporting, extracted PROGRESS_INTERVAL

[Re-dispatch reviewer with updated diff]
Reviewer: Verdict Approved; both dimensions clean

[Mark task complete]
```

## Red Flags

**Never:**
- Implement on the default branch: work happens on the branch/worktree created during brainstorming
- Dispatch implementers in parallel (they share the working tree)
- Make a subagent read the plan file. Provide the full task text instead
- Answer a missing controlled decision only inside a dispatch prompt: repair the upstream artifact through proposal change control
- Dispatch duplicate initial reviews of the same implementation version, inputs, and review task
- Skip the per-task review or the final review
- Proceed while either review dimension has open findings
- Start the next task before both dimensions pass
- Re-dispatch a stuck implementer unchanged
- Fix a failed task yourself. Instead, dispatch a fix subagent with specific instructions
- Accept "close enough" on spec compliance

## Integration

- **using-git-worktrees**: the workspace, created during brainstorming
- **writing-plans**: creates the plan this skill executes
- **test-driven-development**: the implementer prompt embeds its discipline. Subagents cannot invoke skills, so the prompts carry the required behavior
- **requesting-code-review**: ad-hoc reviews outside the plan workflow
- **finishing-a-development-branch**: after the final review passes
