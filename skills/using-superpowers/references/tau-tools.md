# Tau `task` Tool Reference

The `superpowers-subagent` Tau extension registers one tool named `task`. It launches isolated `tau` subprocesses for one or more delegated tasks. You must install the extension under `~/.tau/extensions/superpowers-subagent` or load it explicitly with:

```bash
tau -e extensions/superpowers-subagent
```

## task Tool API

Every `task` call takes a `tasks` array. The examples below are the JSON argument objects for the tool call.

### Task list

`tasks` is required: an array of 1–8 items, each `{agent, task, cwd?}`. One item runs a single child. Two or more items run in parallel, with at most four active. The results keep the input order. Each item can carry its own `cwd`.

```json
{
  "tasks": [
    {
      "agent": "general-purpose",
      "task": "Implement the caching layer as described in the supplied requirements.",
      "cwd": "/path/to/worktree"
    }
  ]
}
```

Two or more items dispatch in parallel — independent work only:

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

Every task in one call must be independent: items share no state and cannot see each other's progress. Conditional sequences require separate `task` calls. This applies to implement → review → fix if needed → re-review, and to any loop where a later step depends on an earlier result. The separate calls let the controller inspect each result.

### When to dispatch

Dispatch a subagent only for substantive multi-step work that benefits from an isolated context window. Also dispatch a subagent for long-running work that must not block the parent session. Simple reads, searches, commands, and small edits are the parent's own tool calls. A subagent replaces the parent's tool calls for its task. Never dispatch a subagent and then perform the same work yourself.

## Common Options

These optional top-level fields work with every call:

| Field | Meaning |
|---|---|
| `description` | Short display description. |
| `agentScope` | `user` (default), `project`, or `both`. |
| `confirmProjectAgents` | Require TUI approval for selected project agents (default `true`). Setting it to `false` explicitly approves them for this call. |
| `provider` | Opaque Tau provider override. |
| `model` | Opaque Tau model override. |
| `reasoningEffort` | Thinking level for every child: `off`, `minimal`, `low`, `medium`, `high`, or `xhigh`. A call-level value overrides the config file and the selected agent definition. Otherwise the level falls back to the config file, then the agent definition, then the parent session's thinking level. The extension applies the level as the child's Tau thinking level at session start. If the level is unsupported for the effective provider/model, the child logs a `[superpowers-subagent] could not apply reasoning effort ...` diagnostic on its `stderr`. You can see this diagnostic in `details.results[].stderr`. The child then runs at its ambient level. |
| `timeoutSeconds` | Per-child timeout. The value must be greater than 0 and at most 3600. The default is 3600. |

Tau resolves a relative `cwd` from the parent Tau session's working directory. `cwd` lives on each item.

## Bundled Agent Profiles

| Agent | Tau tool policy | Default provider/model/reasoning | Use for |
|---|---|---|---|
| `general-purpose` | Normal built-in coding tools | Parent session's active provider, model, and thinking effort | Implementation, scouting, exploration, and tasks requiring commands or edits |
| `read-only` | Allows only `read` | Parent session's active provider, model, and thinking effort | Substantial multi-file investigation and review of named files |
| `implementation` | Normal built-in coding tools | `openrouter:deepseek/deepseek-v4-flash-0731` at `high` | Implementation tasks, TDD, running verification |
| `code-review` | `read` + read-only `bash` | `openrouter:deepseek/deepseek-v4-flash-0731` at `xhigh` | Code quality review, spec compliance review, final review |
| `document-review` | `read` + read-only `bash` | `openrouter:deepseek/deepseek-v4-flash-0731` at `xhigh` | Feature-spec review and plan review at the design workflow gates |

The three pinned cells are the bundled defaults. You can override them per agent through the subagent config file (`[agents.<name>]`). See Provider, Model, and Thinking Effort Selection below.

Review-profile agents (`code-review`, `document-review`) can call `read` and `bash`. Their instructions restrict `bash` strictly to read-only operations. The allowed operations are `git diff`/`log`/`show`/`status`, `grep`/`rg`/`find` searches, and reading files with unknown exact paths. The instructions forbid changing repo or environment state. Forbidden actions include git writes, file creation or deletion, installs, test or build runs, and background processes.

They still cannot call `write`, `edit`, or other state-changing Tau tools. A public Tau `tool_call` hook blocks everything outside the allowed set. This hook is **not** an OS, filesystem, network, credential, model, or provider sandbox. It also cannot parse bash command semantics. Read-only bash usage is instruction-governed.

The plain `read-only` agent remains stricter: it can call only `read`, no `bash` at all. Its controller must provide command and search output in the task prompt. The controller must also identify every file that the agent must read.

`code-review` returns a strict `## Code Review` report that ends in the status line. `document-review` returns a strict `## Document Review` report that ends in the status line. The child's complete final assistant message is the result content. Tau relays the full report verbatim, with no heading extraction.

Agent definitions can pin `provider`, `model`, and `reasoningEffort` in their frontmatter. Unless a skill, the config file, or the user explicitly prescribes the override, **do not override pinned values**. The `implementation` definition pins `provider: "openrouter"`, `model: "deepseek/deepseek-v4-flash-0731"`, and `reasoningEffort: "high"`. The `code-review` and `document-review` definitions pin the same model at `reasoningEffort: "xhigh"`.

## Custom Agents, Scope, and Approval

Tau discovers agent definitions as Markdown files, with increasing precedence:

1. bundled agents in the extension
2. user agents in `~/.tau/agents/*.md`
3. project agents in the nearest ancestor `.tau/agents/*.md` directory

`agentScope: "user"` includes bundled and user definitions, `"project"` includes bundled and project definitions, and `"both"` includes all three layers. A higher-precedence definition replaces the same agent name.

