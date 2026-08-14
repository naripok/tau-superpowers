# Pi Tool Mapping

Skills use a `Task` tool to dispatch subagents. In pi, this is provided by the `superpowers-subagent` extension.

## Task Tool API

The `Task` tool dispatches a subagent with isolated context. It supports three modes:

### Single mode (one agent, one task)
```
Task({
  agent: "general-purpose",
  task: "Implement the caching layer as described in...",
  cwd: "/path/to/worktree"
})
```

### Parallel mode (multiple agents, concurrent execution)
```
Task({
  tasks: [
    { agent: "general-purpose", task: "Fix test failures in auth module" },
    { agent: "general-purpose", task: "Fix test failures in batch module" },
  ]
})
```

### Chain mode (sequential with output passing)
```
Task({
  chain: [
    { agent: "general-purpose", task: "Investigate the authentication code and return structured findings" },
    { agent: "general-purpose", task: "Based on the following context, create an implementation plan:\n\n{previous}" },
    { agent: "general-purpose", task: "Implement this plan:\n\n{previous}" },
  ]
})
```

## Agent Types

| Agent | Tools | Use For |
|-------|-------|---------|
| `general-purpose` | All tools | Implementation, scouting, exploration, general tasks |
| `read-only` | read, grep, find, ls | Code review, spec review, analysis (cannot modify files or run commands — truly read-only) |

## Model Selection

By default, subagents use `vllm/qwen3.6-27b` (local). The `model` parameter can override this, but **do not set it without explicit user approval** — suggest stronger models for complex tasks but let the user decide.

```
Task({
  agent: "general-purpose",
  task: "...",
  model: "openrouter/anthropic/claude-sonnet-4"  // Only when user approves
})
```

## Status Reporting

Subagents report their status in the tool result. Handle each:

- **DONE** — Proceed to next step
- **DONE_WITH_CONCERNS** — Read concerns, decide whether to proceed
- **BLOCKED** — Provide more context or re-dispatch with stronger model
- **NEEDS_CONTEXT** — Provide missing information and re-dispatch

## Skill-to-Task Mapping

| Skill instruction | Pi Task call |
|---|---|
| `Task tool (general-purpose)` with prompt | `Task({ agent: "general-purpose", task: prompt })` |
| `Task tool (code-reviewer)` with template | `Task({ agent: "read-only", task: filled_template })` |
| Dispatch implementer subagent | `Task({ agent: "general-purpose", task: implementer_prompt })` |
| Dispatch spec reviewer subagent | `Task({ agent: "read-only", task: spec_reviewer_prompt })` |
| Dispatch code quality reviewer subagent | `Task({ agent: "read-only", task: code_quality_reviewer_prompt })` |
| Dispatch parallel agents | `Task({ tasks: [...] })` |

## Read-Only Agent and Git Diffs

The `read-only` agent has no bash access — it can only use read, grep, find, and ls. This means it cannot run `git diff` itself.

**When dispatching a read-only reviewer that needs to see code changes:**
1. The controller runs `git diff` (or `git diff <base>..<head>`) itself before dispatching the reviewer
2. The controller includes the diff output in the reviewer's task prompt
3. The reviewer reads the files mentioned in the diff for full context

Example:
```
// Controller runs this first:
// bash: git diff abc123..def456

// Then dispatches:
Task({
  agent: "read-only",
  task: `Review the following changes for code quality.

## Git Diff
${diffOutput}

Read the modified files for full context, then review.`
})
```

## Key Differences from Claude Code

- **No bidirectional communication**: Subagents cannot ask questions mid-task. If a subagent returns NEEDS_CONTEXT, provide context and re-dispatch.
- **Subagents run with `--no-skills`**: Include all behavioral instructions (TDD steps, self-review checklist, status reporting) in the task prompt.
- **Status is in the tool result**: Parse status from the subagent's output, not from a separate mechanism.
- **Read-only agent has no bash**: If a reviewer needs `git diff` output, the controller must provide it in the task prompt.
- **Review loops are sequential Task calls**, not chain mode: Use chain mode only for unconditional pipelines (scout → planner → worker). For conditional loops (implement → review → fix if needed → re-review), make individual Task calls from the controller.
