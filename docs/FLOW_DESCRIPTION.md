# Living Spec Flow in Tau

This document describes the spec-driven development flow enforced by the Tau Superpowers skills and shows where isolated `Task` subagents participate.

## Tau Activation

A user installation links skills individually under `~/.agents/skills`. In this checkout, Tau exposes the canonical tree through `.agents/skills -> ../skills` only after project input is approved. The model initially receives skill metadata only and requests the full `SKILL.md` when its description matches the task. A user may invoke a skill explicitly with `/skill:<name>`.

The Python extension registers the capitalized `Task` tool when installed under `~/.tau/extensions/superpowers-subagent` or explicitly loaded with:

```bash
tau -e extensions/superpowers-subagent
```

Each `Task` child has a fresh conversation context. The controller must provide complete requirements, paths, diffs or command output, and expected response format; a child cannot see the controller conversation or resume it later.

## The Big Picture

A **living spec** (`docs/specs/<domain>.md`) is the canonical description of current behavior for a domain. Feature artifacts describe one proposed change; after implementation is verified and accepted, the delta is merged into the living spec.

```text
The model selects a skill from metadata (or the user invokes `/skill:<name>`)
    -> brainstorming reads the living spec
    -> proposal + behavioral feature spec
    -> writing-plans derives a delta + implementation plan
    -> implementation follows the plan with review gates
    -> finishing verifies and syncs the accepted delta
```

## Artifact Chain

| Path | Role | Lifespan |
| --- | --- | --- |
| `docs/specs/<domain>.md` | Canonical current behavior | Persistent; updated after accepted work |
| `docs/design/<date>-<topic>-proposal.md` | Intent, scope, approach, and impact | One feature |
| `docs/design/<date>-<topic>-spec.md` | Proposed behavioral contract | One feature; drives the delta |
| `docs/design/<date>-<topic>-delta.md` | ADDED/MODIFIED/REMOVED behavior versus the living spec | One feature; consumed by implementation and sync |
| `docs/plans/<date>-<topic>.md` | Bite-sized implementation and verification steps | One feature |

## End-to-End Flow

```text
BRAINSTORMING
  1. Read relevant docs/specs/ files (or identify a new domain).
  2. Explore context and clarify one question at a time.
  3. Compare 2-3 approaches and get design approval.
  4. Write proposal and behavioral feature spec.
  5. Task(read-only): review the spec from named files and supplied context.
  6. Fix and re-dispatch until the reviewer reports DONE.
  7. Get user approval for both artifacts.

  HARD GATE: no implementation before reviewer and user approval.
                                  |
                                  v
WRITING PLANS
  1. Read proposal, feature spec, and living specs.
  2. Derive the delta before implementation tasks.
  3. Map file responsibilities and write TDD-sized tasks.
  4. Self-review feature -> delta -> plan coverage.
  5. Task(read-only): review the plan, full delta, named files, and supplied output.
  6. Fix and re-dispatch until the reviewer reports DONE.
  7. Ask the user to choose subagent-driven or inline executing-plans execution.
                                  |
                                  v
IMPLEMENTATION
  1. Work in an isolated Git worktree, never directly on main/master.
  2. For each task, use red -> green -> refactor and run named checks.
  3. If subagent-driven development was selected:
       a. Task(general-purpose): implement one complete task.
       b. Inspect summary, process fields, semantic status, tests, and commit.
       c. Task(read-only): spec-compliance review against the full delta.
       d. Fix and re-review until DONE.
       e. Task(read-only): code-quality review with controller-supplied diff/output.
       f. Fix and re-review until DONE.
  4. If inline executing-plans was selected:
       a. Execute each plan task directly in order and run its named checks.
       b. Track each checklist item and stop for blockers or failed verification.
       c. Request read-only review at the plan's review checkpoints.
  5. Run a final whole-change review.
                                  |
                                  v
FINISHING
  1. Run fresh repository verification.
  2. Determine the base branch.
  3. Present merge, pull request, keep, or discard options.
  4. Execute the selected outcome. If discard was selected, first require typed
     confirmation, then discard and stop without syncing the living spec.
  5. After merge/PR/keep, inspect the delta:
       a. If it has no behavioral changes, skip sync preview, confirmation, update,
          and sync commit.
       b. If it changes behavior, show the proposed sync, get confirmation, merge
          ADDED/MODIFIED/REMOVED requirements into docs/specs/, and commit the sync.
  6. Clean up the branch/worktree only when the selected outcome requires it.
```

