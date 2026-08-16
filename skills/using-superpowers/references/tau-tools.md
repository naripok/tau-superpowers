# Tau `task` Tool Reference

The `superpowers-subagent` Tau extension registers one tool named `task`. It launches isolated `tau` subprocesses for single, parallel, or chained work. The extension must be installed under `~/.tau/extensions/superpowers-subagent` or explicitly loaded with:

```bash
tau -e extensions/superpowers-subagent
```

## task Tool API

Call `task` with exactly one non-empty mode. The examples below are the JSON argument objects for the tool call.

### Single mode

Use `agent` plus `task` for one child. Top-level `cwd` is optional and applies only to single mode.

```json
{
  "agent": "general-purpose",
  "task": "Implement the caching layer as described in the supplied requirements.",
  "cwd": "/path/to/worktree"
}
```

### Parallel mode

Use `tasks` for independent work. The extension accepts at most eight items, runs at most four children concurrently, and returns results in input order. Each item may have its own `cwd`.

```json
{
  "tasks": [
    {
      "agent": "general-purpose",
      "task": "Fix the supplied authentication test failures. Do not modify the batch module."
    },
    {
      "agent": "general-purpose",
      "task": "Fix the supplied batch test failures. Do not modify the authentication module."
    }
  ]
}
```

### Chain mode

Use `chain` for unconditional sequential work. Every `{previous}` occurrence is replaced with the preceding child's complete final assistant text, not only its summary.

```json
{
  "chain": [
    {
      "agent": "general-purpose",
      "task": "Investigate the authentication code and return structured findings."
    },
    {
      "agent": "general-purpose",
      "task": "Create an implementation plan from these findings:\n\n{previous}"
    },
    {
      "agent": "general-purpose",
      "task": "Implement this plan:\n\n{previous}"
    }
  ]
}
```

A chain stops on child process/protocol failure, timeout, or cancellation. A successful child whose semantic status is `BLOCKED` or `NEEDS_CONTEXT` does not automatically stop the chain, so use separate `task` calls for conditional review or repair loops.

## Common Options

These optional top-level fields work with every mode:

| Field | Meaning |
|---|---|
| `description` | Short display description. |
| `agentScope` | `user` (default), `project`, or `both`. |
| `confirmProjectAgents` | Require TUI approval for selected project agents (default `true`). Setting it to `false` explicitly approves them for this call. |
| `provider` | Opaque Tau provider override. |
| `model` | Opaque Tau model override. |
| `reasoningEffort` | Thinking level for every child: `off`, `minimal`, `low`, `medium`, `high`, or `xhigh`. A call-level value overrides the selected agent definition's own `reasoningEffort`. Applied as the child's Tau thinking level at session start; if the level is unsupported for the effective provider/model, the child logs a `[superpowers-subagent] could not apply reasoning effort ...` diagnostic on its `stderr` (visible in `details.results[].stderr`) and runs at its ambient level. |
| `timeoutSeconds` | Per-child timeout, greater than 0 and at most 3600; default 3600. |

A relative `cwd` is resolved from the parent Tau session's working directory. In parallel and chain modes, put `cwd` on each item rather than at the top level.

## Bundled Agent Profiles

| Agent | Tau tool policy | Pinned model | Use for |
|---|---|---|---|
| `general-purpose` | Normal built-in coding tools | Tau's defaults | Implementation, scouting, exploration, and tasks requiring commands or edits |
| `read-only` | Only `read` is permitted | Tau's defaults | Inspection of known files without a pinned review model |
| `implementation` | Normal built-in coding tools | `local-gateway:qwen3.8-27b` at `xhigh` | Implementation tasks, TDD, running verification |
| `code-review` | Only `read` is permitted | `openrouter:deepseek/deepseek-v4-flash-0731` at `xhigh` | Code quality review, spec compliance review, final review |
| `document-review` | Only `read` is permitted | `openrouter:deepseek/deepseek-v4-flash-0731` at `xhigh` | Feature-spec review and plan review at the design workflow gates |

The read-only children (`read-only`, `code-review`, `document-review`) cannot run `git diff`, list or search for unknown paths, or call `bash`, `write`, `edit`, or other tools. The controller must provide command and search output in the task prompt and identify every file the reviewer should read. A public Tau `tool_call` hook enforces this tool policy, but it is **not** an OS, filesystem, network, credential, model, or provider sandbox.

`code-review` returns a strict `## Code Review` section followed by a `## Summary`; `document-review` returns a strict `## Document Review` section followed by a `## Summary`. The `task` result relays both sections to the controller.

Agent definitions may pin `provider`, `model`, and `reasoningEffort` in their frontmatter. **Do not override pinned values** unless a skill or the user explicitly prescribes the override: the `implementation` agent normally stays on the local gateway, and the fallback for complex, long-context, or repeatedly failing gateway work is `provider: "openrouter"`, `model: "deepseek/deepseek-v4-flash-0731"`, `reasoningEffort: "high"`.

