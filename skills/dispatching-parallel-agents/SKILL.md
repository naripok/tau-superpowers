---
name: dispatching-parallel-agents
description: Use when facing 2+ independent substantive tasks with no shared state or sequential dependencies
---

# Dispatching Parallel Agents

## Overview

You delegate tasks to specialized agents with isolated context. Craft their instructions and context precisely, so that they stay focused and succeed at their task. They must never inherit your session's context or history — you construct exactly what they need.

**Core principle:** Dispatch one agent per independent problem domain. Let them work concurrently.

See the [Tau `task` tool reference](../using-superpowers/references/tau-tools.md) for the complete argument, scope, approval, isolation, and result contract.

## When to Use

**Use when:**
- 3+ test files failing with different root causes
- Multiple subsystems broken independently
- You can understand each problem without context from the others
- No shared state between investigations

**Do not use when:**
- Failures are related — fixing one can fix the others
- Understanding requires seeing the entire system
- Agents can interfere with each other (same files, same resources)
- Exploratory debugging — you do not know what is broken yet
- Simple operations, or work completable in 1-2 tool calls — do it yourself (see using-superpowers)

## The Pattern

### 1. Identify Independent Domains

Group failures by what is broken:
- File A tests: Tool approval flow
- File B tests: Batch completion behavior
- File C tests: Abort functionality

Each domain is independent - fixing tool approval does not affect abort tests.

### 2. Create Focused Agent Tasks

Each agent gets one focused, self-contained prompt: specific scope, clear goal, constraints, expected output (see Agent Prompt Structure below).

### 3. Dispatch in Parallel

Call the Tau `task` tool once, with all tasks in one `tasks` array (call schema: `../using-superpowers/references/tau-tools.md`). Children run concurrently — at most four at a time — and results keep input order:

```json
{
  "tasks": [
    {
      "agent": "general-purpose",
      "task": "Fix agent-tool-abort.test.ts failures. Stay within this test domain and return a summary of the root cause, files changed, and tests run."
    },
    {
      "agent": "general-purpose",
      "task": "Fix batch-completion-behavior.test.ts failures. Stay within this test domain and return a summary of the root cause, files changed, and tests run."
    },
    {
      "agent": "general-purpose",
      "task": "Fix tool-approval-race-conditions.test.ts failures. Stay within this test domain and return a summary of the root cause, files changed, and tests run."
    }
  ]
}
```

### 4. Review and Integrate

When agents return:
- Read each input-ordered summary and inspect `details.results` for status or process failures
- Resolve `DONE_WITH_CONCERNS`, `BLOCKED`, and `NEEDS_CONTEXT` explicitly. If an agent needs more context, re-dispatch it with a complete prompt
- Check that fixes do not conflict
- Run the full test suite
- Spot check the changes — agents can make systematic errors
- Integrate all changes

## Agent Prompt Structure

Good agent prompts are:
1. **Focused** - One clear problem domain
2. **Self-contained** - All context needed to understand the problem
3. **Specific about output** - What the agent must return

```markdown
Fix the 3 failing tests in src/agents/agent-tool-abort.test.ts:

1. "should abort tool with partial output capture" - expects 'interrupted at' in message
2. "should handle mixed completed and aborted tools" - fast tool aborted instead of completed
3. "should properly track pendingToolCount" - expects 3 results but gets 0

These are timing/race condition issues. Your task:

1. Read the test file and understand what each test checks
2. Identify root cause - timing issues or actual bugs?
3. Fix by:
   - Replacing arbitrary timeouts with event-based waiting
   - Fixing bugs in abort implementation if found
   - Adjusting test expectations if testing changed behavior

Do NOT just increase timeouts - find the real issue.

Return: Summary of what you found and what you fixed.
```

## Common Mistakes

**❌ Too broad:** "Fix all the tests" - agent gets lost
**✅ Specific:** "Fix agent-tool-abort.test.ts" - focused scope

**❌ No context:** "Fix the race condition" - the agent does not know where
**✅ Context:** Paste the error messages and test names

**❌ No constraints:** The agent can refactor everything
**✅ Constraints:** "Do NOT change production code" or "Fix tests only"

**❌ Vague output:** "Fix it" - you do not know what changed
**✅ Specific:** "Return summary of root cause and changes"
