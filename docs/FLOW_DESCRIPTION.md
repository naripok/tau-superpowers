# Proposal-Baseline Workflow in Tau

This document describes the spec-driven development flow enforced by the Tau Superpowers skills and shows where isolated `task` subagents participate.

## Tau Activation

A user installation links skills individually under `~/.tau/skills`. In this checkout, Tau exposes the canonical tree through project discovery after project input is approved. The model initially receives skill metadata only and requests the full `SKILL.md` when its description matches the task. A user may invoke a skill explicitly with `/skill:<name>`.

The Python extension registers the `task` tool when installed under `~/.tau/extensions/superpowers-subagent` or explicitly loaded with:

```bash
tau -e extensions/superpowers-subagent
```

Each `task` child has a fresh conversation context. The controller must provide complete requirements, paths, diffs or command output, and expected response format; a child cannot see the controller conversation or resume it later.

## The Big Picture

The **approved proposal** is the sole source of operator intent. The operator reviews and approves one artifact: the cold-reviewed proposal. A fresh agent derives the **feature spec** from the approved proposal without brainstorm history, and a reviewer proves the spec encodes every behavioral intention. The **implementation plan** treats the feature spec and the proposal as complementary contracts. **Living specs** (`docs/specs/<domain>.md`) stay the canonical description of current behavior and are synchronized only after final acceptance.

```text
baseline evidence and depth classification
    -> cold-reviewed, operator-approved proposal
    -> feature spec derived in a fresh context, reviewed for semantic fidelity
    -> plan implementing spec behavior within proposal constraints
    -> TDD implementation with per-task review (depth-dependent)
    -> final acceptance, reviewed living-spec synchronization
    -> operator-chosen integration
```

## Workflow Depth

`using-superpowers` classifies every change before design work starts, from a minimal evidence pass:

