---
name: brainstorming
description: Use before any creative work: new features, components, or behavior changes.
---

# Brainstorming Ideas Into Designs

Turn ideas into an approved proposal and behavioral feature spec through collaborative dialogue.

**Announce at start:** "Using brainstorming to refine this idea into a design."

**HARD GATE:** For non-Direct work, the proposal must pass one cold review, the operator must approve that exact reviewed version, and the feature spec must pass spec review. Until all three hold, do NOT invoke any implementation skill, write any code, or scaffold any project. This applies to every non-Direct change regardless of perceived simplicity. Bounded artifacts stay short, but they MUST exist and stay complete for their roles. Direct work creates no proposal, feature spec, or plan.

## Depth Gates

`using-superpowers` selects the workflow depth and owns the gate matrix. This skill runs the authoring gates for non-Direct depths:

- **Bounded:** concise but complete artifacts. Concise reduces length, not contract integrity.
- **Standard:** complete relevant impact.
- **High-risk:** complete relevant impact plus every applicable risk category: compatibility, migration, rollout, rollback, observability, recovery, and risk treatment.

Direct work needs no proposal, feature spec, or plan. Stop this skill for Direct work and make the targeted edit with its relevant checks.

## Checklist

Copy this checklist into your working notes. Mark each item as you complete it. Complete the items in order:

- [ ] **Confirm the depth**: Check the depth that `using-superpowers` selected. Reassess it when classification evidence changes, not on a schedule
- [ ] **Read living specs**: Check `docs/specs/` for relevant domain specs. A living spec is the current-behavior contract for its domain. A missing living spec never proves that the domain is new
- [ ] **Explore project context**: files, docs, recent commits, tests, interfaces, consumers, contracts, and operational evidence
- [ ] **Select the baseline branch**: Select one branch from repository evidence: the living-spec domain, the undocumented existing domain, or the genuinely new domain.
  - **Living-spec domain**: the domain has a living spec. Use it as the current-behavior contract. Check relevant sources for impact and discrepancies
  - **Undocumented existing domain**: behavior exists but no living spec defines it. Reconstruct complete relevant current behavior from implementation, tests, interfaces, consumers, contracts, documentation, and operational evidence. Record the evidence and every material discrepancy
  - **Genuinely new domain**: repository evidence shows the domain is absent. Record that evidence plus adjacent consumers, interfaces, contracts, and operational impact
  A source discrepancy is material when different resolutions can change a proposal-owned decision. Resolve every material discrepancy in the proposal before approval
- [ ] **Ask clarifying questions**: purpose, constraints, success criteria. Assess scope first. If the request spans multiple independent subsystems, help the user decompose it into sub-projects. Each sub-project gets its own brainstorm, spec, plan, and implementation cycle. Batch independent questions in one message. Prefer multiple-choice
- [ ] **Propose 2-3 approaches**: with trade-offs and your recommendation. Lead with your recommendation
- [ ] **Present the complete design**: One message, scaled to complexity. Cover: architecture, components, data flow, error handling, testing. Record every accepted decision. This conversation is elicitation for the proposal author. It grants no approval
- [ ] **Set up the worktree**: Invoke using-git-worktrees before you persist any artifact. Commit all artifacts and code to this branch, never to the default branch
- [ ] **Write the proposal**: `docs/design/YYYY-MM-DD-<topic>-proposal.md` at the selected depth. Transfer every accepted decision from this conversation into the proposal
- [ ] **Dispatch the cold proposal review**: Use `proposal-document-reviewer-prompt.md`. One initial review per proposal version. Loop until the reviewer approves. Resolve blocking findings before operator review
- [ ] **Operator approval**: Present the cold-reviewed proposal. The operator checks that it captures the intended change. Record the approval as an immutable identity: the commit hash or a content digest of that exact version. An unresolved controlled decision blocks approval
- [ ] **Derive the feature spec**: Dispatch a fresh author with `feature-spec-author-prompt.md` after operator approval. The author receives no brainstorm history
- [ ] **Dispatch the spec reviewer**: Use `spec-document-reviewer-prompt.md`. Loop until the reviewer approves
- [ ] **Commit the artifacts to the branch**
- [ ] **Invoke writing-plans**: the only skill that comes next

## Review Accounting

Each proposal and spec gate makes one initial review dispatch per artifact version, review contract, complete input set, and review task. Do not dispatch a duplicate initial review for the same version, contract, inputs, and task.

- An artifact edit creates a new version. The new version receives one new complete initial review.
- A `BLOCKED` or `NEEDS_CONTEXT` result permits one new complete initial review when the inputs or the review task changed. Use the complete new inputs and task.
- An unchanged rejection confirmation stays a targeted redispatch per the adjudication contract. It does not repeat the complete review.

## Design Rules

- Break the system into units. Each unit must have one clear purpose and communicate through well-defined interfaces. You must be able to understand and test each unit independently
- For each unit, you must be able to answer: what does it do, how does other code use it, what does it depend on
- Prefer smaller, focused files over large ones that do too much

## Working in Existing Codebases

- Explore the current structure before you propose changes. Follow existing patterns
- Include targeted improvements to code this work touches
- Do not propose unrelated refactoring

## The Proposal

The proposal is the sole operator approval artifact. Write it per the writing-developer-facing-text skill, pragmatic mode. Save to `docs/design/YYYY-MM-DD-<topic>-proposal.md`.

The author uses this conversation as elicitation input and transfers every accepted decision into the proposal: behavior, scope, binding architecture, thresholds, exceptions, constraints, assumptions, risk treatment, and acceptance. Downstream agents never read this conversation.

Every non-Direct proposal contains this minimum content:

