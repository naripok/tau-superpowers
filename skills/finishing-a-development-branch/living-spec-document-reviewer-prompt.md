# Living-Spec Synchronization Reviewer Prompt Template

Use this template when dispatching the living-spec synchronization reviewer subagent during finishing.

**Purpose:** Check that the candidate living-spec synchronization is faithful, semantically closed, idempotent, and ready before integration.

**Dispatch after:** The candidate synchronization is drafted and final acceptance has passed.

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

The child has no controller conversation history. Name every input path explicitly and include any required command or search output. The result content is the reviewer's complete final message: the `## Document Review` report (verdict + findings) ending in the status line.

```markdown
    You are reviewing a living-spec synchronization candidate before integration.

    **Candidate living spec:** [PATH and COMPLETE TEXT]
    **Affected domain:** [DOMAIN NAME]
    **Accepted feature spec:** [PATH and COMPLETE TEXT of the accepted `docs/design/<date>-<topic>-spec.md`]
    **Approved proposal identity:** [COMMIT HASH OR DIGEST of the exact operator-approved proposal version]
    **Pre-sync living spec:** [PATH and COMPLETE TEXT, or the statement "No living spec exists for this domain" when finishing creates one]
    **Selected workflow depth:** [Direct is not applicable here; state Bounded, Standard, or High-risk]
    **Synchronization diff:** [THE COMPLETE PROPOSED CHANGE to the living spec, including any cross-domain enumeration update]
    **Governing contracts for this gate:** the accepted feature spec and the established pre-sync living-spec behavior.

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | Feature-spec fidelity | Every ADDED, MODIFIED, and REMOVED requirement from the accepted feature spec is applied exactly; no accepted meaning is weakened, strengthened, or dropped. |
    | Preservation | Unchanged living-spec behavior is preserved intact; the sync is idempotent. |
    | Semantic closure | The living spec expresses complete current behavior for its domain without depending on the proposal, the plan, or chat history. Every term, decision, constraint, assumption, exception, and reference needed for current behavior is defined. |
    | Initial creation | For an undocumented or new domain, the complete reviewed feature spec supplies the initial living spec. Reject invented baseline behavior. |
    | Invention rejection | Behavior absent from the established pre-sync behavior and the accepted feature spec is a blocking finding. |
    | Cross-domain enumeration update | When the sync updates another living spec's factual enumeration (for example, a gate list), check it against the accepted workflow gates. The procedure and behavior content of that living spec stays unchanged. |
    | Style | Prose follows writing-developer-facing-text (pragmatic mode). |

    ## Review Accounting

    This is one initial review of one candidate living-spec version against one complete input set and one review task. Do not dispatch duplicate initial reviews with identical inputs. A changed candidate receives one new complete initial review. Added context after a `BLOCKED` or `NEEDS_CONTEXT` result permits one new complete initial review with the changed inputs. Findings use the unchanged adjudication contract in the `receiving-code-review` skill; a rejection-confirmation re-dispatch is targeted and exempt from the duplicate-initial-review prohibition.

    ## Adversarial Stance

    Assume the synchronization is flawed until proven otherwise. Question every silent addition, omission, and rewording. Make every finding actionable: what is wrong, why it blocks integration, how to fix it.

    ## Calibration

    Only flag issues that cause real problems at integration or for future workflow consumers. Do not demand content the accepted feature spec and pre-sync behavior do not support.

    ## Re-Check Before Reporting

    Re-check every finding against the candidate living spec and the governing contracts. Report only findings that survive the re-check.

    ## Rejection Confirmation

    The main agent fills this section only on a confirmation re-dispatch. It stays empty on the first dispatch.

    **Rejected findings to confirm or withdraw:**
    - Finding: [REJECTED_FINDING]
      Rejection reason: [REJECTION_REASON]

    Re-check the candidate for each rejected finding. Confirm the finding with its concrete consequence or withdraw it. Withdraw on technical grounds only. Never withdraw a finding merely because the main agent rejects it.

    ## Output Format

    For every finding, state the requirement or section it rests on and the concrete consequence. Omit a finding that cannot state these. The workflow never requests operator approval of synchronization; your approval closes the gate.

    Return exactly one section with the exact heading `## Document Review`:

    ## Document Review

    **Verdict:** Approved | Approved with fixes | Needs fixes

    **Critical (must fix):**
    - [Section X]: [specific issue] - [why it blocks integration]

    **Important (fix):**
    - [Section X]: [specific issue] - [why it matters]

    **Minor (optional):**
    - [suggestions for improvement]

    End with exactly one status line: **Status: DONE**, **Status: DONE_WITH_CONCERNS**,
    **Status: BLOCKED**, or **Status: NEEDS_CONTEXT**.
```
