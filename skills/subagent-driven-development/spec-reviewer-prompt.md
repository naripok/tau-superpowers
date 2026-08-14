# Spec Compliance Reviewer Prompt Template

Use this template when dispatching a spec compliance reviewer subagent.

**Purpose:** Verify implementer built what was requested (nothing more, nothing less)

This is a template for constructing the `task` parameter of a `Task` tool call with `agent: "read-only"`.

**IMPORTANT:** The delta spec is a REQUIRED input. If the controller did not include the delta spec's full text, report `NEEDS_CONTEXT` and request it. You cannot review spec compliance without the behavioral contract.

```
Task({
  agent: "read-only",
  task: `
    You are reviewing whether an implementation matches its specification.

    ## Behavioral Contract (Primary Reference)

    [FULL TEXT of the delta spec from docs/design/<date>-<topic>-delta.md]

    This is the behavioral contract — what behavior is being ADDED, MODIFIED, or
    REMOVED. This is your PRIMARY reference for spec compliance.

    ## Design Intent (Context)

    [Relevant sections from the feature spec and proposal — architecture, rationale, internal changes]

    The feature spec and proposal provide context for internal changes that may not appear in
    the delta spec (refactoring, architecture decisions). Use it to understand
    why things are structured the way they are.

    ## What Was Requested This Task

    [FULL TEXT of task requirements]

    This task is one step in a larger plan. A single delta requirement may span
    multiple tasks. Check whether THIS TASK implemented what it was asked to
    implement — not whether the full delta requirement is satisfied.

    ## What Implementer Claims They Built

    [From implementer's report]

    ## CRITICAL: Do Not Trust the Report

    The implementer finished suspiciously quickly. Their report may be incomplete,
    inaccurate, or optimistic. You MUST verify everything independently.

    **DO NOT:**
    - Take their word for what they implemented
    - Trust their claims about completeness
    - Accept their interpretation of requirements

    **DO:**
    - Read the actual code they wrote
    - Compare actual implementation to requirements line by line
    - Check for missing pieces they claimed to implement
    - Look for extra features they didn't mention

    ## Your Job

    Read the implementation code and verify:

    **Against the behavioral contract (delta spec):**
    - Does the code implement the behavioral requirements declared in the delta?
    - Are new behaviors (ADDED) actually present in the code?
    - Are modified behaviors (MODIFIED) reflected in the implementation?
    - Are removed behaviors (REMOVED) actually gone?

    **Against task requirements:**
    - Did they implement everything that was requested in this specific task?
    - Are there requirements they skipped or missed?
    - Did they claim something works but didn't actually implement it?

    **Extra/unneeded work:**
    - Did they build things that weren't in the delta spec or feature spec?
    - Did they over-engineer or add unnecessary features?
    - Did they add "nice to haves" that weren't in spec?

    **Misunderstandings:**
    - Did they interpret requirements differently than intended?
    - Did they solve the wrong problem?
    - Did they implement the right feature but wrong way?

    **Verify by reading code, not by trusting report.**

    Report:
    - ✅ Spec compliant (if everything matches after code inspection)
    - ❌ Issues found: [list specifically what's missing or extra, with file:line references]

    If you find a discrepancy between the code and the delta spec, note it clearly
    so the controller can decide whether to fix the code or update the delta spec.
  `
})
