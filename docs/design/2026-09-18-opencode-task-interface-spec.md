# Spec: OpenCode-aligned task interface

## Domain: subagent-dispatch

### ADDED Requirements

#### Requirement: Task result envelope

For every result that starts a child, the model-facing content SHALL be one envelope of the form `<task id="<taskId>" state="completed|error">`. The envelope SHALL wrap one inner `task_result` or `task_error` tag. The `taskId` SHALL be the child's Tau session id. The envelope state SHALL be the process outcome only. `completed` SHALL mean that the child finished and delivered a final assistant message, whatever status marker that message carries inside its text. `error` SHALL mean that the child failed, was cancelled, timed out, or ended with no final assistant message. Child status markers (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`) SHALL stay inside the message text and SHALL NOT change the envelope state.

A successful child SHALL wrap its complete final assistant message in `task_result`. A final assistant message without text SHALL wrap the placeholder `(no output)`. A child in the `error` state SHALL wrap its final assistant message in `task_error`. When no final message exists, the `task_error` tag SHALL wrap the OpenCode failure form `Subagent failed (task_id: <id>): <error>`. In that form, `<id>` is the effective child session id, so it is the fresh id after a fallback.

A pre-session failure is a call that fails before Tau creates the child session. The causes are a process startup failure, a cancellation before startup, or an interactive project-approval denial. A pre-session failure SHALL carry state `error` with no `id` attribute, and its `task_error` tag SHALL wrap the startup, cancellation, or denial error text.

Repair notes SHALL appear as `Note:` lines before the envelope. The inner content SHALL be the child message verbatim with no escaping. The `id` and `state` attributes SHALL carry the semantics. The envelope tags SHALL be informational.

##### Scenario: Completed envelope
- GIVEN a fresh child finishes and delivers a final assistant message
- WHEN the result content is built
- THEN the content is one envelope with state `completed` and the envelope `id` equal to the child session id
- AND the `task_result` tag wraps the complete final assistant message

##### Scenario: Error envelope with a final message
- GIVEN a child times out after it emitted a final assistant message
- WHEN the result content is built
- THEN the envelope state is `error`
- AND the `task_error` tag wraps the complete final assistant message
- AND the envelope `id` is the child session id

##### Scenario: Error envelope without a final message
- GIVEN a child fails with no final assistant message
- WHEN the result content is built
- THEN the envelope state is `error`
- AND the `task_error` tag wraps `Subagent failed (task_id: <id>): <error>` with the child session id

##### Scenario: Status marker keeps the envelope state
- GIVEN a child exits cleanly and its final message ends with the `BLOCKED` marker
- WHEN the envelope is built
- THEN the envelope state is `completed`
- AND the marker stays inside the wrapped message text

##### Scenario: Final message without text
- GIVEN a successful child whose final assistant message has no text
- WHEN the envelope is built
- THEN the `task_result` tag wraps `(no output)`

##### Scenario: Error final message without text
- GIVEN a child in the error state whose final assistant message has no text
- WHEN the envelope is built
- THEN the `task_error` tag wraps `(no output)`

##### Scenario: Repair note placement
- GIVEN a child-starting result carries a repair note
- WHEN the content is built
- THEN the note appears as a `Note:` line before the envelope

##### Scenario: Verbatim inner content
- GIVEN a child final message contains characters that look like markup
- WHEN the envelope is built
- THEN the inner content is the message text verbatim with no escaping

##### Scenario: Pre-session failure envelope
- GIVEN a child process fails to start
- WHEN the result content is built
- THEN the envelope state is `error` with no `id` attribute
- AND the `task_error` tag wraps the startup error text

##### Scenario: Interactive denial envelope
- GIVEN a requested name resolves to a project definition
- AND the session runs interactively
- WHEN the operator denies the approval request
- THEN the call cancels before any child starts
- AND the envelope state is `error` with no `id` attribute
- AND the `task_error` tag wraps the denial error text
- AND the details entry carries no `taskId` and `planned` is 1

