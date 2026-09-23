# Tau `task` Tool Reference

The `superpowers-subagent` Tau extension registers one tool named `task`. It launches one isolated `tau` subprocess per call for the delegated task. You must install the extension under `~/.tau/extensions/superpowers-subagent` or load it explicitly with:

```bash
tau -e extensions/superpowers-subagent
```

## task Tool API

Every `task` call carries exactly one task as one flat object. The examples below are the JSON argument objects for the tool call.

### One task per call

`prompt` is required: the child's task, preserved verbatim. `subagent_type` is optional, and omission selects `general-purpose`. `cwd` is optional and resolves relative to the parent Tau session's working directory:

```json
{
  "prompt": "Implement the caching layer as described in the supplied requirements.",
  "subagent_type": "general-purpose",
  "cwd": "/path/to/worktree"
}
```

### Parallel dispatch

Dispatch independent work with several `task` calls in one message. The calls run concurrently, and each result carries its own envelope:

```json
{
  "prompt": "Fix the supplied authentication test failures. Do not modify the batch module."
}
```

```json
{
  "prompt": "Fix the supplied batch test failures. Do not modify the authentication module."
}
```

Every task in one message must be independent: the tasks share no state and cannot see each other's progress. Conditional sequences require separate `task` calls across turns. This applies to implement → review → fix if needed → re-review, and to any loop where a later step depends on an earlier result. The separate calls let the controller inspect each result.

### Resume with task_id

A call with `task_id` continues that child session instead of starting a fresh one. Pass the earlier result's `task_id` with `subagent_type`. The child keeps its earlier messages and tool outputs, and the call's `prompt` is the new turn:

```json
{
  "prompt": "Now re-check the authz paths.",
  "subagent_type": "code-review",
  "task_id": "<task_id from the earlier result>"
}
```

`task_id` requires `subagent_type`. A resumed run uses the session's recorded creation cwd and ignores the call's `cwd`. Usage in details covers the resumed run only.

### When to dispatch

Dispatch a subagent only for substantive multi-step work that benefits from an isolated context window. Also dispatch a subagent for long-running work that must not block the parent session. Simple reads, searches, commands, and small edits are the parent's own tool calls. A subagent replaces the parent's tool calls for its task. Never dispatch a subagent and then do the same work yourself.

## Common Options

These optional fields work with every call:

| Field | Meaning |
|---|---|
| `subagent_type` | Optional agent name. Omission selects `general-purpose`. An unknown name fails closed and lists the roster. |
| `description` | Short display description. No behavioral effect. |
| `task_id` | Resume a previous child session. Pass the `task_id` from an earlier task result. It requires `subagent_type`. |
| `cwd` | Working directory for a fresh child. Omission uses the parent session cwd. A resumed run ignores it. |
| `agentScope` | `user` (default), `project`, or `both`. |
| `confirmProjectAgents` | Require TUI approval for selected project agents (default `true`). Setting it to `false` explicitly approves them for this call. |
| `provider` | Optional literal provider override. Omit it to inherit configuration. Otherwise pass an exact configured provider name from `tau providers`. Invalid names fail before any child starts, listing the configured providers. |
| `model` | Optional literal model override. Omit it to inherit configuration. Otherwise pass an exact model ID supported by the selected provider. Invalid IDs fail before any child starts, listing the provider's models. |
| `reasoningEffort` | Optional literal reasoningEffort override: `off`, `minimal`, `low`, `medium`, `high`, or `xhigh`. Omit it to inherit configuration. A call-level value overrides the config file and the selected agent definition. Otherwise the level falls back to the config file, then the agent definition, then the parent session's thinking level. The extension applies the level as the child's Tau thinking level at session start. If the level is unsupported for the effective provider/model, the child logs a `[superpowers-subagent] could not apply reasoning effort ...` diagnostic on its `stderr`. You can see this diagnostic in `details.results[].stderr`. The child then runs at its ambient level. |
| `timeoutSeconds` | Per-child timeout in seconds. The value must be greater than 0 and at most 10800. The default is 3600. |

Tau resolves a relative `cwd` from the parent Tau session's working directory. `cwd` applies to a fresh child. A resumed run uses the session's recorded creation cwd and ignores the call's `cwd`.

The values `default`, `inherit`, and `auto` are placeholders for the override fields. The call treats them as omitted and reports a repair note. Omit the field instead.

## Bundled Agent Profiles

| Agent | Tau tool policy | Use for |
|---|---|---|
| `general-purpose` | Normal built-in coding tools | Implementation, scouting, exploration, and tasks requiring commands or edits |
| `read-only` | Allows only `read` | Substantial multi-file investigation and review of named files |
| `implementation` | Normal built-in coding tools | Implementation tasks, TDD, running verification |
| `code-review` | `read` + read-only `bash` | Code quality review, spec compliance review, final review |
| `document-review` | `read` + read-only `bash` | Feature-spec review and plan review at the design workflow gates |

You can override provider, model, and thinking level per agent through the subagent config file (`[agents.<name>]`). See Provider, Model, and Thinking Effort Selection below.