| Level | Selection |
| --- | --- |
| Direct | Representation-only change: no behavioral, contract, data, security, privacy, operational, or controlled-document effect, and no design decision. |
| High-risk | Any trigger applies: external contracts, schema or stored-data migration and recovery, security and privacy, concurrency and distributed consistency, behavior-affecting runtime or data ordering, destructive or irreversible action, availability or compliance, rollback needing coordinated recovery. |
| Bounded | One behavioral domain, no material baseline discrepancy, no cross-boundary coordination (including the workflow's own stage order), one safe revert, one cohesive responsibility. |
| Standard | Every other non-Direct change. File and line counts never raise a level. |

An unresolved High-risk fact selects provisional High-risk until resolved. Other unknowns take least-escalating values and then cause one aggregate one-level escalation, capped at High-risk. The highest applicable level wins. Reassessment happens when classification evidence changes; after operator approval, evidence can raise the level through proposal change control but never silently lowers it.

### Gate Matrix

| Gate | Direct | Bounded | Standard | High-risk |
| --- | --- | --- | --- | --- |
| Baseline and classification | Minimal evidence and Direct test | Concise relevant baseline in proposal | Complete relevant baseline and impact | Standard content plus applicable compatibility, migration, rollout, rollback, observability, recovery, and risk treatment |
| Proposal | None | Concise complete proposal, one cold review, operator approval | Complete proposal and impact, one cold review, operator approval | Standard proposal plus every High-risk category, one cold review, operator approval |
| Feature spec | None | Concise complete spec and one review | Full spec and one review | Full spec and one two-pass review |
| Plan | None | Concise one-to-two-task plan and one review | Full plan and one review | Obligation-mapped plan and one review |
| Execution | Targeted edit and relevant checks | Inline execution of one or two tasks | Per-task implementation and review | Mapped evidence plus per-task implementation and review |
| Final acceptance | Relevant repository checks | One final whole-change review and fresh verification | One final whole-change review and fresh verification | One two-pass final review, acceptance checks, and fresh verification |
| Living-spec sync and integration | None | Synchronize, check, then integrate | Synchronize, check, then integrate | Synchronize, check, then integrate after final-review approval |

Every non-Direct level keeps semantic fidelity, proposal change control, brownfield grounding, artifact reviews, and the ban on dispatch-only design repair.

## Artifact Chain

| Path | Role | Lifespan |
| --- | --- | --- |
| `docs/specs/<domain>.md` | Canonical current behavior | Persistent; updated at finishing |
| `docs/design/<date>-<topic>-proposal.md` | Operator-approved intent: outcomes, acceptance examples, scope, constraints, approach, risks | One feature |
| `docs/design/<date>-<topic>-spec.md` | Complete observable post-change behavior, derived from the approved proposal | One feature; drives plan, review, and sync |
| `docs/plans/<date>-<topic>.md` | Task contracts: spec behavior plus proposal constraints, tests to prove | One feature |

Artifact existence never establishes state completion. Each review or approval attaches to the exact input version that received it; an edit invalidates that artifact's approvals, and a changed upstream input invalidates every affected downstream review.

## End-to-End Flow

Every non-Direct change passes these states in order:

```text
 1. Minimal baseline evidence established (domain status and trigger status)
 2. Provisionally classified
 3. Worktree established through using-git-worktrees before any persisted artifact
 4. Baseline and proposal completed at the selected depth
 5. Proposal cold-reviewed and approved by the reviewer
 6. Proposal approved by the operator (exact version; immutable identity)
 7. Feature spec derived in a fresh context without brainstorm history
 8. Feature spec reviewed and approved (temporary governing-claim dispositions)
 9. Plan written (changed behavior -> tasks; unchanged baseline -> preservation checks)
10. Plan reviewed and approved
11. Implementation completed with level-required reviews
12. Final acceptance passed (identities, depth reassessment, acceptance examples, fresh verification)
13. Living spec synchronized, reviewed, and committed
14. Integration performed on explicit operator choice
```

### Brownfield Baseline Branches

The proposal author selects one branch from repository evidence:

1. **Domain with a living spec:** the living spec is the current-behavior contract; inspect code, tests, interfaces, consumers, contracts, and documentation for impact and discrepancies.
2. **Existing undocumented domain:** reconstruct complete relevant current behavior from implementation, tests, interfaces, consumers, contracts, documentation, and operational evidence; record evidence and material discrepancies. The feature spec formalizes complete relevant post-change behavior, including established unchanged baseline behavior; planning maps unchanged behavior to preservation or regression checks; finishing can then create the living spec without invention.
3. **Genuinely new domain:** record evidence that the domain is absent and describe adjacent impact.

A missing living spec never proves that a domain is new. A material source discrepancy is resolved through the proposal before approval.

### Proposal Review and Operator Approval

The proposal author transfers every accepted brainstorm decision into the proposal (behavior, scope, architecture, thresholds, exceptions, constraints, assumptions, risks, acceptance). A fresh `document-review` child with no brainstorm history checks semantic closure, clarity, consistency, grounding, depth content, and actionable completeness. Undefined option labels and references to prior chat are blocking findings. The reviewer cannot detect a decision omitted entirely from the proposal; the operator owns the check that the proposal captures the intended change. Unresolved controlled decisions block approval. Every edit to an approved proposal — including a format-only edit — creates a new version and repeats cold review and operator approval.

### Feature-Spec Derivation and Review

A fresh author derives the spec from the approved proposal, established baseline, and living specs. It preserves each claim's actor, trigger, timing, ordering, scope, conditions, exceptions, strength, threshold, and observable result, and never invents a decision. When two valid meanings remain, it stops and returns the decision through proposal revision. The spec reviewer assigns a temporary classification and disposition to every governing proposal claim (behavior and quality map to requirements; internal constraints stay with planning; acceptance examples map to scenarios; non-goals stay excluded; rationale creates no contract). Dispositions stay in review output and never become a committed ledger. Spec-review approval gates planning for every non-Direct level.

### Planning and Execution

The plan treats the feature spec as the behavioral contract and the approved proposal as the contract for intent, scope, binding architecture, constraints, non-goals, acceptance, and risk treatment. A proposal-and-spec conflict stops planning. Bounded plans contain one or two cohesive tasks and run inline via `executing-plans`; Standard and High-risk work routes to `subagent-driven-development` regardless of task count. Implementation dispatches derive controlled design context only from the approved artifacts; a controller never answers a missing controlled decision only inside a child prompt — it repairs the owning upstream artifact. Prompt-only repository evidence is valid when it selects no controlled outcome.

### Review Accounting

One initial reviewer dispatch covers one artifact version against one complete input set and one review contract. Duplicate initial reviews with identical inputs are prohibited. A changed artifact receives one new complete initial review; added context after `BLOCKED` or `NEEDS_CONTEXT` permits one new complete review with changed inputs. An unchanged rejected-finding confirmation is a targeted adjudication redispatch to the same reviewer profile and does not repeat a complete review. The High-risk spec and final reviews use one reviewer that performs a contract pass and a risk pass before one verdict. Every automated review gate applies the unchanged adjudication contract in `docs/specs/review-adjudication.md`.

### Final Acceptance and Finishing

Final acceptance checks approval identities, reassesses depth once from accumulated evidence, checks every proposal acceptance example against named evidence, and runs fresh repository verification. Any failure blocks synchronization. The synchronization applies accepted feature-spec changes idempotently, preserves unchanged behavior, and creates a living spec from the complete reviewed feature spec for an undocumented or new domain without invention. A fresh `document-review` child reviews each candidate synchronization; the sync commit follows only after approval. Stale factual enumerations in other living specs (such as the gate list in `docs/specs/review-adjudication.md`) are updated in the same reviewed pass, with procedure content untouched. Synchronization requests no operator approval. Finishing then offers exactly a local merge or a pull request; operator silence leaves the branch and worktree untouched.

## `task` Dispatch in the Flow

The full argument and result contract is in the [Tau `task` tool reference](../skills/using-superpowers/references/tau-tools.md). Workflow dispatches use five bundled agents:

| Agent | Tool access | Workflow use |
| --- | --- | --- |
| `implementation` | Tau's normal built-in coding tools | One implementation task at a time |
| `code-review` | `read` + read-only `bash`, enforced by a public hook | Per-task, final, and whole-change implementation reviews; returns a strict `## Code Review` report ending in a status line |
| `document-review` | `read` + read-only `bash`, enforced by a public hook | Proposal, feature-spec, plan, and living-spec synchronization reviews; returns a strict `## Document Review` report ending in a status line |
| `general-purpose` | Tau's normal built-in coding tools | Fresh-context feature-spec derivation and unpinned work |
| `read-only` | Only the `read` tool, enforced by a public hook | Isolated behavior trials of skill guidance |

Review agents may run read-only `bash` themselves (`git diff`/`log`/`status`, `grep`/`rg`/`find`) but must never change repository or environment state. Multiple items in one call run in parallel and must be independent; conditional loops require separate calls so the controller can inspect each result.

### Result and Status Flow

```text
child Tau JSONL
    -> accepted message_end messages stored in details.results[*].messages
    -> the complete final assistant message becomes parent content
    -> last supported status marker recorded independently
    -> controller checks semantic status AND process/error fields
```

| Semantic status | Controller action |
| --- | --- |
| `DONE` | Continue to the next gate. |
| `DONE_WITH_CONCERNS` | Read concerns; resolve correctness or scope issues before continuing. |
| `NEEDS_CONTEXT` | Add the missing material to a new complete prompt and re-dispatch. For a missing controlled decision, repair the owning upstream artifact first. |
| `BLOCKED` | Change context, approach, task size, or escalate to the user. |

## Behavioral Requirement Lifecycle

```text
approved proposal              feature spec                  plan                    implementation          living spec
    |                              |                            |                        |                       |
    | intent, outcomes,            | complete post-change       | tasks + tests to       | verified behavior      | current behavior
    | acceptance, constraints      | behavior (fresh context)   | prove, constraints     | and constraints        |
    |----------------------------->|--------------------------->|----------------------->|                       |
    |            semantic fidelity review                       |  plan review           |---- accept --------->|
```

The feature spec expresses complete post-change behavior derived from the approved proposal. Plan tasks and tests trace to it while carrying proposal constraints. Implementation review checks code against the spec and the proposal. Finishing merges only accepted changes into the living spec.

## Gate Enforcement

| Gate | Skill | What it blocks |
| --- | --- | --- |
| Depth classification | `using-superpowers` | No design work before a provisional depth from evidence |
| Branch/worktree setup | `using-git-worktrees` | No persisted artifact or code on the default branch |
| Proposal cold review + operator approval | `brainstorming` | No spec derivation before the exact proposal version is cold-reviewed and operator-approved |
| Feature-spec review | `brainstorming` | No planning before semantic proposal-to-spec approval |
| Plan review | `writing-plans` | No execution with coverage gaps, missing constraints, or incomplete contracts |
| Per-task and final reviews | `subagent-driven-development` / `executing-plans` | No task or integration with open spec-compliance, code-quality, or proposal-constraint findings |
| Review-finding adjudication | `receiving-code-review` | No gate advances on unadjudicated findings; no fix dispatch carries rejected findings |
| Final acceptance | `finishing-a-development-branch` | No synchronization before identities, acceptance examples, and fresh verification pass |
| Living-spec sync | `finishing-a-development-branch` | No integration before the reviewed synchronization is committed |
| Fresh verification | `verification-before-completion` | No completion claim without current evidence |

## Edge Cases

| Case | Handling |
| --- | --- |
| **Cold start** (no living spec) | Determine the baseline branch from evidence; an undocumented domain is reconstructed, not treated as new; finishing creates the domain living spec from the complete reviewed feature spec. |
| **No behavioral change** | The feature spec declares `No Behavioral Changes`; finishing skips the sync. |
| **Multiple domains** | The feature spec uses one domain section per living spec; sync each independently. |
| **Omitted brainstorm decision** | Cold review cannot detect it; the operator owns intended-change fidelity. A discovered omission returns through proposal change control. |
| **Missing living spec** | Never treated as proof of a new domain; reconstruct from evidence. |
| **Material source conflict** | Resolved through the proposal before approval; never silently selected. |
| **Depth escalation** | Later evidence stops work, revises the proposal, repeats cold review and operator approval, and invalidates affected downstream artifacts. After approval, depth never silently lowers. |
| **Bounded task overflow** | A required third task stops planning or execution and invokes proposal change control. |
| **Missing controlled implementation context** | Implementation stops; the owning upstream artifact is repaired through change control. Dispatch-only clarification is prohibited. |
| **Implementation diverges from the spec** | Fix the code, or update the artifact; a controlled-meaning change returns to proposal approval. |
| **Reviewer lacks context** | Supply named paths plus missing evidence in a new complete prompt; changed inputs permit one new complete review. |
| **Child reports a semantic blocker** | Inspect details and re-dispatch or escalate. |
| **Sync invention** | Behavior absent from the baseline and accepted spec is a blocking finding; integration stays blocked. |
| **Stale cross-domain enumeration** | Updated in the same reviewed synchronization pass; procedure content untouched. |
| **Operator never chooses an integration** | The branch and worktree stay untouched; nothing is integrated. |
| **Maintained Critical rejection** | Stop all workflow dispatches, escalate to the user with an architectural overview and situation summary, resume per the user decision. |

## Isolation Boundaries

`task` isolates conversation context and disables discovered child extensions and protected project resources. It is not an operating-system, filesystem, network, credential, provider, or model sandbox. The read-only and review profiles enforce Tau tool calls only, and the instruction not to invoke ambient user skills is prompt guidance only. Parent content is the child's complete final assistant message; complete accepted messages remain in structured details.

## Rollout and Rollback

Rollout: install the changed skills (`./install.sh` or `git pull` plus re-install), then run `/reload` or restart active Tau sessions. Rollback: revert the workflow change in the repository, re-install the prior skills, and reload active sessions.