## `Task` Dispatch in the Flow

The full argument and result contract is in the [Tau `Task` tool reference](../skills/using-superpowers/references/tau-tools.md). Workflow dispatches use two bundled profiles:

| Profile | Tool access | Workflow use |
| --- | --- | --- |
| `general-purpose` | Tau's normal built-in coding tools | One implementation task at a time |
| `read-only` | Only the `read` tool, enforced by a public hook | Spec, plan, compliance, and quality review of named files |

A typical reviewer call supplies every readable path and embeds any information the reviewer cannot obtain with `read`:

```json
{
  "agent": "read-only",
  "task": "Review the named spec against the supplied requirements. Read docs/design/2026-08-14-example-spec.md.\n\n## Required context\n[COMPLETE REQUIREMENTS AND RELEVANT COMMAND OUTPUT]"
}
```

The controller, not a read-only child, must run searches, produce `git diff`, and identify files. Use parallel mode only for independent work and chain mode only for unconditional pipelines; conditional implement/review/fix loops require separate calls so the controller can inspect each result.

### Result and Status Flow

```text
child Tau JSONL
    -> accepted message_end messages stored in details.results[*].messages
    -> final assistant text parsed for last exact ## Summary
    -> summary/fallback returned in parent-model content
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
feature spec                 delta + plan                 implementation              living spec
    |                             |                            |                           |
    | proposed SHALL behavior     | ADDED/MODIFIED/REMOVED     | tests and reviews         |
    |---------------------------->|--------------------------->|                           |
    |                             |                            | verified accepted behavior |
    |                             |                            |-------------------------->|
    |                             |                            | delta merged, not copied   |
```

The feature spec expresses desired behavior. The delta expresses only the change from current behavior. Plan tasks and tests trace to the delta. Spec-compliance review checks implementation against the delta while using the proposal and feature spec as context. Finishing merges only accepted changes into the living spec.

## Gate Enforcement

| Gate | Skill | What it blocks |
| --- | --- | --- |
| Proposal + feature spec | `brainstorming` | No code before both artifacts exist |
| Spec reviewer + user approval | `brainstorming` | No planning handoff before behavioral and human approval |
| Delta-first planning | `writing-plans` | No implementation plan detached from current behavior |
| Plan reviewer | `writing-plans` | No execution handoff with coverage gaps or placeholders |
| Worktree baseline | `using-git-worktrees` | No feature work on main/master or from a failing unexplained baseline |
| Spec compliance before quality | `subagent-driven-development` | No quality approval for behavior that misses the delta |
| Fresh verification | `verification-before-completion` / `finishing-a-development-branch` | No completion or integration claim without current evidence |
| Confirmed living-spec sync | `finishing-a-development-branch` | No merge/PR/keep workflow completes without its required sync being confirmed, applied, and committed; discard and no-behavior-change paths do not sync |

## Edge Cases

| Case | Handling |
| --- | --- |
| **Cold start** (no living spec) | Feature requirements are all ADDED; finishing creates the domain living spec. |
| **No behavioral change** | Feature spec and delta say `No Behavioral Changes`; finishing skips living-spec sync. |
| **Multiple domains** | Feature spec and delta use one domain section per living spec; sync each independently. |
| **Implementation diverges from delta** | Decide whether code or delta is wrong, update the correct artifact, recheck coverage, and re-run compliance review. |
| **Reviewer lacks context** | Supply named paths plus missing diff/search/command output in a new complete `Task` prompt. |
| **Child reports a semantic blocker** | Do not infer process failure or automatic chain stopping; inspect details and re-dispatch or escalate. |
| **User discards the branch** | Do not sync the delta; leave canonical behavior unchanged. |
| **User keeps the branch** | If behavior changes, sync it first; otherwise skip sync. Preserve the branch/worktree in either case. |

## Isolation Boundaries

`Task` isolates conversation context and disables discovered child extensions and protected project resources. It is not an operating-system, filesystem, network, credential, provider, or model sandbox. The read-only profile enforces Tau tool calls only, and the instruction not to invoke ambient user skills is prompt guidance only. Complete child messages remain in structured details; parent content uses the extracted summary when present and complete final output as fallback when absent.
