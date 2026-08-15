# Subagent Dispatch

## Purpose

The `task` tool delegates complete units of work to isolated Tau subprocesses. It supports single, ordered parallel, and sequential chain dispatch while preferring summary-first parent-model content and preserving complete accepted child messages in structured details. When a child omits the exact summary heading, its complete final assistant output is the documented fallback.

This is the canonical description of current behavior. See the [Tau `task` tool reference](../../skills/using-superpowers/references/tau-tools.md) for copyable calls and the [README](../../README.md) for installation.

## Requirements

### Requirement: Tau-discoverable installation

The package SHALL keep one canonical top-level `skills/` tree and expose it to project Tau sessions through the relative `.agents/skills` link. The installer SHALL link individual skills under `~/.tau/skills` and the extension under `~/.tau/extensions/superpowers-subagent` without replacing unrelated resources. A checkout SHALL support explicit extension loading with `tau -e extensions/superpowers-subagent` and SHALL NOT expose executable code through project `.tau/extensions` by default.

#### Scenario: Checkout discovery

- GIVEN Tau runs in an approved repository checkout
- WHEN Tau discovers project skills and the extension is explicitly loaded
- THEN Tau discovers the canonical skills and registers one tool named `task`

#### Scenario: User installation collision

- GIVEN an install destination exists and does not already point to this checkout's resource
- WHEN the installer preflights the destinations
- THEN installation stops before creating any new links
- AND the unrelated destination is not replaced

#### Scenario: Clone without extension approval

- GIVEN a user only clones the repository
- WHEN Tau starts without a user installation or explicit extension path
- THEN no executable project extension is discovered from this checkout

### Requirement: task modes and validation

A `task` call SHALL select exactly one non-empty mode: single (`agent` and `task`), parallel (`tasks`), or chain (`chain`). Empty arrays SHALL NOT select a mode. Single mode SHALL accept an optional top-level `cwd`; parallel and chain items SHALL accept their own optional `cwd` values. Every mode MAY include an optional `description` string used only as a display label.

Parallel mode SHALL accept at most eight items, run no more than four child processes concurrently, and preserve input order. Chain mode SHALL run sequentially, replace every `{previous}` occurrence with the preceding child's complete final assistant text, and assign one-based step numbers.

Invalid fields, values, mode combinations, or required strings SHALL prevent child startup and produce a normal Tau tool result describing the validation error and eligible agents.

#### Scenario: Single dispatch

- GIVEN exactly one non-empty `agent` and `task`
- WHEN `task` executes
- THEN one child runs with the requested agent and effective working directory

#### Scenario: Ordered parallel dispatch

- GIVEN between one and eight valid parallel items
- WHEN dispatch completes
- THEN at most four children were active concurrently
- AND final results have the same order as the input items

#### Scenario: Chain substitution

- GIVEN a successful chain step returns final assistant text
- WHEN the next step starts
- THEN every `{previous}` token in its task is replaced with that complete text rather than only the extracted summary

#### Scenario: Chain process failure

- GIVEN a chain child has a process or protocol failure, times out, or is cancelled
- WHEN that step ends
- THEN no later step starts
- AND details retain every completed or partial step

#### Scenario: Chain semantic status

- GIVEN a chain child exits successfully with `BLOCKED` or `NEEDS_CONTEXT`
- WHEN the child is finalized
- THEN the semantic status is recorded
- AND semantic status alone does not stop the chain

#### Scenario: Invalid request

- GIVEN zero or multiple selected modes, a partial single mode, an empty required string, an oversized parallel array, an unknown field, or an invalid common option
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

Definitions SHALL contain scalar YAML frontmatter with non-empty string `name` and `description` values. They MAY contain `profile` (`general-purpose` or `read-only`), `provider`, and `model`; profile SHALL default to `general-purpose`. Unknown metadata SHALL be ignored. Malformed, unreadable, incomplete, empty optional, or unknown-profile definitions SHALL be skipped with diagnostics that do not expose the body.

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

Each child SHALL run as a separate Tau JSON-mode process with safe argv and no shell. The process SHALL use its effective working directory and receive `--no-extensions`, `--no-approve`, `--cwd`, and a temporary `--append-system-prompt` file before the positional delegated task. Discovered child extensions and protected project resources SHALL be disabled, and a recursion guard SHALL prevent `task` registration if the extension is explicitly loaded in a child.

The appended prompt SHALL preserve the selected agent body and state that the child has no controller conversation history. It SHALL tell the child not to invoke ambient user skills. Because Tau cannot independently disable user-global skills, that instruction SHALL be documented as behavioral guidance rather than security enforcement.

#### Scenario: Safe default arguments

- GIVEN no provider, model, or read-only profile override
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

