---
name: using-superpowers
description: Use when implementing new features or applications, or starting complex multi-step tasks that benefit from structured workflows (brainstorming, TDD, debugging). NOT for simple questions or straightforward operations.
---

**Subagents:** If a controller dispatched you as a subagent to execute a specific task, skip this skill.

If a skill can apply to your task, even at 1% probability, read its `SKILL.md` before you act. Then follow it. If the skill does not apply, discard it. Continue with your task.

## Simple Operations — No Skill Needed

Do NOT invoke skills or dispatch subagents for operations that are fast and carry no risk of errors:

- Reading 1-3 files to understand code, configuration, or output
- Making a single edit to a file
- Running a simple command (for example: ls, grep, find, git status)
- Answering a question based on information you already have
- Searching the codebase for a string or pattern
- Inspecting test output or error logs.

**Editing discipline:** make targeted edits. Do not rewrite whole files to change a few lines. If an edit does not apply, fix the search text. Then retry the edit. Do not rewrite the full file instead.

These are tool calls, not tasks. Dispatch subagents only for work that is:

- **Multi-step:** 3+ distinct actions with judgment between them
- **Substantive:** implementation, debugging, or design decisions
- **Risk-bearing:** incorrect work can introduce bugs
- **Time-consuming:** more than a few tool calls

Never dispatch a subagent and then do the same read or command yourself. The dispatch replaces your tool calls for that work.

## Instruction Priority

1. **User's explicit instructions** (AGENTS.md, direct requests): highest priority.
2. **Superpowers skills**: override default system behavior where they conflict.
3. **Default system prompt**: lowest priority.

## Writing Standard

Write all developer-facing text per the writing-developer-facing-text skill. Use pragmatic mode. This text includes documentation, specs, plans, docstrings, code comments, commit message bodies, error and log messages, and reports to the user. Short sentences. Imperative procedures, with the condition before the command. Banned modals: should, would, may, might, could. Use "check" as the only verb for verification. Identifiers, code, and quoted messages stay exact. Language tooling rules for doc comments override style rules. Read the writing-developer-facing-text SKILL.md before you write or rewrite a long document.

## How Skills Work

Tau initially places only the name, description, and path of each skill in the system prompt. Users can invoke a skill explicitly with `/skill:<name>`. Resolve supporting files relative to the skill directory.

The `task` tool handles subagent dispatch (see [`references/tau-tools.md`](references/tau-tools.md)). A child does not inherit this conversation, so every delegated task must be self-contained.

## Workflow Depth

Before you route a task, select its workflow depth from repository evidence. Run this procedure in order. Select a provisional depth before any proposal work starts.

### Minimal Evidence Pass

Run a minimal evidence pass over the repository first. The pass identifies the domain status and the known or unresolved status of every High-risk trigger below. The domain status is one of: a domain with a living spec, an existing undocumented domain, or a genuinely new domain.

A behavioral domain is one named subject area whose current behavior belongs in one living spec.

### Direct Test

A change is Direct only when established facts show all of these conditions:

- The change alters representation without altering program or controlled-document meaning.
- The change has no behavioral, contract, data, security, privacy, operational, or controlled-document effect.
- The change requires no design decision.

A controlled document defines required or current behavior, workflow policy, acceptance, or operations. Proposals, feature specs, plans, living specs, policies, and runbooks are controlled documents.

### High-risk Triggers

A non-Direct change is High-risk when it affects any of these areas:

- An external contract or compatibility commitment that consumers rely on.
- A schema, stored-data migration, or data recovery procedure.
- Security, privacy, authentication, authorization, or secrets.
- Concurrency, distributed consistency, or race safety.
- Runtime event ordering or data ordering whose failure affects observable behavior, safety, consistency, or integrity.
- A destructive or irreversible action.
- Production availability or compliance.
- A rollback that needs a coordinated rollback across components or cannot use a safe revert.

Runtime or data ordering is High-risk only when an ordering failure affects observable behavior, safety, consistency, or integrity. Workflow gate ordering alone does not activate the High-risk ordering trigger.

### Bounded Conditions

When classification facts are resolved and no High-risk trigger applies, a non-Direct change is Bounded only when all of these pre-plan conditions hold:

