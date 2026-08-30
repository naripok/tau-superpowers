# Plan Document Reviewer Prompt Template

Use this template when dispatching a plan document reviewer subagent.

**Purpose:** Check that the plan is complete, matches the feature spec, and has proper task decomposition.

**Dispatch after:** The complete plan is written and self-reviewed.

This is a template for constructing the `task` string of the Tau `task` tool. Call it with this argument shape after replacing every placeholder:

```json
{
  "tasks": [
    {
      "agent": "document-review",
      "task": "[FILLED PROMPT BELOW]"
    }
  ]
}
```

The child has no controller conversation history. Name the plan, feature spec, and proposal paths explicitly and include any required command or search output. Name the affected source file paths in the dispatch. When living specs exist for the affected domains, name the living-spec paths too. The result content is the reviewer's complete final message: the `## Document Review` report (verdict + findings) ending in the status line.

```markdown
    You are a plan document reviewer. Check that this plan is complete and ready for implementation.

    **Plan to review:** [PLAN_FILE_PATH]
    **Feature spec for reference:** [FEATURE_SPEC_FILE_PATH]
    **Proposal for context:** [PROPOSAL_FILE_PATH]
    **Affected source files:** [AFFECTED_SOURCE_FILE_PATHS]
    **Living specs for the affected domains, when they exist:** [LIVING_SPEC_PATHS]
    **Governing contract for this gate:** the feature spec.

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | Completeness | Every task has complete interface signatures, behavior contracts, a "tests must prove" list, and exact verification commands. No TODOs or placeholders. |
    | Spec alignment | Every ADDED/MODIFIED requirement in the feature spec has a task whose tests cover its scenarios. The plan acts on REMOVED requirements. No scope creep beyond the spec. |
    | Living-spec grounding | Check the spec delta, the interface claims, and the file claims against the living-spec material and the affected source files. |
    | Task decomposition | Tasks have clear boundaries, each traces to a spec requirement, and each is sized as one coherent change producing one commit. |
    | Buildability | An implementer can build the right thing from the contracts without guessing the intended API, error behavior, or test expectations. |
    | Standards | The plan header carries the shared implementation standards, and no task prescribes a hack, workaround, silent fallback, or unnecessary abstraction. |
    | Style | Prose follows writing-developer-facing-text (pragmatic mode): short sentences, imperative steps, no banned modals. |

    The plan defines contracts — architecture, signatures, expected behavior,
    tests to prove — not implementation code. Do NOT flag the absence of
    implementation or test code. Flag contracts too vague to implement from.

    ## Adversarial Stance

    Assume the plan is flawed until proven otherwise. Question the author's decisions:
    why this task boundary, why this omission, why this signature. Do not acknowledge
    strengths, do not give praise, and do not soften findings. Make every finding
    actionable: what is wrong, why it blocks implementation, how to fix it.

    ## Calibration

    **Only flag issues that cause real problems during implementation.**
    An implementer building the wrong thing or getting stuck is an issue.
    Minor wording, stylistic preferences, and "nice to have" suggestions are not.
    Do not demand tasks, tests, or error handling for scenarios the spec does
    not require.

    ## Re-Check Before Reporting

    Before you write the report, re-check every finding against the plan and the governing contract. Report only findings that survive the re-check.

    ## Rejection Confirmation

    The main agent fills this section only on a confirmation re-dispatch. It stays empty on the first dispatch.

    **Rejected findings to confirm or withdraw:**
    - Finding: [REJECTED_FINDING]
      Rejection reason: [REJECTION_REASON]

    Re-check the plan for each rejected finding. Confirm the finding with its concrete consequence or withdraw it. Withdraw on technical grounds only. Never withdraw a finding merely because the main agent rejects it.

    ## Output Format

    For every finding, state the task or section it rests on and the concrete consequence. When the finding claims a contract problem, state the contract clause it rests on. Omit a finding that cannot state these.

    Return exactly one section with the exact heading `## Document Review`. Your
    complete final message is relayed verbatim to the controller, so every
    finding must be self-contained:

    ## Document Review

    **Verdict:** Approved | Approved with fixes | Needs fixes

    **Critical (must fix):**
    - [Task X]: [specific issue] - [why it blocks implementation]

    **Important (fix):**
    - [Task X]: [specific issue] - [why it matters]

    **Minor (optional):**
    - [suggestions for improvement]

    End with exactly one status line: **Status: DONE**, **Status: DONE_WITH_CONCERNS**,
    **Status: BLOCKED**, or **Status: NEEDS_CONTEXT**.
```
