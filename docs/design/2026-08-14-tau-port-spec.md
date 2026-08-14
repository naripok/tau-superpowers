# Spec: Tau Subagent Dispatch

## Domain: subagent-dispatch

### Requirement: Tau-discoverable installation

The package SHALL keep one canonical copy of each skill and expose the checkout through `.agents/skills`. User installation SHALL link individual skills under `~/.agents/skills` and the extension directory under `~/.tau/extensions/superpowers-subagent` without replacing unrelated resources.

#### Scenario: Checkout skill discovery

- GIVEN Tau runs in a trusted repository checkout
- WHEN Tau discovers project skills
- THEN it discovers the canonical skills through `.agents/skills`

#### Scenario: Extension development loading

- GIVEN a repository checkout
- WHEN Tau is started with `-e extensions/superpowers-subagent`
- THEN the Python extension registers the `Task` tool

#### Scenario: Clone alone does not expose project code

- GIVEN a user only clones the repository
- WHEN Tau starts without an explicit extension or user installation
- THEN no executable extension is exposed through project `.tau/extensions`

### Requirement: Task modes and validation

The extension SHALL register one tool named `Task`. A call SHALL select exactly one non-empty mode: single (`agent` plus `task`), parallel (`tasks`), or chain (`chain`). Parallel calls SHALL accept at most eight tasks and run at most four child processes concurrently. Results SHALL preserve input order.

#### Scenario: Single dispatch

- GIVEN exactly one non-empty `agent` and `task`
- WHEN `Task` executes
- THEN it runs one child with the requested agent and effective cwd

#### Scenario: Parallel dispatch

- GIVEN between one and eight valid `tasks`
- WHEN `Task` executes
- THEN it runs no more than four children concurrently
- AND returns results in input order

#### Scenario: Chain dispatch

- GIVEN a non-empty valid `chain`
- WHEN `Task` executes
- THEN it runs each step sequentially
- AND replaces every `{previous}` in a step task with the preceding step's complete final assistant text

#### Scenario: Invalid mode selection

- GIVEN zero or multiple modes, a partial single mode, empty required strings, an empty selected array, more than eight parallel tasks, or an invalid common option
- WHEN `Task` validates the call
- THEN no child starts
- AND content explains the error and available agents
- AND details contain no child results

#### Scenario: Chain process failure

- GIVEN a chain child fails, times out, is cancelled, or produces no valid final assistant message
- WHEN that step ends
- THEN no later chain step starts
- AND the result includes completed and partial steps

#### Scenario: Chain semantic status

- GIVEN a chain child exits cleanly with `BLOCKED` or `NEEDS_CONTEXT`
- WHEN the step ends
- THEN its status is recorded
- AND the chain continues because semantic status alone is not a process failure

### Requirement: Agent definition discovery

The system SHALL discover bundled agents, user agents from `~/.tau/agents`, and the nearest ancestor `.tau/agents` directory. Precedence SHALL be bundled, then user, then project. The default `agentScope` SHALL be `user`; `project` SHALL include bundled plus project; `both` SHALL include all layers.

Valid definitions SHALL have non-empty string `name` and `description`, a Markdown body, and optional `profile`, `provider`, and `model` strings. `profile` SHALL be `general-purpose` or `read-only` and default to `general-purpose`. Invalid or unreadable files SHALL be skipped with diagnostics.

#### Scenario: Same-name override

- GIVEN bundled, user, and project definitions share a name
- WHEN discovery runs with `both`
- THEN the project definition is selected

#### Scenario: Nearest project directory

- GIVEN multiple ancestor directories contain `.tau/agents`
- WHEN discovery starts at the Task session cwd
- THEN only the nearest directory is the project agent source

#### Scenario: User default excludes project definitions

- GIVEN project definitions exist
- WHEN `agentScope` is omitted
- THEN bundled and user definitions are eligible
- AND project definitions are not read or selected

#### Scenario: Invalid agent definition

- GIVEN a malformed, unreadable, incomplete, or unknown-profile agent file
- WHEN discovery runs
- THEN that definition is skipped
- AND a diagnostic identifies the file and reason without exposing its body

#### Scenario: Unknown requested agent

- GIVEN a requested name is not eligible in the selected scope
- WHEN dispatch is attempted
- THEN no process starts for it
- AND content lists eligible names and sources

### Requirement: Explicit project-agent approval

The system SHALL separately approve any requested agent that resolves to project-controlled Markdown. With confirmation enabled, the TUI SHALL ask before spawning and headless mode SHALL reject. `confirmProjectAgents: false` SHALL be explicit per-call approval. Tau project trust SHALL NOT implicitly approve project agent definitions.

#### Scenario: TUI approval

- GIVEN a requested name resolves to a project agent and confirmation is enabled
- WHEN the TUI user confirms the displayed names and source directory
- THEN dispatch proceeds

