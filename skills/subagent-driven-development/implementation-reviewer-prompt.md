# Implementation Reviewer Prompt Template

Use this template when dispatching the implementation reviewer subagent — for a single task, a checkpoint batch, or the final whole-change review.

**Purpose:** Verify, in one pass, that the implementation matches its specification (spec compliance) and is well-built (code quality). The report has one section per dimension.

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

**Required inputs:** the feature spec's full text (without it the reviewer reports NEEDS_CONTEXT), the task text (or full task list for the final review), every relevant file path, the complete diff, and the verification output.

**Scope variants:**
- Per-task review: fill `[SCOPE NOTE]` with "This task is one step in a larger plan. Check whether THIS task implemented what it was asked to implement — not whether the full feature spec is satisfied."
- Final review: fill `[SCOPE NOTE]` with "This is the final review of the entire change. Verify the FULL feature spec is satisfied across all tasks: every ADDED requirement present, every MODIFIED reflected, every REMOVED gone, nothing extra."

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

    **Files you may read:** [LIST EVERY RELEVANT FILE PATH]

    **Controller-provided diff and verification output:**

    [PASTE THE COMPLETE DIFF AND TEST/LINT/TYPE-CHECK OUTPUT]

    You may run read-only bash (git diff/log/status, grep/rg/find) to verify, but
    never change the state of the repository. If required evidence is missing,
    report NEEDS_CONTEXT and identify exactly what the controller must provide.

    ## Do Not Trust the Report

    The implementer's report may be incomplete, inaccurate, or optimistic. Verify
    everything independently: read the actual code, compare it to the contract
    line by line, check for missing pieces and unrequested extras. Review
    adversarially — assume the work is flawed until proven otherwise, question
    the implementer's decisions, and report only actionable findings, no praise.

    ## Dimension 1: Spec Compliance

    - Is every feature-spec requirement relevant to this scope implemented?
      ADDED present, MODIFIED reflected, REMOVED gone?
    - Did they skip or miss requested behavior? Claim something works that doesn't?
    - Did they build anything NOT in the spec or task (over-engineering, "nice to haves")?
    - Did they misinterpret a requirement or solve the wrong problem?

    If you find a discrepancy between code and spec, note it explicitly so the
    controller can decide whether to fix the code or update the feature spec.

    ## Dimension 2: Code Quality

    - Does each file have one clear responsibility with a well-defined interface?
    - Do tests verify real behavior (not mocks), cover edge cases, and have
      docstrings saying what behavior they prove and why?
    - Is the code clean, maintainable, well-named? Security or performance concerns?
    - Is cyclomatic complexity low — a single valid path per function where possible?
    - Are invalid states unrepresentable (no untyped escapes or stringly-typed states)?
    - Any unnecessary abstractions, unnecessary fallbacks, or hacks/workarounds?
    - Do docstrings say what and why (not how)? Does documentation describe only
      the current behavior, with no references to old states or removed behavior?

    ## Output Format (strict)

    Return exactly one section with the exact heading `## Code Review`. Your
    complete final message is relayed verbatim to the controller, so every
    finding must be self-contained:

    ## Code Review

    **Verdict:** Approved | Approved with fixes | Needs fixes

    ### Spec Compliance

    **Verdict:** Compliant | Issues found

    - ✅ [what was verified, with file:line references]
    - ❌ [what is missing, extra, or wrong, with file:line references]

    ### Code Quality

    **Critical (must fix):**
    - [file:line] what's wrong, why it matters, how to fix

    **Important (should fix):**
    - [file:line] what's wrong, why it matters, how to fix

    **Minor (nice to have):**
    - [file:line] what could be improved

    End with exactly one status line: **Status: DONE**, **Status: DONE_WITH_CONCERNS**,
    **Status: BLOCKED**, or **Status: NEEDS_CONTEXT**.
```
