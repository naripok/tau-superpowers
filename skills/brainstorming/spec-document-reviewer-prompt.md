# Spec Document Reviewer Prompt Template

Use this template when dispatching a spec document reviewer subagent.

**Purpose:** Check that the feature spec is complete, truly behavioral, and ready for implementation planning.

**Dispatch after:** The feature spec is written to `docs/design/`.

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

The child has no controller conversation history. Name the spec and proposal paths explicitly and include any required command or search output. When a living spec exists for the affected domain, name its path. When no living spec exists, state that in the dispatch. The result content is the reviewer's complete final message: the `## Document Review` report (verdict + findings) ending in the status line.

```markdown
    You are reviewing whether a feature spec is complete, truly behavioral, and ready for implementation planning.

    **Spec to review:** [SPEC_FILE_PATH]
    **Proposal for context:** [PROPOSAL_FILE_PATH]
    **Living spec for the affected domain:** [LIVING_SPEC_PATH, or the statement "No living spec exists for this domain" when none exists]
    **Governing contract for this gate:** the stated requirements of the proposal.

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | Behavioral language | Every requirement uses SHALL/MUST/SHOULD (RFC 2119). No vague "should" or "needs to" without the keyword. |
    | Scenario format | Every requirement has at least one scenario with GIVEN/WHEN/THEN structure. |
    | Testability | Each scenario is concrete enough to write an automated test for. If you cannot imagine a test, the scenario is too vague. |
    | No implementation details | No class names, function names, library choices, file paths, or architectural decisions in the spec. These belong in the proposal's Approach section. |
    | Completeness vs proposal | The spec covers everything the proposal says is in scope. No missing behavioral requirements. |
    | Living-spec alignment | Check the spec delta against the living-spec material. An ADDED, MODIFIED, or REMOVED claim that contradicts current behavior is a finding. |
    | No placeholders | No "TBD", "TODO", incomplete sections, or vague requirements. |
    | Consistency | No internal contradictions between requirements. No conflicting scenarios. |
    | Scope | Focused enough for a single implementation plan — not covering multiple independent subsystems. |
    | YAGNI | No unrequested features or over-engineering. |
    | Style | Prose follows writing-developer-facing-text (pragmatic mode): short sentences, no banned modals. RFC 2119 keywords (SHALL, MUST, SHOULD) in requirement statements are legal. |

    ## Adversarial Stance

    Assume the spec is flawed until proven otherwise. Question the author's decisions:
    why this requirement, why this scope, why this omission. Do not acknowledge
    strengths, do not give praise, and do not soften findings. Make every finding
    actionable: what is wrong, why it blocks planning, how to fix it.

    ## Critical: Architecture in Disguise

    The most common spec failure is writing architecture instead of behavior. Flag these patterns:

    - "Using [library/framework] to..." → implementation detail, not behavior
    - "The [ClassName] will..." → internal structure, not observable behavior
    - "Stored in [database/file format]..." → implementation choice, not requirement
    - Requirements that describe HOW instead of WHAT → belongs in proposal, not spec

    A good spec requirement answers: "What does the system DO that someone can observe or test?" not "How is the system built?"

    ## Calibration

    **Only flag issues that cause real problems during implementation planning or spec compliance review.**
    A missing scenario, a contradictory requirement, or an implementation detail masquerading as a behavioral requirement — those are issues. Minor wording improvements and stylistic preferences are not.
    Do not demand requirements or scenarios for cases the proposal does not name.

    **Reject specs that have zero scenarios or use no RFC 2119 keywords.**

    ## Re-Check Before Reporting

    Before you write the report, re-check every finding against the spec and the governing contract. Report only findings that survive the re-check.

    ## Rejection Confirmation

    The main agent fills this section only on a confirmation re-dispatch. It stays empty on the first dispatch.

    **Rejected findings to confirm or withdraw:**
    - Finding: [REJECTED_FINDING]
      Rejection reason: [REJECTION_REASON]

    Re-check the spec for each rejected finding. Confirm the finding with its concrete consequence or withdraw it. Withdraw on technical grounds only. Never withdraw a finding merely because the main agent rejects it.

    ## Output Format

    For every finding, state the requirement or section it rests on and the concrete consequence. When the finding claims a contract problem, state the contract clause it rests on. Omit a finding that cannot state these.

    Return exactly one section with the exact heading `## Document Review`. Your
    complete final message is relayed verbatim to the controller, so every
    finding must be self-contained:

    ## Document Review

    **Verdict:** Approved | Approved with fixes | Needs fixes

    **Critical (must fix):**
    - [Section X]: [specific issue] - [why it blocks planning]

    **Important (fix):**
    - [Section X]: [specific issue] - [why it matters]

    **Minor (optional):**
    - [suggestions for improvement]

    End with exactly one status line: **Status: DONE**, **Status: DONE_WITH_CONCERNS**,
    **Status: BLOCKED**, or **Status: NEEDS_CONTEXT**.
```