#### Scenario: TUI denial

- GIVEN project-agent confirmation is shown
- WHEN the user denies or cancels
- THEN no child starts
- AND content reports cancellation

#### Scenario: Headless fail closed

- GIVEN a requested name resolves to a project agent, confirmation is enabled, and no UI exists
- WHEN `Task` executes
- THEN no child starts
- AND content says to inspect the definition and explicitly set `confirmProjectAgents: false` to approve it

#### Scenario: Explicit bypass

- GIVEN `confirmProjectAgents` is false
- WHEN a requested project agent is otherwise valid
- THEN no extension dialog is required

#### Scenario: Project scope without project selection

- GIVEN project scope is enabled but requested names resolve only to bundled or user definitions
- WHEN `Task` executes
- THEN no project-agent confirmation is required

### Requirement: Isolated Tau child invocation

Each child SHALL be launched with argv and no shell in its effective cwd using Tau JSON print mode. It SHALL pass `--no-extensions`, `--no-approve`, `--cwd`, and an appended temporary agent/summary prompt. The task SHALL be positional prompt input. It SHALL set a recursion guard and SHALL clean temporary files.

The extension SHALL NOT pass unsupported Pi flags. Discovered child extensions and protected project resources SHALL be disabled. User-global skills may remain listed, so the appended prompt SHALL instruct the child not to invoke skills; this is a behavioral instruction, not a security guarantee.

#### Scenario: Default child arguments

- GIVEN no provider or model override
- WHEN invocation arguments are built
- THEN neither `--provider` nor `--model` is present
- AND Tau's configured defaults remain effective

#### Scenario: No recursive Task registration

- GIVEN the child recursion environment guard is present
- WHEN the Task extension is explicitly loaded in that child despite `--no-extensions`
- THEN setup does not register `Task`

#### Scenario: Working directory

- GIVEN an item-specific cwd
- WHEN its child starts
- THEN both the process cwd and Tau `--cwd` use that cwd
- AND otherwise both use the parent Task session cwd

### Requirement: Provider and model overrides

`provider` and `model` SHALL be independent opaque strings at call and agent-definition levels. A non-empty call value SHALL override the corresponding agent value. Effective values SHALL map directly to Tau's separate `--provider` and `--model` flags. Missing values SHALL omit their flags. Combined strings SHALL NOT be parsed.

#### Scenario: Independent call overrides

- GIVEN an agent provider and model and a call-level model only
- WHEN arguments are built
- THEN the agent provider is passed with `--provider`
- AND the call model is passed with `--model`

#### Scenario: Opaque model identifier

- GIVEN a model value containing `/`
- WHEN arguments are built
- THEN the complete value is passed to `--model`
- AND no provider is inferred from it

### Requirement: Child tool profiles

A `general-purpose` agent SHALL use Tau's normal built-in coding tools. A `read-only` agent SHALL append read-only instructions and explicitly load a temporary public-API policy extension that blocks every tool call except `read`.

The documentation SHALL state that this policy is not an OS sandbox and does not restrict model behavior, filesystem readability through allowed tools, credentials, network, providers, or vulnerabilities.

#### Scenario: Read-only write attempt

- GIVEN a read-only child requests `write`, `edit`, or `bash`
- WHEN the temporary policy extension receives the tool call
- THEN it blocks the call before the built-in tool executes

#### Scenario: Read-only file read

- GIVEN a read-only child requests `read`
- WHEN the policy extension receives the call
- THEN it permits the call

#### Scenario: General-purpose child

- GIVEN a general-purpose agent
- WHEN arguments are built
- THEN no read-only policy extension is loaded

### Requirement: Tau JSON collection

The runner SHALL decode stdout as UTF-8 JSON Lines, retain validated portable messages from `message_end` events in arrival order, capture stderr independently, count malformed JSON or invalid `message_end` lines, and ignore other valid lifecycle events. It SHALL derive the final output by concatenating all text blocks in the last assistant message. A clean process with no assistant message SHALL be a protocol failure.

#### Scenario: Multiple assistant text blocks

- GIVEN the final assistant message contains multiple text blocks
- WHEN final output is extracted
- THEN their text is concatenated in block order

#### Scenario: Tool and assistant messages

- GIVEN valid assistant and tool-result `message_end` events
- WHEN stdout is parsed
- THEN all validated messages are retained in details
- AND only the last assistant message determines final output and status

#### Scenario: Malformed JSON line

- GIVEN stdout contains malformed JSON or an invalid `message_end` among valid events
- WHEN parsing completes
- THEN valid messages remain available
- AND the malformed line count increases

#### Scenario: No assistant message

- GIVEN Tau exits zero without a valid assistant message
- WHEN the runner finalizes the child
- THEN the child is marked as a protocol failure with `BLOCKED` status

### Requirement: Summary extraction and status

