# Subagent Dispatch

## Purpose

The `task` tool delegates complete units of work to isolated Tau subprocesses through one homogeneous interface: every call takes a `tasks` array, one item runs a single child, and two or more items run in parallel with bounded concurrency and input-ordered results. Parent-model content is each child's complete final assistant message — never tool calls, thinking, or earlier messages, and with no heading extraction — while structured details retain the complete accepted wire messages. Per-subagent provider, model, and thinking-effort values resolve at call, then a `superpowers-subagent.toml` config file (`[agents.<name>]` and `[defaults]` sections), then agent definitions, then the parent session's active provider, model, and thinking level.

This is the canonical description of current behavior. See the [Tau `task` tool reference](../../skills/using-superpowers/references/tau-tools.md) for copyable calls and the [README](../../README.md) for installation.

## Requirements

### Requirement: Tau-discoverable installation

The package SHALL keep one canonical top-level `skills/` tree and expose it to project Tau sessions through the relative `.agents/skills` link. The installer SHALL link individual skills under `~/.tau/skills` and the extension under `~/.tau/extensions/superpowers-subagent` without replacing unrelated resources. A checkout SHALL support explicit extension loading with `tau -e extensions/superpowers-subagent` and SHALL NOT expose executable code through project `.tau/extensions` by default.

#### Scenario: Checkout discovery

- GIVEN Tau runs in an approved repository checkout
- WHEN Tau discovers project skills and the extension is explicitly loaded
- THEN Tau discovers the canonical skills and registers one tool named `task`

#### Scenario: Prompt threshold

- GIVEN the task tool is registered
- WHEN its always-visible prompt surface (description, snippet, and guidelines) is read
- THEN it states that subagents exist for substantive multi-step work that benefits from an isolated context window or for long-running work that must not block the parent session
- AND it forbids dispatching simple reads, searches, commands, and small edits the parent can perform itself
- AND it forbids dispatching work the parent is about to perform itself, because a subagent replaces the parent's tool calls for its task

#### Scenario: User installation collision

- GIVEN an install destination exists and does not already point to this checkout's resource
- WHEN the installer preflights the destinations
- THEN installation stops before creating any new links
- AND the unrelated destination is not replaced

#### Scenario: Clone without extension approval

- GIVEN a user only clones the repository
- WHEN Tau starts without a user installation or explicit extension path
- THEN no executable project extension is discovered from this checkout

### Requirement: task interface and validation

