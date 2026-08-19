---
name: brainstorming
description: Use before any creative work - creating features, building components, adding functionality, or modifying behavior.
---

# Brainstorming Ideas Into Designs

Turn ideas into an approved proposal and behavioral feature spec through collaborative dialogue.

**Announce at start:** "I'm using the brainstorming skill to refine this idea into a design."

**HARD GATE:** Do NOT invoke any implementation skill, write any code, or scaffold any project until the proposal and feature spec exist, the spec reviewer has approved the feature spec, and the user has approved both artifacts. This applies to every project regardless of perceived simplicity. For truly simple projects the artifacts can be short, but they MUST exist.

## Checklist

Copy this checklist into your working notes and mark each item as you complete it. Complete the items in order:

- [ ] **Read living specs** — check `docs/specs/` for relevant domain specs; they describe current system behavior. If no spec exists for the domain, the feature spec will define its initial requirements
- [ ] **Explore project context** — files, docs, recent commits
- [ ] **Ask clarifying questions** — purpose, constraints, success criteria
- [ ] **Propose 2-3 approaches** — with trade-offs and your recommendation
- [ ] **Present the complete design** — get user approval
- [ ] **Set up the worktree** — invoke using-git-worktrees. All artifacts and code are committed to this branch, never to the default branch
- [ ] **Write the proposal** — `docs/design/YYYY-MM-DD-<topic>-proposal.md`
- [ ] **Write the feature spec** — `docs/design/YYYY-MM-DD-<topic>-spec.md`
- [ ] **Dispatch the spec reviewer** — use `spec-document-reviewer-prompt.md`; loop until approved
- [ ] **User reviews proposal + spec** — if changes are requested: fix, re-run the spec reviewer, re-present
- [ ] **Commit the artifacts to the branch**
- [ ] **Invoke writing-plans** — the only skill that comes next

## Process Flow

```dot
digraph brainstorming {
    "Read living specs\n(docs/specs/)" [shape=box];
    "Explore project context" [shape=box];
    "Ask clarifying questions" [shape=box];
    "Propose 2-3 approaches" [shape=box];
    "Present complete design" [shape=box];
    "User approves design?" [shape=diamond];
    "Set up worktree\n(using-git-worktrees)" [shape=box];
    "Write proposal + feature spec\n(docs/design/)" [shape=box];
    "Dispatch spec reviewer" [shape=box];
    "Spec reviewer approves?" [shape=diamond];
    "User approves artifacts?" [shape=diamond];
    "Commit artifacts to the branch" [shape=box];
    "Invoke writing-plans skill" [shape=doublecircle];

    "Read living specs\n(docs/specs/)" -> "Explore project context";
    "Explore project context" -> "Ask clarifying questions";
    "Ask clarifying questions" -> "Propose 2-3 approaches";
    "Propose 2-3 approaches" -> "Present complete design";
    "Present complete design" -> "User approves design?";
    "User approves design?" -> "Present complete design" [label="no, revise"];
    "User approves design?" -> "Set up worktree\n(using-git-worktrees)" [label="yes"];
    "Set up worktree\n(using-git-worktrees)" -> "Write proposal + feature spec\n(docs/design/)";
    "Write proposal + feature spec\n(docs/design/)" -> "Dispatch spec reviewer";
    "Dispatch spec reviewer" -> "Spec reviewer approves?";
    "Spec reviewer approves?" -> "Write proposal + feature spec\n(docs/design/)" [label="issues found"];
    "Spec reviewer approves?" -> "User approves artifacts?" [label="approved"];
    "User approves artifacts?" -> "Write proposal + feature spec\n(docs/design/)" [label="changes requested"];
    "User approves artifacts?" -> "Commit artifacts to the branch" [label="approved"];
    "Commit artifacts to the branch" -> "Invoke writing-plans skill";
}
```

## The Process

**Understanding the idea:**

- Read `docs/specs/<domain>.md` if it exists — it describes current behavior for the domain
- Check the current project state first (files, docs, recent commits)
- Assess scope before detailed questions: if the request spans multiple independent subsystems, help the user decompose it into sub-projects first. Each sub-project gets its own brainstorm → spec → plan → implementation cycle
- Ask clarifying questions. Batch independent questions in one message. Prefer multiple-choice questions when possible
- Focus on: purpose, constraints, success criteria

**Exploring approaches:**

- Propose 2-3 different approaches with trade-offs
- Lead with your recommended option

**Presenting the design:**

- Present the complete design in one message, scaled to its complexity
- Cover: architecture, components, data flow, error handling, testing
- Get a single approval for the whole design; go back and clarify anything that doesn't make sense

**Design rules:**

- Break the system into units that each have one clear purpose, communicate through well-defined interfaces, and can be understood and tested independently
- For each unit you should be able to answer: what does it do, how is it used, what does it depend on
- Prefer smaller, focused files over large ones that do too much

**Working in existing codebases:**

- Explore the current structure before proposing changes; follow existing patterns
- Include targeted improvements to code this work touches
- Do not propose unrelated refactoring

## The Artifacts

### Proposal

Captures **why** and **what scope**. Save to `docs/design/YYYY-MM-DD-<topic>-proposal.md`.

```markdown
# Proposal: <Topic>

## Intent
<!-- Why are we doing this? What problem does it solve? Why now? -->

## Scope
**In scope:**
<!-- What this change covers -->

**Out of scope:**
<!-- What is explicitly excluded -->

## Approach
<!-- The recommended approach and why. Briefly note alternatives considered. -->

## Impact
<!-- Affected code, APIs, dependencies, systems -->
```

### Feature Spec

The feature spec is the behavioral contract, written as the delta against the living spec (ADDED/MODIFIED/REMOVED per domain). It drives the implementation plan in writing-plans, the implementation review during execution, and the living-spec sync in finishing.

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

**If modifying an existing domain** (living spec exists): write ADDED/MODIFIED/REMOVED sections relative to the current living spec.

**If creating a new domain** (no living spec exists): everything is ADDED.

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
- Scenarios MUST be testable — if you can't write a test for it, it's not a behavioral requirement
- Requirements describe WHAT the system does, not HOW — no class names, library choices, or file paths (those belong in the proposal's Approach section)
- Requirement names descriptive and under 50 characters
- One `## Domain:` section per affected domain

### Spec Review

Dispatch a `document-review` subagent using `spec-document-reviewer-prompt.md`.

- **Issues found:** fix the spec, re-dispatch. Loop until the reviewer approves
- **Fundamental issues** (the spec is architecture instead of behavior; the approach is wrong at the behavioral level): present the findings to the user and ask whether to revise the approach — do not silently rewrite the spec
- Do NOT proceed to the user gate until the reviewer approves

### User Gate

Present both artifacts to the user for review. If they request changes: make them, re-run the spec reviewer, re-present. Proceed only once the user approves.

### Commit

Commit the approved artifacts to the branch:

```bash
git add docs/design/
git commit -m "docs: proposal and feature spec for <topic>"
```

### Transition

Invoke the writing-plans skill. Do NOT invoke any other skill — writing-plans is the only next step.