### Requirement: Provider and model overrides

`provider` and `model` SHALL be independent opaque strings at call and agent-definition levels. A call-level value SHALL override only the corresponding agent value. Effective values SHALL map directly to Tau's separate `--provider` and `--model` flags; absent values SHALL omit their flags. The extension SHALL NOT split combined values or infer a provider from a slash-containing model identifier.

#### Scenario: Partial call override

- GIVEN an agent definition sets provider and model and the call sets only model
- WHEN child argv is built
- THEN the agent provider is passed to `--provider`
- AND the call model is passed to `--model`

#### Scenario: Omitted overrides

- GIVEN neither the call nor agent defines provider or model
- WHEN child argv is built
- THEN both flags are absent
- AND the child uses Tau's configured defaults

#### Scenario: Opaque model identifier

- GIVEN a model value contains `/`
- WHEN the value is mapped to argv
- THEN the complete value is passed to `--model`
- AND no provider is inferred

### Requirement: Child tool profiles

A `general-purpose` definition SHALL use Tau's normal built-in coding tools. A `read-only` definition SHALL receive matching instructions and explicitly load a temporary public Tau policy extension that blocks every tool call except `read` before the built-in tool executes.

The read-only profile SHALL be documented as a Tau tool-call policy, not an operating-system sandbox. It does not constrain filesystem readability through allowed tools, subprocess account privileges, credentials, network access, model or provider behavior, prompt injection, or vulnerabilities.

#### Scenario: Read-only file access

- GIVEN a read-only child requests the `read` tool
- WHEN the policy hook handles the request
- THEN the request is permitted

#### Scenario: Read-only state-changing call

- GIVEN a read-only child requests `bash`, `write`, `edit`, or any other non-`read` tool
- WHEN the policy hook handles the request
- THEN the call is blocked before the built-in tool executes

#### Scenario: General-purpose child

- GIVEN an agent has the general-purpose profile
- WHEN child argv is built
- THEN no read-only policy extension is loaded

### Requirement: Tau JSON collection

The runner SHALL decode stdout as UTF-8 JSON Lines, retain validated portable messages from `message_end` events in arrival order, capture stderr separately, and ignore other valid lifecycle events. Malformed JSON and invalid `message_end` messages SHALL increment `malformedJsonLines` without discarding valid messages. A zero exit with no valid assistant message SHALL be a protocol failure.

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

### Requirement: Summary extraction and status

The appended response instructions SHALL tell every child to end with an exact `## Summary` heading and one of four status markers: `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, or `NEEDS_CONTEXT`.

Summary extraction SHALL recognize only a full line whose horizontal-whitespace-trimmed value is exactly `## Summary`, use the last matching line, and return from that heading through output end unchanged. Without a matching heading, the complete final assistant output SHALL be the fallback.

Status parsing SHALL independently use the last recognized case-insensitive bold or plain supported marker in final assistant output. If no marker exists, a successful child SHALL default to `DONE`; a failed, cancelled, timed-out, or protocol-invalid child SHALL default to `BLOCKED`.

#### Scenario: Last exact summary

- GIVEN final output contains multiple exact summary headings and similar non-heading text
- WHEN summary extraction runs
- THEN the last exact heading wins
- AND inline or extended heading text is ignored

#### Scenario: Missing summary

- GIVEN final output has no exact summary heading
- WHEN content is constructed
- THEN the complete final output is returned as fallback

#### Scenario: Independent status

- GIVEN a valid summary has no supported status marker
- WHEN summary and status parsing run
- THEN summary extraction still succeeds
- AND status uses the process-outcome default

#### Scenario: Last status

- GIVEN final output contains more than one recognized marker
- WHEN status is parsed
- THEN the last recognized marker determines semantic status

### Requirement: Context-small content and complete details

Final `content` SHALL prefer summary-scale text while `details` retains complete accepted child messages. Successful single content SHALL be the extracted summary, the complete final-output fallback when no exact heading exists, or `(no output)` for empty final text; failed single content SHALL be a concise failure. Parallel content SHALL include a success count and one input-ordered `[agent] (completed|failed)` summary/fallback section per item. Successful chain content SHALL be the final step's summary/fallback; failed chain content SHALL identify the stopped step concisely. A child that omits the requested summary can therefore return complete final output to the parent context.

Details SHALL be JSON with `schemaVersion: 1`, mode, scope, project agent directory, discovery diagnostics, and ordered child results. Each child result SHALL contain `agent`, `agentSource`, effective `task` and `cwd`, `exitCode`, complete accepted wire `messages`, `stderr`, usage fields, `status`, `timedOut`, `cancelled`, and `malformedJsonLines`; applicable `provider`, `model`, `stopReason`, `errorMessage`, and `step` fields SHALL also be included. Failure SHALL be represented through content and these fields because Tau tool results have no portable `isError` property.