#### Requirement: task_id resume

A call with `task_id` SHALL resume that child session instead of creating one. A resume run SHALL launch a new child process against the existing session. The session SHALL retain its previous messages and tool outputs. The call's `prompt` SHALL be the new user turn. The result content SHALL relay the new final assistant message in an envelope whose `id` is the existing session's id.

`task_id` SHALL require `subagent_type` to name the agent whose prompt the resumed run uses. A call with `task_id` and no `subagent_type` SHALL fail closed with a teach-back that names both fields. The tool SHALL NOT record a per-session agent owner. A `task_id` resumed under a different `subagent_type` SHALL continue that session with the named agent's prompt and policies.

The runner SHALL regenerate the agent body prompt and the profile policy extensions for the resumed run. It SHALL apply the thinking policy, the overrides, and the recursion guard exactly as in a fresh run. The appended prompt SHALL use a resume variant of the isolation sentence. That variant states the session's own prior turns are the child's earlier work on this task. Effective provider, model, and reasoning effort SHALL resolve exactly as in a fresh call and SHALL apply to the resumed run. `timeoutSeconds` SHALL bound the resumed run. Usage in details SHALL cover the resumed run only. Only the new turn's events SHALL stream.

##### Scenario: Resume continues the child session
- GIVEN a prior child session with messages and tool outputs
- WHEN a call carries that `task_id`, a `subagent_type`, and a `prompt`
- THEN a new child process runs against the existing session
- AND the session keeps its earlier messages and tool outputs
- AND the content is the new final assistant message in a completed envelope with the same id

##### Scenario: Resume requires subagent_type
- GIVEN a call carries `task_id` and no `subagent_type`
- WHEN validation runs
- THEN no child starts
- AND the teach-back names `task_id` and `subagent_type`

##### Scenario: Resume under a different agent
- GIVEN a child session started with one agent
- WHEN a call resumes it with a different `subagent_type`
- THEN the resumed run uses the named agent's body prompt and policies

##### Scenario: Resume prompt uses the resume variant
- GIVEN a resumed run
- WHEN the appended prompt is built
- THEN the isolation sentence states the session's own prior turns are the child's earlier work on this task

##### Scenario: Resume overrides and timeout apply
- GIVEN a resume call carries `provider`, `model`, and `timeoutSeconds`
- WHEN the resumed child launches
- THEN the resolved provider and model apply to the resumed run exactly as in a fresh call
- AND `timeoutSeconds` bounds the resumed run

##### Scenario: Resume usage covers the resumed run
- GIVEN a resumed child completes
- WHEN its details usage is read
- THEN the usage covers the resumed run only

#### Requirement: Resume working directory

A resumed run SHALL use the session's recorded creation cwd as its working directory. The call's `cwd` SHALL NOT relocate a resumed run. A resume call that carries `cwd` SHALL get a repair note that states the resumed run uses the session's recorded cwd. The store record SHALL keep its creation cwd.

##### Scenario: Resume cwd is the recorded cwd
- GIVEN a child session created in one directory
- WHEN a resume call carries a different `cwd`
- THEN the resumed child runs in the session's recorded creation cwd
- AND the result carries the repair note about the recorded cwd

##### Scenario: Store record keeps creation cwd
- GIVEN a resumed run completed
- WHEN the session record is read
- THEN the recorded creation cwd is unchanged

#### Requirement: Resume authorization model

Resume authorization SHALL be possession-based. Possession of the `task_id` SHALL authorize the resume. The tool SHALL NOT add per-caller authorization and SHALL NOT add access auditing. A call from any parent session SHALL resume any child session named by its `task_id`, including a parent in a different project. The same-id lock SHALL coordinate task-tool calls only.

The accepted prevention for cross-account exposure is the single-user deployment. A direct resume of a child session by another process is not prevented by the same-id lock. The operator accepts both exposures.

