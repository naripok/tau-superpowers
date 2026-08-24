# Implementation Reviewer Prompt Template

Use this template when dispatching the implementation reviewer subagent — for a single task, a checkpoint batch, or the final whole-change review.

**Purpose:** Check, in one pass, that the implementation matches its specification (spec compliance) and is well-built (code quality). The report has one section per dimension.

This is a template for constructing the `task` string of the Tau `task` tool. Call it with this argument shape after replacing every placeholder:

```json
{
  "tasks": [
    {
      "agent": "code-review",
      "task": "[FILLED PROMPT BELOW]"
    }
  ]
}
```

**Required inputs:**
- The feature spec's full text — without it the reviewer reports NEEDS_CONTEXT
- The task text, or the full task list for the final review
- Every relevant file path
- The complete diff and the verification output

**Scope variants:**
- Per-task review: fill `[SCOPE NOTE]` with "This task is one step in a larger plan. Check whether THIS task implemented what it was asked to implement — not whether the full feature spec is satisfied."
- Final review: fill `[SCOPE NOTE]` with "This is the final review of the entire change. Check that the FULL feature spec is satisfied across all tasks: every ADDED requirement present, every MODIFIED reflected, every REMOVED gone, nothing extra."

```markdown
    You are reviewing an implementation against its specification and for code quality, in one pass.

    ## Behavioral Contract (Primary Reference)

    [FULL TEXT of the feature spec from docs/design/<date>-<topic>-spec.md]

    ## Design Intent (Context)

    [Relevant proposal sections: architecture, rationale, internal changes]

    ## What Was Requested

    [FULL TEXT of the task — or the full task list for the final review]

    [SCOPE NOTE]

    ## What the Implementer Claims

    [From the implementer's report]

    ## Implementation Evidence

    **Files you can read:** [LIST EVERY RELEVANT FILE PATH]

    **Controller-provided diff and verification output:**

    [PASTE THE COMPLETE DIFF AND TEST/LINT/TYPE-CHECK OUTPUT]

    You can run read-only bash (git diff/log/status, grep/rg/find) to check
    claims. Never change the state of the repository. If required evidence is
    missing, report NEEDS_CONTEXT and name what the controller must provide.

    ## Do Not Trust the Report

    The implementer's report can be incomplete, inaccurate, or optimistic. Check
    everything independently: read the actual code, compare it to the contract
    line by line, and look for missing pieces and unrequested extras. Review
    adversarially: assume the work is flawed until the code proves otherwise,
    question the implementer's decisions, and report only actionable findings.
    No praise.

    ## Dimension 1: Spec Compliance

    - Is every feature-spec requirement relevant to this scope implemented?
      ADDED present, MODIFIED reflected, REMOVED gone?
    - Did they skip or miss requested behavior? Claim that something works when it does not?
    - Did they build anything NOT in the spec or task: over-engineering,
      "nice to haves", speculative edge-case handling?
    - Did they misinterpret a requirement or solve the wrong problem?

    If you find a discrepancy between code and spec, note it explicitly so the
    controller can decide whether to fix the code or update the feature spec.

    ## Dimension 2: Code Quality

    - Does each file have one clear responsibility with a well-defined interface?
    - Is the implementation the simplest code that satisfies the contract? Flag
      speculative edge-case handling, defensive checks for states that cannot
      occur, and error paths that no requirement names.
    - Do tests check real behavior (not mocks), cover the contract's scenarios,
      and have docstrings saying what behavior they prove and why?
    - Is the code clean, maintainable, well-named? Security or performance problems?
    - Is cyclomatic complexity low — a single valid path per function where possible?
    - Are invalid states unrepresentable (no untyped escapes or stringly-typed states)?
    - Any unnecessary abstractions, unnecessary fallbacks, or hacks/workarounds?
    - Do docstrings say what and why (not how)? Does documentation describe only
      the current behavior, with no references to old states or removed behavior?

    ## Scope Calibration

    Review against the contract, nothing more. Do not request handling, tests,
    or robustness for scenarios that the spec and the task do not name. If the
    spec is silent on a real risk, report it once under Minor so the controller
    can decide whether to update the spec. Do not demand code for it.

    ## Output Format (strict)

    Return exactly one section with the exact heading `## Code Review`. Your
    complete final message is relayed verbatim to the controller, so every
    finding must be self-contained:

    ## Code Review

    **Verdict:** Approved | Approved with fixes | Needs fixes

    ### Spec Compliance

    **Verdict:** Compliant | Issues found

    - ✅ [what was checked, with file:line references]
    - ❌ [what is missing, extra, or wrong, with file:line references]

    ### Code Quality

    **Critical (must fix):**
    - [file:line] what is wrong, why it matters, how to fix

    **Important (should fix):**
    - [file:line] what is wrong, why it matters, how to fix

    **Minor (nice to have):**
    - [file:line] what can be improved

    End with exactly one status line: **Status: DONE**, **Status: DONE_WITH_CONCERNS**,
    **Status: BLOCKED**, or **Status: NEEDS_CONTEXT**.
```
