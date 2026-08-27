# Living Spec Flow in Tau

This document describes the spec-driven development flow enforced by the Tau Superpowers skills and shows where isolated `task` subagents participate.

## Tau Activation

A user installation links skills individually under `~/.tau/skills`. In this checkout, Tau exposes the canonical tree through `.agents/skills -> ../skills` only after project input is approved. The model initially receives skill metadata only and requests the full `SKILL.md` when its description matches the task. A user may invoke a skill explicitly with `/skill:<name>`.

The Python extension registers the `task` tool when installed under `~/.tau/extensions/superpowers-subagent` or explicitly loaded with:

```bash
tau -e extensions/superpowers-subagent
```

Each `task` child has a fresh conversation context. The controller must provide complete requirements, paths, diffs or command output, and expected response format; a child cannot see the controller conversation or resume it later.

## The Big Picture

A **living spec** (`docs/specs/<domain>.md`) is the canonical description of current behavior for a domain. A **feature spec** describes one proposed change as the delta against the living spec (ADDED/MODIFIED/REMOVED per domain); after implementation is verified and accepted, the feature spec's changes are merged into the living spec.

```text
The model selects a skill from metadata (or the user invokes `/skill:<name>`)
    -> brainstorming reads the living spec
    -> proposal + behavioral feature spec on a new branch/worktree
    -> writing-plans maps the spec to contract-based implementation tasks
    -> implementation follows the plan with per-task review
    -> finishing verifies, syncs the living spec, and merges or opens a PR
```

## Artifact Chain

| Path | Role | Lifespan |
| --- | --- | --- |
| `docs/specs/<domain>.md` | Canonical current behavior | Persistent; updated at finishing |
| `docs/design/<date>-<topic>-proposal.md` | Intent, scope, approach, and impact | One feature |
| `docs/design/<date>-<topic>-spec.md` | Behavioral contract and delta against the living spec | One feature; drives plan, review, and sync |
| `docs/plans/<date>-<topic>.md` | Architecture, interface and behavior contracts, tests to prove | One feature |

## End-to-End Flow

```text
BRAINSTORMING
  1. Read relevant docs/specs/ files (or identify a new domain).
  2. Explore context; clarify (batch independent questions).
  3. Compare 2-3 approaches; present the complete design once for approval.
  4. Set up the branch/worktree — every artifact and all code land here,
     never on the default branch.
  5. Write the proposal and the behavioral feature spec
     (ADDED/MODIFIED/REMOVED relative to the living spec).
  6. task(document-review): review the spec; fix and re-dispatch until approved.
  7. Get user approval for both artifacts; commit them to the branch.

  HARD GATE: no implementation before reviewer and user approval.
                                  |
                                  v
WRITING PLANS
  1. Read the proposal, feature spec, and living specs.
  2. Map the file structure, then write contract-based tasks: files,
     interface signatures, expected behavior, tests to prove, exact
     verification commands — no implementation code in the plan.
  3. Self-review spec<->plan coverage, placeholders, signature
     consistency, and standards.
  4. task(document-review): review the plan; fix and re-dispatch until approved.
  5. Commit the plan to the branch. Execute with subagent-driven-development
     (executing-plans inline for trivial plans).
                                  |
                                  v
IMPLEMENTATION
  1. Work in the branch/worktree — never on the default branch.
  2. If subagent-driven development:
       a. task(implementation): implement one task per dispatch, TDD from
          the task's contracts, commit per task.
       b. Inspect the report, tests, commit, and semantic status.
       c. task(code-review): ONE review pass per task; the report carries
          separate Spec Compliance and Code Quality sections.
       d. Fix and re-review until both dimensions pass.
  3. If inline executing-plans:
       a. Execute each task's contract with TDD and run its named checks;
          commit per task.
       b. Checkpoint review each batch with the same implementation reviewer.
  4. Final whole-change review against the full feature spec.
                                  |
                                  v
FINISHING
  1. Run fresh repository verification.
  2. Determine the base branch.
  3. Sync the feature spec's ADDED/MODIFIED/REMOVED sections into
     docs/specs/ (skip when the spec declares "No Behavioral Changes")
     and commit to the branch — automatically, no confirmation.
  4. Offer exactly two outcomes: local merge or pull request.
     Operator silence leaves the branch untouched.
  5. Execute the choice: merge (verify the merged result, delete the
     branch, remove the worktree) or PR (push, gh pr create, keep the
     branch and worktree until it lands).
```

## `task` Dispatch in the Flow

The full argument and result contract is in the [Tau `task` tool reference](../skills/using-superpowers/references/tau-tools.md). Workflow dispatches use five bundled agents:

| Agent | Tool access | Workflow use |
| --- | --- | --- |
| `implementation` | Tau's normal built-in coding tools | One implementation task at a time |
| `code-review` | `read` + read-only `bash`, enforced by a public hook | Per-task, checkpoint, and final implementation review of named files; returns a strict `## Code Review` report ending in a status line |
| `document-review` | `read` + read-only `bash`, enforced by a public hook | Feature-spec and plan review at the design gates; returns a strict `## Document Review` report ending in a status line |
| `general-purpose` | Tau's normal built-in coding tools | Unpinned implementation or scouting work |
| `read-only` | Only the `read` tool, enforced by a public hook | Unpinned substantial read-only investigation of named files |