##### Scenario: Cross-project resume proceeds
- GIVEN a child session created under one project
- WHEN a parent session in a different project resumes it with its `task_id`
- THEN the resume proceeds like any other resume

##### Scenario: Lock scope is task calls
- GIVEN a task call holds the same-id lock for a session
- WHEN another process resumes that session directly through Tau
- THEN the direct resume is not prevented by the task tool's lock

#### Requirement: Unknown task_id fallback

Before resuming, the tool SHALL verify through the Tau session store that the session exists and that its recorded role is the subagent role. A call whose `task_id` matches no session SHALL start a fresh child with a new session id. Its result SHALL carry a repair note that states the id matched no session. A `task_id` that matches a session whose recorded role is not the subagent role SHALL also start a fresh child with a new session id. Its repair note SHALL state that the session is not a task child. A fallback fresh child SHALL follow the fresh-run rules. A fallback child that fails with no final message SHALL produce the OpenCode failure form with the fresh session id.

##### Scenario: Unknown session falls back
- GIVEN a `task_id` that matches no session in the store
- WHEN the call runs
- THEN a fresh child starts with a new session id
- AND the result carries a `Note:` line that states the id matched no session
- AND the note appears before the envelope

##### Scenario: Non-subagent session falls back
- GIVEN a `task_id` that names a session whose recorded role is not the subagent role
- WHEN the call runs
- THEN a fresh child starts with a new session id
- AND the repair note states that the session is not a task child

##### Scenario: Fallback failure names the fresh id
- GIVEN a fallback fresh child fails with no final message
- WHEN the error envelope is built
- THEN the OpenCode failure form names the fresh session id

#### Requirement: Pinned child sessions

Every fresh run SHALL create a pinned child session. The tool SHALL generate a new session id for every fresh child. The tool SHALL record it as the child's `taskId` on the child result, in the details entry, and as the envelope `id`. The child session SHALL carry the subagent role, so it stays out of the default `tau sessions` listing and lists under `tau sessions --all`. The runner SHALL record the id for every fresh-child attempt, including an attempt that fails after startup. When tau never persisted the session record, a later resume with that id SHALL fall back per the Unknown task_id fallback requirement.

Child sessions accumulate in the Tau session store with no retention. The accepted recovery for unwanted child sessions is manual store maintenance while no tau process uses the store. The store root is `~/.tau/sessions/`, with one directory per parent project, one `index.jsonl` per project directory, and one transcript file per session. The maintenance steps:

1. Find the child's line by `id` in the project `index.jsonl` files under the store root.
2. Stop the tau processes that use the store.
3. Delete the transcript file that the line's `path` names.
4. Delete the child's line from that `index.jsonl`.
5. Verify with `tau sessions --all` that the child no longer lists.

The store manager guards index updates with a process lock and atomic replacement, so editing a quiescent store avoids the race.

##### Scenario: Fresh child session id
- GIVEN a fresh call
- WHEN the child starts
- THEN the child runs in a new pinned session
- AND the child result, the details entry, and the envelope `id` carry that session id as `taskId`

##### Scenario: Child session listing
- GIVEN a completed child session
- WHEN the session listings run
- THEN `tau sessions --all` lists the session
- AND the default `tau sessions` listing omits it

##### Scenario: Failed attempt still records the id
- GIVEN a fresh child that fails after startup
- WHEN the result is built
- THEN the result records the generated session id

##### Scenario: Recovery removes the session
- GIVEN the operator deletes a child's transcript file and its `index.jsonl` line while no tau process uses the store
- WHEN a later call resumes that id
- THEN the id matches no session
- AND the call starts a fresh child with the repair note that the id matched no session

#### Requirement: Concurrent task calls

Several `task` calls in one assistant message SHALL run concurrently. Each call SHALL be validated, approved, and dispatched independently. The tool SHALL set no cap on the number of `task` calls in one message. Each result SHALL carry its own envelope. One call's failure SHALL NOT stop the others.