## Custom Agents, Scope, and Approval

Agent definitions are Markdown files discovered with increasing precedence:

1. bundled agents in the extension;
2. user agents in `~/.tau/agents/*.md`;
3. project agents in the nearest ancestor `.tau/agents/*.md` directory.

`agentScope: "user"` includes bundled and user definitions, `"project"` includes bundled and project definitions, and `"both"` includes all three layers. A higher-precedence definition replaces the same agent name.

Definitions require non-empty `name` and `description` frontmatter. They may set `profile: general-purpose` or `profile: read-only` and optional independent `provider` and `model` strings. Their Markdown body becomes child instructions. Tau does not support an arbitrary per-agent `tools` list in this extension.

If a requested name resolves to a project definition, `confirmProjectAgents: true` asks for confirmation in Tau's TUI and fails closed in headless mode. After inspecting the definition, set `confirmProjectAgents: false` to approve it explicitly for that call. Tau project trust and project-extension approval are separate and do not approve project agent prompts.

## Provider and Model Selection

By default, omit both `provider` and `model`; the child uses Tau's configured defaults or the selected agent definition's optional values. Do not override either without explicit user direction or approval.

The fields are independent and map directly to Tau's separate provider and model settings:

```json
{
  "agent": "implementation",
  "task": "Complete the delegated task.",
  "reasoningEffort": "high"
}
```

Do not combine or split values. In particular, a slash inside `model` remains part of the model identifier and does not infer a provider. A call-level value overrides only the corresponding agent-level value.

## Child Context and Skill Isolation

Each child receives the selected agent body and the complete delegated task, but not the controller's conversation history. There is no mid-task conversation with the controller: when a child reports missing context, supply it in a new complete `task` call.

Children run with discovered extensions and project resources disabled. Tau cannot independently disable user-global skills, so those skills may remain listed; the appended child prompt instructs the child not to invoke them. That prompt-only instruction is behavioral guidance, not a security boundary. Always include all workflow steps, requirements, relevant file paths, command output, and expected response format in the delegated task.

## Results and Status

Parent-model `content` stays summary-sized:

- when final output contains an exact review heading (`## Code Review` or `## Document Review`) followed by an exact `## Summary` heading, successful single mode returns both sections (all actionable points plus the summary) instead of only the summary; otherwise it returns the final `## Summary` section, or the complete final output if no exact summary heading exists; failed single mode returns a concise failure message;
- parallel mode returns a success count and one ordered summary/fallback section per child;
- successful chain mode returns the final child's summary/fallback; a failed chain returns a concise stop message.

Structured `details` uses this versioned shape (fields marked `?` are optional):

```text
{
  schemaVersion: 1,
  mode: "single" | "parallel" | "chain",
  agentScope: "user" | "project" | "both",
  projectAgentsDir: string | null,
  discoveryDiagnostics: string[],
  results: [{
    agent, agentSource, task, cwd, exitCode, messages, stderr,
    usage: { input, output, cacheRead, cacheWrite, cost, contextTokens, turns },
    provider?, model?, reasoningEffort?, stopReason?, errorMessage?, status, step?,
    timedOut, cancelled, malformedJsonLines
  }]
}
```

Inspect `details.results` for semantic status and process state; `messages` contains the complete accepted Tau wire messages even though parent-model content is summary-sized. Failures are represented in content and details; Tau tool results do not have an `isError` field.

Supported semantic statuses are:

- **DONE** — Continue.
- **DONE_WITH_CONCERNS** — Read and resolve the concerns before continuing when they affect correctness or scope.
- **BLOCKED** — Address the blocker, add context, change the approach, or ask the user.
- **NEEDS_CONTEXT** — Supply the missing information in a new complete dispatch.

Semantic status is distinct from process success. Check the result's failure text and structured process fields rather than assuming `BLOCKED` means the subprocess itself failed.

## Read-Only Reviews That Need Diffs

The controller must obtain the diff before dispatching the `code-review` reviewer (its read-only profile cannot run `git diff`):

```bash
BASE_SHA=$(git rev-parse HEAD~1)
HEAD_SHA=$(git rev-parse HEAD)
git diff "$BASE_SHA".."$HEAD_SHA"
```

Then call `task` with the complete output embedded in `task`. The result relays the reviewer's `## Code Review` section (verdict and actionable points) together with its `## Summary`:

```json
{
  "agent": "code-review",
  "task": "Review the named modified files for code quality. The controller-provided git diff follows.\n\n## Git Diff\n[PASTE COMPLETE DIFF HERE]\n\n## Requirements\n[PASTE REQUIREMENTS HERE]\n\nReturn the strict two-section format: exact `## Code Review` heading (verdict, Critical/Important/Minor points — review adversarially, no praise), then exact `## Summary` heading, ending with the status line."
}
```

Use chain mode only for unconditional pipelines. For conditional loops such as implement → review → fix if needed → re-review, inspect each result and make separate `task` calls.
