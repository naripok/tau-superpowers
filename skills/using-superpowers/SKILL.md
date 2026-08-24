---
name: using-superpowers
description: Use when implementing new features or applications, or starting complex multi-step tasks that can benefit from structured workflows like brainstorming, TDD, or debugging. NOT for simple questions or straightforward operations.
---

**Subagents:** If a controller dispatched you as a subagent to execute a specific task, skip this skill.

If a skill can apply to what you are doing, even at 1% probability, read its `SKILL.md` before you act. Then follow it. If the skill does not apply, discard it. Continue with your task.

## Simple Operations — No Skill Needed

Do NOT invoke skills or dispatch subagents for operations that are fast and carry no risk of errors:

- Reading 1-3 files to understand code, configuration, or output
- Making a single edit to a file
- Running a simple command (for example: ls, grep, find, git status)
- Answering a question based on information you already have
- Searching the codebase for a string or pattern
- Inspecting test output or error logs

**Editing discipline:** make targeted edits rather than rewriting whole files to change a few lines. If an edit does not apply, fix the search text and retry — do not fall back to a full rewrite.

These are tool calls, not tasks. Dispatch subagents only for work that is:

- **Multi-step:** 3+ distinct actions with judgment between them
- **Substantive:** implementation, debugging, or design decisions
- **Risk-bearing:** incorrect work can introduce bugs
- **Time-consuming:** more than a few tool calls

Never dispatch a subagent and then do the same read or command yourself. The dispatch replaces your tool calls for that work.

## Instruction Priority

1. **User's explicit instructions** (AGENTS.md, direct requests) — highest priority
2. **Superpowers skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

## How Skills Work

Tau initially places only each skill's name, description, and path in the system prompt. Users can invoke a skill explicitly with `/skill:<name>`. Resolve supporting files relative to the skill directory.

The `task` tool handles subagent dispatch (see [`references/tau-tools.md`](references/tau-tools.md)). A child does not inherit this conversation, so every delegated task must be self-contained.

## The Flow

Invoke relevant or requested skills BEFORE any response or action. Announce each one: "Using [skill] to [purpose]".

```
IF building something new AND the proposal + feature spec do not both exist:
    invoke brainstorming first
IF it is a simple operation (list above):
    do it directly — no skill, no subagent
ELSE IF any skill can apply (even 1%):
    read its SKILL.md
    announce: "Using [skill] to [purpose]"
    if it has a checklist, create task tracking per item
    follow the skill exactly
ELSE:
    respond (including clarifications)
```

## Skill Priority

When multiple skills can apply:

1. **Process skills first** (brainstorming, systematic-debugging) — they determine HOW to approach the task
2. **Implementation skills second** (domain-specific) — they guide execution

"Let's build X" → brainstorming first, then implementation skills.
"Fix this bug" → systematic-debugging first, then domain-specific skills.

**What counts as "already brainstormed":** brainstorming is complete when the proposal (`docs/design/YYYY-MM-DD-<topic>-proposal.md`) and the feature spec (`docs/design/YYYY-MM-DD-<topic>-spec.md`) both exist. A conversation about the idea is not brainstorming. If the artifacts do not exist, invoke brainstorming, even if you have already discussed the idea at length.