##### Scenario: Parallel dispatch
- GIVEN two `task` calls in one assistant message
- WHEN both run
- THEN both children are active in parallel
- AND each result carries its own envelope

##### Scenario: Independent failure
- GIVEN two `task` calls in one message and one child fails
- WHEN both finish
- THEN the failed call carries its error envelope
- AND the other result is intact

##### Scenario: No call cap
- GIVEN an assistant message with three `task` calls
- WHEN dispatch runs
- THEN all three calls dispatch their children

#### Requirement: Same-task_id exclusion

Two concurrent calls that carry the same `task_id` SHALL NOT both run. Exactly one SHALL start its child. The other SHALL fail closed with a teach-back that names the same-id conflict. The losing call's result SHALL carry the fail-closed result contract of the Content envelope and complete details requirement. The exclusion SHALL be process-safe: a lock keyed by `task_id` SHALL coordinate parent processes on the machine that hosts the session store.

##### Scenario: Same-id pair in one message
- GIVEN two `task` calls in one message carry the same `task_id`
- WHEN both run
- THEN one result carries the child envelope
- AND the other result is a fail-closed teach-back that names the same-id conflict
- AND the losing result carries no envelope, an empty `results` array, and no `planned` field

##### Scenario: Cross-process same-id exclusion
- GIVEN two parent processes on the machine that hosts the session store
- WHEN both dispatch a call with the same `task_id`
- THEN exactly one child starts
- AND the other call fails closed

#### Requirement: Tool description roster

The tool description SHALL carry a one-liner, the agent roster with tool-policy annotations, the default selection rule, a when-not-to-use section, and usage notes. The `subagent_type` parameter description SHALL keep the roster. Each roster line SHALL render in the form `- <name>: <description> (Tools: <policy>)`.

The annotation SHALL render from the resolved definition's effective profile. The `general-purpose` profile SHALL render `Tools: all`. The `read-only` profile SHALL render `Tools: read`. The `review` profile SHALL render `Tools: read, bash`, where the review instructions govern `bash` use. For the unshadowed bundled definitions, `general-purpose` and `implementation` SHALL render `Tools: all`. `read-only` SHALL render `Tools: read`. `code-review` and `document-review` SHALL render `Tools: read, bash`.

The description SHALL state that omitting `subagent_type` selects `general-purpose`. The usage notes SHALL state these rules:

- Several tasks are several `task` calls in one message.
- Delegated work is not duplicated.
- The prompt must be self-contained.
- The result names the `task_id` that a later call can reuse to continue the same subagent session.
- The caller states whether the child writes code or does research and how to verify the result.

The description SHALL keep the dispatch-threshold rule. The rule is: delegate only substantive multi-step work that benefits from an isolated context window, or long-running work that must not block this session. It SHALL keep the prohibitions: never delegate simple reads, searches, commands, or small edits, and never dispatch a task and then do the same work. It SHALL keep the prompt-guideline sentences, including the self-contained prompt requirement.

The description roster and the `subagent_type` description roster SHALL be static per session. They SHALL list the agents discovered at session start from the bundled and user layers only. Discovery is anchored at the session cwd. Name resolution SHALL follow the collision precedence of the task interface and validation requirement. The roster SHALL fall back to the bundled agents when discovery fails at session start. Teach-back rosters SHALL list the same bundled and user agents. Project agents SHALL stay out of every roster and every teach-back, including by name.

##### Scenario: Roster line format
- GIVEN the bundled definitions
- WHEN the roster renders
- THEN the `general-purpose` line reads `- general-purpose: <description> (Tools: all)`
- AND the `read-only` line renders `Tools: read`
- AND the `code-review` line renders `Tools: read, bash`

##### Scenario: Annotation follows the resolved definition
- GIVEN a user definition shadows a bundled name and carries the `review` profile
- WHEN the roster renders
- THEN that line renders `Tools: read, bash`

##### Scenario: Default rule and when-not-to-use
- GIVEN the tool description
- WHEN a reader reads it
- THEN it contains the sentence that omitting `subagent_type` selects `general-purpose`
- AND it contains a when-not-to-use section

