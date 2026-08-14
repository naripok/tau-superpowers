---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Save plans to:** `docs/plans/YYYY-MM-DD-<topic>.md`
- (User preferences for plan location override this default)

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## Step 1: Read Inputs

Read these three artifacts before writing anything:

1. **The proposal** (`docs/design/YYYY-MM-DD-<topic>-proposal.md`) — intent, scope, approach, impact
2. **The feature spec** (`docs/design/YYYY-MM-DD-<topic>-spec.md`) — behavioral requirements with SHALL/MUST/SHOULD and GIVEN/WHEN/THEN scenarios
3. **The living specs** (`docs/specs/<domain>.md`) — current system behavior for affected domains (may not exist yet)

These are your source material. Every task in the plan must trace back to a requirement in the feature spec.

## Step 2: Write the Delta Spec

Write the delta spec FIRST, before the file structure and tasks. The delta spec is derived by comparing the feature spec (proposed behavior) against the living spec (current behavior). It declares what behavioral requirements are changing.

Save to: `docs/design/YYYY-MM-DD-<topic>-delta.md`

**Why delta spec before tasks:** The delta spec is the behavioral contract. Tasks implement it. Writing tasks first and backfilling the delta spec produces a spec that mirrors the implementation rather than driving it. The delta spec must stand on its own as a complete statement of behavioral change — tasks are the execution plan, not the specification.

### Delta Spec Format

```markdown
# Delta: <Feature Name>

## Domain: <domain-name>

### ADDED Requirements

#### Requirement: <requirement-name>
The system SHALL do something new.

##### Scenario: <scenario-name>
- GIVEN <precondition>
- WHEN <trigger>
- THEN <expected outcome>

### MODIFIED Requirements

#### Requirement: <existing-requirement-name>
##### Scenario: <new-or-changed-scenario>
- GIVEN <precondition>
- WHEN <trigger>
- THEN <expected outcome>

### REMOVED Requirements

#### Requirement: <deprecated-requirement-name>
(Brief explanation of why.)
```

### How to Derive the Delta

- **If a living spec exists for the domain:** Compare the feature spec against it. Requirements that are new → ADDED. Requirements that already exist but are changing → MODIFIED (include only the changed parts). Requirements being removed → REMOVED.
- **If no living spec exists (new domain):** Everything in the feature spec is ADDED. Copy the requirements from the feature spec into ADDED sections.
- **If the feature spec declares "No Behavioral Changes":** The delta spec also declares "No Behavioral Changes."

### Multi-Domain Deltas

If the feature touches multiple domains, include a section for each:

```markdown
# Delta: <Feature Name>

## Domain: auth
### ADDED Requirements
...

## Domain: notifications
### MODIFIED Requirements
...
```

### Non-Behavioral Changes

If the change has no behavioral impact (refactoring, bug fix that doesn't change requirements, performance improvement), declare it explicitly:

```markdown
# Delta: <Feature Name>

## No Behavioral Changes

<Brief description of the internal change.>
No requirements added, modified, or removed.
```

The sync step in finishing-a-development-branch skips living spec updates when this is declared.

### Delta Spec Conventions

- **ADDED:** A new behavioral requirement. The full requirement text + all scenarios.
- **MODIFIED:** Only the changed parts (a new scenario, a changed description). The sync process preserves existing content not mentioned in the delta.
- **REMOVED:** The requirement is deprecated. Brief explanation required.
- Use SHALL/MUST/SHOULD keywords (RFC 2119) for requirement strength.
- Scenarios use GIVEN/WHEN/THEN format.
- **No implementation details** — class names, library choices, file paths belong in the proposal, not the delta.

## Step 3: File Structure

Map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Step 4: Write Tasks

Write bite-sized tasks that implement the delta spec. Every task must trace to a requirement in the delta spec.

### Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

### Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach — from proposal]

**Tech Stack:** [Key technologies/libraries]

**Feature spec:** `docs/design/YYYY-MM-DD-<topic>-spec.md`

**Delta spec:** `docs/design/YYYY-MM-DD-<topic>-delta.md`

---
```

### Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Delta requirement:** [Which ADDED/MODIFIED/REMOVED requirement this task implements]

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

### No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

### Remember
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Every task traces to a delta spec requirement

## Step 5: Self-Review

After writing the complete plan and delta spec, look at everything with fresh eyes. This is a checklist you run yourself — not a subagent dispatch.

**1. Feature spec coverage (spec → delta):** For each requirement in the feature spec, can you point to a corresponding ADDED/MODIFIED/REMOVED entry in the delta spec? List any gaps. A feature spec requirement with no delta entry is a plan failure.

**2. Delta coverage (delta → plan):** For each ADDED/MODIFIED requirement in the delta spec, can you point to a task with a corresponding failing test? List any gaps. A requirement without a test is a plan failure.

**3. Reverse coverage (plan → delta + spec):** Does every task in the plan map to something in the delta spec or the feature spec? Tasks that don't map to either are scope creep.

**4. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**5. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task. If you find a delta requirement with no test, add the test step.

**Dispatch plan reviewer.** After the self-review passes, dispatch a read-only subagent using `plan-document-reviewer-prompt.md` to verify plan completeness and spec alignment. This is required — the self-review catches what you can see, the plan reviewer catches what you miss.

**If the reviewer finds issues:** Fix the plan, then re-dispatch the reviewer. Loop until the reviewer approves.

**Do NOT proceed to the execution handoff until the plan reviewer approves.**

## Execution Handoff

After saving the plan and delta spec, ask the user which execution approach to use:

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use subagent-driven-development
- Fresh subagent per task + two-stage review

**If Inline Execution chosen:**
- **REQUIRED SUB-SKILL:** Use executing-plans
- Batch execution with checkpoints for review