Review-profile agents (`code-review`, `document-review`) can call `read` and `bash`. Their instructions restrict `bash` strictly to read-only operations. The allowed operations are `git diff`/`log`/`show`/`status`, `grep`/`rg`/`find` searches, and reading files with unknown exact paths. The instructions forbid changing repo or environment state. Forbidden actions include git writes, file creation or deletion, installs, test or build runs, and background processes.

They still cannot call `write`, `edit`, or other state-changing Tau tools. A public Tau `tool_call` hook blocks everything outside the allowed set. This hook is **not** an OS, filesystem, network, credential, model, or provider sandbox. It also cannot parse bash command semantics. Read-only bash usage is instruction-governed.

The plain `read-only` agent remains stricter: it can call only `read`, no `bash` at all. Its controller must provide command and search output in the task prompt. The controller must also identify every file that the agent must read.

`code-review` returns a strict `## Code Review` report that ends in the status line. `document-review` returns a strict `## Document Review` report that ends in the status line. The result content wraps the child's complete final assistant message in the task envelope. Tau relays the full report verbatim, with no heading extraction.

Agent definitions can pin `provider`, `model`, and `reasoningEffort` in their frontmatter. Unless a skill, the config file, or the user explicitly prescribes the override, **do not override pinned values**.

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

The config file is `superpowers-subagent.toml` in `~/.tau/` or the nearest ancestor `<project>/.tau/` (project shadows user per key). An example file ships at `extensions/superpowers-subagent/superpowers-subagent.example.toml`:

```toml
[defaults]
# provider = "openai"
# model = "gpt-5.6-sol"
# reasoningEffort = "medium"   # off | minimal | low | medium | high | xhigh

[agents.code-review]
# provider = "openrouter"
# model = "z-ai/glm-5.3"
# reasoningEffort = "medium"
```

Loaded config files and dropped-config diagnostics appear in `details.configPaths` and `details.configDiagnostics`. Tau also reports in those fields every section whose agent name matches no bundled, user, or project definition. As a result, a typo cannot silently no-op. Edits to the file apply to the next `task` call. You do not need to reload Tau.

The fields are independent and map directly to Tau's separate provider and model settings:

```json
{
  "prompt": "Complete the delegated task.",
  "subagent_type": "implementation",
  "reasoningEffort": "high"
}
```

Do not combine or split values. In particular, a slash inside `model` remains part of the model identifier and does not infer a provider. A call-level value overrides only the corresponding lower-layer value.

## Child Context and Skill Isolation

Each child receives the selected agent body and the complete delegated task, but not the controller's conversation history. There is no mid-task conversation with the controller. If a child reports missing context, supply the context in a new complete `task` call.

Children run with discovered extensions and project resources disabled. Tau cannot independently disable user-global skills. Those skills can remain listed. The appended child prompt instructs the child not to invoke them. That prompt-only instruction is behavioral guidance, not a security boundary. Always include all workflow steps, requirements, relevant file paths, command output, and expected response format in the delegated task.

## Results and Status

Parent-model `content` is one task envelope for every result that starts a child:

```text
<task id="<taskId>" state="completed|error"><task_result>COMPLETE FINAL MESSAGE</task_result></task>
```

The envelope `id` is the child's Tau session id, and details carry the same id as `taskId`. `completed` means the child finished and delivered a final assistant message. `error` means the child failed, was cancelled, timed out, or ended with no final assistant message. Child status markers (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`) stay inside the message text and do not change the envelope state.

A successful child wraps its complete final assistant message in `task_result`. A final message without text wraps the placeholder `(no output)`. An error child wraps its final assistant message in `task_error`. When no final message exists, the tag wraps the failure form `Subagent failed (task_id: <id>): <error>`. Repair notes appear as `Note:` lines before the envelope. The inner content is the child message verbatim.

Structured `details` uses this versioned shape (fields marked `?` are optional):

```text
{
  schemaVersion: 2,
  agentScope: "user" | "project" | "both",
  projectAgentsDir: string | null,
  discoveryDiagnostics: string[],
  planned?: 1,
  configPaths?: string[],
  configDiagnostics?: string[],
  results: [{
    agent, agentSource, taskId, task, cwd, exitCode, messages, stderr,
    usage: { input, output, cacheRead, cacheWrite, cost, estimatedCost, contextTokens, turns },
    provider?, model?, reasoningEffort?, stopReason?, errorMessage?, status,
    timedOut, cancelled, malformedJsonLines
  }]
}
```

For every result that starts a child, `results` holds exactly one entry and `planned` is 1. The entry carries no `taskId` after a failure before Tau creates the session.

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
  "subagent_type": "code-review",
  "prompt": "Review the named modified files for code quality. The controller-provided git diff follows; you can run read-only bash (git diff/log/status, grep/rg/find) to check claims, but never change the repository state.\n\n## Git Diff\n[PASTE COMPLETE DIFF HERE]\n\n## Requirements\n[PASTE REQUIREMENTS HERE]\n\nReturn the strict report format: exact `## Code Review` heading (verdict, Critical/Important/Minor points — review adversarially, no praise), ending with the status line."
}
```

For conditional loops such as implement → review → fix if needed → re-review, make separate `task` calls. Inspect each result.