#### Scenario: Single success

- GIVEN a successful child returns a summary after earlier output
- WHEN `task` returns
- THEN parent-model content contains only the summary
- AND details retain every accepted child message

#### Scenario: Parallel mixed outcome

- GIVEN successful and failed parallel children
- WHEN final content and details are built
- THEN the success count and child sections match input order
- AND every child retains complete partial and final messages in details

#### Scenario: Chain failure

- GIVEN a chain stops on a process or protocol failure, timeout, or cancellation
- WHEN `task` returns
- THEN content identifies the stopped step
- AND details contain completed and partial steps

#### Scenario: Semantic status versus process outcome

- GIVEN a child exits cleanly and reports `BLOCKED`
- WHEN result details are built
- THEN its semantic status is `BLOCKED`
- AND its process outcome can still be successful

### Requirement: Progress, cancellation, timeout, and cleanup

The extension SHALL emit portable partial results after each accepted assistant or tool-result message and after child completion. Single and chain updates SHALL retain accumulated results; parallel updates SHALL use deterministic input-order slots and progress counts.

Each child SHALL default to a 3600-second timeout and accept a positive call override no greater than 3600. Cancellation or timeout SHALL terminate the process, wait no more than five seconds, kill it if necessary, preserve partial messages and stderr, and prevent queued parallel or later chain work from starting. Every temporary prompt and read-only policy file SHALL be removed on success and all failure paths.

#### Scenario: Partial message update

- GIVEN a child emits an accepted assistant or tool-result message
- WHEN the update callback runs
- THEN it receives content under the same summary/fallback contract and schema-versioned partial details

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

#### Scenario: Timeout

- GIVEN a child exceeds its effective timeout
- WHEN its deadline expires
- THEN the process is terminated
- AND its result records `timedOut: true`, a failed process outcome, and default `BLOCKED` status when no marker exists

#### Scenario: Temporary cleanup

- GIVEN dispatch exits through success, spawn error, protocol error, cancellation, or timeout
- WHEN finalization completes
- THEN no temporary prompt or policy file remains

### Requirement: Portable rendering

The tool MAY provide public string-returning `render_call` and `render_result` callbacks. Collapsed rendering MAY show mode and success counts; expanded rendering MAY show complete final assistant output from details without adding it to parent-model content. Rendering SHALL use only public Tau APIs, and generic portable content SHALL remain usable if custom rendering is unavailable or returns no rendering.

#### Scenario: Expanded result

- GIVEN schema-versioned details contain a child's final assistant message
- WHEN the result is rendered in expanded form
- THEN the renderer may display the complete final assistant output from details
- AND rendering does not add or change parent-model content

#### Scenario: Unsupported details

- GIVEN details are absent or use an unsupported schema version
- WHEN the custom result renderer runs
- THEN it returns no custom rendering
- AND Tau can use generic portable rendering

## Intentional Port Differences

The current Tau implementation uses the lowercase `task` tool name and preserves all three dispatch modes, deterministic ordering, agent precedence, summary-first content with complete-output fallback, complete details, timeout, and cancellation. These differences from the historical pre-Tau implementation are intentional:

| Historical capability | Current Tau behavior |
| --- | --- |
| Combined provider/model setting | Separate opaque `provider` and `model` values |
| Arbitrary per-agent tool lists | Fixed `general-purpose` and `read-only` profiles |
| Complete skill suppression in children | Project resources and extensions are disabled; ambient user skills are discouraged by prompt only |
| Framework-specific component rendering | Public string renderers with generic fallback |
| Error-only result flag | Normal Tau result with explicit process/error fields |
| Project-agent prompt in headless use | Fails closed unless the caller explicitly approves it for that call |

## Security Boundaries

- Child processes isolate conversation context; they do not isolate the operating-system account, filesystem, network, credentials, provider, or model.
- `--no-approve` and `--no-extensions` disable protected project resources and discovered extensions for children. They are not a process sandbox.
- The read-only profile blocks Tau tool calls except `read`; it is defense in depth at the tool layer only.
- Ambient user skills can remain visible to children. The instruction not to invoke them is not enforcement.
- Project-agent approval protects against silently consuming repository-controlled prompt files. It is separate from Tau project trust and extension-code trust.
- Summary extraction is a context-management feature, not redaction. Complete final output is returned when the exact heading is absent, and complete accepted messages always remain in `details` and may appear in expanded rendering.
- Installing or explicitly loading the extension executes Python with the same account privileges as Tau; users must inspect code and use external sandboxing or restricted credentials when stronger isolation is required.