The appended prompt SHALL preserve the agent body and instruct every child to end with a `## Summary` section and one supported status marker. Summary extraction SHALL use the last line exactly headed `## Summary`, allowing horizontal whitespace, and return that heading through end of output. Without it, the complete output SHALL be returned unchanged.

Status parsing SHALL use the last recognized case-insensitive bold or plain status marker in final assistant text. Clean output without a marker SHALL default to `DONE`; failed, cancelled, timed-out, or protocol-invalid output without a marker SHALL default to `BLOCKED`.

#### Scenario: Last summary wins

- GIVEN final output contains multiple exact `## Summary` heading lines
- WHEN summary content is extracted
- THEN content starts at the last heading and continues unchanged through output end

#### Scenario: Similar text is not a heading

- GIVEN output contains `## Summary details` or inline text containing `## Summary`
- WHEN extraction runs
- THEN no summary heading is recognized
- AND complete output is the fallback

#### Scenario: Missing or malformed status

- GIVEN a valid summary has no supported status marker
- WHEN extraction and status parsing run
- THEN summary extraction still succeeds
- AND status follows the clean/failure default

#### Scenario: Last status wins

- GIVEN final output contains more than one supported marker
- WHEN status is parsed
- THEN the final recognized marker determines status

### Requirement: Context-small content and complete details

Final tool content SHALL contain only summaries/fallbacks and concise orchestration text. Stable JSON details SHALL use `schemaVersion: 1` and include mode, scope, project directory, discovery diagnostics, and input-ordered child results. Each child result SHALL include identity/source, effective task and cwd, exit/process state, complete validated wire messages, stderr, usage, status, timeout/cancellation state, and malformed-line count.

#### Scenario: Single success

- GIVEN a successful child with a summary
- WHEN `Task` returns
- THEN content contains the summary rather than all prior output
- AND details contain every validated child message

#### Scenario: Empty successful output

- GIVEN a successful child has an empty final assistant text
- WHEN `Task` returns
- THEN content is `(no output)`
- AND the empty message remains represented in details

#### Scenario: Parallel mixed outcome

- GIVEN parallel children have successful and failed outcomes
- WHEN `Task` returns
- THEN content states the success count
- AND each input-ordered `[agent] (completed|failed)` section contains that child's summary or fallback
- AND details retain all partial and complete results

#### Scenario: Chain success

- GIVEN every chain step succeeds
- WHEN `Task` returns
- THEN content is the final step's summary or fallback
- AND details contain every step with one-based `step` values

#### Scenario: Portable failure representation

- GIVEN a child fails
- WHEN `Task` returns an `AgentToolResult`
- THEN concise content and details represent the failure
- AND the implementation does not rely on a nonexistent `AgentToolResult.isError` field

### Requirement: Progress, cancellation, timeout, and cleanup

The system SHALL emit partial `AgentToolResult` updates after accepted messages and child completion. Updates SHALL preserve accumulated chain results and deterministic parallel slots. Per-child timeout SHALL default to 3600 seconds and accept a positive call override no greater than 3600.

When cancellation or timeout occurs, the runner SHALL terminate the process, wait no more than five seconds, kill it if needed, retain partial output, and stop starting queued parallel work and later chain steps. It SHALL remove all temporary prompt/policy files on success and every failure path.

#### Scenario: Partial update

- GIVEN a child emits a valid assistant or tool-result message
- WHEN it is accepted
- THEN the callback receives current context text and schema-versioned partial details

#### Scenario: Cancellation before spawn

- GIVEN the cancellation token is already cancelled
- WHEN work is scheduled
- THEN no new child starts
- AND the result records cancellation

#### Scenario: Cancellation while running

- GIVEN one or more children are running
- WHEN cancellation is observed
- THEN each running process is terminated and eventually killed if necessary
- AND queued children do not start

#### Scenario: Timeout

- GIVEN a child exceeds its effective timeout
- WHEN the deadline expires
- THEN it is terminated
- AND its result records `timedOut: true`, a failure outcome, and `BLOCKED` default status

#### Scenario: Temporary cleanup

- GIVEN execution exits through success, spawn error, parse error, cancellation, or timeout
- WHEN finalization completes
- THEN no temporary prompt or policy file remains

### Requirement: Portable rendering

The tool MAY provide public `render_call` and `render_result` callbacks that return Rich-markup or plain strings. Rendering failure SHALL fall back to Tau's generic tool rendering. The implementation SHALL NOT import private Tau session or Textual APIs.

#### Scenario: Expanded result

- GIVEN complete details and an expanded frontend row
- WHEN the public result renderer runs
- THEN it may show complete child output from details without adding it to parent model context

#### Scenario: Renderer unavailable or fails

- GIVEN no custom renderer or a renderer failure
- WHEN Tau displays the call/result
- THEN generic portable content remains usable
