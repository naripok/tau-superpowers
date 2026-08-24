---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
---

# Systematic Debugging

## Overview

Random fixes waste time and create new bugs. Quick patches mask underlying issues.

**Core principle:** ALWAYS find the root cause before you attempt a fix. A symptom fix is a failure.

**Violating the letter of this process is violating the spirit of debugging.**

## The Iron Law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you have not completed Phase 1, you cannot propose fixes.

## When to Use

Use for ANY technical issue:
- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**ESPECIALLY when:**
- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You have already tried multiple fixes
- A previous fix did not work
- You do not fully understand the issue

Do not skip it for simple bugs, hurry, or pressure — systematic is faster than thrashing.

## The Four Phases

You MUST complete each phase before you proceed to the next.

### Phase 1: Root Cause Investigation

**BEFORE you attempt ANY fix:**

1. **Read Error Messages Carefully**
   - Do not skip past errors or warnings
   - They often contain the exact solution
   - Read stack traces completely
   - Note line numbers, file paths, error codes

2. **Reproduce Consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - Does it happen every time?
   - If it is not reproducible → gather more data. Do not guess

3. **Check Recent Changes**
   - What changed that can cause this?
   - Git diff, recent commits
   - New dependencies, config changes
   - Environmental differences

4. **Gather Evidence in Multi-Component Systems**

   **WHEN the system has multiple components (CI → build → signing, API → service → database):**

   **BEFORE proposing fixes, add diagnostic instrumentation:**
   ```
   For EACH component boundary:
     - Log what data enters component
     - Log what data exits component
     - Check environment/config propagation
     - Check state at each layer

   Run once to gather evidence showing WHERE it breaks
   THEN analyze evidence to identify failing component
   THEN investigate that specific component
   ```

   **Example (multi-layer system):**
   ```bash
   # Layer 1: Workflow
   echo "=== Secrets available in workflow: ==="
   echo "IDENTITY: ${IDENTITY:+SET}${IDENTITY:-UNSET}"

   # Layer 2: Build script
   echo "=== Env vars in build script: ==="
   env | grep IDENTITY || echo "IDENTITY not in environment"

   # Layer 3: Signing script
   echo "=== Keychain state: ==="
   security list-keychains
   security find-identity -v

   # Layer 4: Actual signing
   codesign --sign "$IDENTITY" --verbose=4 "$APP"
   ```

   **This reveals:** Which layer fails (secrets → workflow ✓, workflow → build ✗)

5. **Trace Data Flow**

   **WHEN the error is deep in the call stack:**

   See `root-cause-tracing.md` in this directory for the complete backward tracing technique.

   **Quick version:**
   - Where does the bad value originate?
   - What called this with the bad value?
   - Keep tracing up until you find the source
   - Fix at the source, not at the symptom

### Phase 2: Pattern Analysis

**Find the pattern before fixing:**

1. **Find Working Examples**
   - Locate similar working code in the same codebase
   - Which working code is similar to the broken code?

2. **Compare Against References**
   - If you implement a pattern, read the reference implementation COMPLETELY
   - Do not skim. Read every line
   - Understand the pattern fully before you apply it

3. **Identify Differences**
   - What is different between the working and the broken code?
   - List every difference, even the smallest
   - Do not assume "that can't matter"

4. **Understand Dependencies**
   - What other components does this need?
   - What settings, config, environment?
   - What assumptions does it make?

### Phase 3: Hypothesis and Testing

**Scientific method:**

1. **Form Single Hypothesis**
   - State clearly: "I think X is the root cause because Y"
   - Write it down
   - Be specific, not vague

2. **Test Minimally**
   - Make the SMALLEST possible change to test the hypothesis
   - One variable at a time
   - Do not fix multiple things at once

3. **Check Before Continuing**
   - Did it work? Yes → Phase 4
   - Did not work? Form a NEW hypothesis
   - DO NOT add more fixes on top

4. **When You Do Not Know**
   - Say "I don't understand X"
   - Do not pretend to know
   - Ask for help
   - Research more

### Phase 4: Implementation

**Fix the root cause, not the symptom:**

1. **Create Failing Test Case**
   - The simplest possible reproduction
   - If you can automate it, write an automated test
   - If there is no framework, write a one-off test script
   - You MUST have this test before you fix
   - Use the `test-driven-development` skill to write proper failing tests