A `task` call SHALL provide a required non-empty `tasks` array of 1–8 items, each `{agent, task, cwd?}` with non-empty `agent` and `task` strings and an optional string `cwd` resolved relative to the parent session working directory, plus the optional common fields (`description`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`). Call-level provider and model fields SHALL be trimmed literal overrides: whitespace-only values and case-insensitive `default`, `inherit`, or `auto` placeholders SHALL be rejected, and omission SHALL select lower-precedence configuration. One item SHALL run a single child; two or more items SHALL run no more than four child processes concurrently and SHALL preserve input order in results. The removed top-level `agent`, `task`, `cwd`, and `chain` fields SHALL be rejected as unknown fields, as SHALL any other unknown field or item field. `description` SHALL be a display label only.

An absent or empty `tasks` array, more than eight items, an invalid item (empty agent/task, non-string `cwd`, unknown item field), or an invalid common option SHALL prevent child startup and produce a normal Tau tool result describing the validation error and eligible agents.

#### Scenario: Single-item dispatch

- GIVEN exactly one valid task item with an item-level `cwd`
- WHEN `task` executes
- THEN one child runs with the requested agent and the effective working directory

#### Scenario: Ordered parallel dispatch

- GIVEN two to eight valid task items
- WHEN dispatch completes
- THEN at most four children were active concurrently
- AND final results have the same order as the input items

#### Scenario: Invalid request

- GIVEN a missing or empty `tasks` array, more than eight items, an invalid item, a removed mode field (top-level `agent`/`task`/`cwd`/`chain`), or an invalid common option
- WHEN request validation runs
- THEN no child starts
- AND content explains the error
- AND details contain no child results

### Requirement: Agent definition discovery

The extension SHALL discover Markdown agent definitions in three increasing-precedence layers:

1. bundled `extensions/superpowers-subagent/agents/*.md`;
2. user `~/.tau/agents/*.md`;
3. the nearest ancestor `.tau/agents/*.md` from the parent session working directory.

`agentScope: user` SHALL be the default and include bundled plus user definitions. `project` SHALL include bundled plus project definitions. `both` SHALL include all layers. A higher layer SHALL replace an agent with the same name, and final ordering SHALL be lexical.

Definitions SHALL contain scalar YAML frontmatter with non-empty string `name` and `description` values. They MAY contain `profile` (`general-purpose`, `read-only`, or `review`), `provider`, `model`, and `reasoningEffort` (one of `off`, `minimal`, `low`, `medium`, `high`, `xhigh`); profile SHALL default to `general-purpose`. Unknown metadata SHALL be ignored. Malformed, unreadable, incomplete, empty optional, unknown-profile, or unknown-reasoning-effort definitions SHALL be skipped with diagnostics that do not expose the body.

The bundled definitions are `general-purpose`, `read-only`, `implementation` (general-purpose profile), `code-review` (review profile, strict `## Code Review` report format ending in the status line), and `document-review` (review profile, strict `## Document Review` report format ending in the status line). They set no frontmatter provider, model, or reasoning-effort values, so they fall through to the configuration file and parent-session values described under the overrides requirement.

#### Scenario: Same-name override

- GIVEN bundled, user, and project definitions use the same agent name
- WHEN discovery runs with `agentScope: both`
- THEN the nearest project definition is selected

#### Scenario: Nearest project directory

- GIVEN more than one ancestor contains `.tau/agents`
- WHEN discovery starts from the parent session working directory
- THEN only the nearest directory is used as the project layer

#### Scenario: User scope

- GIVEN project definitions exist
- WHEN `agentScope` is omitted
- THEN bundled and user definitions are eligible
- AND project definitions are not read

#### Scenario: Invalid definition

- GIVEN a definition is malformed, unreadable, incomplete, or uses an unsupported profile
- WHEN its layer is scanned
- THEN that definition is skipped
- AND a discovery diagnostic identifies the file and reason

#### Scenario: Unknown requested agent

- GIVEN a requested name is not eligible in the selected scope
- WHEN that item is dispatched
- THEN no process starts for the item
- AND its failed result lists eligible names and sources

### Requirement: Explicit project-agent approval

Requested definitions that resolve to the project layer SHALL require separate approval. With `confirmProjectAgents: true`, an interactive Tau UI SHALL display the resolved names and source directory before spawning; headless execution SHALL fail closed. Setting `confirmProjectAgents: false` SHALL be explicit approval for that call only. Tau project trust and project-extension approval SHALL NOT imply approval of extension-managed project agent prompts.

#### Scenario: TUI approval

- GIVEN at least one requested name resolves to a project definition and confirmation is enabled
- WHEN the user approves the displayed definitions
- THEN dispatch proceeds

#### Scenario: TUI denial

- GIVEN project-agent confirmation is displayed
- WHEN the user denies or cancels it
- THEN no child starts
- AND content reports the cancellation

#### Scenario: Headless fail closed

- GIVEN a requested name resolves to a project definition, confirmation is enabled, and no UI is available
- WHEN `task` executes
- THEN no child starts
- AND content explains how to inspect and explicitly approve the definition

#### Scenario: Scope without project selection

- GIVEN project scope is enabled but every requested name resolves to bundled or user definitions
- WHEN `task` executes
- THEN no project-agent confirmation is required

### Requirement: Isolated Tau child invocation

Each child SHALL run as a separate Tau JSON-mode process with safe argv and no shell. The process SHALL use its effective working directory and receive `--no-extensions`, `--no-approve`, `--cwd`, and a temporary `--append-system-prompt` file before the positional delegated task. Discovered child extensions and protected project resources SHALL be disabled, and a recursion guard SHALL prevent `task` registration if the extension is explicitly loaded in a child. Read-only and review children SHALL additionally load a temporary profile policy extension permitting exactly their profile's tools (`read` only, or `read` plus `bash` for read-only use), and children with an effective reasoning effort SHALL additionally load a temporary extension that applies that level to the child session before its first turn.

Tau 0.3 exposes no CLI flag or extension-hook seam for a child's startup thinking level, so the generated extension calls the child session's own `set_thinking_level` API at `session_start`, reaching the bound session through the extension runtime view. The level is validated against the effective provider/model catalog; when it is unavailable, the child SHALL print a `[superpowers-subagent] could not apply reasoning effort ...` diagnostic to `stderr` and continue at its ambient level.

The appended prompt SHALL preserve the selected agent body and state that the child has no controller conversation history. Its response-format instructions SHALL state that the child's complete final assistant message is relayed verbatim to the controller (earlier messages, tool calls, and thinking are not), SHALL require a self-contained final message covering what was accomplished or found, files read or modified, tests, errors, and concerns, and SHALL require it to end with exactly one supported status marker. The prompt SHALL tell the child not to invoke ambient user skills. Because Tau cannot independently disable user-global skills, that instruction SHALL be documented as behavioral guidance rather than security enforcement.

#### Scenario: Safe default arguments

- GIVEN no provider, model, or profile override
- AND the parent session exposes no provider or model values
- WHEN child argv is built
- THEN neither a shell nor unsupported legacy flags are used
- AND neither `--provider`, `--model`, nor a policy extension is present

#### Scenario: Working directory

- GIVEN an item-specific relative or absolute `cwd`
- WHEN the child starts
- THEN the process working directory and Tau `--cwd` both use the resolved directory
- AND a relative value is resolved from the parent session working directory

#### Scenario: Recursion guard

- GIVEN a child process carries the recursion environment guard
- WHEN the subagent extension is explicitly loaded despite disabled discovery
- THEN its setup does not register `task`

### Requirement: Provider, model, and reasoning-effort overrides

`provider` and `model` SHALL be independent opaque strings at call, config-file, and agent-definition levels. Call-level `provider`, `model`, and `reasoningEffort` fields are optional literal overrides. Callers SHALL omit them for normal dispatch and inheritance. `default`, `inherit`, and `auto` SHALL NOT select defaults and are invalid placeholders. For call-level provider and model values, validation SHALL trim surrounding whitespace, reject values empty after trimming, and reject the reserved placeholders after case-insensitive normalization. It SHALL preserve all other internal content. A rejected override SHALL prevent every child from starting and explain that omitting the field selects inherited configuration.

Per field, provider and model resolution SHALL fall through call-level value, then the config file's `[agents.<name>]` section, then the agent definition, then the config file's `[defaults]` section, then the parent session's active provider and model, when the parent exposes them. A value at a higher layer SHALL override only the corresponding lower-layer value. Effective values SHALL map directly to Tau's separate `--provider` and `--model` flags; values absent at every level SHALL omit their flags. The extension SHALL NOT split combined values or infer a provider from a slash-containing model identifier.

`reasoningEffort` SHALL resolve at call, then config-file `[agents.<name>]`, then agent-definition, then config-file `[defaults]` precedence, then SHALL fall back to the parent session's active thinking level by default, so unpinned children inherit it. The effective level SHALL be mapped to the generated child extension described under child invocation and recorded as `reasoningEffort` on the child result. Invalid or empty call values SHALL be rejected before child startup; invalid agent-definition values SHALL skip that definition with a diagnostic; invalid config-file values SHALL be dropped with a config diagnostic. When no level resolves, the child runs at its ambient level and no thinking extension is generated.

The task schema, always-visible prompt guidance, and README SHALL identify all three fields as optional literal overrides. They SHALL tell callers to omit the fields during normal calls and for inheritance, and state that placeholders do not select defaults. Provider guidance SHALL require an exact configured provider name from `tau providers`. Model guidance SHALL require an exact model ID supported by the selected provider. Reasoning guidance SHALL list `off`, `minimal`, `low`, `medium`, `high`, and `xhigh`.

#### Scenario: Reserved override placeholders

- GIVEN a task call passes `default`, `inherit`, or `auto` as provider or model with surrounding whitespace or mixed-case letters
- WHEN request validation runs
- THEN no child starts
- AND content identifies the field as a literal override
- AND content tells the caller to omit the field for inherited configuration

#### Scenario: Exact literal override

- GIVEN a task call passes `provider: " openai "` and `model: " vendor/model name "`
- WHEN request validation runs
- THEN `openai` and `vendor/model name` reach child configuration
- AND validation changes no other content

#### Scenario: Whitespace-only override

- GIVEN a task call passes only whitespace as provider or model
- WHEN request validation runs
- THEN no child starts
- AND content states that the field requires a non-empty string

#### Scenario: Schema, prompt, and README override guidance

- GIVEN a caller reads the task schema, always-visible prompt guidance, and README override documentation
- WHEN the caller selects an override
- THEN each source identifies provider, model, and reasoningEffort as optional literal overrides
- AND each source tells the caller to omit the fields during normal calls and for inheritance
- AND each source states that placeholders do not select defaults
- AND provider guidance refers to an exact configured provider name from `tau providers`
- AND model guidance refers to an exact model ID supported by the selected provider
- AND reasoning guidance lists `off`, `minimal`, `low`, `medium`, `high`, and `xhigh`

#### Scenario: Partial call override

- GIVEN an agent definition sets provider and model and the call sets only model
- WHEN child argv is built
- THEN the agent provider is passed to `--provider`
- AND the call model is passed to `--model`

#### Scenario: Config shadows a definition pin

- GIVEN the config file sets `[agents.<name>]` model and the agent definition pins provider and model
- WHEN child argv is built
- THEN the config model is passed to `--model`
- AND the agent provider is still passed to `--provider`

#### Scenario: Omitted overrides

- GIVEN no call, config, or agent value defines provider or model
- AND the parent session exposes no provider or model values
- WHEN child argv is built
- THEN both flags are absent
- AND no default provider or model flags are passed

#### Scenario: Opaque model identifier

- GIVEN a model value contains `/`
- WHEN the value is mapped to argv
- THEN the complete value is passed to `--model`
- AND no provider is inferred

#### Scenario: Effective reasoning effort

- GIVEN a call passes `reasoningEffort` and the agent definition also sets one
- WHEN the child is launched
- THEN the call value wins
- AND the generated child extension applies it before the first turn
- AND the child result records the effective value

#### Scenario: Parent thinking inheritance

- GIVEN an unpinned agent and no call- or config-level reasoning value
- AND the parent session runs at a thinking level
- WHEN the child is launched
- THEN the parent level is the effective reasoning effort
- AND the generated child extension applies it before the first turn

#### Scenario: Unsupported reasoning effort

- GIVEN the effective provider/model does not support the requested level
- WHEN the child session validates the level
- THEN the child prints a `[superpowers-subagent]` diagnostic to `stderr`
- AND the child still completes at its ambient level
- AND the result retains the `stderr` diagnostic

### Requirement: Subagent configuration file

A `superpowers-subagent.toml` file SHALL be optional and discovered in the same directories Tau reads its other durable configs from: the user Tau home (`~/.tau/`) and the nearest ancestor `<cwd>/.tau/` directory with a file, mirroring agent-definition discovery. The project file SHALL shadow the user file per key, so a partial project config overrides only the keys it sets.

The file SHALL support a `[defaults]` table (provider, model, `reasoningEffort` fallbacks for every agent) and `[agents.<name>]` tables with the same keys. Values SHALL be non-empty strings; `reasoningEffort` SHALL be one of `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, normalized case-insensitively. An absent or empty file SHALL leave the parent-inheritance defaults intact, so installing the shipped example SHALL NOT change behavior. Unknown keys, wrong-typed tables, empty strings, and invalid thinking levels SHALL be dropped with a diagnostic. A section whose agent name matches no bundled, user, or project definition SHALL be reported as a config diagnostic rather than silently no-oping, so a typo in an `[agents.<name>]` heading cannot be mistaken for an applied override.

The loaded file paths and diagnostics SHALL be recorded on every Task result as `configPaths` and `configDiagnostics` when non-empty. Missing files SHALL NOT produce diagnostics. A malformed or unreadable file SHALL be skipped with a diagnostic and SHALL NOT block other files or dispatch. Config edits SHALL apply to the next `task` call without a Tau reload.

#### Scenario: User file only

- GIVEN a `[defaults]` table in `~/.tau/superpowers-subagent.toml`
- WHEN an unpinned agent dispatches
- THEN the default values apply ahead of parent-session fallback

#### Scenario: Project shadows user per key

- GIVEN the user file sets a default model and the project file sets a different model plus a provider
- WHEN dispatch resolves the effective values
- THEN the project model and provider apply
- AND keys the project file does not set still come from the user file

#### Scenario: Nearest project directory only

- GIVEN more than one ancestor contains `.tau/superpowers-subagent.toml`
- WHEN dispatch resolves the config
- THEN only the nearest file is the project layer

#### Scenario: Invalid config content

- GIVEN a file is unreadable, malformed TOML, or contains unknown keys or invalid values
- WHEN the config loads
- THEN the invalid file or values are skipped
- AND diagnostics are recorded on the Task details
- AND dispatch still runs with the remaining valid configuration

### Requirement: Child tool profiles

A `general-purpose` definition SHALL use Tau's normal built-in coding tools. A `read-only` definition SHALL receive matching instructions and explicitly load a temporary public Tau policy extension that blocks every tool call except `read` before the built-in tool executes. A `review` definition SHALL receive matching instructions and explicitly load a temporary public Tau policy extension that permits only `read` and `bash`; its instructions SHALL restrict `bash` strictly to read-only operations — git read commands, `grep`/`rg`/`find` searches, and reading files with unknown exact paths — and SHALL forbid changing repository or environment state (no git commands that write, no file or directory mutation, no installs, no test or build runs, no background processes), reporting what is needed when a review requires a state change.

The profiles SHALL be documented as a Tau tool-call policy, not an operating-system sandbox. They do not constrain filesystem readability through allowed tools, subprocess account privileges, credentials, network access, model or provider behavior, prompt injection, or vulnerabilities. The policy hook cannot parse bash command semantics, so read-only bash usage is instruction-governed: a review-profile child that disobeys its instructions can still change state through `bash`, and the profile is defense in depth at the tool layer only.

#### Scenario: Read-only file access

- GIVEN a read-only child requests the `read` tool
- WHEN the policy hook handles the request
- THEN the request is permitted

#### Scenario: Read-only state-changing call

- GIVEN a read-only child requests `bash`, `write`, `edit`, or any other non-`read` tool
- WHEN the policy hook handles the request
- THEN the call is blocked before the built-in tool executes

#### Scenario: Review bash permitted

- GIVEN a review-profile child requests `bash` or `read`
- WHEN the policy hook handles the request
- THEN the request is permitted
- AND the child's instructions confine bash to read-only operations

#### Scenario: Review state-changing Tau tool

- GIVEN a review-profile child requests `write`, `edit`, or any other tool outside `read`/`bash`
- WHEN the policy hook handles the request
- THEN the call is blocked before the built-in tool executes

#### Scenario: General-purpose child

- GIVEN an agent has the general-purpose profile
- WHEN child argv is built
- THEN no profile policy extension is loaded

### Requirement: Tau JSON collection

The runner SHALL decode stdout as UTF-8 JSON Lines, retain validated portable messages from `message_end` events in arrival order, capture stderr separately, and ignore other valid lifecycle events. Malformed JSON and invalid `message_end` messages SHALL increment `malformedJsonLines` without discarding valid messages. A zero exit with no valid assistant message SHALL be a protocol failure.

When a child exits nonzero without an existing error message, the runner SHALL create an error message containing the exit code and a cleaned stderr excerpt. Cleaning SHALL remove only ECMA-48 CSI sequences with `ESC [`, zero or more parameter bytes from `0` through `?`, zero or more intermediate bytes from space through `/`, and one final byte from `@` through `~`. It SHALL preserve all other code points. The runner SHALL clean before it truncates and SHALL retain the final 2,000 Unicode code points when stderr exceeds that limit. The error message SHALL include all cleaned stderr at or below that limit. Structured child details SHALL retain complete, unmodified stderr. An existing error message SHALL remain unchanged.

If the created error's excerpt contains `Unknown provider:` case-insensitively, the error message SHALL tell the caller to omit provider, model, and reasoning overrides for configured values and to use an exact provider name from `tau providers`. If the excerpt contains `Model is not configured for provider` case-insensitively, it SHALL tell the caller to omit the model for inheritance or use an exact model ID supported by the provider. Recovery instructions SHALL depend only on the bounded excerpt.

Final assistant output SHALL concatenate every text block in the last accepted assistant message in block order. Accepted assistant usage SHALL accumulate input, output, cache, and cost fields, count turns, and record the latest assistant context-token total.

#### Scenario: Mixed event stream

- GIVEN stdout contains valid lifecycle events, malformed lines, and valid assistant and tool-result `message_end` events
- WHEN collection finishes
- THEN valid messages remain in arrival order
- AND malformed input is counted
- AND unrelated valid events are ignored

#### Scenario: Multiple assistant text blocks

- GIVEN the last assistant message contains more than one text block
- WHEN final output is extracted
- THEN their text is concatenated in block order

#### Scenario: No assistant message

- GIVEN Tau exits zero without a valid assistant message
- WHEN the runner finalizes the child
- THEN the result is a protocol failure with default `BLOCKED` status

#### Scenario: Nonzero exit exposes cleaned stderr

- GIVEN a child writes an ANSI-colored diagnostic to stderr and exits nonzero without an existing error message
- WHEN the runner finalizes the child result
- THEN the error message contains the exit code and diagnostic text without a CSI sequence
- AND structured details retain the original stderr

#### Scenario: Bounded Unicode stderr excerpt

- GIVEN a child writes CSI text, then more than 2,000 Unicode code points, then more CSI text to stderr
- AND the child exits nonzero without an existing error message
- WHEN the runner finalizes the child result
- THEN the error message contains exactly the final 2,000 cleaned Unicode code points
- AND structured details retain complete original stderr

#### Scenario: Malformed CSI text is preserved

- GIVEN a child writes a trailing bare `ESC [` without a final byte and exits nonzero without an existing error message
- WHEN the runner finalizes the child result
- THEN the stderr excerpt retains the trailing bare `ESC [` unchanged

#### Scenario: Existing error message is preserved

- GIVEN a child has an error message and writes stderr before a nonzero exit
- WHEN the runner finalizes the child result
- THEN its error message remains unchanged
- AND structured details retain complete stderr

#### Scenario: Provider recovery

- GIVEN the bounded stderr excerpt identifies an unknown provider
- WHEN the runner creates the nonzero-exit error message
- THEN the error message tells the caller to omit provider, model, and reasoning overrides for configured values
- AND it refers to exact provider names from `tau providers`

#### Scenario: Model recovery

- GIVEN the bounded stderr excerpt identifies a model that is not configured for its provider
- WHEN the runner creates the nonzero-exit error message
- THEN the error message tells the caller to omit the model for inheritance
- AND it refers to an exact model ID supported by the provider

#### Scenario: Diagnostic outside stderr excerpt

- GIVEN cleaned stderr identifies an unknown provider before more than 2,000 later code points
- WHEN the runner creates the nonzero-exit error message
- THEN the error message contains the bounded stderr excerpt
- AND it contains no provider recovery instruction

### Requirement: final-message content and status

The appended response instructions SHALL tell every child that its complete final assistant message — the concatenated text blocks of its last accepted assistant message — is relayed verbatim to the controller, that earlier messages, tool calls, and thinking are never relayed, and that the final message must therefore be self-contained and end with exactly one of four status markers: `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, or `NEEDS_CONTEXT`. The bundled `code-review` definition SHALL require exactly one `## Code Review` report section (verdict plus Critical/Important/Minor points) ending in the status line; the bundled `document-review` definition SHALL require exactly one `## Document Review` report section likewise. No agent SHALL be required to produce a dedicated summary section, and no heading extraction SHALL occur anywhere.

Status parsing SHALL use the last recognized case-insensitive bold or plain supported marker in final assistant output. If no marker exists, a successful child SHALL default to `DONE`; a failed, cancelled, timed-out, or protocol-invalid child SHALL default to `BLOCKED`.

#### Scenario: Verbatim relay

- GIVEN a child's last assistant message contains several text blocks, preceded by tool calls, thinking, and earlier assistant messages
- WHEN parent-model content is built
- THEN the complete concatenated last-message text is returned
- AND tool calls, thinking, and earlier messages are absent

#### Scenario: Reviewer report

- GIVEN a code-review child returns a `## Code Review` report ending in the status line
- WHEN parent-model content is built
- THEN the complete report is relayed verbatim
- AND no section is extracted or rewritten

#### Scenario: Independent status

- GIVEN a valid final message has no supported status marker
- WHEN status parsing runs
- THEN status uses the process-outcome default

#### Scenario: Last status

- GIVEN final output contains more than one recognized marker
- WHEN status is parsed
- THEN the last recognized marker determines semantic status

### Requirement: Content envelope and complete details

Final `content` SHALL follow the envelope contract built from child results only. With exactly one result, a successful child SHALL produce its complete final assistant message, or `(no output)` when that message has no text; a failed child SHALL produce `Agent <name> failed: <error>`, or `see details` when no error text exists. With two or more results, content SHALL begin with a `<succeeded>/<total> succeeded` line and contain one `[<agent>] (completed|failed)` section per child in input order; a section body SHALL be that child's complete final assistant message, else its error message, else `(no output)`. A failed child with no final assistant text SHALL expose the runner's actionable startup-configuration error in model-visible content, so the controller can retry with corrected arguments. Structured details SHALL retain complete stderr independently from the bounded error excerpt.

Details SHALL be JSON with `schemaVersion: 2`, scope, project agent directory, discovery diagnostics, and ordered child results, and SHALL contain no `mode` or `step` fields; non-empty subagent-config file paths and diagnostics SHALL be included as `configPaths` and `configDiagnostics`; partial results SHALL include `planned`, the intended child count, so live viewers can show accurate counts before every child has produced a message, and renderers SHALL fall back to the result count when `planned` is absent. Each child result SHALL contain `agent`, `agentSource`, effective `task` and `cwd`, `exitCode`, complete accepted wire `messages`, `stderr`, usage fields, `status`, `timedOut`, `cancelled`, and `malformedJsonLines`; applicable `provider`, `model`, `reasoningEffort`, `stopReason`, and `errorMessage` fields SHALL also be included. Failure SHALL be represented through content and these fields because Tau tool results have no portable `isError` property.

#### Scenario: Single success

- GIVEN a successful child returns a final message after earlier output and tool calls
- WHEN `task` returns
- THEN parent-model content is the complete final assistant message
- AND details retain every accepted child message

#### Scenario: Parallel mixed outcome

- GIVEN successful and failed children in one call
- WHEN final content and details are built
- THEN the success count and per-child sections match input order
- AND a failed child's section body is its error message when it has no final text
- AND every child retains complete partial and final messages in details

#### Scenario: Single failure

- GIVEN exactly one child fails without final text
- WHEN `task` returns
- THEN content is the concise `Agent <name> failed: <error>` form
- AND details retain the child's partial messages and error fields

#### Scenario: Recoverable startup failure

- GIVEN one child fails before it emits a valid assistant message
- AND the bounded cleaned stderr excerpt identifies an invalid provider or model
- WHEN `task` returns
- THEN content includes the agent name, Tau diagnostic, and matching recovery instruction
- AND structured details retain complete stderr

#### Scenario: Semantic status versus process outcome

- GIVEN a child exits cleanly and reports `BLOCKED`
- WHEN result details are built
- THEN its semantic status is `BLOCKED`
- AND its process outcome can still be successful

### Requirement: Progress, cancellation, timeout, and cleanup

The extension SHALL emit portable partial results after each accepted assistant or tool-result message and after child completion, for any item count. Updates SHALL carry `<done>/<planned> done` progress content and SHALL use deterministic input-order slots.

Each child SHALL default to a 3600-second timeout and accept a positive call override no greater than 3600. Cancellation or timeout SHALL terminate the process, wait no more than five seconds, kill it if necessary, preserve partial messages and stderr, and prevent queued work from starting. A hard cancellation of the task executing the dispatch (for example a print-mode SIGINT) SHALL kill any running child process so no child outlives the dispatch. Every temporary prompt, profile policy file, and thinking-policy file SHALL be removed on success and all failure paths.

#### Scenario: Partial message update

- GIVEN a child emits an accepted assistant or tool-result message
- WHEN the update callback runs
- THEN it receives `<done>/<planned> done` content and schema-versioned partial details

#### Scenario: Cancellation before spawn

- GIVEN cancellation is already requested when a child is scheduled
- WHEN the runner checks the token
- THEN no process starts
- AND the result records cancellation

#### Scenario: Cancellation while running

- GIVEN children are active and others are queued
- WHEN cancellation is observed
- THEN active processes are terminated and eventually killed if necessary
- AND queued children do not start

#### Scenario: Hard cancellation of the dispatch task

- GIVEN a child process is running and the task executing the dispatch is cancelled
- WHEN the cancellation propagates to the runner
- THEN the running child process is killed and does not outlive the dispatch

#### Scenario: Timeout

- GIVEN a child exceeds its effective timeout
- WHEN its deadline expires
- THEN the process is terminated
- AND its result records `timedOut: true`, a failed process outcome, and default `BLOCKED` status when no marker exists

#### Scenario: Temporary cleanup

- GIVEN dispatch exits through success, spawn error, protocol error, cancellation, or timeout
- WHEN finalization completes
- THEN no temporary prompt, policy, or thinking-policy file remains

### Requirement: Portable rendering

The tool MAY provide public string-returning `render_call` and `render_result` callbacks. Rendering SHALL use only public Tau APIs, and generic portable content SHALL remain usable if custom rendering is unavailable or returns no rendering.

Any child count SHALL render as one frame: a counts headline (`task · <succeeded>/<total> succeeded` with running/failed/pending clauses when positive, icon `…` while any child runs, else `✗` when any failed, else `✓`) followed by one self-contained child component per child in input order: a header, the streamed work (collapsed: the newest items with a truncation hint; expanded: the full stream), status icons/hints, error, delegated task, and usage counters. A `Total:` aggregate usage line SHALL appear only when more than one child exists. The call label SHALL derive from the task count (`1 child`, `N children`). Rendering SHALL distinguish in-flight children (process not yet reaped) from succeeded and failed ones and SHALL map semantic status to icons (`DONE` ✓, `DONE_WITH_CONCERNS` ⚠, `BLOCKED` ✗, `NEEDS_CONTEXT` ?). Because Tau re-renders the tool row after every accepted child message, expanded and collapsed views SHALL update live from the same details payload. Rendering SHALL NOT add or change parent-model content.

#### Scenario: Live child view

- GIVEN a child is running and has emitted an assistant message with a tool call
- WHEN the update renders the result
- THEN the row shows an in-flight marker, the streamed tool call, and partial usage
- AND the child's final assistant output remains available in subsequent renders

#### Scenario: Live planned counts

- GIVEN partial details include `planned` and fewer children than planned
- WHEN the result renders collapsed
- THEN the headline shows `succeeded/planned` with running and pending counts

#### Scenario: Expanded result

- GIVEN schema-versioned details contain a child's final assistant message
- WHEN the result is rendered in expanded form
- THEN the renderer shows complete streamed output, the delegated task, and usage from details
- AND rendering does not add or change parent-model content

#### Scenario: Unsupported details

- GIVEN details are absent or use an unsupported schema version
- WHEN the custom result renderer runs
- THEN it returns no custom rendering
- AND Tau can use generic portable rendering

### Requirement: Session-scoped subagent usage aggregation

The extension SHALL accumulate each child result's reported token usage and cost into session-scoped totals across task calls. Live partial results SHALL update an in-flight snapshot of the current call's children that replaces the call's previous snapshot. Committing a call's final result SHALL fold it into the committed totals exactly once and SHALL clear that call's in-flight snapshot. A call that ends without a final result being committed SHALL discard that call's in-flight snapshot. The displayed totals at any moment SHALL equal the committed totals plus the latest in-flight snapshot of every active call; concurrent calls SHALL keep separate in-flight snapshots. A run SHALL be a child result that reports non-zero token usage or cost. Children whose results report no token usage or cost SHALL contribute nothing, including the run count. The accumulation SHALL reset to zero when the active session rebinds to a new, resumed, or branched session. The aggregation SHALL NOT alter task result content, details, per-child usage reporting, or the tool's portable rendering.

The dispatcher feeds the tracker as an observer: every live `Task` update replaces the snapshot keyed to that call's tool call id, and each call's final result commits once, so snapshots never double-count even when concurrent task calls share one session.

#### Scenario: No double counting across live updates
- GIVEN a running call emits multiple live updates whose per-child usage accumulates over the child's messages
- WHEN the call commits its final result
- THEN each child's final usage is included exactly once in the committed totals

#### Scenario: Snapshot cleared on commit
- GIVEN a call has committed and no later call has started
- WHEN the displayed totals are read
- THEN they equal the committed totals with no contribution from the committed call's snapshot

#### Scenario: Snapshot discarded without commit
- GIVEN a call is aborted before its final result is committed
- WHEN the displayed totals are read before any later call emits
- THEN they equal the committed totals alone

#### Scenario: Sequential calls accumulate
- GIVEN two calls complete successfully in the same session
- WHEN the totals are read
- THEN they equal the sum of both calls' child usage and cost

#### Scenario: Concurrent calls keep separate snapshots
- GIVEN two calls are in flight in the same session
- WHEN one call commits or is discarded
- THEN the other call's in-flight snapshot still contributes to the displayed totals

#### Scenario: Zero-usage children
- GIVEN a child never started or reported no token usage or cost
- WHEN the totals are read
- THEN it contributes no tokens, cost, or run count

#### Scenario: Partial usage on process failure
- GIVEN a child that timed out, was cancelled, or failed its protocol retains partial messages with usage
- WHEN its call commits
- THEN its partial usage is included in the totals

#### Scenario: Session rebind resets
- GIVEN the active session rebinds to a new, resumed, or branched session
- WHEN the totals are read
- THEN they are zero

#### Scenario: Aggregation leaves results unchanged
- GIVEN a task call completes while aggregation is active
- WHEN the task result, its details, and its per-child usage fields are inspected
- THEN they are identical to the same call without aggregation

### Requirement: Sidebar subagent usage section

In a frontend that shows a sidebar summary, the extension SHALL display the current totals (committed plus in-flight) in a `subagents` section positioned immediately below the `usage` section. The section SHALL be omitted when no child has reported non-zero token usage or cost. When the summary contains no `usage` section, the `subagents` section SHALL NOT be injected. The section SHALL present the number of runs and the accumulated input, output, and cost using the same token and cost formatting as the `usage` section, where input SHALL include cached and cache-written tokens as the `usage` section's input does. The section SHALL show a cost value only when at least one child reported a non-zero cost. The section SHALL NOT appear in the narrow-layout session summary. Whenever the sidebar summary is rebuilt, the section SHALL reflect the latest committed or in-flight totals.

Tau 0.3 exposes no public sidebar content extension point (the sidebar summary is built by core from session stats), so the display wraps `tau_coding.tui.widgets._build_sidebar_content`, the one function through which every sidebar summary is constructed, and splices the section below the usage section. The seam is version-guarded: when any expected part is missing or a build fails, the original summary is returned unchanged. Mid-run display updates on the sidebar's normal rebuild cadence; a live per-message refresh of subagent totals is intentionally not provided.

#### Scenario: Rebuild shows the section
- GIVEN a task call with child usage completed
- WHEN the sidebar summary is rebuilt
- THEN a `subagents` section appears directly below the `usage` section
- AND it shows the run count and accumulated token and cost totals

#### Scenario: In-flight totals
- GIVEN a call is in progress and at least one child has emitted usage
- WHEN the sidebar summary is rebuilt
- THEN the section shows the committed totals plus that child's latest cumulative usage
- AND the run count includes each in-flight child that reports non-zero usage

#### Scenario: Summary without a usage section
- GIVEN a sidebar summary contains no `usage` section and child usage is non-zero
- WHEN the summary is built
- THEN no `subagents` section appears

#### Scenario: Empty totals hide the section
- GIVEN no child has reported non-zero token usage or cost
- WHEN the sidebar summary is rebuilt
- THEN no `subagents` section appears

#### Scenario: Cost omitted when unreported
- GIVEN children reported token usage but no cost
- WHEN the `subagents` section renders
- THEN the run count and token totals remain visible and no cost value appears

#### Scenario: Narrow layout omits the section
- GIVEN the frontend renders the narrow-layout session summary
- WHEN that summary is built
- THEN no `subagents` section appears

### Requirement: Unavailable sidebar display degrades safely

The display of the `subagents` section SHALL fail safe: when the running frontend shows no sidebar, lacks the sidebar-summary integration point the display relies on, or the display path fails while a summary is being built, the extension SHALL skip or abandon the display without raising, and the task tool, its results, and the usage aggregation SHALL remain fully functional.

#### Scenario: Print mode
- GIVEN a session runs without a sidebar frontend
- WHEN a task call completes
- THEN the aggregation still records totals
- AND the display path raises no error

#### Scenario: Missing integration point
- GIVEN the sidebar-summary integration point is unavailable
- WHEN the extension loads
- THEN the display is skipped
- AND task dispatch and aggregation continue unaffected

#### Scenario: Display failure during rebuild
- GIVEN the display path fails while a sidebar summary is being built
- WHEN the summary build completes
- THEN the summary remains the normal sidebar summary
- AND no error propagates to the frontend or the task tool

## Intentional Port Differences

The current Tau implementation uses the lowercase `task` tool name and provides one homogeneous tasks-array interface with deterministic ordering, agent precedence, complete-final-message content, complete details, timeout, and cancellation. These differences from the historical pre-Tau implementation are intentional:

| Historical capability | Current Tau behavior |
| --- | --- |
| Three dispatch modes | One homogeneous `tasks` array: one item for a single child, two or more for ordered parallel dispatch |
| Sequential output substitution | Removed; conditional sequences use separate calls so the controller can inspect each result |
| Summary/review-section extraction | Removed; content is the child's complete final assistant message, with complete accepted messages retained in `details` |
| Combined provider/model setting | Separate opaque `provider` and `model` values |
| Per-agent reasoning level | `reasoningEffort` at call, config-file, and definition levels with parent-session thinking inheritance by default, applied by a generated child extension because Tau 0.3 has no thinking-level CLI flag |
| Arbitrary per-agent tool lists | Fixed `general-purpose`, `read-only`, and `review` profiles |
| Complete skill suppression in children | Project resources and extensions are disabled; ambient user skills are discouraged by prompt only |
| Framework-specific component rendering | Public string renderers with generic fallback |
| Error-only result flag | Normal Tau result with explicit process/error fields |
| Project-agent prompt in headless use | Fails closed unless the caller explicitly approves it for that call |

## Security Boundaries

- Child processes isolate conversation context; they do not isolate the operating-system account, filesystem, network, credentials, provider, or model.
- `--no-approve` and `--no-extensions` disable protected project resources and discovered extensions for children. They are not a process sandbox.
- The read-only profile blocks Tau tool calls except `read`, and the review profile permits only `read` and `bash` with instruction-governed read-only bash usage; both are defense in depth at the tool layer only.
- Ambient user skills can remain visible to children. The instruction not to invoke them is not enforcement.
- Project-agent approval protects against silently consuming repository-controlled prompt files. It is separate from Tau project trust and extension-code trust.
- Parent-model content is the child's complete final assistant message only — tool calls, thinking, and earlier messages are never relayed. Complete accepted messages always remain in `details` and may appear in expanded rendering.
- Installing or explicitly loading the extension executes Python with the same account privileges as Tau; users must inspect code and use external sandboxing or restricted credentials when stronger isolation is required.
