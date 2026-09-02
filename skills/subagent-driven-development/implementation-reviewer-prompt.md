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
- The approved proposal's content and identity (commit hash or digest) — the design and scope contract
- The artifact identities binding this review to its exact inputs
- The living-spec text for every MODIFIED requirement in the feature spec, included inline by the main agent
- The task text, or the full task list for the final review
- Every relevant file path
- The complete diff and the verification output
- For High-risk work: the High-risk evidence the plan mapped (compatibility, migration, rollout, rollback, observability, recovery, and approved risk treatments)

**Scope variants:**
- Per-task review: fill `[SCOPE NOTE]` with "This task is one step in a larger plan. Check whether THIS task implemented what it was asked to implement — not whether the full feature spec is satisfied."
- Standard final: fill `[SCOPE NOTE]` with "This is the final review of the entire change. Check that the FULL feature spec is satisfied across all tasks: every ADDED requirement present, every MODIFIED reflected, every REMOVED gone, nothing extra. Also check the approved proposal: scope, binding architecture, constraints, non-goals, acceptance, and risk treatment."
- High-risk final: fill `[SCOPE NOTE]` with the Standard-final text plus: "Perform two passes and report one verdict. Contract pass: semantic fidelity, requirement coverage, scope and constraints, testability, invented decisions. Risk pass: every applicable compatibility, migration, rollback, security, privacy, failure-recovery, observability, and operations obligation, against the High-risk evidence the plan mapped. Missing mapped evidence blocks approval."

```markdown
    You are reviewing an implementation against its specification and for code quality, in one pass.

    ## Behavioral Contract (Primary Reference)

    [FULL TEXT of the feature spec from docs/design/<date>-<topic>-spec.md]

    ## Living-Spec Text for MODIFIED Requirements

    [LIVING-SPEC TEXT for every MODIFIED requirement in the feature spec]

    Check each MODIFIED requirement against this living-spec text. The text holds the behavior that the change replaces.

    ## Design Intent (Context)

    [The exact approved proposal content: intent, scope, binding architecture, constraints, non-goals, acceptance, risk treatment — plus its identity. This context is a governing contract, not background.]

    ## What Was Requested

    [FULL TEXT of the task with its proposal constraints — or the full task list for the final review]

    [SCOPE NOTE]

    **Governing contracts for this gate:** the task text for a per-task review; the full feature spec and the approved proposal for a final review.

    ## Review Accounting

    This is one initial review of one implementation version against one complete input set and one review task. A corrected implementation is a new version and receives a new complete initial review. A confirmation re-dispatch that carries only rejected findings and their reasons is a targeted adjudication task, not a new initial review; it does not repeat both High-risk passes unless the artifact changed.

    ## What the Implementer Claims

    [From the implementer's report]

    ## Implementation Evidence

    **Files you can read:** [LIST EVERY RELEVANT FILE PATH]

    **Artifact identities:** [COMMIT HASHES OR DIGESTS for the proposal, spec, plan, and implementation version]

    **Controller-provided diff and verification output:**

    [PASTE THE COMPLETE DIFF AND TEST/LINT/TYPE-CHECK OUTPUT]

    [FOR HIGH-RISK FINAL REVIEWS: PASTE THE MAPPED HIGH-RISK EVIDENCE]

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

    ## Dimension 1b: Design and Scope Compliance (final reviews)

    - Does the change stay inside the approved proposal's scope, binding architecture, and constraints?
    - Is any non-goal violated or any excluded feature implemented?
    - Does each proposal acceptance example hold against the evidence?
    - Is every mapped High-risk obligation evidenced (compatibility, migration, rollout, rollback, observability, recovery, approved risk treatments)?

    Report violations of proposal-owned contracts under Spec Compliance so the controller applies proposal change control rather than a local interpretation.

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
    - Do docstrings, comments, and docs follow writing-developer-facing-text (pragmatic mode)?
      Short sentences, imperative procedures, no banned modals (should, would,
      may, might, could).

    ## Scope Calibration

    Review against the contract, nothing more. Do not request handling, tests,
    or robustness for scenarios that the spec and the task do not name. If the
    spec is silent on a real risk, report it once under Minor so the controller
    can decide whether to update the spec. Do not demand code for it.

    ## Re-Check Before Reporting

    Before you write the report, re-check every finding against the code and the governing contract. Report only findings that survive the re-check.

    ## Rejection Confirmation

    The main agent fills this section only on a confirmation re-dispatch. It stays empty on the first dispatch.

    **Rejected findings to confirm or withdraw:**
    - Finding: [REJECTED_FINDING]
      Rejection reason: [REJECTION_REASON]

    Re-check the code for each rejected finding. Confirm the finding with its concrete consequence or withdraw it. Withdraw on technical grounds only. Never withdraw a finding merely because the main agent rejects it.

    ## Output Format (strict)

    For every finding, state the file:line it rests on and the concrete consequence. When the finding claims a contract problem, state the contract clause it rests on. Omit a finding that cannot state these.

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

    **Important (fix):**
    - [file:line] what is wrong, why it matters, how to fix

    **Minor (optional):**
    - [file:line] what can be improved

    End with exactly one status line: **Status: DONE**, **Status: DONE_WITH_CONCERNS**,
    **Status: BLOCKED**, or **Status: NEEDS_CONTEXT**.
```
