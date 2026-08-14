# Code Quality Reviewer Prompt Template

Use this template when dispatching a code quality reviewer subagent.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

**Only dispatch after spec compliance review passes.**

This is a template for constructing the `task` parameter of a `Task` tool call with `agent: "read-only"`.

**Note:** The `read-only` agent has no bash access (no `git diff`). The controller must run `git diff` itself and include the diff output in the reviewer's task prompt.

```
Task({
  agent: "read-only",
  task: `
    Review the following changes for code quality.

    ## Git Diff
    [Controller must provide git diff output here]

    ## Context
    WHAT_WAS_IMPLEMENTED: [from implementer's report]
    PLAN_OR_REQUIREMENTS: Task N from [plan-file]
    DESCRIPTION: [task summary]

    ## What to Check

    Read the modified files for full context, then review:
    - Does each file have one clear responsibility with a well-defined interface?
    - Are units decomposed so they can be understood and tested independently?
    - Is the implementation following the file structure from the plan?
    - Did this implementation create new files that are already large, or significantly grow existing files?
    - Are tests comprehensive and do they verify actual behavior?
    - Is the code clean, maintainable, and well-named?
    - Are there security or performance concerns?

    ## Output Format

    ## Code Review

    **Strengths:**
    - [what's good]

    **Issues:**
    - Critical: [must fix]
    - Important: [should fix]
    - Minor: [nice to fix]

    **Assessment:** Approved | Needs fixes
  `
})
