# Delta: Port Subagent Dispatch to Tau

## Domain: subagent-dispatch

This delta compares [the Tau feature specification](2026-08-14-tau-port-spec.md) with the current living spec in `docs/specs/subagent-dispatch.md`.

### ADDED Requirements

#### Requirement: Tau-discoverable installation

The package SHALL expose its single canonical skill tree through `.agents/skills`, support per-skill user installation under `~/.agents/skills`, install the extension under `~/.tau/extensions/superpowers-subagent`, and support explicit development loading with `tau -e extensions/superpowers-subagent`. A clone SHALL NOT expose executable project extension code by default.

##### Scenario: Checkout resources

- GIVEN a trusted checkout
- WHEN Tau discovers project skills and is explicitly passed the extension path
- THEN it discovers the canonical skills and registers `Task`

#### Requirement: Task modes and validation

The extension SHALL register one capitalized `Task` tool and require exactly one valid single, parallel, or chain mode. Parallel mode SHALL accept at most eight tasks, execute at most four concurrently, and preserve input order. Chain mode SHALL replace every `{previous}` with the preceding complete final output and stop on process/protocol failure, timeout, or cancellation, but not on semantic status alone.

##### Scenario: Invalid mode

- GIVEN zero, partial, empty, invalid, or multiple modes
- WHEN validation runs
- THEN no child starts and the result explains the error

##### Scenario: Deterministic orchestration

- GIVEN valid parallel or chain input
- WHEN dispatch completes
- THEN child results retain input order and chain steps retain one-based step order

#### Requirement: Agent definition discovery

The system SHALL discover bundled agents, `~/.tau/agents`, and the nearest ancestor `.tau/agents` with increasing precedence. Scope SHALL default to bundled plus user definitions. Definitions require non-empty `name` and `description`, support fixed `profile`, `provider`, and `model` fields, and produce diagnostics when skipped.

##### Scenario: Override precedence

- GIVEN the same name exists in all layers and scope is `both`
- WHEN discovery runs
- THEN the nearest project definition wins

##### Scenario: Invalid definition

- GIVEN malformed or unsupported frontmatter
- WHEN discovery runs
- THEN the file is skipped with a diagnostic

#### Requirement: Explicit project-agent approval

Requested project-controlled agent definitions SHALL require a successful TUI confirmation by default. Headless execution SHALL fail closed while confirmation is enabled. `confirmProjectAgents: false` SHALL represent explicit per-call approval. Tau's separate project trust decision SHALL NOT implicitly approve these files.

##### Scenario: Headless project agent

- GIVEN a requested agent resolves to a project source in headless mode
- WHEN confirmation is enabled
- THEN no child starts

##### Scenario: Explicit approval

- GIVEN confirmation is disabled for the call
- WHEN the project definition is otherwise valid
- THEN dispatch may proceed without a dialog

#### Requirement: Isolated Tau child invocation

Children SHALL run Tau in JSON print mode with safe argv, no shell, explicit cwd, `--no-extensions`, `--no-approve`, an appended temporary prompt, and a recursion guard. Unsupported Pi options SHALL NOT be passed. User skills SHALL be discouraged by appended instructions because Tau cannot disable them independently; that instruction SHALL be documented as non-security enforcement.

##### Scenario: Recursion prevention

- GIVEN the recursion guard is set
- WHEN the Task extension loads in a child despite extension discovery being disabled
- THEN it does not register `Task`

#### Requirement: Provider and model overrides

Call and agent configuration SHALL carry separate opaque `provider` and `model` values. Call values override corresponding agent values; effective values map directly to separate Tau flags; absent values omit those flags; slash-containing models SHALL NOT be split.

##### Scenario: Partial override

- GIVEN only a call-level model overrides agent configuration
- WHEN argv is built
- THEN the agent provider and call model are passed independently

#### Requirement: Child tool profiles

`general-purpose` SHALL use Tau's built-in tool set. `read-only` SHALL load a temporary public-API extension that blocks every tool except `read` and SHALL receive matching instructions. This SHALL be documented as a tool-layer policy, not an OS or credential sandbox.

##### Scenario: Block state-changing tool

- GIVEN a read-only child calls `bash`, `write`, or `edit`
- WHEN the policy hook handles it
- THEN execution is blocked before the built-in tool runs

#### Requirement: Tau JSON collection