##### Scenario: Usage notes present
- GIVEN the tool description
- WHEN a reader reads the usage notes
- THEN the notes state the multi-call parallelism rule
- AND the notes state the `task_id` reuse rule
- AND the notes state the verification-statement rule

##### Scenario: Roster scope at session start
- GIVEN project agents exist and a session starts
- WHEN the roster is built
- THEN the roster lists the bundled and user agents discovered at session start
- AND the roster names no project agent

##### Scenario: Discovery failure falls back to bundled
- GIVEN user-layer discovery fails at session start
- WHEN the roster is built
- THEN the roster lists the bundled agents

##### Scenario: Teach-back roster excludes project agents
- GIVEN a teach-back that lists agents
- WHEN it renders
- THEN it lists the same bundled and user agents as the description roster
- AND it names no project agent

### MODIFIED Requirements

#### Requirement: task interface and validation
<!-- Only the changed parts. The sync preserves existing content not mentioned. This replaces the `tasks`-array surface: the array, the 1-8 item rule, the `{agent, task, cwd?}` item shape, the four-children concurrency cap, and the input-order rule are superseded by the flat single-object surface below. The living spec's Purpose paragraph and the Intentional Port Differences table also describe the `tasks`-array surface; the finishing-stage sync rewrites both to the flat single-object surface. The finishing-stage sync also rewrites the living spec's Headless fail closed scenario content description (under Explicit project-agent approval) to the teach-back rule below. The removed-fields sentence ("The removed top-level `agent`, `task`, `cwd`, and `chain` fields...") is superseded by the uniform unknown-field rule, because `cwd` is now a valid field. The invalid-request paragraph is replaced by the fail-closed behaviors below. -->

A `task` call SHALL carry exactly one task as one flat object. The fields SHALL be exactly `prompt`, `subagent_type`, `description`, `task_id`, `cwd`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, and `timeoutSeconds`. The tool SHALL run exactly one child per call.

