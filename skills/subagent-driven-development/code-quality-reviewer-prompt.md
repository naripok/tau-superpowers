# Code Quality Reviewer Prompt Template

Use this template when dispatching a code quality reviewer subagent.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

**Only dispatch after spec compliance review passes.**

This is a template for constructing the `task` string of the Tau `task` tool. Call it with this argument shape after replacing every placeholder:

```json
{
  "agent": "code-review",
  "task": "[FILLED PROMPT BELOW]"
}
```

**Note:** The `code-review` agent may run read-only `bash` (git diff/log/status, grep/rg/find) in addition to `read`, but must never change the repository or environment state — no git writes, no file creation or deletion, no installs, no test or build runs, no background processes. It cannot execute tests. The controller should still include the complete diff, verification output, and every relevant file path for speed and focus. `write`, `edit`, and other state-changing Tau tools are blocked by the tool policy. This tool policy is not an OS, filesystem, network, credential, model, or provider sandbox. Do not add `provider`, `model`, or `reasoningEffort` unless the user explicitly requested or approved the override; the agent runs its bundled pinned setup (overridable per agent in the subagent config file), and its result carries a strict `## Code Review` section plus a `## Summary` that the `task` result relays to the controller.

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

    Review adversarially: assume the work is flawed until proven otherwise, and question
    the implementer's decisions. Do not acknowledge strengths or give praise — only
    actionable findings. Read the named modified files for full context, then review. If
    required evidence or a file path is missing, report NEEDS_CONTEXT and request that
    exact input. Check:
    - Does each file have one clear responsibility with a well-defined interface?
    - Are units decomposed so they can be understood and tested independently?
    - Is the implementation following the file structure from the plan?
    - Did this implementation create new files that are already large, or significantly grow existing files?
    - Are tests comprehensive, do they verify actual behavior, and do their docstrings explain what behavior they prove and why they are needed?
    - Is the code clean, maintainable, and well-named?
    - Are there security or performance concerns?
    - Is cyclomatic complexity low — code should encode a single valid path whenever possible?
    - Are invalid system states unrepresentable by the type system (no untyped escapes, stringly-typed states where a precise variant exists)?
    - Are there unnecessary abstractions (prefer simple, direct solutions), unnecessary fallbacks (prefer explicit error handling), or hacks/workarounds (prefer correct, complete solutions by design)?
    - Do application-code docstrings say what the code does and why, not how?
    - Does documentation describe only the current implemented behavior, with no references to old system states or removed behavior?

    ## Output Format

    Return exactly two sections with the exact headings `## Code Review` and
    `## Summary`, in that order, so the controller can relay both to the parent.

    ## Code Review

    **Verdict:** Approved | Approved with fixes | Needs fixes

    **Critical (must fix):**
    - [file:line] what's wrong, why it matters, how to fix

    **Important (should fix):**
    - [file:line] what's wrong, why it matters, how to fix

    **Minor (nice to fix):**
    - [file:line] what could be improved

    ## Summary

    [One short paragraph: what was reviewed, key findings, verdict. Self-contained because it is relayed to the parent session.]
```