```markdown
# Proposal: <Topic>

## Intent
<!-- Why are we doing this? What problem does it solve? Why now? -->

## Baseline Evidence
<!-- The selected baseline branch, the relevant current behavior, the named evidence, and every material discrepancy. Record consumers, interfaces, contracts, data, security, operations, rollout, and rollback. Use None for a category with no relevant content. -->

## Required Outcomes
<!-- What must be true after the change? -->

## Acceptance Examples
<!-- Representative acceptance examples that final acceptance checks. -->

## Scope
**In scope:**
<!-- What this change covers -->

**Out of scope:**
<!-- What this change excludes. Non-goals receive no requirement and no implementation work. -->

## Constraints
<!-- Binding constraints the change must respect. Use None when there are none. -->

## Approach
<!-- The selected approach and why. Briefly note the alternatives considered. -->

## Impact
<!-- Affected code, APIs, dependencies, systems, consumers, operations. -->

## Risks
<!-- Risks and their treatment. A High-risk proposal adds compatibility, migration, rollout, rollback, observability, recovery, and risk treatment. Use None for a category the change does not need. -->

## Assumptions
<!-- Assumptions the plan can rely on. Use None when there are none. -->

## Unresolved Decisions
<!-- Every decision that can govern downstream work. This section MUST read None before cold review and operator review. -->
```

Each required section uses `None` when it has no relevant content. The `Unresolved Decisions` section MUST read `None` before cold review and operator review. An unresolved controlled decision blocks cold-review approval and operator approval.

### Proposal Change Control

Any proposal edit after operator approval creates a new version. The edit invalidates the cold review and the operator approval. The new version repeats cold review and operator approval. A format-only edit follows the same path.

A changed upstream input invalidates every affected downstream review.

### Depth Reassessment

Reassess the depth only when classification evidence changes. Evidence can arrive during proposal review, spec derivation, planning, implementation, or final acceptance. Before operator approval, a resolved fact updates the proposal and its depth before cold review. After operator approval, evidence that selects a higher depth stops work and uses proposal change control: revise the proposal, repeat cold review, and obtain operator reapproval before work resumes. Postapproval evidence never lowers the approved depth silently. Retaining the approved higher depth is valid. A lower depth takes effect only through proposal revision, cold review, and operator reapproval.

## The Feature Spec

The feature spec is the behavioral contract. A fresh author derives it after operator approval with `feature-spec-author-prompt.md`. You write it as the delta against the living spec (ADDED/MODIFIED/REMOVED per domain). It drives the implementation plan in writing-plans, the implementation review during execution, and the living-spec sync in finishing.

Save to `docs/design/YYYY-MM-DD-<topic>-spec.md`.

```markdown
# Spec: <Topic>

## Domain: <domain-name>

### ADDED Requirements

#### Requirement: <requirement-name>
The system SHALL <behavioral description>.

##### Scenario: <scenario-name>
- GIVEN <precondition>
- WHEN <trigger>
- THEN <expected outcome>

### MODIFIED Requirements

#### Requirement: <existing-requirement-name>
<!-- Only the changed parts. The sync preserves existing content not mentioned. -->

##### Scenario: <new-or-changed-scenario>
- GIVEN <precondition>
- WHEN <trigger>
- THEN <expected outcome>

### REMOVED Requirements

#### Requirement: <deprecated-requirement-name>
(Brief explanation of why.)
```

**If the domain has a living spec:** Write ADDED/MODIFIED/REMOVED sections relative to the current living spec.

**If the domain is undocumented (behavior exists, no living spec):** Use the existing feature-spec format. Formalize complete relevant post-change behavior: established unchanged baseline behavior and requested changes. Do not defer unchanged behavior to planning or finishing. `ADDED` means addition to the absent living spec, not that every behavior needs implementation work.

**If the domain is genuinely new:** Everything is ADDED. Select this branch only when repository evidence shows the domain is absent. A missing living spec never proves the domain is new.

**If the change has no behavioral impact** (refactoring, internal restructure):

```markdown
# Spec: <Topic>

## No Behavioral Changes

<Brief description of the internal change.>
No requirements added, modified, or removed.
```

**Spec writing rules:**

- Every requirement MUST use RFC 2119 keywords (SHALL, MUST, SHOULD)
- Every requirement MUST have at least one scenario with GIVEN/WHEN/THEN
- Scenarios MUST be testable. If you cannot write a test for a scenario, it is not a behavioral requirement
- Requirements describe WHAT the system does, not HOW: no class names, library choices, or file paths. Those belong in the Approach section of the proposal
- Requirement names must be descriptive and under 50 characters
- Use one `## Domain:` section per affected domain

### Spec Review

Dispatch a `document-review` subagent using `spec-document-reviewer-prompt.md`. One initial review covers one spec version, one complete input set, and one review task.

- **Adjudication:** Before you act on any finding, adjudicate every finding per `receiving-code-review`. Fix endorsed findings through dispatched subagents. The reviewer re-dispatch carries the fixes, the rejection list, and the rejection reasons for confirmation. An unchanged rejection confirmation stays a targeted redispatch
- **Issues found:** Fix the endorsed findings. Dispatch one new complete initial review for the changed version. Loop until the reviewer approves
- **Fundamental issues:** The spec is architecture instead of behavior, or the approach is wrong at the behavioral level. Present the findings to the user. Ask whether to revise the approach. Do not silently rewrite the spec
- Planning starts only after semantic spec-review approval. The workflow requests no operator approval for the feature spec, the plan, or living-spec synchronization.

### Commit

Commit the approved artifacts to the branch:

```bash
git add docs/design/
git commit -m "docs: proposal and feature spec for <topic>"
```

### Transition

Invoke the writing-plans skill. Do NOT invoke any other skill: writing-plans is the only next step.