2. **Implement Single Fix**
   - Address the identified root cause
   - ONE change at a time
   - No "while I'm here" improvements
   - No bundled refactoring

3. **Check the Fix**
   - Does the test pass?
   - Do all other tests still pass?
   - Is the issue actually resolved?

4. **If the Fix Does Not Work**
   - STOP
   - Count: How many fixes have you tried?
   - If < 3: Return to Phase 1, re-analyze with new information
   - **If ≥ 3: STOP and question the architecture (step 5 below)**
   - DO NOT attempt Fix #4 without an architectural discussion

5. **If 3+ Fixes Failed: Question Architecture**

   **Pattern indicating architectural problem:**
   - Each fix reveals new shared state/coupling/problem in a different place
   - Fixes require "massive refactoring" to implement
   - Each fix creates new symptoms elsewhere

   **STOP and question fundamentals:**
   - Is this pattern fundamentally sound?
   - Are we "sticking with it through sheer inertia"?
   - Must we refactor the architecture instead of continuing to fix symptoms?

   **Discuss with your human partner before you attempt more fixes**

   This is NOT a failed hypothesis - this is a wrong architecture.

## Red Flags and Rationalizations

If you catch yourself thinking any of these, STOP and take the action:

| Thought | Action |
|---------|--------|
| "Quick fix for now, investigate later" | Return to Phase 1. |
| "Just try changing X and see if it works" | Form a hypothesis first (Phase 3). |
| "It's probably X, let me fix that" / "I see the problem, let me fix it" | Seeing symptoms ≠ understanding the root cause. Investigate first. |
| "I don't fully understand but this might work" | You do not know. Say so. Research more. |
| "Here are the main problems: [fixes]" / proposing solutions before tracing data flow | That is a symptom list, not an investigation. Trace the data first. |
| "Add multiple changes, run tests" / "Multiple fixes at once saves time" | ONE change at a time — you cannot isolate what worked. |
| "Skip the test, I'll manually verify" / "I'll write the test after the fix works" | Test first. A test written first proves the fix. |
| "Pattern says X but I'll adapt it differently" / "Reference too long, I'll adapt" | Read the reference completely. Partial understanding guarantees bugs. |
| "Issue is simple, don't need process" | Simple issues have root causes too. The process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| **"One more fix attempt" (after 2+ failures)** | 3+ failures = an architectural problem. Question the fundamentals. Discuss with your human partner before more fixes. |
| **Each fix reveals a new problem in a different place** | Same signal: wrong architecture, not failed hypothesis. See Phase 4.5. |

**If you recognize a thought: STOP. Do the paired action before more code.**

## Signals You're Doing It Wrong

**Watch for these redirections:**
- "Is that not happening?" - You made an assumption without a check
- "Will it show us...?" - You did not add evidence gathering
- "Stop guessing" - You are proposing fixes without understanding
- "Step back" / "What are you assuming?" - Re-examine core assumptions, not the symptoms only
- "We're stuck?" (frustrated) - Your approach is not working

**When you see these:** STOP. Return to Phase 1.

## Quick Reference

| Phase | Key Activities | Success Criteria |
|-------|---------------|------------------|
| **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form a theory, test minimally | Confirmed or new hypothesis |
| **4. Implementation** | Create a test, fix, check | Bug resolved, tests pass |

## When Process Reveals "No Root Cause"

If systematic investigation reveals that the issue is truly environmental, timing-dependent, or external:

1. You have completed the process
2. Document what you investigated
3. Implement appropriate handling (retry, timeout, error message)
4. Add monitoring/logging for future investigation

**But:** most "no root cause" cases are incomplete investigation.

## Supporting Techniques

These techniques are part of systematic debugging. You can find them in this directory:

- **`root-cause-tracing.md`** - Trace bugs backward through the call stack to find the original trigger
- **`defense-in-depth.md`** - Add validation at multiple layers after you find the root cause
- **`condition-based-waiting.md`** - Replace arbitrary timeouts with condition polling

**Related skills:**
- **test-driven-development** - For creating the failing test case (Phase 4, Step 1)
- **verification-before-completion** - Check that the fix worked before you claim success
