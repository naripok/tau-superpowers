# Spec Document Reviewer Prompt Template

Use this template when dispatching a spec document reviewer subagent.

**Purpose:** Verify the feature spec is complete, truly behavioral, and ready for implementation planning.

**Dispatch after:** Feature spec is written to `docs/design/`

This is a template for constructing the `task` parameter of a `Task` tool call with `agent: "read-only"`.

```
Task({
  agent: "read-only",
  task: `
    You are reviewing whether a feature spec is complete, truly behavioral, and ready for implementation planning.

    **Spec to review:** [SPEC_FILE_PATH]
    **Proposal for context:** [PROPOSAL_FILE_PATH]

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | Behavioral language | Every requirement uses SHALL/MUST/SHOULD (RFC 2119). No vague "should" or "needs to" without the keyword. |
    | Scenario format | Every requirement has at least one scenario with GIVEN/WHEN/THEN structure. |
    | Testability | Each scenario is concrete enough to write an automated test for. If you can't imagine a test, the scenario is too vague. |
    | No implementation details | No class names, function names, library choices, file paths, or architectural decisions in the spec. These belong in the proposal's Approach section. |
    | Completeness vs proposal | The spec covers everything the proposal says is in scope. No missing behavioral requirements. |
    | No placeholders | No "TBD", "TODO", incomplete sections, or vague requirements. |
    | Consistency | No internal contradictions between requirements. No conflicting scenarios. |
    | Scope | Focused enough for a single implementation plan — not covering multiple independent subsystems. |
    | YAGNI | No unrequested features or over-engineering. |

    ## Critical: Architecture in Disguise

    The most common spec failure is writing architecture instead of behavior. Flag these patterns:

    - "Using [library/framework] to..." → implementation detail, not behavior
    - "The [ClassName] will..." → internal structure, not observable behavior
    - "Stored in [database/file format]..." → implementation choice, not requirement
    - Requirements that describe HOW instead of WHAT → belongs in proposal, not spec

    A good spec requirement answers: "What does the system DO that someone can observe or test?" not "How is the system built?"

    ## Calibration

    **Only flag issues that would cause real problems during implementation planning or spec compliance review.**
    A missing scenario, a contradictory requirement, or an implementation detail masquerading as a behavioral requirement — those are issues. Minor wording improvements and stylistic preferences are not.

    **Reject specs that have zero scenarios or use no RFC 2119 keywords.** These are not behavioral specs — they are architecture documents in disguise.

    ## Output Format

    ## Spec Review

    **Status:** Approved | Issues Found

    **Issues (if any):**
    - [Section X]: [specific issue] - [why it matters for planning]

    **Recommendations (advisory, do not block approval):**
    - [suggestions for improvement]
  `
})
```

**Reviewer returns:** Status, Issues (if any), Recommendations
