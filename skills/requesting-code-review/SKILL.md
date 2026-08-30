---
name: requesting-code-review
description: Use when completing a task or major feature, or before merging, to check work against requirements
---

# Requesting Code Review

Dispatch a read-only reviewer subagent with exact context: the diff, the verification output, the requirements, and every relevant file path.

**Core principle:** Review early, review often.

See the [Tau `task` tool reference](../using-superpowers/references/tau-tools.md) for the call schema and result contract.

## When to Request Review

**Mandatory:**
- After each task in subagent-driven development (via the implementation reviewer)
- At executing-plans checkpoints
- After completing a major feature
- Before merging to the default branch

**Optional but valuable:**
- When stuck (fresh perspective)
- Before refactoring (baseline check)
- After fixing a complex bug

## How to Request

**1. Collect the diff and verification output:**

```bash
BASE_SHA=$(git rev-parse HEAD~1)  # or origin/main, or the checkpoint's start
HEAD_SHA=$(git rev-parse HEAD)
git diff "$BASE_SHA".."$HEAD_SHA"
```

**2. Choose the template:**

- Plan-driven work (a feature spec exists): use `../subagent-driven-development/implementation-reviewer-prompt.md` for one pass that covers spec compliance and code quality
- Ad-hoc work (no feature spec): use `code-reviewer.md` in this directory to check code quality against the stated requirements

**3. Fill the template and dispatch** with the `task` tool: `agent: "code-review"`, `task: <filled prompt>` (call schema: `../using-superpowers/references/tau-tools.md`).

Embed the complete diff, verification output, and every relevant file path. The result content is the complete final message of the reviewer: the strict `## Code Review` report (verdict + findings) that ends in the status line.

**4. Act on feedback:**

Before you act on any finding, adjudicate every finding per `receiving-code-review`. Then:

- Send endorsed Critical and Important findings to dispatched fix subagents
- Apply endorsed Minor findings through the same fix path, or note them for later and record each deferral
- Send rejected findings back to the reviewer for confirmation

## Red Flags

**Never:**
- Skip review because "it's simple"
- Proceed with unfixed Critical or Important issues
- Argue with valid technical feedback

## Integration

- **subagent-driven-development**: per-task and final reviews use the implementation reviewer template
- **executing-plans**: checkpoint review after each batch of tasks
- **Ad-hoc**: before a merge, when stuck
