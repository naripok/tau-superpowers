# Living Spec Flow

This document describes the spec-driven development flow enforced by the superpowers skills.

## The Big Picture

A **living spec** (`docs/specs/<domain>.md`) is a canonical description of how the system _currently_ behaves, organized by domain (auth, notifications, payments, etc.). It is created the first time a feature touches a domain and updated each time subsequent features change that domain's behavior.

The loop:

```
Brainstorming reads the living spec
    → writes proposal + feature spec (behavioral contract)
    → Planning derives delta spec from feature spec vs living spec
    → Implementation follows the plan
    → Finishing syncs the delta into the living spec
```

## Artifact Chain

| Path                                     | What                                          | Lifespan                              |
| ---------------------------------------- | --------------------------------------------- | ------------------------------------- |
| `docs/specs/<domain>.md`                 | How the system _currently_ behaves            | Persistent, updated by sync           |
| `docs/design/<date>-<topic>-proposal.md` | Why and what scope (intent, approach, impact) | One-off per feature                   |
| `docs/design/<date>-<topic>-spec.md`     | What behavior (SHALL, scenarios)              | One-off per feature, drives delta     |
| `docs/plans/<date>-<topic>.md`           | How to build it (step-by-step)                | One-off per feature                   |
| `docs/design/<date>-<topic>-delta.md`    | What behavioral requirements are changing     | One-off per feature, consumed by sync |

## Step-by-Step Flow

```
┌─ BRAINSTORMING ───────────────────────────────────────────────────────────┐
│                                                                           │
│  1. Read living specs  (docs/specs/ — may not exist)                      │
│  2. Explore context                                                       │
│  3. Ask questions (one at a time)                                         │
│  4. Propose 2-3 approaches                                                │
│  5. Present design, get user approval                                     │
│  6. Write proposal  → docs/design/<topic>-proposal.md                     │
│  7. Write feature spec → docs/design/<topic>-spec.md                      │
│     └── ADDED/MODIFIED/REMOVED, SHALL, GIVEN/WHEN/THEN                    │
│  8. ▶ Spec reviewer (read-only subagent)                                  │
│     └── catches architecture-in-disguise, missing scenarios               │
│  9. User reviews proposal + spec                                          │
│                                                                           │
│  HARD-GATE: No code until spec reviewer + user approve                    │
└───────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─ WRITING PLANS ───────────────────────────────────────────────────────────┐
│                                                                           │
│  1. Read proposal + feature spec + living specs                           │
│  2. Write delta spec → docs/design/<topic>-delta.md                       │
│     └── derived by diffing feature spec vs living spec                    │
│  3. File structure                                                        │
│  4. Write tasks → docs/plans/<topic>.md                                   │
│     └── each task traces to a delta requirement                           │
│  5. Self-review (5 checks: spec→delta coverage, delta→plan coverage, ...) │
│  6. ▶ Plan reviewer (read-only subagent)                                  │
│     └── verifies spec alignment, delta coverage, buildability             │
│  7. Execution handoff (subagent-driven or inline)                         │
└───────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─ SUBAGENT-DRIVEN DEVELOPMENT ─────────────────────────────────────────────┐
│                                                                           │
│  Per task:                                                                │
│    ▶ Implementer (TDD, commits, self-review)                              │
│    ▶ Spec compliance reviewer (checks against delta spec — REQUIRED)      │
│    ▶ Code quality reviewer                                                │
│  Final code review                                                        │
└───────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─ FINISHING ───────────────────────────────────────────────────────────────┐
│                                                                           │
│  1. Verify tests pass                                                     │
│  2. Determine base branch                                                 │
│  3. Present merge / PR / keep / discard options                           │
│  4. Execute choice                                                        │
│  5. Sync delta → living spec (docs/specs/<domain>.md)                     │
│     └── ADDED→append, MODIFIED→replace, REMOVED→delete                    │
│  6. Cleanup worktree                                                      │
└───────────────────────────────────────────────────────────────────────────┘
```

## The Behavioral Requirement Lifecycle

A single behavioral requirement traces through the entire flow:

```
brainstorming                    writing-plans              SDD                     finishing
    │                              │                          │                        │
    │  writes feature spec         │                          │                        │
    │  (SHALL, GIVEN/WHEN/THEN)    │                          │                        │
    │                              │                          │                        │
    │              writes delta spec                     checks code                   │
    │              (diff spec vs living)                 against delta                 │
    │                              │                          │                        │
    │                              │────── behavioral requirement ──────────────────────→ syncs
    │                              │                          │                        │
    │                              │                   implements                      │
    │                              │                   from delta                      │
    │                              │                          │                        │
    └──────────────────────────────┴──────────────────────────┴────────────────────────┘
```

## Gate Enforcements

| Gate                    | Skill                       | What It Blocks                                                                   |
| ----------------------- | --------------------------- | -------------------------------------------------------------------------------- |
| HARD-GATE               | brainstorming               | No code until proposal + spec written, spec reviewer approved, user approved     |
| "Already brainstormed?" | using-superpowers           | Requires proposal AND feature spec files to exist — conversation ≠ brainstorming |
| Spec reviewer           | brainstorming step 8        | Catches architecture-in-disguise, missing scenarios, non-behavioral language     |
| Plan reviewer           | writing-plans step 6        | Catches missing task-coverage for delta requirements, placeholders               |
| Delta spec REQUIRED     | subagent-driven-development | Spec compliance reviewer reports NEEDS_CONTEXT if delta spec not included        |

## Edge Cases

| Case                                   | Handling                                                                                                                               |
| -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Cold start** (no living specs)       | Feature spec defines the domain's initial requirements (all ADDED). Delta spec copies them. Sync creates the living spec from scratch. |
| **Non-behavioral changes**             | Both feature spec and delta declare "No Behavioral Changes." Sync skips living spec updates. Normal SDD flow still applies.            |
| **Multi-domain features**              | Feature spec and delta have multiple `## Domain:` sections. Sync iterates over each, updating the corresponding living spec.           |
| **Implementation diverges from delta** | Controller decides during review: fix code or update delta. Delta is mutable during implementation.                                    |
| **User discards the branch**           | Sync never runs. Living spec untouched.                                                                                                |
| **User keeps branch as-is**            | Sync runs. Living spec reflects the behavioral contract from the delta spec.                                                           |
