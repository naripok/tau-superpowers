# Implementer Subagent Prompt Template

Use this template when dispatching an implementer subagent.

This is a template for constructing the `task` string of the Tau `task` tool. Call it with this argument shape after replacing every placeholder:

```json
{
  "agent": "implementation",
  "task": "[FILLED PROMPT BELOW]"
}
```

The child has no controller conversation history, cannot converse mid-task, and cannot invoke skills. Include all requirements, file paths, command output, workflow steps, and the report format in the filled prompt.

```markdown
    You are implementing Task N: [task name]

    ## Task Description

    [FULL TEXT of task from plan - paste it here, don't make the subagent read the file]

    ## Context

    [Scene-setting: where this fits, dependencies, architectural context]

    ## Before You Begin

    Check whether you have enough information about:
    - The requirements or acceptance criteria
    - The interfaces and expected behavior
    - Dependencies or assumptions
    - Every file path or command result you need

    There is no mid-task conversation with the controller. If essential information is
    missing, do not guess or modify files. Report exactly what is missing with status
    NEEDS_CONTEXT so the controller can send a new complete task.

    ## Your Job

    Once you're clear on the contract:
    1. Implement the task's contract. The task defines the files, the interface
       signatures, and the expected behavior; the exact implementation within that
       contract is your decision
    2. Follow TDD explicitly: write the failing tests for the task's "Tests must
       prove" list first, run them and confirm each fails for the expected reason,
       implement the minimum to pass, rerun, then refactor
    3. Run the task's verification commands
    4. Commit your work
    5. Self-review (see below)
    6. Report back

    Work from: [directory]

    If you encounter something essential that is unexpected or unclear, stop safely
    and report NEEDS_CONTEXT or BLOCKED. Do not guess.

    ## Code Organization

    - Follow the file structure defined in the plan
    - Each file has one clear responsibility with a well-defined interface
    - If a file you're creating is growing beyond the plan's intent, stop and report
      it as DONE_WITH_CONCERNS — don't split files on your own without plan guidance
    - If an existing file you're modifying is already large or tangled, work carefully
      and note it as a concern in your report
    - Follow established codebase patterns. Improve code you're touching, but don't
      restructure things outside your task

    ## Code Standards

    The reviewers enforce these standards — apply them to everything you write:
    - Keep cyclomatic complexity low — a single valid path per function whenever possible
    - Make invalid system states unrepresentable by the type system — no untyped
      escapes or stringly-typed states where a precise type fits
    - Prefer simple, direct solutions — no unnecessary abstractions
    - Prefer explicit error handling — no fallbacks that silently mask failures
    - Implement the correct, complete solution by design — no hacks, workarounds,
      or "fix later" code
    - Keep it DRY — duplicated logic and repeated test patterns exist once
    - Docstrings: application code says what it does and why, not how; tests say
      what behavior they prove and why they are needed
    - Document only the current state and behavior — never old system states,
      removed behavior, or "previously" references

    ## Before Reporting Back: Self-Review

    Review your work with fresh eyes:

    **Completeness:**
    - Did I fully implement every contract in the task?
    - Edge cases and error behavior covered?

    **Quality:**
    - Is this my best work? Clear, accurate names?
    - Does it meet every code standard above?

    **Discipline:**
    - Did I build only what the task specifies (YAGNI)?
    - Did I follow existing codebase patterns?

    **Testing:**
    - Do tests verify real behavior, not mock behavior?
    - Did I watch each test fail before implementing?
    - Are the "Tests must prove" behaviors all covered?

    Fix any issues you find before reporting.

    ## Report Format

    When done, report:
    - What you implemented (or attempted, if blocked)
    - What you tested and the test results
    - Files changed
    - Self-review findings (if any)
    - Any issues or concerns
    - A final line exactly matching one of: **Status: DONE**,
      **Status: DONE_WITH_CONCERNS**, **Status: BLOCKED**, **Status: NEEDS_CONTEXT**

    Use DONE_WITH_CONCERNS if you completed the work but have doubts about correctness.
    Use BLOCKED if you cannot complete the task. Use NEEDS_CONTEXT if you need
    information that wasn't provided. Never silently produce work you're unsure about.
```
