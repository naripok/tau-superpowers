---
name: receiving-code-review
description: Use when receiving code review feedback, before implementing any suggestion
---

# Code Review Reception

## Overview

Code review requires technical evaluation, not emotional performance.

**Core principle:** Check before implementing. Ask before assuming. Technical correctness over social comfort.

## The Response Pattern

```
WHEN receiving code review feedback:

1. READ: Complete feedback without reacting
2. UNDERSTAND: Restate requirement in own words (or ask)
3. CHECK: Compare with codebase reality
4. EVALUATE: Technically sound for THIS codebase?
5. RESPOND: Technical acknowledgment or reasoned pushback
6. IMPLEMENT: One item at a time, test each
```

## Forbidden Responses

**NEVER:**
- "You're absolutely right!"
- "Great point!" / "Excellent feedback!" (performative)
- "Thanks for [anything]" (no gratitude)
- "Let me implement that now" (before verification)

**INSTEAD:**
- Restate the technical requirement
- Ask clarifying questions
- If the suggestion is wrong, push back with technical reasoning

## Handling Unclear Feedback

```
IF any item is unclear:
  STOP - do not implement anything yet
  ASK for clarification on unclear items

WHY: Items can be related. Partial understanding = wrong implementation.
```

**Example:**
```
your human partner: "Fix 1-6"
You understand 1,2,3,6. Unclear on 4,5.

❌ WRONG: Implement 1,2,3,6 now, ask about 4,5 later
✅ RIGHT: "I understand items 1,2,3,6. Need clarification on 4 and 5 before proceeding."
```

## Source-Specific Handling

### From your human partner
- **Trusted** - after you understand the feedback, implement it
- If the scope is unclear, **still ask**
- **No performative agreement**
- **Skip to action** or technical acknowledgment

### From External Reviewers
```
BEFORE implementing:
  1. Check: Technically correct for THIS codebase?
  2. Check: Breaks existing functionality?
  3. Check: Reason for current implementation?
  4. Check: Works on all platforms/versions?
  5. Check: Does reviewer understand full context?

IF suggestion seems wrong:
  Push back with technical reasoning

IF you cannot check easily:
  Say so: "I cannot check this without [X]. Do I investigate, ask, or proceed?"

IF conflicts with your human partner's prior decisions:
  Stop and discuss with your human partner first
```

## Adjudicating Review-Agent Findings

This section applies to findings from the `code-review` and `document-review` reviewer agents at workflow review gates. The sections above cover feedback from your human partner and from external reviewers.

**The artifact** is the code or document under review.

**The governing contract** is the stated requirements that the artifact was produced against. The requirements come from one of these:

- The task text
- The plan
- The feature spec
- The stated requirements of the proposal for the spec review
- The stated requirements of an ad-hoc review

When a report from a reviewer agent arrives at a review gate:

```
1. Split the report into findings.
2. Verify each finding against the artifact.
3. Classify each finding with the endorsement conditions and the rejection grounds.
4. Record an endorse or reject verdict with its reason for each finding.
5. Apply the endorsed findings.
6. Send the rejected findings back to the reviewer agent for confirmation.
```

The main agent acts only on endorsed findings and records every verdict with its reason. Record the verdicts before the first fix.

**Endorsement conditions.** When all of these conditions hold, endorse the finding:

- The claim is factually correct for the artifact.
- The finding has a concrete consequence.
- No rejection ground applies.

A concrete consequence is one of these:

- The claim identifies behavior that the artifact breaks or hides.
- The claim identifies a violation of the governing contract.
- The claim identifies contract-required work that the artifact omits.

**Rejection grounds.** When at least one rejection ground applies, reject the finding:

- The claim is factually wrong for the artifact.
- The finding has no concrete consequence.
- The finding demands handling for a scenario the governing contract does not require.
- The finding demands changes beyond the contract scope.

A claim that the artifact does not exhibit at its stated location counts as factually wrong for the artifact.

**Compound findings.** Split a finding with several claims into one finding per claim. Adjudicate each claim separately.

**Fix dispatches.** Endorsed Critical and Important findings go to fix dispatches. A fix dispatch carries only endorsed findings. It carries, for each endorsed finding:

- The finding text
- The artifact locations
- The governing contract
- The verification commands that the review report provides