The user can override provider, model, and thinking level per agent with the subagent config file (`[agents.<name>]` in `superpowers-subagent.toml`). Agents without a pin at any layer inherit the parent session's active provider, model, and thinking level at dispatch time.

A typical reviewer call supplies every readable path and embeds any information the reviewer cannot obtain with `read`:

```json
{
  "tasks": [
    {
      "agent": "code-review",
      "task": "Review the named spec against the supplied requirements. Read docs/design/2026-08-14-example-spec.md.\n\n## Required context\n[COMPLETE REQUIREMENTS AND RELEVANT COMMAND OUTPUT]"
    }
  ]
}
```

Review agents may run read-only `bash` themselves (`git diff`/`log`/`status`, `grep`/`rg`/`find`) but must never change repository or environment state; the plain `read-only` agent cannot run commands at all, so searches, `git diff`, and file identification for it come from the controller. Multiple items in one call run in parallel and must be independent; conditional implement/review/fix loops require separate calls so the controller can inspect each result.

### Result and Status Flow

```text
child Tau JSONL
    -> accepted message_end messages stored in details.results[*].messages
    -> the complete final assistant message becomes parent content
       (concatenated text blocks of the last accepted assistant message
       only; tool calls, thinking, and earlier messages are never relayed)
    -> last supported status marker recorded independently
    -> controller checks semantic status AND process/error fields
```

| Semantic status | Controller action |
| --- | --- |
| `DONE` | Continue to the next gate. |
| `DONE_WITH_CONCERNS` | Read concerns; resolve correctness or scope issues before continuing. |
| `NEEDS_CONTEXT` | Add the missing material to a new complete prompt and re-dispatch. |
| `BLOCKED` | Change context, approach, task size, or escalate to the user. |

Semantic status is not process state. A child may exit successfully while reporting `BLOCKED`, and a failed process may have partial messages. Inspect `details.results` for `exitCode`, `errorMessage`, `timedOut`, `cancelled`, and `status` before deciding what to do.

Project-controlled agent definitions require confirmation by default. In headless Tau, a selected project agent fails closed unless the caller has inspected it and sets `confirmProjectAgents: false` for that call.

## Behavioral Requirement Lifecycle

```text
feature spec                 plan                        implementation              living spec
    |                             |                            |                           |
    | ADDED/MODIFIED/REMOVED      | contracts + tests to prove | tests and reviews         |
    |---------------------------->|--------------------------->|                           |
    |                             |                            | verified accepted behavior |
    |                             |                            |-------------------------->|
    |                             |                            | merged, not copied         |
```

The feature spec expresses the change from current behavior. Plan tasks and tests trace to it. Implementation review checks code against it while using the proposal as context. Finishing merges only accepted changes into the living spec.

## Gate Enforcement

| Gate | Skill | What it blocks |
| --- | --- | --- |
| Proposal + feature spec | `brainstorming` | No code before both artifacts exist |
| Spec reviewer + user approval | `brainstorming` | No planning handoff before behavioral and human approval |
| Branch/worktree setup | `using-git-worktrees` | No artifacts or code on the default branch |
| Plan reviewer | `writing-plans` | No execution with coverage gaps or incomplete contracts |
| Worktree baseline | `using-git-worktrees` | No feature work from a failing unexplained baseline |
| Per-task implementation review | `subagent-driven-development` | No task completes with open spec-compliance or code-quality findings |
| Fresh verification | `verification-before-completion` / `finishing-a-development-branch` | No completion or integration claim without current evidence |
| Living-spec sync | `finishing-a-development-branch` | No merge/PR before the branch carries the synced specs (skipped for no-behavior-change work) |

## Edge Cases

| Case | Handling |
| --- | --- |
| **Cold start** (no living spec) | Feature requirements are all ADDED; finishing creates the domain living spec. |
| **No behavioral change** | The feature spec declares `No Behavioral Changes`; finishing skips the sync. |
| **Multiple domains** | The feature spec uses one domain section per living spec; sync each independently. |
| **Implementation diverges from the spec** | Decide whether code or spec is wrong, update the correct artifact, recheck task coverage, and re-review. |
| **Reviewer lacks context** | Supply named paths plus missing diff/search/command output in a new complete `task` prompt. |
| **Child reports a semantic blocker** | Do not infer process failure; inspect details and re-dispatch or escalate. |
| **Operator never chooses an integration** | The branch and worktree stay untouched; nothing is integrated. |

## Isolation Boundaries

`task` isolates conversation context and disables discovered child extensions and protected project resources. It is not an operating-system, filesystem, network, credential, provider, or model sandbox. The read-only and review profiles enforce Tau tool calls only (read-only: `read`; review: `read` plus instruction-governed read-only `bash`), and the instruction not to invoke ambient user skills is prompt guidance only. Parent content is the child's complete final assistant message; complete accepted messages remain in structured details.
