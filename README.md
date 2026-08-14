# pi-superpowers

This is a Frankenstein merge of [obra/superpowers](https://github.com/obra/superpowers) and [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec), along with a `Task` subagent extension. All the skills stripped down and made specific for [pi-coding-agent](https://github.com/badlogic/pi).

What you get as a result is a spec-driven development flow with a living spec that reflects the up-to-date state of the application at any given time, along with a TDD implementation flow with a two-phase review process using sub-agents for context managing and parallel execution.

## Quickstart

```bash
# From a git repo
pi install git:github.com/naripok/pi-superpowers@master

# Or ask pi to install it for you
Install pi-superpowers from github.com/naripok/pi-superpowers
```

## Core Concept: Living Specs

A **living spec** (`docs/specs/<domain>.md`) is a canonical description of how the system _currently_ behaves, organized by domain (auth, notifications, payments, etc.). It is created the first time a feature touches a domain and updated each time subsequent features change that domain's behavior.

The loop:

```
Brainstorming reads the living spec
    → writes proposal + feature spec (behavioral contract)
    → Planning derives delta spec from feature spec vs living spec
    → Implementation follows the plan
    → Finishing syncs the delta into the living spec
```

The living spec is the starting point for every new feature — it tells you what exists before you design what comes next. The feature spec is the behavioral contract — it defines what the system SHALL do before any code is written.

## What's Included

### Skills

| Skill                          | Description                                                  |
| ------------------------------ | ------------------------------------------------------------ |
| brainstorming                  | Explore requirements and design before implementation        |
| dispatching-parallel-agents    | Coordinate independent parallel subagent tasks               |
| executing-plans                | Execute written implementation plans with review checkpoints |
| finishing-a-development-branch | Guide completion and integration of development work         |
| receiving-code-review          | Process code review feedback with verification               |
| requesting-code-review         | Request review before merging or completing work             |
| subagent-driven-development    | Execute implementation plans with isolated subagents         |
| systematic-debugging           | Structured debugging methodology                             |
| test-driven-development        | TDD workflow for features and bugfixes                       |
| using-git-worktrees            | Work with isolated git worktrees                             |
| using-superpowers              | Core skill discovery and invocation protocol                 |
| verification-before-completion | Verify work before claiming completion                       |
| writing-plans                  | Create structured implementation plans                       |
| writing-skills                 | Create and test new pi skills                                |

### Extensions

- **superpowers-subagent** — Registers the `Task` tool that enables skills to dispatch subagents with isolated context windows. Supports single, parallel, and chain execution modes.

### Agents

The extension ships with two bundled agents (`general-purpose` and `read-only`). Place custom agents in `~/.pi/agent/agents/` (user-level) or `.pi/agents/` (project-level) to override or extend them. Project agents take priority over user agents, which take priority over bundled agents.

#### Model Configuration

The superpowers-subagent extension does not hardcode a model. Subagents use **your pi default model** from `settings.json`:

```json
{
  "defaultProvider": "vllm",
  "defaultModel": "qwen3.6-27b"
}
```

To override for a specific task, use the `model` parameter in the Task tool call:

```typescript
Task({
  agent: "general-purpose",
  task: "...",
  model: "openrouter/anthropic/claude-sonnet-4",
});
```

**For the complete flow diagram, artifact chain, and step-by-step walkthrough, see [docs/FLOW_DESCRIPTION.md](docs/FLOW_DESCRIPTION.md).**

## The Full Workflow

### 1. Brainstorming (`brainstorming/SKILL.md`)

Before any creative work — no exceptions.

1. **Read living specs** — check `docs/specs/` for relevant domain specs. They describe current behavior. If none exist, note that the feature spec will define the domain's initial behavioral requirements.
2. **Explore project context** — files, docs, recent commits
3. **Ask clarifying questions** — one at a time
4. **Propose 2–3 approaches** — with trade-offs and recommendation
5. **Present design** — in sections, get user approval after each
6. **Write proposal** → `docs/design/YYYY-MM-DD-<topic>-proposal.md` — intent, scope, approach, impact
7. **Write feature spec** → `docs/design/YYYY-MM-DD-<topic>-spec.md` — behavioral contract with SHALL/MUST/SHOULD requirements and GIVEN/WHEN/THEN scenarios
8. **Dispatch spec reviewer** — verify the spec is behavioral (not architecture in disguise)
9. **User reviews proposal + spec**
10. **Transition** → invoke `writing-plans`

**Hard gate:** No code, no implementation skills, no scaffolding until both the proposal and feature spec are approved.

### 2. Writing Plans (`writing-plans/SKILL.md`)

Convert the approved proposal and feature spec into a delta spec and implementation plan.

1. **Read the proposal** — intent, scope, approach, impact
2. **Read the feature spec** — behavioral requirements
3. **Read relevant living specs** from `docs/specs/` (current behavior for affected domains)
4. **Write delta spec** → `docs/design/YYYY-MM-DD-<topic>-delta.md` — derived by diffing the feature spec against the living spec

   The delta spec declares what behavioral requirements are changing:

   ```markdown
   # Delta: Add WebPush Notifications

   ## Domain: notifications

   ### ADDED Requirements

   #### Requirement: push-delivery

   The system SHALL deliver notifications via WebPush to subscribed clients.

   ##### Scenario: user receives push

   - GIVEN user has an active WebPush subscription
   - WHEN a notification event is published
   - THEN the user receives a push notification within 5 seconds

   ### MODIFIED Requirements

   #### Requirement: email-delivery

   ##### Scenario: new priority scenario

   - GIVEN a notification with severity "urgent"
   - WHEN the notification is published
   - THEN an email is sent within 10 seconds
   ```

   If the change has no behavioral impact:

   ```markdown
   # Delta: Refactor Notification Queue

   ## No Behavioral Changes

   Internal refactoring: replaced callback queue with event emitter.
   No requirements added, modified, or removed.
   ```

5. **File structure** — map which files are created/modified
6. **Write tasks** — bite-sized (2–5 min), TDD steps, each tracing to a delta spec requirement
7. **Self-review** — 5 checks:
   - Feature spec coverage (spec → delta — every requirement in the feature spec has a delta entry)
   - Delta coverage (delta → tasks — every ADDED/MODIFIED requirement has a test)
   - Reverse coverage (tasks → delta + spec — no scope creep)
   - Placeholder scan
   - Type consistency
8. **Dispatch plan reviewer** — verify plan completeness and spec alignment (required, not optional)
9. **Execution handoff** — offer subagent-driven (recommended) or inline execution

### 3. Execution (`subagent-driven-development/SKILL.md` or `executing-plans/SKILL.md`)

**Subagent-Driven Development (recommended):** Fresh subagent per task, two-stage review after each.

Per task:

1. Dispatch implementer → implements with TDD, commits, self-reviews
2. Dispatch **spec compliance reviewer** → checks against:
   - **Delta spec** (primary) — behavioral contract (REQUIRED input — must be included in full)
   - **Feature spec** (context) — intent and rationale
   - **Task text** — what was asked this task
3. If spec issues → implementer fixes → re-review (loop)
4. Dispatch **code quality reviewer** → standard code review (Critical/Important/Minor)
5. If quality issues → implementer fixes → re-review (loop)
6. Mark task complete

**Delta spec mutability:** If the spec reviewer finds a discrepancy between code and delta spec, the controller decides whether to fix the code or update the delta spec. If the delta is updated, re-check coverage and re-review.

**Per-task scope:** A single delta requirement may span multiple tasks. The per-task reviewer checks "did this task implement what was asked" — full delta compliance is verified after all tasks.

After all tasks: final code review → invoke `finishing-a-development-branch`.

### 4. Finishing (`finishing-a-development-branch/SKILL.md`)

1. **Verify tests pass**
2. **Determine base branch**
3. **Present 4 options:** merge locally, push + PR, keep as-is, discard
4. **Execute choice**
5. **Sync living specs** (Options 1, 2, 3 only — never for discard):

   Read `docs/design/<date>-<topic>-delta.md`, merge into `docs/specs/`:
   - ADDED → append (or treat as MODIFIED if name exists)
   - MODIFIED → add/replace scenarios, preserve existing content
   - REMOVED → delete requirement block

   Show sync summary, get user confirmation, commit as `sync: update <domain> spec(s)`.

   If the delta declares "No Behavioral Changes," skip the sync.

6. **Cleanup worktree** (Options 1, 2, 4)

### Spec/Design/Plan Directory Structure

```
docs/
├── specs/                                 # Living specs (canonical behavior)
│   ├── auth.md
│   ├── notifications.md
│   └── ...
├── design/                                # Proposals, feature specs, deltas
│   ├── 2026-05-06-add-webpush-proposal.md  # Intent, scope, approach
│   ├── 2026-05-06-add-webpush-spec.md      # Behavioral contract (SHALL/GIVEN/WHEN/THEN)
│   └── 2026-05-06-add-webpush-delta.md     # Delta spec (derived from spec vs living spec)
└── plans/
    └── 2026-05-06-add-webpush.md          # Implementation plan
```

| Path                                     | What                                            | Lifespan                              |
| ---------------------------------------- | ----------------------------------------------- | ------------------------------------- |
| `docs/specs/<domain>.md`                 | How the system _currently_ behaves              | Persistent, updated by sync           |
| `docs/design/<date>-<topic>-proposal.md` | Why and what scope (intent, approach, impact)   | One-off per feature                   |
| `docs/design/<date>-<topic>-spec.md`     | What behavior (SHALL, scenarios)                | One-off per feature, drives delta     |
| `docs/plans/<date>-<topic>.md`           | How to build it (step-by-step)                  | One-off per feature                   |
| `docs/design/<date>-<topic>-delta.md`    | What behavioral requirements are changing       | One-off per feature, consumed by sync |

## Cross-Cutting Skills

| Skill                            | When                             | What                                                                           |
| -------------------------------- | -------------------------------- | ------------------------------------------------------------------------------ |
| `test-driven-development`        | During every implementation task | Iron Law: no production code without a failing test first. Red-green-refactor. |
| `verification-before-completion` | Before any completion claim      | Evidence before assertions. Run the command, read the output, then claim.      |
| `requesting-code-review`         | After tasks, before merges       | Dispatch read-only reviewer with git diff. Fix Critical/Important.             |
| `systematic-debugging`           | Any bug or test failure          | Root cause first. No fixes without investigation. 4 phases.                    |
| `using-git-worktrees`            | Before implementation            | Isolated workspace on feature branch. Verify .gitignore, baseline tests.       |
| `dispatching-parallel-agents`    | Multiple independent problems    | One agent per problem domain. Concurrent execution.                            |

## Skill Trigger Rules

Skills are invoked automatically via metadata headers and harness integration. The `using-superpowers` skill is the bootstrap — it establishes that skills must be checked before _any_ action.

**Instruction priority:** User instructions > Superpowers skills > Default system prompt. The user is always in control.

**Simple operations** (reading 1–3 files, single edits, `ls`/`grep`/`git status`) do not trigger skills. Skills are for multi-step, substantive, risk-bearing work.

**"Already brainstormed" means the artifacts exist:** The brainstorming skill is complete when both the proposal (`docs/design/`) and the feature spec (`docs/design/`) exist. A conversation about the idea is not the same as brainstorming. If the artifacts don't exist, invoke brainstorming.

## Edge Cases

| Case                                   | Handling                                                                                                          |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Cold start** (no living specs)       | Feature spec defines the domain's initial requirements (all ADDED). Delta spec copies them. Sync creates the living spec from scratch. |
| **Non-behavioral changes**             | Both feature spec and delta declare "No Behavioral Changes." Sync skips living spec updates. Normal SDD flow still applies. |
| **Multi-domain features**              | Feature spec and delta have multiple `## Domain: <name>` sections. Sync iterates over each, updating the corresponding living spec. |
| **Implementation diverges from delta** | Controller decides during review: fix code or update delta. Delta is mutable during implementation.               |
| **User discards the branch**           | Sync never runs. Living spec untouched.                                                                           |
| **User keeps branch as-is**            | Sync runs. Living spec reflects the behavioral contract from the delta spec (which may differ from actual implementation if divergence occurred).                                                   |