- The change affects one domain: one behavioral domain whose current behavior belongs in one living spec.
- The baseline has no material discrepancy between evidence sources.
- The change needs no coordination across a runtime or deployment boundary, consumer, producer, external service, or operational process.
- A single safe revert restores the prior state without migration or recovery work.
- The change has one cohesive responsibility.

Coordination includes the workflow's own stage order. A change that reorders or re-wires the workflow's own gates, artifacts, or handoffs coordinates across an operational process. It is therefore not Bounded; classify it as Standard unless a High-risk trigger applies.

### Standard Default and Escalation

Every other non-Direct change is Standard. The depth escalation order is Direct, Bounded, Standard, then High-risk. The highest applicable level wins.

- Any unresolved fact about a High-risk trigger selects provisional High-risk until evidence resolves the fact.
- Assign every other unresolved fact its least-escalating value for base-level calculation. All unresolved non-High-risk facts then cause one aggregate escalation of one level, capped at High-risk. Multiple facts do not cause multiple escalations.
- File count, line count, and future implementation-plan task count do not increase the provisional depth.
- An operator-selected higher level requires proposal content for that level before approval.

Reassess the depth when classification evidence changes. Do not add reassessments when no evidence changes.

### Route by Verified State

Artifact paths do not prove state completion. Check the exact review and approval status of each required artifact version before you route work onward. The gate matrix defines the required reviews and approvals for each depth:

| Gate | Direct | Bounded | Standard | High-risk |
| --- | --- | --- | --- | --- |
| Baseline and classification | Minimal evidence and Direct test | Concise relevant baseline in proposal | Complete relevant baseline and impact | Standard content plus applicable compatibility, migration, rollout, rollback, observability, recovery, and risk treatment |
| Proposal | None | Concise complete proposal, one cold review, operator approval | Complete proposal and impact, one cold review, operator approval | Standard proposal plus every High-risk category, one cold review, operator approval |
| Feature spec | None | Concise complete spec and one review | Full spec and one review | Full spec and one two-pass review |
| Plan | None | Concise one-to-two-task plan and one review | Full plan and one review | Obligation-mapped plan and one review |
| Execution | Targeted edit and relevant checks | Inline execution of one or two tasks | Per-task implementation and review | Mapped evidence plus per-task implementation and review |
| Final acceptance | Relevant repository checks | One final whole-change review and fresh verification | One final whole-change review and fresh verification | One two-pass final review, acceptance checks, and fresh verification |
| Living-spec synchronization and integration | None | Synchronize, check, then integrate | Synchronize, check, then integrate | Synchronize, check, then integrate after final-review approval |

## The Flow

Select the workflow depth first (see Workflow Depth). Then invoke relevant or requested skills BEFORE any response or action. Announce each one: "Using [skill] to [purpose]".

```
IF it is a simple operation (list above):
    do it directly — no skill, no subagent
ELSE IF the Direct test passes (see Workflow Depth):
    make the targeted edit and run the relevant repository checks
    Direct work creates no proposal, feature spec, or plan
ELSE IF any skill can apply (even 1%):
    read its SKILL.md
    announce: "Using [skill] to [purpose]"
    if it has a checklist, create task tracking per item
    follow the skill exactly
ELSE:
    respond (including clarifications)
```

For non-Direct work, brainstorming applies the proposal, feature-spec, plan, execution, and final-acceptance gates from the matrix.

## Skill Priority

When multiple skills can apply:

1. **Process skills first** (brainstorming, systematic-debugging): they determine HOW to approach the task.
2. **Implementation skills second** (domain-specific): they guide execution.

"Let's build X" → brainstorming first, then implementation skills.
"Fix this bug" → systematic-debugging first, then domain-specific skills.

**What counts as "already brainstormed":** brainstorming is complete when the exact current proposal version holds cold-review approval and operator approval, and the derived feature spec holds spec-review approval. Artifact paths do not prove state completion. Check the exact review and approval status of each artifact version. A conversation about the idea is not brainstorming. If the state is incomplete for a non-Direct change, invoke brainstorming. Do this even if you already discussed the idea at length.
