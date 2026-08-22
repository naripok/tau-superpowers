---
name: verification-before-completion
description: Use when about to claim work is complete, fixed, or passing, before committing or creating a pull request
---

# Verification Before Completion

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you have not run the verification command in this message, you cannot claim it passes. Violating the letter of this rule is violating its spirit.

## The Gate

Before claiming any status or expressing satisfaction:

1. **IDENTIFY:** What command proves this claim?
2. **RUN:** Execute the full command — fresh, complete
3. **READ:** Full output, exit code, failure count
4. **CHECK:** Does the output match the claim?
   - No → state the actual status, with evidence
   - Yes → state the claim, with the evidence
5. Only then make the claim

Skipping any step is lying, not checking.

## Claims and Required Evidence

| Claim | Requires | Not sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test of the original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle checked | Test passes once |
| Agent completed | VCS diff shows the changes | Agent reports "success" |
| Requirements met | Line-by-line checklist against the spec | Tests passing |

## Red Flags — STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!")
- About to commit/push/PR without verification
- Trusting an agent's success report without checking the diff
- Relying on partial verification
- Any wording implying success without having run verification

## Patterns

**Tests:**

```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Regression tests (red-green):**

```
✅ Write test → run (passes with fix) → revert fix → run (MUST FAIL) → restore fix → run (passes)
❌ "I've written a regression test" (without the red-green check)
```

**Build:**

```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (lint doesn't check compilation)
```

**Requirements:**

```
✅ Re-read the spec → checklist → verify each item → report gaps or completion
❌ "Tests pass, phase complete"
```

**Agent delegation:**

```
✅ Agent reports success → check VCS diff → verify changes → report actual state
❌ Trust the agent's report
```

## When to Apply

Always, before:

- Any success/completion claim, expression of satisfaction, or positive statement about work state
- Committing, PR creation, marking a task complete
- Moving to the next task
- Accepting a delegated agent's result