Definitions require non-empty `name` and `description` frontmatter. They can set `profile: general-purpose`, `profile: read-only` (only `read`), or `profile: review` (`read` + read-only `bash`) and optional independent `provider`, `model`, and `reasoningEffort` strings. Their Markdown body becomes child instructions. Tau does not support an arbitrary per-agent `tools` list in this extension.

If a requested name resolves to a project definition, `confirmProjectAgents: true` asks for confirmation in Tau's TUI and fails closed in headless mode. After inspecting the definition, set `confirmProjectAgents: false` to approve it explicitly for that call. Tau project trust and project-extension approval are separate and do not approve project agent prompts.

## Provider, Model, and Thinking Effort Selection

By default, omit `provider`, `model`, and `reasoningEffort`. Subagents then inherit the parent session's active provider, model, and thinking level unless a config file, agent definition, or call value pins one. Unless the user explicitly directs or approves an override, do not override any of them.

Per-field resolution, highest first:

1. `task` call `provider` / `model` / `reasoningEffort`
2. the subagent config file `[agents.<name>]` section
3. the selected agent definition's frontmatter
4. the subagent config file `[defaults]` section
5. the parent session's active provider, model, and thinking level.

The config file is `superpowers-subagent.toml` in `~/.tau/` or the nearest ancestor `<project>/.tau/` (project shadows user per key). A copy that encodes the current defaults ships at `extensions/superpowers-subagent/superpowers-subagent.example.toml`:

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

Loaded config files and dropped-config diagnostics appear in `details.configPaths` and `details.configDiagnostics`. Tau also reports in those fields every section whose agent name matches no bundled, user, or project definition. A typo therefore cannot silently no-op. Edits to the file apply to the next `task` call. You do not need to reload Tau.

The fields are independent and map directly to Tau's separate provider and model settings:

```json
{
  "tasks": [
    {
      "agent": "implementation",
      "task": "Complete the delegated task."
    }
  ],
  "reasoningEffort": "high"
}
```

Do not combine or split values. In particular, a slash inside `model` remains part of the model identifier and does not infer a provider. A call-level value overrides only the corresponding lower-layer value.

## Child Context and Skill Isolation

Each child receives the selected agent body and the complete delegated task, but not the controller's conversation history. There is no mid-task conversation with the controller. If a child reports missing context, supply the context in a new complete `task` call.

Children run with discovered extensions and project resources disabled. Tau cannot independently disable user-global skills. Those skills can remain listed. The appended child prompt instructs the child not to invoke them. That prompt-only instruction is behavioral guidance, not a security boundary. Always include all workflow steps, requirements, relevant file paths, command output, and expected response format in the delegated task.

## Results and Status

Parent-model `content` is the child's complete final assistant message. It contains only the concatenated text blocks of the last accepted assistant message, never tool calls, thinking, or earlier messages. Tau applies no heading extraction anywhere:

- one result: success returns the complete final message, or `(no output)` when the message is empty. Failure returns `Agent <name> failed: <error>`.
- several results: a `<succeeded>/<total> succeeded` header plus one `[<agent>] (completed|failed)` section per child in input order. A section body is that child's complete final message, else its error message, else `(no output)`.

Structured `details` uses this versioned shape (fields marked `?` are optional):

```text
{
  schemaVersion: 2,
  agentScope: "user" | "project" | "both",
  projectAgentsDir: string | null,
  discoveryDiagnostics: string[],
  planned?: number,
  configPaths?: string[],
  configDiagnostics?: string[],
  results: [{
    agent, agentSource, task, cwd, exitCode, messages, stderr,
    usage: { input, output, cacheRead, cacheWrite, cost, contextTokens, turns },
    provider?, model?, reasoningEffort?, stopReason?, errorMessage?, status,
    timedOut, cancelled, malformedJsonLines
  }]
}
```

Inspect `details.results` for semantic status and process state. It also holds each child's complete accepted Tau wire messages, including tool calls and earlier turns. Content and details both represent failures. Tau tool results do not have an `isError` field.

Supported semantic statuses are:

- **DONE** — Continue.
- **DONE_WITH_CONCERNS** — If the concerns affect correctness or scope, read and resolve them before you continue.
- **BLOCKED** — Address the blocker, add context, change the approach, or ask the user.
- **NEEDS_CONTEXT** — Supply the missing information in a new complete dispatch.

Semantic status is distinct from process success. Check the result's failure text and structured process fields rather than assuming `BLOCKED` means the subprocess itself failed.

## Reviews That Can Run Read-Only bash

The `code-review` and `document-review` agents can obtain diffs and run searches themselves with read-only `bash` (`git diff`, `git log`, `git show`, `git status`, `grep`/`rg`/`find`). They must never change repo state. If the task itself can tempt a write, instruct them explicitly. Even so, supply the diff, verification output, and requirements in the task prompt. This keeps reviewers fast and their context focused.

A typical review call embeds the controller-provided diff while letting the reviewer check with read-only bash:

```json
{
  "tasks": [
    {
      "agent": "code-review",
      "task": "Review the named modified files for code quality. The controller-provided git diff follows; you may run read-only bash (git diff/log/status, grep/rg/find) to verify, but never change the repository state.\n\n## Git Diff\n[PASTE COMPLETE DIFF HERE]\n\n## Requirements\n[PASTE REQUIREMENTS HERE]\n\nReturn the strict report format: exact `## Code Review` heading (verdict, Critical/Important/Minor points — review adversarially, no praise), ending with the status line."
    }
  ]
}
```

For conditional loops such as implement → review → fix if needed → re-review, make separate `task` calls. Inspect each result.
