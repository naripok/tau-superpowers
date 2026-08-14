# Proposal: Port pi-superpowers to Tau

## Intent

Make the repository installable and usable with Tau while preserving the skill-driven workflow and isolated subagent dispatch. The port replaces the Pi TypeScript extension with a Python Tau extension built only on public APIs.

## Scope

### In scope

- Expose the existing Agent Skills through a Tau-discovered project layout.
- Replace the Pi extension with a Python extension registering `Task`.
- Preserve single, parallel, and chained subprocess dispatch, agent definitions, summaries, status reporting, cancellation, progress, and structured details.
- Map provider and model selection to Tau's separate CLI options.
- Define explicit project-agent approval and child-resource isolation behavior.
- Port active skills, installation documentation, the living specification, and flow documentation to Tau.

### Out of scope

- Changes to Tau itself or use of private Tau session/Textual internals.
- An OS, filesystem, network, credential, or provider sandbox for subagents.
- Perfect visual parity with Pi's widget renderer.
- Supporting Pi and Tau from one extension implementation.
- Automatically migrating users' `~/.pi` configuration.

## Accepted contract

### Repository and install layout

The canonical, editable skill sources remain in top-level `skills/`. The checkout exposes them at `.agents/skills` with a relative directory symlink, avoiding duplicate copies and using the portable Agent Skills namespace. User installation symlinks each skill into `~/.agents/skills/` so it does not replace unrelated user skills.

The canonical extension and bundled agents live in `extensions/superpowers-subagent/`. Development and checkout use explicitly load it with:

```bash
tau -e extensions/superpowers-subagent
```

The installer symlinks that directory into `~/.tau/extensions/superpowers-subagent`, where Tau discovers it as user code. The repository will not auto-expose executable Python under project `.tau/extensions`; cloning a repository must not silently make its code extension-discoverable. If a user intentionally creates a project extension link, Tau's normal project trust plus `--project-extensions` requirements apply.

### Tool API

The extension registers exactly one tool named `Task` (capitalized) to keep all shipped skill examples compatible. It does not register a lowercase alias because duplicate tool surfaces add ambiguity.

The input object supports the existing modes and names:

- single: non-empty `agent` and `task`, with optional `cwd`;
- parallel: non-empty `tasks` array, at most 8 entries, each with non-empty `agent`, `task`, and optional `cwd`;
- chain: non-empty `chain` array, each with non-empty `agent`, `task`, and optional `cwd`; every `{previous}` occurrence receives the preceding step's complete final assistant text;
- common: optional `description`, `agentScope` (`user`, `project`, or `both`, default `user`), `confirmProjectAgents` (default `true`), `provider`, `model`, and `timeoutSeconds` (default 3600 per child, positive and at most 3600).

Exactly one mode must be supplied. In single mode `agent` and `task` must appear together. Empty arrays do not select a mode. Unknown or invalid values produce a normal `AgentToolResult` whose content and details describe the validation failure; Tau's portable result has no `isError` field.

Parallel mode preserves input ordering, accepts at most 8 tasks, and runs at most 4 children concurrently. Chain mode is sequential and stops on process/protocol failure, timeout, or cancellation. A semantic `BLOCKED` or `NEEDS_CONTEXT` status from an otherwise successful child is reported but does not itself stop a chain.

### Agent definitions and precedence

Agent files are Markdown with YAML frontmatter and a body used as appended system instructions. Discovery uses:

1. bundled `extensions/superpowers-subagent/agents/*.md` (lowest precedence),
2. `~/.tau/agents/*.md`,
3. the nearest ancestor `<directory>/.tau/agents/*.md` from the Task session cwd (highest precedence).

`agentScope: user` includes bundled and user agents; `project` includes bundled and project agents; `both` includes all three layers. Later layers replace the same agent name. Files and final agent ordering are lexically deterministic.

Required frontmatter fields are non-empty string `name` and `description`. Optional fields are `profile` (`general-purpose` or `read-only`), `provider`, and `model`. The default profile is `general-purpose`. Unknown fields are ignored. Malformed frontmatter, unknown profiles, unreadable files, and invalid required fields are skipped and included in discovery diagnostics. The old arbitrary `tools` field is removed because Tau has no `--tools` child option.

### Project-agent approval

Project agent Markdown is repository-controlled prompt input read by this extension, not Tau's built-in resource loader. The extension therefore applies a separate fail-closed rule whenever a requested name resolves to a project agent:

- with `confirmProjectAgents: true` in the TUI, show the resolved names and directory and run only after confirmation;
- with `confirmProjectAgents: true` in headless/print mode, reject the dispatch because no dialog is possible;
- with `confirmProjectAgents: false`, run without a dialog in either mode; setting this flag is the caller's explicit approval for that Task invocation.

No prompt is needed when project scope is requested but every requested agent resolves to bundled/user sources. Tau project trust and `--project-extensions` remain separate controls and do not substitute for this approval.

### Child Tau invocation and profiles

Children are launched without a shell using safe argv. The baseline is conceptually:

```text
tau --mode json --no-extensions --no-approve --cwd <child-cwd> \
  --append-system-prompt <temporary-agent-prompt> [provider/model flags] <task>
```