The runner SHALL retain validated portable messages from JSON `message_end` events, capture stderr, count malformed JSON and invalid `message_end` lines, ignore other valid lifecycle events, concatenate all text blocks in the last assistant message, and treat a zero exit with no assistant message as protocol failure.

##### Scenario: Mixed stream

- GIVEN malformed lines and valid assistant/tool-result events
- WHEN parsing completes
- THEN valid messages are retained in order and malformed lines are diagnosed

#### Requirement: Stable result details

Details SHALL be JSON schema version 1 and include orchestration metadata, discovery diagnostics, and complete input-ordered child results: identity, source, effective task/cwd, process state, portable messages, stderr, usage, provider/model, stop/error/status, step, timeout/cancellation, and malformed-line count. Failures SHALL use these fields because Tau's portable tool result has no `isError` property.

##### Scenario: Full details with small content

- GIVEN a child produces multiple messages and a final summary
- WHEN the result is built
- THEN complete messages remain in details while parent context receives summary-scale content

#### Requirement: Progress, cancellation, timeout, and cleanup

The system SHALL emit portable partial results after accepted messages and completion. It SHALL default to a 3600-second per-child timeout with a positive, capped override. Cancellation or timeout SHALL terminate, then kill after at most five seconds, preserve partial data, stop queued/later work, and clean every temporary file.

##### Scenario: Cancel active and queued work

- GIVEN active and queued children
- WHEN cancellation is observed
- THEN active children are terminated and queued children do not start

##### Scenario: Cleanup on failure

- GIVEN any spawn, protocol, timeout, or cancellation path
- WHEN finalization completes
- THEN temporary prompt and policy files are absent

#### Requirement: Portable rendering

Custom renderers, if implemented, SHALL use public string-returning Tau renderer protocols with generic fallback and SHALL NOT import private session or Textual APIs.

##### Scenario: Renderer failure

- GIVEN custom rendering fails
- WHEN Tau displays the result
- THEN generic portable content remains available

### MODIFIED Requirements

#### Requirement: Summary instruction appended to subagent prompt

The system SHALL preserve each selected agent body and append instructions to end with an exact `## Summary` heading and a final supported status marker. The same append instructions SHALL tell children not to invoke ambient user skills, while explicitly stating this is behavioral rather than security isolation.

##### Scenario: Prompt composition

- GIVEN a selected agent body
- WHEN the temporary append prompt is written
- THEN the body is unchanged before the response-format and child-isolation instructions

#### Requirement: Summary section extracted for tool result content

The system SHALL identify only a full line whose trimmed horizontal whitespace equals `## Summary`, use the LAST such heading, and return from that heading through output end unchanged. If no exact heading exists, it SHALL return the complete final assistant output. Final assistant output SHALL concatenate all text blocks from the last assistant message.

Status parsing SHALL independently use the last recognized case-insensitive bold or plain supported marker. Missing status SHALL default to `DONE` for a clean child and `BLOCKED` for process/protocol failure, cancellation, or timeout.

##### Scenario: Exact last heading

- GIVEN multiple exact summary headings and similar non-heading text
- WHEN extraction runs
- THEN the last exact heading wins and similar text is ignored

##### Scenario: Missing heading

- GIVEN no exact summary heading, including empty output
- WHEN extraction runs
- THEN complete final output is returned unchanged

##### Scenario: Status independent of summary

- GIVEN a summary heading without a marker
- WHEN parsing runs
- THEN summary extraction succeeds and status uses the outcome default

#### Requirement: Tool result content contract

Tool result content SHALL remain summary-sized while schema-versioned details retain complete validated child messages. Single content SHALL be the summary/fallback or `(no output)` for empty successful text. Parallel content SHALL include a success count and input-ordered `[agent] (completed|failed)` sections. Successful chain content SHALL use the final step summary/fallback; failed chain content SHALL be a concise stop message. Partial updates SHALL follow the same separation.

##### Scenario: Parallel mixed result

- GIVEN successful and failed parallel children
- WHEN the final result is built
- THEN each ordered section contains that child's summary/fallback and outcome
- AND details retain complete partial and final messages

##### Scenario: Failed chain

- GIVEN a chain stops on process/protocol failure, cancellation, or timeout
- WHEN the result is built
- THEN content identifies the stopped step concisely
- AND details contain all completed and partial steps

### REMOVED Requirements

None. The old summary behaviors are retained but made precise for Tau's message and result types. Pi-specific implementation mechanisms are replaced, not treated as living behavioral requirements.
