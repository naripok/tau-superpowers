---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write an implementation plan that defines **architecture, interfaces, and expected behavior** and stops there. The implementer (a skilled subagent or inline executor) decides the exact implementation within those contracts.

A plan task specifies which files to touch. It specifies the signatures and behavior contracts of new or changed functions and types. It specifies which behaviors tests must prove and the exact verification commands. It does NOT contain implementation code or test code.

Assume the implementer is a skilled developer with zero context for our codebase. Give them complete contracts and exact commands. Trust them to write the code. DRY. YAGNI. TDD. One commit per task.

**Announce at start:** "Using writing-plans to create the implementation plan."

**Context:** Run inside the worktree created during brainstorming. Never plan or implement on the default branch.

**Save plans to:** `docs/plans/YYYY-MM-DD-<topic>.md`
- (User preferences for plan location override this default)

**Style:** write the plan per the writing-developer-facing-text skill, pragmatic mode.

## Scope Check

If the spec covers multiple independent subsystems, check that brainstorming broke it into sub-project specs. If it did not, suggest separate plans, one per subsystem. Each plan must produce working, testable software on its own.

## Step 1: Read Inputs

Read these artifacts before you write anything:

1. **The proposal** (`docs/design/YYYY-MM-DD-<topic>-proposal.md`): intent, scope, approach, impact
2. **The feature spec** (`docs/design/YYYY-MM-DD-<topic>-spec.md`): the behavioral contract: ADDED/MODIFIED/REMOVED requirements with SHALL/MUST/SHOULD and GIVEN/WHEN/THEN scenarios
3. **The living specs** (`docs/specs/<domain>.md`): current system behavior for affected domains, if these specs exist

Every task in the plan must map to a requirement in the feature spec.

## Step 2: File Structure

Map which files the plan creates or modifies and what each file is responsible for. This step fixes the decomposition decisions.

- Design units with clear boundaries and well-defined interfaces. Each file has one clear responsibility.
- Prefer smaller, focused files over large ones that do too much.
- Files that change together live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If a file that you modify became unwieldy, include a split in the plan.

This structure informs task decomposition. Each task produces one self-contained commit.

## Step 3: Write Tasks

Write tasks that implement the feature spec. **Task sizing:** one task = one implementer dispatch = one commit. A task is a coherent component (or one aspect of one) plus its tests. It must be small enough to hold in context at once.

### Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach — from proposal]

**Tech Stack:** [Key technologies/libraries]

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-developer-facing-text prose.

**Feature spec:** `docs/design/YYYY-MM-DD-<topic>-spec.md` (the behavioral contract)

---
```

Follow the header with a **commands section**. Give the exact project commands that implementers must run: test a single file, run the full suite, lint, format-check, type-check. Include any environment setup that they need. Implementers do not guess commands.

### Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py` — [one-line responsibility]
- Modify: `exact/path/to/existing.py` — [what changes]
- Test: `tests/exact/path/to/test.py`

**Spec requirement:** [Which ADDED/MODIFIED/REMOVED requirement this task implements]

**Interface:**
- `new_function(arg: Type, opt: Type = default) -> ReturnType` — [contract: what it does, what it returns, errors raised, edge cases]
- `ExistingClass.method(...)` — [signature and/or behavior change: before → after]
- [Any new types, dataclasses, or constants: fields and meaning]

**Behavior:**
- [Observable behavior: inputs → outputs, error and boundary cases, interactions with existing code]

**Tests must prove:**
- [Behavior 1 — one named test per behavior]
- [Behavior 2]

**Check:** `[exact commands]` — expected: all pass

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add <files> && git commit -m "feat: <specific change>"`
````

### Contract Completeness (No Placeholders)

Every task must contain complete contracts. Never write these **plan failures**:

- Missing or vague signatures ("add a helper function", "update the method")
- Unspecified behavior ("handle errors appropriately", "add validation")
- Test lists like "write tests for the above" without naming the behaviors to prove
- "TBD", "TODO", "implement later", "fill in details"
- "Similar to Task N": repeat the contract, because readers can read tasks out of order
- References to types, functions, or methods not defined in any task
- Tasks without verification commands

The plan does NOT contain:

- Implementation code or test code
- Step-by-step coding instructions (the implementer follows TDD on their own)

## Implementation Standards (Include in Every Plan)

Every plan embeds the shared code standards in its header so that implementers and reviewers apply them consistently:

- **DRY**: duplicated logic and repeated test patterns exist once.
- **Minimal implementation (YAGNI)**: the simplest code that satisfies the contract of the task. No speculative edge-case handling, no defensive checks for states that cannot occur, no unrequested error paths.
- **Low cyclomatic complexity**: code must encode a single valid path whenever possible. Keep branches shallow and conditionals honest.
- **Type safety**: invalid system states must not be representable by the type system. Use precise types rather than untyped escapes or stringly-typed states.
- **No unnecessary abstractions**: prefer simple, direct solutions. If a real caller needs indirection, add it. Otherwise, do not add it.
- **No unnecessary fallbacks**: prefer explicit error handling. Silent defaults that mask failures are bugs.
- **No hacks or workarounds**: implement the correct, complete solution by design. Never write a "fix later" workaround.
- **Informative docstrings**: application code: what the code does and why, not how. Tests: what behavior the test proves and why the test is needed.
- **Documentation of current state only**: docs describe the current implemented behavior and why it is that way, never old system states or removed behavior.
- **Simple English**: docstrings, comments, and documentation follow the writing-developer-facing-text skill, pragmatic mode.

## Step 4: Self-Review

After you write the complete plan, check it yourself before you dispatch the reviewer:

**1. Spec coverage (spec → plan):** For each ADDED/MODIFIED requirement in the feature spec, is there a task whose "Tests must prove" list covers its scenarios? A requirement without a task and tests is a plan failure.

**2. Reverse coverage (plan → spec):** Does every task map to a feature-spec requirement? Tasks that do not are scope creep.

**3. Placeholder scan:** Search for the patterns from "Contract Completeness" above. Fix them.

**4. Signature consistency:** Do the types, signatures, and names used in later tasks match what earlier tasks define? A function named `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.

**5. Standards coverage:** Does every contract respect the Implementation Standards? A task that prescribes a workaround, a silent fallback, or an unnecessary abstraction is a plan failure.

Fix issues inline, then continue. Add missing tasks. Add missing test behaviors.

## Step 5: Plan Review

Dispatch a `document-review` subagent using `plan-document-reviewer-prompt.md` to check plan completeness and spec alignment.

- **Issues found:** fix the plan, then re-dispatch the reviewer. Loop until the reviewer approves.
- Do NOT proceed to execution until the reviewer approves.

## Step 6: Commit and Execute

Commit the approved plan to the branch:

```bash
git add docs/plans/
git commit -m "docs: implementation plan for <topic>"
```

Then execute:

- **Default:** invoke subagent-driven-development: fresh implementer subagent per task, one review pass per task
- **Trivial plans** (1-2 small tasks): executing-plans inline is acceptable

State which you are using. Do not ask the operator to choose.