`--no-approve` excludes project skills, prompts, context, system-prompt files, and project extensions. `--no-extensions` excludes discovered user and project extensions and prevents recursive `Task` dispatch. Tau has no `--no-skills`: user-global skills remain listed. The appended child instructions tell the child not to invoke skills and to rely on the complete delegated prompt, but that instruction is not a security boundary.

`general-purpose` receives Tau's normal built-in coding tools. `read-only` receives an explicitly loaded temporary policy extension (`-e`) that blocks every tool call except Tau's `read` tool, plus matching prompt instructions. Tau does not provide separate `grep`, `find`, or `ls` tools; a read-only child may only read named files and must request missing command output from its controller. The policy is defense in depth at Tau's tool-call layer, not an OS sandbox: subprocess credentials, provider behavior, filesystem readability, and vulnerabilities are outside its boundary.

A recursion-guard environment variable is set for children. If the Task extension is nevertheless explicitly loaded in such a child, setup refuses to register `Task`.

### Provider and model selection

`provider` and `model` are separate optional Task strings and separate optional agent-frontmatter fields. Per-call values override agent values independently. Effective non-empty values map directly to `--provider` and `--model`; no `provider/model` splitting or inference occurs. If a value is absent at both levels its flag is omitted, so the child uses Tau's configured default. This is not guaranteed to reproduce a non-persisted provider/model selected only for the parent process.

### Output, status, and details

The extension parses UTF-8 JSON Lines from stdout. Valid `message_end` events are validated as portable Tau messages and retained in arrival order; malformed/non-event lines are ignored for message extraction and counted in diagnostics. Stderr is captured separately. A zero exit with no valid assistant message is a protocol failure.

The final output is all text blocks concatenated from the last assistant message. Summary extraction finds the last line exactly matching `## Summary` (allowing surrounding horizontal whitespace) and returns from that heading through the end unchanged. If absent, it returns the complete final output unchanged.

Status parsing examines the final assistant text and uses its last recognized case-insensitive bold or plain marker for `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, or `NEEDS_CONTEXT`. Without a marker, a clean child defaults to `DONE`; process/protocol failure, cancellation, or timeout defaults to `BLOCKED`.

Final `content` is deliberately context-small:

- single: extracted summary/fallback, or `(no output)` for an empty successful output;
- parallel: a success count followed by one input-ordered `[agent] (completed|failed)` section containing each summary/fallback;
- chain: final step summary/fallback, or a concise stop message when the chain fails.

`details` is JSON with this stable shape:

```text
{
  schemaVersion: 1,
  mode: "single" | "parallel" | "chain",
  agentScope: "user" | "project" | "both",
  projectAgentsDir: string | null,
  discoveryDiagnostics: string[],
  results: [{
    agent, agentSource, task, cwd, exitCode,
    messages, stderr,
    usage: {input, output, cacheRead, cacheWrite, cost, contextTokens, turns},
    provider?, model?, stopReason?, errorMessage?, status?, step?,
    timedOut, cancelled, malformedJsonLines
  }]
}
```

`messages` contains complete validated portable messages serialized with Tau wire aliases. Error results still use `AgentToolResult`; failure is represented by concise content and result fields because Tau has no portable `isError` result property.

The update callback emits partial `AgentToolResult` values after each accepted assistant/tool-result message and child completion. Single and chain updates include accumulated results; parallel updates include slots in input order and progress counts. Final output ordering is deterministic.

Cancellation is detected through `ToolCancellationToken.is_cancelled()`. On cancellation or timeout, the runner sends terminate, waits up to five seconds, then kills the process, retains partial messages/stderr, marks the result, and stops launching chain/queued parallel work. Every temporary prompt and policy file is removed in `finally` paths.

### Rendering

The implementation may attach `AgentTool.render_call` and `render_result` functions. Public Tau renderers return Rich-markup/plain strings, not Pi components or Textual widgets. Expanded rendering may use complete `details`; generic portable rendering remains the fallback. No private TUI API is permitted.

## Compatibility decisions

| Existing Pi behavior | Tau decision |
|---|---|
| Capitalized `Task` | Retained |
| Single, max-8 parallel/max-4 active, and chain modes | Retained |
| `{previous}` receives full output | Retained |
| Bundled/user/project agent overrides | Retained with Tau paths and nearest-project lookup |
| User-only default scope | Retained |
| TUI confirmation for project agents | Retained; headless now fails closed unless explicitly bypassed |
| Combined `model` such as `provider/model` | Removed; separate opaque `provider` and `model` fields |
| Arbitrary agent `tools` list and Pi `--tools` | Removed; fixed profiles and a public hook policy are used |
| Pi `--no-session --no-skills` | Removed; Tau print invocation uses `--no-extensions --no-approve`; user skills are prompt-discouraged only |
| Full Pi component rendering | Changed to public string renderers/generic fallback |
| Error `isError` result | Removed because Tau's portable result lacks it; details carry failure state |
| Summary-only parent context and full details | Retained |
| One-hour timeout and cancellation | Retained and made explicit/testable |

## Impact

- Step 1 replaces TypeScript in `extensions/superpowers-subagent/` with Python and tests this contract.
- Steps 3–4 update skill paths, tool examples, and claims about read-only enforcement and skill isolation.
- Step 5 adds the `.agents/skills` project link and installer/documentation without exposing project Python by default.
- Steps 6–7 reconcile the living specification and historical Pi documents after runtime verification.