If the report provides no verification commands for a finding, the dispatch states their absence. For dispatch conventions, read `docs/FLOW_DESCRIPTION.md`.

**Minor findings.** Apply an endorsed Minor finding through the same fix path. If you defer it, record the deferral. A deferral does not block gate closure.

**Inline case.** At the `executing-plans` checkpoint, the main agent is the implementer. The main agent applies endorsed Critical and Important fixes itself instead of dispatching them.

**Confirmation loop.** When at least one finding is rejected, send every rejected finding back to the same reviewer agent. The re-dispatch carries:

- The fix results, when endorsed findings exist
- Every rejected finding
- The rejection reason for each rejected finding

Instruct the reviewer agent to confirm or withdraw each rejected finding on technical grounds only.

When the reviewer agent withdraws a finding, close it. A withdrawn finding no longer appears in fix dispatches or in the findings that the gate treats as open. The gate continues.

When every finding is rejected, send the rejections back with no fix results. When no finding is rejected, continue the gate without a confirmation re-dispatch.

**Escalation.** When the reviewer agent maintains a rejected Critical finding, stop all workflow dispatches. Start no further workflow dispatch before the user decides. Present an architectural overview of the problem area and a situation summary to the user. The summary states the finding, the rejection reason, the maintenance reason, and the decision the user must make.

Apply the user decision:

- A decision that upholds the finding endorses it. Apply it through the normal fix path.
- A decision that upholds the rejection closes the finding. Record the decision. Continue the gate.

When the reviewer agent maintains a rejected finding that is not Critical, record the disagreement. Close the finding. Continue the gate.

## YAGNI Check for "Professional" Features

```
IF reviewer suggests "implementing properly":
  grep codebase for actual usage

  IF unused: "This endpoint is not called. Remove it (YAGNI)?"
  IF used: Then implement properly
```

## Implementation Order

```
FOR multi-item feedback:
  1. Clarify anything unclear FIRST
  2. Then implement in this order:
     - Blocking issues (breaks, security)
     - Simple fixes (typos, imports)
     - Complex fixes (refactoring, logic)
  3. Test each fix individually
  4. Check for regressions
```

## When To Push Back

Push back when:
- The suggestion breaks existing functionality
- The reviewer lacks full context
- The suggestion violates YAGNI (unused feature)
- The suggestion is technically incorrect for this stack
- Legacy/compatibility reasons exist
- The suggestion conflicts with the architectural decisions of your human partner

**How to push back:**
- Use technical reasoning, not defensiveness
- Ask specific questions
- Reference working tests/code
- If the issue is architectural, involve your human partner

## Acknowledging Correct Feedback

When feedback IS correct:
```
✅ "Fixed. [Brief description of what changed]"
✅ "Good catch - [specific issue]. Fixed in [location]."
✅ [Just fix it and show in the code]
```

**If you catch yourself about to write "Thanks":** DELETE IT. State the fix instead.

## Gracefully Correcting Your Pushback

If you pushed back and were wrong:
```
✅ "You were right - I checked [X] and it does [Y]. Implementing now."
✅ "Checked this and you are correct. My initial understanding was wrong because [reason]. Fixing."

❌ Long apology
❌ Defending why you pushed back
❌ Over-explaining
```

State the correction factually. Then continue.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Performative agreement | State the requirement or act |
| Blind implementation | Check against the codebase first |
| Batch without testing | Implement one fix at a time and test each fix |
| Assuming the reviewer is right | Check whether the suggestion breaks things |
| Avoiding pushback | Technical correctness > comfort |
| Partial implementation | Clarify all items first |
| Cannot check, proceed anyway | State the limitation and ask for direction |

## Example

**Technical Check (Good):**
```
Reviewer: "Remove legacy code"
✅ "Checking... build target is 10.15+, this API needs 13+. Need legacy for backward compat. Current impl has wrong bundle ID - fix it or drop pre-13 support?"
```

## GitHub Thread Replies

When you reply to an inline review comment on GitHub, reply in the comment thread: `gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`. Do not write a top-level PR comment.

## The Bottom Line

**External feedback = suggestions to evaluate, not orders to follow.**

Check. Question. Then implement.

No performative agreement. Technical rigor always.
