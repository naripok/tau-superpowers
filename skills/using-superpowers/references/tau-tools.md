# Tau `task` Tool Reference

The `superpowers-subagent` Tau extension registers two tools named `task` and `task_resume`. `task` launches one isolated `tau` subprocess per call for the delegated task. `task_resume` continues one of those child sessions. You must install the extension under `~/.tau/extensions/superpowers-subagent` or load it explicitly with:

```bash
tau -e extensions/superpowers-subagent
```

## task Tool API

Every `task` call carries exactly one task. The examples below are the JSON argument objects for the tool call.

### One task per call

`prompt` is required: the child's task, preserved verbatim. `subagent_type` is optional, and omission selects `general-purpose`. The child spawns in the parent Tau session's working directory:

```json
{
  "prompt": "Implement the caching layer as described in the supplied requirements.",
  "subagent_type": "general-purpose"
}
```

### task parameters

| Field | Meaning |
|---|---|
| `prompt` | Required. The child's task, preserved verbatim. |
| `subagent_type` | Optional agent name. Omission selects `general-purpose`. An unknown name fails closed and lists the roster. |
| `description` | Short display description. No behavioral effect. |
| `timeout_seconds` | Per-child timeout in seconds. The value must be greater than 0 and at most 10800. The default is 3600. |

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

### When to dispatch

Dispatch a subagent only for substantive multi-step work that benefits from an isolated context window. Also dispatch a subagent for long-running work that must not block the parent session. Simple reads, searches, commands, and small edits are the parent's own tool calls. A subagent replaces the parent's tool calls for its task. Never dispatch a subagent and then do the same work yourself.

## task_resume Tool API

`task_resume` continues an existing child session. The resumed agent comes from the session-agent mapping at `~/.tau/superpowers-subagent-sessions.json`, which records the agent name for every child session a `task` call starts. A `task_resume` call carries no agent name. For work that needs a different agent, make a fresh `task` call.

### Resume with task_id

A `task_resume` call with `task_id` continues that child session instead of starting a fresh one. The child keeps its earlier messages and tool outputs, and the call's `prompt` is the new turn:

```json
{
  "prompt": "Now re-check the authz paths.",
  "task_id": "<task_id from the earlier result>"
}
```

A resumed run uses the session's recorded creation cwd. Usage in details covers the resumed run only.

### task_resume parameters

| Field | Meaning |
|---|---|
| `prompt` | Required. The child's new turn, preserved verbatim. |
| `task_id` | Required. The child session id from an earlier task result. The resumed agent comes from the session-agent mapping. |
| `timeout_seconds` | Per-child timeout in seconds. The value must be greater than 0 and at most 10800. The default is 3600. |

Every resume failure starts zero children and directs the caller to `task` for a fresh child. The failure conditions include a missing mapping entry, a missing session record, and a mapped name that no discoverable agent provides.

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

Agent definitions can pin `provider`, `model`, and `reasoning_effort` in their frontmatter. Unless a skill, the config file, or the user explicitly prescribes the override, **do not override pinned values**.

## Custom Agents

Tau discovers agent definitions as Markdown files, with increasing precedence:

1. bundled agents in the extension
2. user agents in `~/.tau/agents/*.md`
3. project agents in the nearest ancestor `.tau/agents/*.md` directory

Discovery always covers all three layers. A higher-precedence definition replaces the same agent name, and project agents appear in the tool roster.

Definitions require non-empty `name` and `description` frontmatter. They can set `profile: general-purpose`, `profile: read-only` (only `read`), or `profile: review` (`read` + read-only `bash`) and optional independent `provider`, `model`, and `reasoning_effort` strings. Their Markdown body becomes child instructions. Tau does not support an arbitrary per-agent `tools` list in this extension.

## Provider, Model, and Thinking Effort Selection

Children inherit the parent session's active provider, model, and thinking level unless a config file or agent definition pins one. No call-level `provider`, `model`, or reasoning-effort parameter exists on either tool.

Per-field resolution, highest first:

1. the subagent config file `[agents.<name>]` section
2. the selected agent definition's frontmatter
3. the subagent config file `[defaults]` section
4. the parent session's active provider, model, and thinking level.

The config file is `superpowers-subagent.toml` in `~/.tau/` or the nearest ancestor `<project>/.tau/` (project shadows user per key). An example file ships at `extensions/superpowers-subagent/superpowers-subagent.example.toml`:

```toml
[defaults]
# provider = "openai"
# model = "gpt-5.6-sol"
# reasoning_effort = "medium"   # off | minimal | low | medium | high | xhigh

[agents.code-review]
# provider = "openrouter"
# model = "z-ai/glm-5.3"
# reasoning_effort = "medium"
```

Loaded config files and dropped-config diagnostics appear in `details.configPaths` and `details.configDiagnostics`. Tau also reports in those fields every section whose agent name matches no bundled, user, or project definition. As a result, a typo cannot silently no-op. Edits to the file apply to the next `task` or `task_resume` call. You do not need to reload Tau.

The pinned fields are independent and map directly to Tau's separate provider and model settings. Do not combine or split values. In particular, a slash inside `model` remains part of the model identifier and does not infer a provider. A higher-layer value overrides only the corresponding lower-layer value.

## Child Context and Skill Isolation

Each child receives the selected agent body and the complete delegated task, but not the controller's conversation history. There is no mid-task conversation with the controller. If a child reports missing context, supply the missing information in a `task_resume` call that continues the session, or make a fresh complete `task` call.

Children run with discovered extensions and project resources disabled. Tau cannot independently disable user-global skills. Those skills can remain listed. The appended child prompt instructs the child not to invoke them. That prompt-only instruction is behavioral guidance, not a security boundary. Always include all workflow steps, requirements, relevant file paths, command output, and expected response format in the delegated task.

## Results and Status

Parent-model `content` is one task envelope for every result that starts a child:

```text
<task id="<taskId>" state="completed|error"><task_result>COMPLETE FINAL MESSAGE</task_result></task>
```

The envelope `id` is the child's Tau session id, and details carry the same id as `taskId`. `completed` means the child finished and delivered a final assistant message. `error` means the child failed, was cancelled, timed out, or ended with no final assistant message. Child status markers (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`) stay inside the message text and do not change the envelope state.

A successful child wraps its complete final assistant message in `task_result`. A final message without text wraps the placeholder `(no output)`. An error child wraps its final assistant message in `task_error`. When no final message exists, the tag wraps the failure form `Subagent failed (task_id: <id>): <error>`. The inner content is the child message verbatim.

A rejected call starts no child. The result content is the teach-back text with no task envelope. The details carry an empty `results` array and no `planned` field.

Structured `details` uses this versioned shape (fields marked `?` are optional):

```text
{
  schemaVersion: 2,
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
- **NEEDS_CONTEXT** — Supply the missing information in a `task_resume` call that continues the session.

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
