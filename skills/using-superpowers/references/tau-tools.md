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
| `reasoningEffort` | Thinking level for every child: `off`, `minimal`, `low`, `medium`, `high`, or `xhigh`. A call-level value overrides the config file and the selected agent definition; otherwise the level falls back to the config file, then the agent definition, then the parent session's thinking level. Applied as the child's Tau thinking level at session start; if the level is unsupported for the effective provider/model, the child logs a `[superpowers-subagent] could not apply reasoning effort ...` diagnostic on its `stderr` (visible in `details.results[].stderr`) and runs at its ambient level. |
| `timeoutSeconds` | Per-child timeout, greater than 0 and at most 3600; default 3600. |

A relative `cwd` is resolved from the parent Tau session's working directory. In parallel and chain modes, put `cwd` on each item rather than at the top level.

## Bundled Agent Profiles

| Agent | Tau tool policy | Default provider/model/reasoning | Use for |
|---|---|---|---|
| `general-purpose` | Normal built-in coding tools | Parent session's active provider, model, and thinking effort | Implementation, scouting, exploration, and tasks requiring commands or edits |
| `read-only` | Only `read` is permitted | Parent session's active provider, model, and thinking effort | Inspection of known files without a pinned review model |
| `implementation` | Normal built-in coding tools | `openrouter:deepseek/deepseek-v4-flash-0731` at `high` | Implementation tasks, TDD, running verification |
| `code-review` | `read` + read-only `bash` | `openrouter:deepseek/deepseek-v4-flash-0731` at `xhigh` | Code quality review, spec compliance review, final review |
| `document-review` | `read` + read-only `bash` | `openrouter:deepseek/deepseek-v4-flash-0731` at `xhigh` | Feature-spec review and plan review at the design workflow gates |

The three pinned cells are the bundled defaults, overridable per agent through the subagent config file (`[agents.<name>]`); see Provider, Model, and Thinking Effort Selection below.

Review-profile agents (`code-review`, `document-review`) may call `read` and `bash`. Their instructions restrict `bash` strictly to read-only operations — `git diff`/`log`/`show`/`status`, `grep`/`rg`/`find` searches, and reading files with unknown exact paths — and forbid changing repo or environment state (no git writes, no file creation/deletion, no installs, no test or build runs, no background processes). They still cannot call `write`, `edit`, or other state-changing Tau tools: a public Tau `tool_call` hook blocks everything outside the allowed set. This hook is **not** an OS, filesystem, network, credential, model, or provider sandbox, and it cannot parse bash command semantics — read-only bash usage is instruction-governed.

The plain `read-only` agent remains stricter: only `read` is permitted, no `bash` at all. Its controller must provide command and search output in the task prompt and identify every file it should read.

`code-review` returns a strict `## Code Review` section followed by a `## Summary`; `document-review` returns a strict `## Document Review` section followed by a `## Summary`. The `task` result relays both sections to the controller.

Agent definitions may pin `provider`, `model`, and `reasoningEffort` in their frontmatter. **Do not override pinned values** unless a skill, the config file, or the user explicitly prescribes the override: `implementation` is pinned to `provider: "openrouter"`, `model: "deepseek/deepseek-v4-flash-0731"`, `reasoningEffort: "high"`, and `code-review`/`document-review` to the same model at `reasoningEffort: "xhigh"`.

## Custom Agents, Scope, and Approval

Agent definitions are Markdown files discovered with increasing precedence:

1. bundled agents in the extension;
2. user agents in `~/.tau/agents/*.md`;
3. project agents in the nearest ancestor `.tau/agents/*.md` directory.

`agentScope: "user"` includes bundled and user definitions, `"project"` includes bundled and project definitions, and `"both"` includes all three layers. A higher-precedence definition replaces the same agent name.

Definitions require non-empty `name` and `description` frontmatter. They may set `profile: general-purpose`, `profile: read-only` (only `read`), or `profile: review` (`read` + read-only `bash`) and optional independent `provider`, `model`, and `reasoningEffort` strings. Their Markdown body becomes child instructions. Tau does not support an arbitrary per-agent `tools` list in this extension.

If a requested name resolves to a project definition, `confirmProjectAgents: true` asks for confirmation in Tau's TUI and fails closed in headless mode. After inspecting the definition, set `confirmProjectAgents: false` to approve it explicitly for that call. Tau project trust and project-extension approval are separate and do not approve project agent prompts.

## Provider, Model, and Thinking Effort Selection

By default, omit `provider`, `model`, and `reasoningEffort`: subagents inherit the parent session's active provider, model, and thinking level unless a config file, agent definition, or call value pins one. Do not override any of them without explicit user direction or approval.

Per-field resolution, highest first:

1. `task` call `provider` / `model` / `reasoningEffort`;
2. the subagent config file `[agents.<name>]` section;
3. the selected agent definition's frontmatter;
4. the subagent config file `[defaults]` section;
5. the parent session's active provider, model, and thinking level.

The config file is `superpowers-subagent.toml` in `~/.tau/` or the nearest ancestor `<project>/.tau/` (project shadows user per key). A copy encoding today's defaults ships at `extensions/superpowers-subagent/superpowers-subagent.example.toml`:

```toml
[defaults]
# provider = "openai"
# model = "gpt-5.6-sol"
# reasoningEffort = "medium"   # off | minimal | low | medium | high | xhigh

[agents.code-review]
provider = "openrouter"
model = "deepseek/deepseek-v4-flash-0731"
reasoningEffort = "xhigh"
```

Loaded config files and dropped-config diagnostics appear in `details.configPaths` and `details.configDiagnostics`. A section whose agent name matches no bundled, user, or project definition is reported there too, so a typo cannot silently no-op. Editing the file applies to the next `task` call; no Tau reload is needed.

The fields are independent and map directly to Tau's separate provider and model settings:

```json
{
  "agent": "implementation",
  "task": "Complete the delegated task.",
  "reasoningEffort": "high"
}
```

Do not combine or split values. In particular, a slash inside `model` remains part of the model identifier and does not infer a provider. A call-level value overrides only the corresponding lower-layer value.

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
  configPaths?: string[],
  configDiagnostics?: string[],
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

## Reviews That Can Run Read-Only bash

The `code-review` and `document-review` agents can obtain diffs and run searches themselves with read-only `bash` (`git diff`, `git log`, `git show`, `git status`, `grep`/`rg`/`find`). They must never change repo state — instruct them explicitly if the task itself might tempt a write. Supplying the diff, verification output, and requirements in the task prompt is still recommended: it keeps reviewers fast and their context focused.

A typical review call embeds the controller-provided diff while letting the reviewer verify with read-only bash:

```json
{
  "agent": "code-review",
  "task": "Review the named modified files for code quality. The controller-provided git diff follows; you may run read-only bash (git diff/log/status, grep/rg/find) to verify, but never change the repository state.\n\n## Git Diff\n[PASTE COMPLETE DIFF HERE]\n\n## Requirements\n[PASTE REQUIREMENTS HERE]\n\nReturn the strict two-section format: exact `## Code Review` heading (verdict, Critical/Important/Minor points — review adversarially, no praise), then exact `## Summary` heading, ending with the status line."
}
```

Use chain mode only for unconditional pipelines. For conditional loops such as implement → review → fix if needed → re-review, inspect each result and make separate `task` calls.
