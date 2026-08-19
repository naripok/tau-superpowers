---
name: using-superpowers
description: Use when implementing new features or applications, or starting complex multi-step tasks that may benefit from structured workflows like brainstorming, TDD, or debugging. NOT for simple questions or straightforward operations.
---

**Subagents:** If you were dispatched as a subagent to execute a specific task, skip this skill.

If a skill might apply to what you are doing — even at 1% probability — read its `SKILL.md` before acting and follow it. If it turns out not to apply, discard it and proceed.

## Simple Operations — No Skill Needed

Do NOT invoke skills or dispatch subagents for operations that are trivially fast and carry no risk of errors:

- Reading 1-3 files to understand code, configuration, or output
- Making a single edit to a file
- Running a simple command (ls, grep, find, git status, etc.)
- Answering a question based on information you already have
- Searching the codebase for a string or pattern
- Inspecting test output or error logs

These are tool calls, not tasks. Dispatch subagents only for work that is:

- **Multi-step:** 3+ distinct actions with judgment between them
- **Substantive:** implementation, debugging, or design decisions
- **Risk-bearing:** could introduce bugs if done incorrectly
- **Time-consuming:** more than a handful of tool calls

## Instruction Priority

1. **User's explicit instructions** (AGENTS.md, direct requests) — highest priority
2. **Superpowers skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

## How Skills Work

Tau initially places only each skill's name, description, and path in the system prompt. When a skill applies, read its `SKILL.md` before acting and follow its instructions. Users can invoke one explicitly with `/skill:<name>`. Resolve supporting files relative to the skill directory.

Subagent dispatch is handled by the `task` tool (see [`references/tau-tools.md`](references/tau-tools.md)). A child does not inherit this conversation, so every delegated task must be self-contained.

## The Flow

Invoke relevant or requested skills BEFORE any response or action. Announce each one: "Using [skill] to [purpose]".

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "Building something new?" [shape=doublecircle];
    "Proposal + feature spec exist?" [shape=diamond];
    "Invoke brainstorming skill" [shape=box];
    "Simple operation?" [shape=diamond];
    "Might any skill apply?" [shape=diamond];
    "Read SKILL.md" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create task tracking per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Do it directly" [shape=box, style=filled, fillcolor=lightgreen];
    "Respond (including clarifications)" [shape=doublecircle];

    "Building something new?" -> "Proposal + feature spec exist?";
    "Proposal + feature spec exist?" -> "Invoke brainstorming skill" [label="no — artifacts missing"];
    "Proposal + feature spec exist?" -> "Simple operation?" [label="yes — artifacts exist"];
    "Invoke brainstorming skill" -> "Simple operation?";

    "User message received" -> "Simple operation?";
    "Simple operation?" -> "Do it directly" [label="yes"];
    "Simple operation?" -> "Might any skill apply?" [label="no"];
    "Might any skill apply?" -> "Read SKILL.md" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Read SKILL.md" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Create task tracking per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create task tracking per item" -> "Follow skill exactly";
}
```

## Skill Priority

When multiple skills could apply:

1. **Process skills first** (brainstorming, systematic-debugging) — they determine HOW to approach the task
2. **Implementation skills second** (domain-specific) — they guide execution

"Let's build X" → brainstorming first, then implementation skills.
"Fix this bug" → systematic-debugging first, then domain-specific skills.

**What counts as "already brainstormed":** brainstorming is complete when the proposal (`docs/design/YYYY-MM-DD-<topic>-proposal.md`) and the feature spec (`docs/design/YYYY-MM-DD-<topic>-spec.md`) both exist. A conversation about the idea is not brainstorming. If the artifacts don't exist, invoke brainstorming — even if you've already discussed the idea at length.