- `prompt` SHALL be a required non-empty string. It is the child's task. The tool SHALL preserve it verbatim.
- `subagent_type` SHALL be optional. When present, it SHALL be a string whose trimmed value is non-empty and names an eligible agent. Validation SHALL trim surrounding whitespace, and the trimmed value SHALL be the effective name. Omission SHALL select `general-purpose`. A name that no eligible agent provides SHALL fail closed with a teach-back that lists the roster. A value that is empty after trimming SHALL fail closed with a teach-back that states `subagent_type` requires a non-empty string when present.
- `description` SHALL be an optional string. It is a display label with no behavioral effect.
- `task_id` SHALL be optional. A present value SHALL be a string that is non-empty after trimming, or the call SHALL fail closed with a teach-back. No format check SHALL exist beyond that. The trimmed value SHALL be the effective `task_id` for session lookup, for the same-id lock, and for repair notes. A well-formed value that matches no session SHALL fall back per the Unknown task_id fallback requirement.
- `cwd` SHALL be an optional string directory path. Omission SHALL resolve to the parent session cwd. A relative path SHALL resolve against the parent session cwd. Any path, absolute or relative, SHALL expand `~` and SHALL then resolve canonically to an absolute path. On a resumed run, the Resume working directory requirement SHALL govern instead.
- `agentScope` SHALL be one of `user`, `project`, `both`. It selects the agent layers. The bundled layer always applies. `user` adds the user agents directory `~/.tau/agents`. `project` adds the nearest ancestor directory `.tau/agents` found by walking up from the parent session cwd. `both` adds both. On a name collision, a later layer replaces an earlier one: project replaces user, and user replaces bundled. Omission SHALL select `user`. Another value SHALL fail closed.
- `confirmProjectAgents` SHALL be a boolean. Omission SHALL select `true`.
- `provider` and `model` SHALL be optional literal string overrides. They SHALL use the trimming, placeholder coercion, and resolution chain of the Provider, model, and reasoning-effort overrides requirement.
- `reasoningEffort` SHALL be one of `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, with the same trimming, placeholder coercion, and resolution chain. The chain ends at the parent session's thinking level.
- `timeoutSeconds` SHALL be a number greater than 0 and at most 10800. Omission SHALL select 3600.

An unknown field SHALL fail closed. The teach-back SHALL name the unknown fields, the roster, and one valid flat example. A call that carries `background` SHALL fail closed with the dedicated background teach-back, because background dispatch is not supported in this harness. A value that violates a field's type or range rule SHALL fail closed. The result of a `task` call SHALL arrive when the child finishes. A fail-closed result SHALL carry the fail-closed result contract of the Content envelope and complete details requirement. A headless project-approval failure SHALL fail closed, and its result SHALL carry that contract with the teach-back that names the project agents directory as its content. An interactive project-approval denial SHALL cancel the call before any child starts and SHALL carry the pre-session failure contract of the Task result envelope requirement.

##### Scenario: Single-task dispatch
- GIVEN one valid flat call with `prompt` and `subagent_type`
- WHEN `task` executes
- THEN exactly one child runs with the effective agent and the prompt preserved verbatim

##### Scenario: Omitted subagent_type selects the default
- GIVEN a valid call with only `prompt`
- WHEN `task` executes
- THEN one `general-purpose` child runs

##### Scenario: Unknown-field teach-back
- GIVEN a call carries a field outside the allowed field list
- WHEN validation runs
- THEN no child starts
- AND the teach-back names the unknown fields
- AND the teach-back lists the roster
- AND the teach-back shows one valid flat example

##### Scenario: Background teach-back
- GIVEN a call carries `background`
- WHEN validation runs
- THEN no child starts
- AND the dedicated background teach-back states that background dispatch is not supported

##### Scenario: Whitespace subagent_type teach-back
- GIVEN a call passes `" "` as `subagent_type`
- WHEN validation runs
- THEN no child starts
- AND the teach-back states that `subagent_type` requires a non-empty string when present

##### Scenario: Whitespace task_id fails closed
- GIVEN a call passes `" "` as `task_id`
- WHEN validation runs
- THEN no child starts
- AND the teach-back states that `task_id` requires a non-empty string when present

##### Scenario: Missing prompt fails closed
- GIVEN a call omits `prompt` or passes an empty string
- WHEN validation runs
- THEN no child starts
- AND the teach-back states that `prompt` requires a non-empty string

##### Scenario: Non-positive timeout fails closed
- GIVEN a call passes `timeoutSeconds` with the value 0 or a negative number
- WHEN validation runs
- THEN no child starts

##### Scenario: Type-violating common option fails closed
- GIVEN a call passes a non-boolean value as `confirmProjectAgents`
- WHEN validation runs
- THEN no child starts

##### Scenario: Invalid agentScope fails closed
- GIVEN a call passes a value outside `user`, `project`, and `both` as `agentScope`
- WHEN validation runs
- THEN no child starts
- AND the teach-back names the valid `agentScope` values

##### Scenario: Headless project-approval teach-back
- GIVEN a requested name resolves to a project definition
- AND the session runs headless with no explicit `confirmProjectAgents: false`
- WHEN `task` executes
- THEN no child starts
- AND the teach-back names the project agents directory
- AND the result carries no envelope, an empty `results` array, and no `planned` field

##### Scenario: Fresh cwd resolution
- GIVEN a fresh call carries a relative `cwd`
- WHEN the child starts
- THEN the effective directory is the canonically resolved absolute path from the parent session cwd

##### Scenario: Tilde cwd expands
- GIVEN a fresh call carries a `cwd` that starts with `~`
- WHEN the child starts
- THEN the effective directory is the absolute path after `~` expansion and canonical resolution

#### Requirement: Agent definition discovery
<!-- Only the changed parts. The sync preserves existing content not mentioned. Only the unknown-requested-agent result content changed: the failed result lists the roster (bundled and user agents) instead of the eligible names and sources, and it names no project agent. The discovery layers, the `agentScope` semantics, the collision precedence, the metadata rules, and the bundled definitions stay unchanged. -->

A requested name that no eligible agent provides SHALL fail closed with a teach-back that lists the roster. The teach-back SHALL NOT name project agents, and no child SHALL start.

##### Scenario: Unknown requested agent teach-back
- GIVEN a requested name is not eligible in the selected scope
- WHEN validation runs
- THEN no child starts
- AND the teach-back lists the roster
- AND the teach-back names no project agent

#### Requirement: Isolated Tau child invocation
<!-- Only the changed parts. The sync preserves existing content not mentioned. Only the argv sentence changed: `--cwd` applies to a fresh child, and a resumed child omits it and otherwise reuses the fresh-run argv and prompt construction. The recursion guard, the profile policy extensions, the thinking extension, and the fresh-run appended-prompt rules stay unchanged. -->

Each child SHALL run as a separate Tau JSON-mode process with safe argv and no shell. A fresh child SHALL receive `--no-extensions`, `--no-approve`, `--cwd`, and a temporary `--append-system-prompt` file before the positional delegated task. A resumed child SHALL omit `--cwd` and SHALL otherwise use the fresh-run argv and prompt construction, because the resumed run uses the session's recorded cwd.

##### Scenario: Resumed child argv omits the cwd flag
- GIVEN a call with `task_id` that passes session verification
- WHEN child argv is built
- THEN the argv carries no `--cwd` flag
- AND the argv keeps the fresh-run flags and extensions

#### Requirement: Provider, model, and reasoning-effort overrides
<!-- Only the changed parts. The sync preserves existing content not mentioned. The placeholder rule changes: `default`, `inherit`, and `auto` coerce to omitted with a repair note instead of being rejected. `reasoningEffort` gains the same trimming and placeholder coercion. The guidance states the coercion instead of "placeholders do not select defaults". The resolution chain, the exact-literal rule, the opaque-value rule, and the lower-layer rules stay unchanged. -->

Call-level `provider`, `model`, and `reasoningEffort` fields SHALL be optional literal overrides. Callers SHALL omit them for normal dispatch and inheritance. Validation SHALL trim surrounding whitespace and SHALL reject a value that is empty after trimming. A case-insensitive `default`, `inherit`, or `auto` placeholder SHALL coerce to omitted with a repair note, and resolution SHALL continue at the next lower layer. A rejected value SHALL fail the call closed and explain that omitting the field selects inherited configuration. `reasoningEffort` SHALL use the same trimming and placeholder coercion as `provider` and `model`.

The task schema, always-visible prompt guidance, and README SHALL identify all three fields as optional literal overrides. They SHALL tell callers to omit the fields during normal calls and for inheritance. They SHALL state that a `default`, `inherit`, or `auto` placeholder is coerced to omitted with a repair note.

##### Scenario: Placeholder coerces to omitted
- GIVEN a call passes `Default` with surrounding whitespace as `provider`
- WHEN validation runs
- THEN the value is treated as omitted
- AND a repair note states the coercion
- AND resolution continues at the next lower layer

##### Scenario: Reasoning-effort placeholder coerces
- GIVEN a call passes `AUTO` as `reasoningEffort`
- WHEN validation runs
- THEN the value is treated as omitted with a repair note
- AND the effective level resolves down to the parent session's thinking level

##### Scenario: Whitespace-only override fails closed
- GIVEN a call passes only whitespace as `provider` or `model`
- WHEN validation runs
- THEN no child starts
- AND content explains that omitting the field selects inherited configuration

##### Scenario: Override guidance states coercion
- GIVEN a caller reads the task schema, the always-visible prompt guidance, and the README override documentation
- WHEN the caller selects an override
- THEN each source identifies the three fields as optional literal overrides
- AND each source tells the caller to omit the fields during normal calls and for inheritance
- AND each source states that a `default`, `inherit`, or `auto` placeholder is coerced to omitted with a repair note

#### Requirement: Content envelope and complete details
<!-- Only the changed parts. The sync preserves existing content not mentioned. The content construction changes: every child-starting result carries the task result envelope, and the previous single-child message form and multi-child section form are superseded. The fail-closed result contract is new. Details keep `schemaVersion: 2` and the one-element `results` array, `planned` is fixed at 1, and each result gains the additive `taskId` field. The details field list, the `configPaths` and `configDiagnostics` rule, and the stderr-retention rules stay unchanged. -->

For every result that starts a child, final `content` SHALL be the task result envelope of the Task result envelope requirement. The tool SHALL NOT produce the previous single-child message form or the multi-child section form.

A fail-closed result SHALL carry the teach-back as its content, no envelope, an empty `results` array, and no `planned` field, because no child starts.

Details SHALL keep `schemaVersion: 2` and the one-element `results` array. A result that starts or attempts a child SHALL carry `planned` with the value 1. Each child result SHALL carry the additive `taskId` field. A pre-session failure SHALL carry a details entry with no `taskId`, and `planned` SHALL keep the value 1.

##### Scenario: Envelope replaces the prior content forms
- GIVEN a successful fresh child with a final assistant message
- WHEN `task` returns
- THEN content is the envelope with the child session id and state `completed`
- AND no counts line or per-child section appears

##### Scenario: Fail-closed result shape
- GIVEN a call fails validation
- WHEN the result is built
- THEN content is the teach-back
- AND content carries no envelope
- AND `results` is empty
- AND `planned` is absent

##### Scenario: Details carry planned and taskId
- GIVEN a completed fresh child
- WHEN the details are inspected
- THEN `schemaVersion` is 2
- AND `results` holds one entry whose `taskId` equals the envelope `id`
- AND `planned` is 1

##### Scenario: Pre-session failure details
- GIVEN a child fails before Tau creates its session
- WHEN the details are inspected
- THEN the entry carries no `taskId`
- AND `planned` is 1

#### Requirement: Progress, cancellation, timeout, and cleanup
<!-- Only the changed parts. The sync preserves existing content not mentioned. The timeout cap changes from 3600 to 10800. The partial-update sentence is restated for the single child, so the item-count and input-order-slot language is superseded. The cancellation, hard-cancellation, and temporary-file cleanup rules stay unchanged. -->

Each child SHALL default to a 3600-second timeout. A call override SHALL be a number greater than 0 and at most 10800. The extension SHALL emit portable partial results after each accepted assistant or tool-result message of the child and after child completion. A partial result SHALL carry `planned` with the value 1.

##### Scenario: Timeout override at the cap
- GIVEN a call passes `timeoutSeconds: 10800`
- WHEN the child runs
- THEN the override is accepted and bounds the child

##### Scenario: Timeout override above the cap
- GIVEN a call passes `timeoutSeconds: 10801`
- WHEN validation runs
- THEN no child starts

##### Scenario: Partial updates for one child
- GIVEN a child emits accepted assistant and tool-result messages
- WHEN the updates run
- THEN partial results stream from that child
- AND each partial result carries `planned` with the value 1

#### Requirement: Portable rendering
<!-- Only the changed parts. The sync preserves existing content not mentioned. The call label changes from the task-count form to the description-else-subagent_type form. The single-frame layout, the headline, the icons, the usage lines, and the live-update rules stay unchanged. -->

The call label SHALL be the `description` value when it is non-empty after trimming, and the effective `subagent_type` otherwise. The call label SHALL NOT derive from the task count.

##### Scenario: Call label from the description
- GIVEN a call with `description: "Review auth"` and effective `subagent_type` `code-review`
- WHEN the result renders
- THEN the call label is `Review auth`

##### Scenario: Call label falls back to the agent name
- GIVEN a call whose `description` is only whitespace
- WHEN the result renders
- THEN the call label is the effective `subagent_type`
