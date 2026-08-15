# Code Quality Reviewer Prompt Template

Use this template when dispatching a code quality reviewer subagent.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

**Only dispatch after spec compliance review passes.**

This is a template for constructing the `task` string of the Tau `task` tool. Call it with this argument shape after replacing every placeholder:

```json
{
  "agent": "read-only",
  "task": "[FILLED PROMPT BELOW]"
}
```

**Note:** The enforced read-only profile permits only Tau's `read` tool. It cannot run `git diff`, search for unknown paths, or execute tests. The controller must include the complete diff and verification output and name every file the reviewer may need to read. This tool policy is not an OS, filesystem, network, credential, model, or provider sandbox. Do not add `provider` or `model` unless the user explicitly requested or approved the override.

```markdown
    Review the following changes for code quality.

    ## Modified Files
    [Controller must list every relevant file path here]

    ## Git Diff
    [Controller must provide complete git diff output here]

    ## Verification Output
    [Controller must provide relevant test, lint, and type-check output here]

    ## Context
    WHAT_WAS_IMPLEMENTED: [from implementer's report]
    PLAN_OR_REQUIREMENTS: Task N from [plan-file]
    DESCRIPTION: [task summary]

    ## What to Check

    Read the named modified files for full context, then review. If required evidence or
    a file path is missing, report NEEDS_CONTEXT and request that exact input. Check:
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
```
