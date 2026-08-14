# Plan Document Reviewer Prompt Template

Use this template when dispatching a plan document reviewer subagent.

**Purpose:** Verify the plan is complete, matches the feature spec, and has proper task decomposition.

**Dispatch after:** The complete plan and delta spec are written and self-reviewed.

This is a template for constructing the `task` parameter of a `Task` tool call with `agent: "read-only"`.

```
Task({
  agent: "read-only",
  task: `
    You are a plan document reviewer. Verify this plan is complete and ready for implementation.

    **Plan to review:** [PLAN_FILE_PATH]
    **Delta spec for reference:** [DELTA_SPEC_FILE_PATH]
    **Feature spec for reference:** [FEATURE_SPEC_FILE_PATH]

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | Completeness | TODOs, placeholders, incomplete tasks, missing steps |
    | Spec alignment | Plan covers feature spec requirements, no scope creep beyond delta spec |
    | Delta coverage | Every ADDED/MODIFIED requirement in the delta spec has a corresponding task with a test |
    | Task Decomposition | Tasks have clear boundaries, steps are actionable, each traces to a delta requirement |
    | Buildability | Could an engineer follow this plan without getting stuck? |

    ## Calibration

    **Only flag issues that would cause real problems during implementation.**
    An implementer building the wrong thing or getting stuck is an issue.
    Minor wording, stylistic preferences, and "nice to have" suggestions are not.

    Approve unless there are serious gaps — missing requirements from the feature spec,
    delta requirements without corresponding tasks, contradictory steps, placeholder content,
    or tasks so vague they can't be acted on.

    ## Output Format

    ## Plan Review

    **Status:** Approved | Issues Found

    **Issues (if any):**
    - [Task X, Step Y]: [specific issue] - [why it matters for implementation]

    **Recommendations (advisory, do not block approval):**
    - [suggestions for improvement]
  `
})
```

**Reviewer returns:** Status, Issues (if any), Recommendations
