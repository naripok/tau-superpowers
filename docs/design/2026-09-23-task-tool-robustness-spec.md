# Spec: Two-tool task dispatch with fail-closed validation

## Domain: subagent-dispatch

<!-- Living-spec sync notes (finishing stage): besides the requirement blocks
below, the sync rewrites the living spec's Purpose paragraph to the two-tool
snake_case surface, the four-layer pin resolution chain, and fail-closed
validation and resume. It rewrites the Intentional Port Differences row
"Project-agent prompt in headless use" to: project-layer definitions dispatch
without per-call approval; the roster names them. It deletes the Security
Boundaries line "Project-agent approval protects against silently consuming
repository-controlled prompt files" and states instead that the operator runs
the tools inside a secure sandbox and accepts repository-controlled agent
prompts as dispatch input. It adjusts the "Resume authorization model"
requirement: possession-based authorization and the same-id lock stay, and a
resume whose mapped agent is not discoverable from the parent session cwd
fails closed. It rewrites the maintenance steps in Pinned child
sessions to include the session-agent mapping entry deletion. -->

Terms used throughout this spec:

- **Fail closed** means the tool rejects the call, starts no child, and returns a teach-back as the result content.
- A **teach-back** is a rejection result whose content names the valid values and the exact next call.
- A **child** is one isolated Tau subagent process. A **child session** is the Tau session that persists one subagent's messages and tool outputs. One fresh run creates one child session. A resume run launches a new child process against an existing child session. A **subagent** is the logical agent across one or more child runs.
- **`task`** is the tool that dispatches a new child. **`task_resume`** is the tool that continues an existing child session.
- A **pin** is a provider, model, or reasoning-effort value set in the subagent config file or in an agent-definition frontmatter.
- The **roster** is the model-visible agent list discovered at session start from the parent session cwd.
- The **envelope** is the model-facing `<task ...>` result wrapper.
- The **background teach-back** is the dedicated rejection stating that background dispatch is not supported in this harness and that several calls of the same tool in one message run children in parallel.
- The **same-id lock** is the process-safe lock keyed by the requested `task_id` that lets exactly one same-id call run and fails the others closed.
- A **repair note** is a removed `Note:` line that the previous surface printed before an envelope to report a tolerated caller mistake. This change removes the mechanism.
- The **session-agent mapping** is the extension-owned durable file that records the agent name for every child session a fresh `task` call starts, so a later `task_resume` call can recover the agent without repeating it as a call argument.
- **All-layer discovery** means discovery of bundled agent definitions, user agent definitions, and the nearest ancestor project agent definitions, with the collision precedence: project replaces user, and user replaces bundled.

### ADDED Requirements

#### Requirement: Two-tool task surface

The extension SHALL register exactly two task tools, named `task` and `task_resume`. `task` SHALL dispatch a new child. `task_resume` SHALL continue an existing child session. Both tools SHALL execute through one shared validation, dispatch, same-id-locking, envelope-rendering, and child-execution path. Each call of either tool SHALL carry exactly one task, and each tool SHALL run exactly one child per call. The result of each call SHALL arrive when the child finishes; neither tool SHALL offer a way to return a result later.

The parameter surface SHALL be exactly:

- `task`: `prompt` (required), `subagent_type`, `description`, `timeout_seconds`.
- `task_resume`: `prompt` (required), `task_id` (required), `timeout_seconds`.

No other parameter SHALL exist on either tool, and every parameter name SHALL be snake_case.

`prompt` SHALL be a required non-empty string on both tools. It is the child's task, and the tool SHALL preserve it verbatim.

`subagent_type` exists on `task` only and SHALL be optional. When present, it SHALL be a non-empty string that names an agent which call-time all-layer discovery can resolve. Validation SHALL trim surrounding whitespace, and the trimmed value SHALL be the effective name. Omission SHALL select `general-purpose`. A name that call-time all-layer discovery cannot resolve SHALL fail closed with the roster teach-back. A value that is empty after trimming SHALL fail closed with a teach-back that states `subagent_type` requires a non-empty string when present.

`description` exists on `task` only and SHALL be an optional string. It is a display label with no behavioral effect.

`timeout_seconds` exists on both tools and SHALL be a number greater than 0 and at most 10800. Omission SHALL select 3600.

`task_id` exists on `task_resume` only and SHALL be required. It SHALL be a non-empty string naming a child session id from an earlier task result, with no format check beyond non-empty after trimming. Validation SHALL trim surrounding whitespace, and the trimmed value SHALL be the effective `task_id` for session lookup and for the same-id lock. A value that is empty after trimming SHALL fail closed.

##### Scenario: Two-tool registration
- GIVEN the extension loads in a session
- WHEN the tool surface is read
- THEN exactly two task tools are registered, named `task` and `task_resume`
- AND each tool carries its own parameter schema and description

##### Scenario: Single-task dispatch
- GIVEN one valid `task` call with `prompt` and `subagent_type`
- WHEN `task` executes
- THEN exactly one child runs with the effective agent and the prompt preserved verbatim

##### Scenario: Omitted subagent_type selects the default
- GIVEN a valid `task` call with only `prompt`
- WHEN `task` executes
- THEN one `general-purpose` child runs

##### Scenario: task_resume requires task_id
- GIVEN a `task_resume` call with only `prompt`
- WHEN validation runs
- THEN no child starts
- AND the teach-back states that `task_id` is required

##### Scenario: Whitespace subagent_type teach-back
- GIVEN a `task` call passes `" "` as `subagent_type`
- WHEN validation runs
- THEN no child starts
- AND the teach-back states that `subagent_type` requires a non-empty string when present

##### Scenario: Whitespace task_id fails closed
- GIVEN a `task_resume` call passes `" "` as `task_id`
- WHEN validation runs
- THEN no child starts
- AND the teach-back states that `task_id` requires a non-empty string

##### Scenario: Missing prompt fails closed
- GIVEN a call on either tool omits `prompt` or passes an empty string
- WHEN validation runs
- THEN no child starts
- AND the teach-back states that `prompt` requires a non-empty string

##### Scenario: Out-of-range timeout fails closed
- GIVEN a call on either tool passes `timeout_seconds` with the value 0, a negative number, or a number greater than 10800
- WHEN validation runs
- THEN no child starts

##### Scenario: Unknown agent name fails closed with the roster
- GIVEN a `task` call whose `subagent_type` names an agent that call-time all-layer discovery cannot resolve
- WHEN validation runs
- THEN no child starts
- AND the roster teach-back lists the bundled, user, and project agents of the session start

#### Requirement: Cross-tool field rejection

Each tool SHALL reject the other tool's fields and every removed field. A `task` call that carries `task_id` SHALL fail closed with a teach-back that names `task_resume` as the tool that continues a child session. A `task_resume` call that carries `subagent_type`, `description`, or `cwd` SHALL fail closed as an unknown field. The background check SHALL precede the `task_id` check, so a call that carries both `background` and `task_id` SHALL get the background teach-back. On `task`, the `task_id` rejection SHALL precede the other argument validation.

##### Scenario: task rejects task_id
- GIVEN a `task` call carries a `task_id`
- WHEN validation runs
- THEN no child starts
- AND the teach-back names `task_resume` as the resume tool

##### Scenario: task_resume rejects subagent_type
- GIVEN a `task_resume` call carries `subagent_type`
- WHEN validation runs
- THEN no child starts
- AND the teach-back names `subagent_type` as an unknown field

##### Scenario: task_resume rejects description and cwd
- GIVEN a `task_resume` call carries `description` or `cwd`
- WHEN validation runs
- THEN no child starts
- AND the teach-back names the field as an unknown field

##### Scenario: Background check precedes the task_id check
- GIVEN a `task` call carries both `background` and `task_id`
- WHEN validation runs
- THEN no child starts
- AND the teach-back is the dedicated background teach-back

#### Requirement: Fail-closed validation

Both tools SHALL fail closed on every invalid argument: unknown fields, wrong types, empty required values, and out-of-range timeouts, where a call carrying `background`, a removed field, or a `task_id` on `task` takes its dedicated teach-back below instead of the generic unknown-field teach-back. No value SHALL be coerced, silently dropped, or reinterpreted. A fail-closed result SHALL carry the teach-back as its content, no envelope, an empty `results` array, and no `planned` field.

A call that carries `background` SHALL fail closed with the dedicated background teach-back on both tools. The background teach-back SHALL state that background dispatch is not supported in this harness and that several calls of the same tool in one message run children in parallel.

An unknown-field teach-back on `task` SHALL name the unknown fields, the all-layer roster, and one valid `task` example. An unknown-field teach-back on `task_resume` SHALL name the unknown fields, its three fields (`prompt`, `task_id`, `timeout_seconds`), and the session-agent mapping, and SHALL list no agents.

A removed override field (`provider`, `model`, or `reasoningEffort`) SHALL get the unknown-field teach-back with wording that names the removal of the call-level override and directs the caller to the config-file or agent-definition pins. A removed environment or approval field (`cwd`, `agentScope`, or `confirmProjectAgents`) SHALL get the unknown-field teach-back with wording that names the removal of the call-level capability and states the fixed behavior: a fresh child spawns in the parent session's working directory, and discovery covers all layers. The camelCase `timeoutSeconds` SHALL get the unknown-field teach-back that shows `timeout_seconds`.

The repair-note mechanism SHALL be removed entirely: no result of either tool SHALL carry a `Note:` line.

##### Scenario: Unknown-field teach-back on task
- GIVEN a `task` call carries a field outside its parameter list
- WHEN validation runs
- THEN no child starts
- AND the teach-back names the unknown fields
- AND the teach-back lists the all-layer roster
- AND the teach-back shows one valid `task` example

##### Scenario: Unknown-field teach-back on task_resume
- GIVEN a `task_resume` call carries a field outside its parameter list
- WHEN validation runs
- THEN no child starts
- AND the teach-back names the unknown field
- AND the teach-back names `prompt`, `task_id`, and `timeout_seconds`
- AND the teach-back names the session-agent mapping
- AND the teach-back lists no agents

##### Scenario: Background teach-back on both tools
- GIVEN a call carries `background` on either tool
- WHEN validation runs
- THEN no child starts
- AND the dedicated background teach-back states that background dispatch is not supported in this harness
- AND it states that several calls of the same tool in one message run children in parallel

##### Scenario: Removed override field names the pins
- GIVEN a call on either tool carries `reasoningEffort`
- WHEN validation runs
- THEN no child starts
- AND the teach-back names `reasoningEffort` as an unknown field whose call-level capability was removed
- AND the teach-back directs the caller to the config-file or agent-definition pins

##### Scenario: Removed environment field states the fixed behavior
- GIVEN a `task` call carries `cwd`
- WHEN validation runs
- THEN no child starts
- AND the teach-back names `cwd` as an unknown field
- AND the teach-back states that a fresh child spawns in this session's working directory

##### Scenario: Removed scope field names the removal
- GIVEN a `task` call carries `agentScope`
- WHEN validation runs
- THEN no child starts
- AND the teach-back names `agentScope` as an unknown field whose call-level capability was removed
- AND the teach-back states that discovery covers all layers

##### Scenario: camelCase timeout names the snake_case field
- GIVEN a `task` call passes `timeoutSeconds` with the value 60
- WHEN validation runs
- THEN no child starts
- AND the teach-back names `timeoutSeconds` as an unknown field and shows `timeout_seconds`

##### Scenario: Wrong type fails closed
- GIVEN a call passes a non-string value as `subagent_type` on `task` or as `task_id` on `task_resume`
- WHEN validation runs
- THEN no child starts
- AND the result carries the fail-closed contract

##### Scenario: No repair notes anywhere
- GIVEN any result of either tool, successful or failed
- WHEN its content is read
- THEN no `Note:` line appears

#### Requirement: Session-agent mapping

The extension SHALL own a durable session-agent mapping that records, for every child session a fresh `task` dispatch starts, the child session id and its agent name. The mapping SHALL live at `~/.tau/superpowers-subagent-sessions.json`, a sibling of the `superpowers-subagent.toml` config file.

Every fresh dispatch SHALL write the mapping entry before the child process spawns. A failed or impossible write SHALL fail the dispatch closed with the standard fail-closed contract, so no child ever starts without a mapping entry.

Mapping writes SHALL serialize through a dedicated process-safe mapping lock held across each read-modify-write cycle, so concurrent fresh dispatches cannot lose an entry. The lock SHALL use the same file-lock mechanism as the same-id lock. Each write SHALL land through atomic write-and-rename, so a concurrent reader SHALL see the file whole. A write that cannot read the file because it is unreadable or corrupted SHALL rebuild it from an empty map plus the new entry. The same-id lock SHALL NOT coordinate mapping writes: it keys resumed ids, and resume runs never write the mapping.

A `task_resume` call SHALL read the mapping first and then check the session record, in that order. It SHALL look up the mapped agent name, re-discover that agent's definition by name through all-layer discovery anchored at the parent session's working directory, and regenerate the resume-variant prompt. A missing mapping entry, a corrupted mapping read treated as a missing entry, a missing session record, a non-subagent role, or a mapped name that no discoverable agent provides SHALL each fail closed. An entry whose session never started is stale and harmless: the session-record check fails closed before any child starts.

The mapping SHALL be append-only across normal operation. The documented store-maintenance cleanup of the Pinned child sessions requirement SHALL delete a removed child's mapping entry beside the transcript and index line.

##### Scenario: Entry written before spawn
- GIVEN a fresh `task` dispatch
- WHEN the child process spawns
- THEN the session-agent mapping contains an entry that maps the child's session id to the dispatched agent's name

##### Scenario: Failed write fails the dispatch closed
- GIVEN the mapping write fails or is impossible
- WHEN the fresh dispatch runs
- THEN no child starts
- AND the result carries the teach-back as its content, no envelope, an empty `results` array, and no `planned` field

##### Scenario: Concurrent fresh dispatches keep both entries
- GIVEN two fresh `task` dispatches run concurrently
- WHEN both write the mapping
- THEN both entries exist in the mapping

##### Scenario: Corrupted file rebuilds on write
- GIVEN the mapping file is unreadable or corrupted
- WHEN a fresh dispatch writes its entry
- THEN the mapping is rebuilt from an empty map plus the new entry
- AND the child starts

##### Scenario: Mapping lookup precedes the session-record check
- GIVEN a `task_resume` call
- WHEN resume verification runs
- THEN the mapping lookup runs before the session-record check

##### Scenario: Missing entry fails closed
- GIVEN a `task_resume` call whose `task_id` has no session-agent mapping entry, for example after the mapping file was deleted
- WHEN the call executes
- THEN no child starts
- AND the teach-back directs the caller to `task` for a fresh child

##### Scenario: Corrupted read on resume is a missing entry
- GIVEN the mapping file is corrupted when a `task_resume` call reads it
- WHEN the call executes
- THEN the call fails closed as if the entry were missing
- AND no child starts

##### Scenario: Stale entry is harmless
- GIVEN a mapping entry whose session id has no session record
- WHEN a `task_resume` call names that id
- THEN the session-record check fails the call closed before any child starts

#### Requirement: Fail-closed resume

Every resume failure SHALL start zero children. The failure conditions are: a missing mapping entry, a corrupted mapping read, a missing session record, a session whose recorded role is not the subagent role, a mapped name that no discoverable agent provides, and a Tau-process unknown-session diagnostic.

In the Tau-process unknown-session condition, the attempted process's immediate CLI failure SHALL count as no child: it SHALL perform no agent work, SHALL start no session, SHALL NOT start a fresh fallback child, and its diagnostic SHALL fold into the teach-back content.

A fail-closed resume result SHALL carry the teach-back as its content, no envelope, an empty `results` array, and no `planned` field. The teach-back SHALL preserve the requested id, SHALL state that no child started, and SHALL direct the caller to `task` for a fresh child.

A successful resume SHALL stay pinned to the original session and its recorded cwd.

##### Scenario: Unknown id fails closed
- GIVEN a `task_resume` call whose `task_id` matches no session, for example the text `nonexistent`
- WHEN the call executes
- THEN zero children start
- AND the result carries the teach-back as its content, no envelope, an empty `results` array, and no `planned` field
- AND the teach-back preserves the requested id text
- AND the teach-back states that no child started and directs the caller to `task` for a fresh child

##### Scenario: Unknown-session diagnostic fails closed
- GIVEN a resume whose session and mapping verification passed
- WHEN the attempted Tau process fails immediately with an unknown-session diagnostic
- THEN no fresh child starts and no session is created
- AND the teach-back includes the diagnostic
- AND the result carries the fail-closed contract

##### Scenario: Non-subagent role fails closed
- GIVEN a `task_resume` call whose `task_id` names a session whose recorded role is not the subagent role
- WHEN the call executes
- THEN no child starts
- AND the result carries the fail-closed contract

##### Scenario: Unmappable agent name fails closed
- GIVEN a mapped agent name that no discoverable agent provides
- WHEN a `task_resume` call for that mapping entry executes
- THEN no child starts
- AND the result carries the fail-closed contract

##### Scenario: Successful resume is not fail-closed
- GIVEN a `task_resume` call whose mapping entry, session record, role, and mapped agent all verify
- WHEN the resume runs
- THEN exactly one child starts against the original session
- AND the result carries the normal envelope contract

#### Requirement: Fixed dispatch environment

The dispatch environment SHALL be fixed on both tools. A fresh child SHALL spawn in the parent session's working directory. No `cwd` parameter SHALL exist on either tool. A child that needs another directory SHALL change its own directory or SHALL receive absolute paths in its prompt.

Agent discovery SHALL be fixed to all layers: bundled agent definitions, user agent definitions, and the nearest ancestor project agent definitions, with the collision precedence of project replacing user and user replacing bundled. No per-call control SHALL narrow or widen discovery. The former per-call scope and approval parameters and the project-agent approval flow SHALL be removed, so project-layer definitions dispatch without per-call approval.

##### Scenario: Fresh child spawns in the parent session cwd
- GIVEN a fresh `task` dispatch
- WHEN the child starts
- THEN the child's working directory is the parent session's working directory

##### Scenario: Project definitions dispatch without approval
- GIVEN project-layer definitions exist
- WHEN a `task` call names an agent that the nearest ancestor project layer provides
- THEN that definition is dispatched
- AND no confirmation step runs and no approval parameter exists

##### Scenario: No per-call discovery control
- GIVEN the parameter surface of either tool
- WHEN it is read
- THEN it contains no parameter that selects agent layers or requires project-agent approval

#### Requirement: Per-tool descriptions

Each tool's schema description, tool description, and prompt guidelines SHALL describe only that tool's supported shape.

The `task` tool description SHALL show the minimal new-child example, SHALL state the inheritance default (an unpinned child resolves to the parent session's provider, model, and thinking level), SHALL state the fixed environment (spawn in the parent session's working directory, all-layer discovery), SHALL carry the all-layer roster, and SHALL name `task_resume` in a one-line continuation pointer.

The `task_resume` tool description SHALL show the continuation shape with `task_id` and `timeout_seconds` and SHALL name the session-agent mapping as the source of the resumed agent. It SHALL carry no roster, because its caller cannot select an agent: a roster on the resume tool re-creates the agent-invention surface this change removes.

`task_resume` teach-backs SHALL name its three fields and the mapping, and SHALL list no agents.

The prompt guidelines of both tools SHALL keep the dispatch threshold, the prohibition on delegating simple reads, searches, commands, or small edits, the prohibition on dispatching work the caller is about to perform itself, the self-contained-prompt requirement, and the single-task-per-call rule, split so each tool's guidelines reference only that tool.

##### Scenario: Task description content
- GIVEN the `task` tool description
- WHEN a reader reads it
- THEN it shows the minimal new-child example
- AND it states the inheritance default
- AND it states the fixed spawn directory and all-layer discovery
- AND it carries the all-layer roster
- AND it names `task_resume` in a one-line continuation pointer

##### Scenario: Resume description content
- GIVEN the `task_resume` tool description
- WHEN a reader reads it
- THEN it shows the continuation shape with `task_id` and `timeout_seconds`
- AND it names the session-agent mapping as the source of the resumed agent
- AND it carries no agent roster

##### Scenario: Resume teach-backs list no agents
- GIVEN a `task_resume` teach-back
- WHEN it renders
- THEN it names `prompt`, `task_id`, and `timeout_seconds`
- AND it names the session-agent mapping
- AND it lists no agents

##### Scenario: Guidelines reference only their own tool
- GIVEN each tool's prompt guidelines
- WHEN they are read
- THEN the `task` guidelines reference the `task` surface only
- AND the `task_resume` guidelines reference the `task_resume` surface only

#### Requirement: Clean-cut consumer update

Every in-repo consumer of the task surface SHALL update in the same change: the skills and reviewer prompts that embed task-call examples, the README task sections, the task-tool reference document, and the example configuration file. No legacy tool, no alias, and no deprecation window SHALL exist. The README task sections SHALL announce the removed behaviors in the same change, including the removal of resuming a session under a different agent.

##### Scenario: No legacy tool or alias
- GIVEN the extension after this change
- WHEN the registered tool surface is read
- THEN only `task` and `task_resume` are registered
- AND no alias or deprecated legacy tool exists

##### Scenario: Consumers show the new surface
- GIVEN every shipped document that embeds a task-call example
- WHEN it is read
- THEN it shows the two-tool snake_case surface
- AND no shipped document shows the removed flat single-tool parameter surface

### MODIFIED Requirements

#### Requirement: task_id resume
<!-- Only the changed parts. The sync preserves existing content not mentioned. The resumed agent now comes from the session-agent mapping instead of a call-level `subagent_type`: the baseline rule that the tool records no per-session agent owner and the "Resume under a different agent" and "Resume requires subagent_type" scenarios are replaced. Every resume failure follows the Fail-closed resume requirement. The timeout override parameter is `timeout_seconds`. -->

A `task_resume` call SHALL resume that child session instead of creating one. A resume run SHALL launch a new child process against the existing session. The session SHALL retain its previous messages and tool outputs. The call's `prompt` SHALL be the new user turn. The result content SHALL relay the new final assistant message in an envelope whose `id` is the existing session's id.

The resumed agent SHALL be the agent name recorded in the session-agent mapping for the requested `task_id`. A `task_resume` call SHALL NOT name an agent: `subagent_type` is not a `task_resume` parameter, and the initial `task` call owns the agent choice for the session's lifetime. Recovery for a different agent is a fresh `task` call.

The runner SHALL re-discover the mapped agent's definition by name through all-layer discovery anchored at the parent session's working directory, and SHALL regenerate the agent body prompt and the profile policy extensions for the resumed run. It SHALL apply the thinking policy and the recursion guard exactly as in a fresh run. The appended prompt SHALL use a resume variant of the isolation sentence. That variant states the session's own prior turns are the child's earlier work on this task. Effective provider, model, and reasoning effort SHALL resolve exactly as in a fresh call and SHALL apply to the resumed run. `timeout_seconds` SHALL bound the resumed run. Usage in details SHALL cover the resumed run only. Only the new turn's events SHALL stream.

A timed-out resume SHALL leave the session's recorded turns intact, and a later resume SHALL continue the retained context.

Every resume failure SHALL follow the Fail-closed resume requirement.

##### Scenario: Resume continues the child session
- GIVEN a prior child session with messages and tool outputs
- WHEN a `task_resume` call carries that `task_id` and a `prompt`
- THEN a new child process runs against the existing session
- AND the session keeps its earlier messages and tool outputs
- AND the content is the new final assistant message in a completed envelope with the same id

##### Scenario: Resume agent comes from the mapping
- GIVEN a child session started with one agent
- WHEN a `task_resume` call resumes it without naming an agent
- THEN the resumed run uses the mapped agent's re-discovered definition, prompt, and policies

##### Scenario: Resume prompt uses the resume variant
- GIVEN a resumed run
- WHEN the appended prompt is built
- THEN the isolation sentence states the session's own prior turns are the child's earlier work on this task

##### Scenario: Resume timeout applies
- GIVEN a `task_resume` call carries `timeout_seconds` with the value 7200
- WHEN the resumed child launches
- THEN the resumed run is bounded by 7200 seconds

##### Scenario: Timed-out resume retains turns
- GIVEN a resumed run times out
- WHEN a later `task_resume` call resumes the same session
- THEN the session's earlier recorded turns are intact
- AND the later resume continues the retained context

##### Scenario: Resume usage covers the resumed run
- GIVEN a resumed child completes
- WHEN its details usage is read
- THEN the usage covers the resumed run only

#### Requirement: Resume working directory
<!-- Only the changed parts. The sync preserves existing content not mentioned. The repair-note rule and the call-`cwd` sentences dissolve: no `cwd` parameter exists on `task_resume`. The recorded-cwd behavior and the store-record rule stay unchanged. -->

A resumed run SHALL use the session's recorded creation cwd as its working directory. The store record SHALL keep its creation cwd.

##### Scenario: Resume cwd is the recorded cwd
- GIVEN a child session created in one directory
- WHEN a `task_resume` call resumes it
- THEN the resumed child runs in the session's recorded creation cwd

##### Scenario: Store record keeps creation cwd
- GIVEN a resumed run completed
- WHEN the session record is read
- THEN the recorded creation cwd is unchanged

#### Requirement: Agent definition discovery
<!-- Only the changed parts. The sync preserves existing content not mentioned. The scope-selection sentences ("`agentScope: user` SHALL be the default...", the `project` and `both` sentences) and the "User scope" scenario dissolve under fixed all-layer discovery. The frontmatter key `reasoningEffort` renames to `reasoning_effort`, and the "Unknown metadata SHALL be ignored" rule gains the stale-key diagnostic exception. The teach-back exclusion reverses: the roster teach-back names project agents. The three-layer structure, collision precedence, metadata rules, skip diagnostics, and the bundled definitions' set and profiles stay unchanged; this block generalizes the living spec's layer-1 path wording to "bundled agent definitions shipped with the extension" with no behavioral change. -->

The extension SHALL discover Markdown agent definitions in three increasing-precedence layers:

1. bundled agent definitions shipped with the extension;
2. user definitions at `~/.tau/agents/*.md`;
3. project definitions at the nearest ancestor `.tau/agents/*.md` found by walking up from the parent session working directory.

Discovery SHALL always include all three layers. A higher layer SHALL replace an agent with the same name, and final ordering SHALL be lexical.

Definitions SHALL contain scalar YAML frontmatter with non-empty string `name` and `description` values. They MAY contain `profile` (`general-purpose`, `read-only`, or `review`), `provider`, `model`, and `reasoning_effort` (one of `off`, `minimal`, `low`, `medium`, `high`, `xhigh`); profile SHALL default to `general-purpose`. Unknown metadata SHALL be ignored, except that a definition carrying the stale `reasoningEffort` key SHALL produce a discovery diagnostic that names the stale key, SHALL lose that reasoning-effort pin, and SHALL otherwise load with its remaining metadata. Malformed, unreadable, incomplete, empty optional, unknown-profile, or unknown-reasoning-effort definitions SHALL be skipped with diagnostics that do not expose the body.

The bundled definitions are `general-purpose`, `read-only`, `implementation` (general-purpose profile), `code-review` (review profile, strict `## Code Review` report format ending in the status line), and `document-review` (review profile, strict `## Document Review` report format ending in the status line). They set no frontmatter provider, model, or reasoning-effort values, so they fall through to the configuration file and parent-session values described under the overrides requirement.

A requested name that no discoverable agent provides SHALL fail closed with a teach-back that lists the roster, and the roster SHALL name bundled, user, and project agents. No child SHALL start.

##### Scenario: Same-name override
- GIVEN bundled, user, and project definitions use the same agent name
- WHEN discovery runs
- THEN the nearest project definition is selected

##### Scenario: Nearest project directory
- GIVEN more than one ancestor contains `.tau/agents`
- WHEN discovery starts from the parent session working directory
- THEN only the nearest directory is used as the project layer

##### Scenario: Invalid definition
- GIVEN a definition is malformed, unreadable, incomplete, or uses an unsupported profile
- WHEN its layer is scanned
- THEN that definition is skipped
- AND a discovery diagnostic identifies the file and reason

##### Scenario: Stale frontmatter key
- GIVEN an agent definition carries the stale `reasoningEffort` key
- WHEN discovery runs
- THEN a discovery diagnostic names the stale key
- AND the definition loads with its remaining metadata
- AND its reasoning-effort pin is dropped

##### Scenario: Other unknown frontmatter keys stay ignored
- GIVEN an agent definition carries an unknown metadata key that is not `reasoningEffort`
- WHEN discovery runs
- THEN the key is ignored without a diagnostic

##### Scenario: Unknown requested agent teach-back
- GIVEN a requested name that no discoverable agent provides
- WHEN validation runs
- THEN no child starts
- AND the teach-back lists the roster
- AND the roster names the project agents

##### Scenario: Project-layer dispatch
- GIVEN a call whose `subagent_type` names a project-layer definition
- AND the nearest ancestor `.tau/agents` provides it
- WHEN dispatch runs
- THEN that definition is dispatched

#### Requirement: Provider, model, and reasoning-effort overrides
<!-- Only the changed parts. The sync preserves existing content not mentioned. The call-level legs dissolve: no call-level `provider`, `model`, or `reasoningEffort` parameter exists, so the optional-literal-override rule, the trimming and placeholder coercion, and the resolution chain's call-level first leg are removed. The four-layer chain replaces the five-layer chain. The catalog fail-fast teach-back wording changes to direct the caller to the config-file or agent-definition pins. The opaque-value rules, the lower-layer precedence, the parent-session fallback, and the config diagnostics stay unchanged. -->

No call-level `provider`, `model`, or reasoning-effort parameter exists on either tool. Children SHALL resolve provider, model, and thinking level per field from, highest first: the config file's `[agents.<name>]` section, then the agent-definition frontmatter, then the config file's `[defaults]` section, then the parent session's active provider, model, and thinking level, when the parent exposes them. A value at a higher layer SHALL override only the corresponding lower-layer value. Effective values SHALL map directly to Tau's separate provider and model flags; values absent at every level SHALL omit their flags. The extension SHALL NOT split combined values or infer a provider from a slash-containing model identifier.

`reasoning_effort` SHALL resolve at config-file `[agents.<name>]`, then agent-definition, then config-file `[defaults]` precedence, then SHALL fall back to the parent session's active thinking level by default, so unpinned children inherit it. The effective level SHALL be applied by the generated child extension described under the child-invocation requirement and recorded on the child result. When no level resolves, the child runs at its ambient level and no thinking extension is generated.

Config-file and frontmatter pins SHALL remain fail-fast validated against the provider catalog before any child starts on either tool, and the failure SHALL list the valid options. The catalog fail-fast teach-back SHALL NOT reference call-level parameters, because no such parameter exists: it SHALL direct the caller to correct the config pin or the agent definition.

Invalid agent-definition reasoning-effort values SHALL skip that definition with a diagnostic; invalid config-file values SHALL be dropped with a config diagnostic. No schema description, prompt guidance, or README text SHALL present a call-level `provider`, `model`, or `reasoningEffort` override; the shipped documentation SHALL present the config-file and agent-definition pin keys and the four-layer resolution chain instead.

##### Scenario: Config pin shadows a definition pin
- GIVEN the config file sets `[agents.<name>]` model and the agent definition pins provider and model
- WHEN the child launches
- THEN the config model applies to the child
- AND the agent definition's provider still applies

##### Scenario: Omitted pins inherit the parent session
- GIVEN no config-file or agent-definition pin defines provider or model
- AND the parent session exposes provider and model values
- WHEN the child launches
- THEN the child inherits the parent session's provider and model

##### Scenario: No pins and no parent values omit the flags
- GIVEN no config-file or agent-definition pin defines provider or model
- AND the parent session exposes no provider or model values
- WHEN the child launches
- THEN both provider and model flags are absent

##### Scenario: Parent thinking inheritance
- GIVEN an unpinned agent and no config-file or frontmatter reasoning value
- AND the parent session runs at a thinking level
- WHEN the child is launched
- THEN the parent level is the effective reasoning effort
- AND the generated child extension applies it before the first turn

##### Scenario: Unresolved pin fails closed before launch
- GIVEN a config pin that names an unconfigured provider
- WHEN validation runs
- THEN the call fails closed before any child starts
- AND the teach-back lists the configured providers
- AND the teach-back directs the caller to correct the config pin or the agent definition

##### Scenario: Opaque model identifier
- GIVEN a model value contains `/`
- WHEN the value is mapped to argv
- THEN the complete value is passed to `--model`
- AND no provider is inferred

##### Scenario: Unsupported reasoning effort
- GIVEN the effective provider/model does not support the requested level
- WHEN the child session validates the level
- THEN the child prints a `[superpowers-subagent]` diagnostic to `stderr`
- AND the child still completes at its ambient level
- AND the result retains the `stderr` diagnostic

#### Requirement: Isolated Tau child invocation
<!-- Only the changed parts. The sync preserves existing content not mentioned. The fresh child's `--cwd` value is always the parent session's working directory. The recursion guard prevents registration of both tools. The safe-argv construction, the resumed-child argv, the profile policy extensions, the thinking extension, and the appended-prompt rules stay unchanged. -->

Each child SHALL run as a separate Tau JSON-mode process with safe argv and no shell. Every fresh child SHALL receive a generated session id with `--session-id` and the subagent role with `--session-role`, alongside `--no-extensions`, `--no-approve`, `--cwd` carrying the parent session's working directory, and a temporary `--append-system-prompt` file before the positional delegated task. A resumed child SHALL omit `--cwd` and SHALL otherwise use the fresh-run argv and prompt construction, because the resumed run uses the session's recorded cwd. A resumed child SHALL reconnect by the existing session id through `--session` instead of pinning a new session id. Discovered child extensions and protected project resources SHALL be disabled, and a recursion guard SHALL prevent registration of `task` and `task_resume` if the extension is explicitly loaded in a child. Read-only and review children SHALL additionally load a temporary profile policy extension permitting exactly their profile's tools (`read` only, or `read` plus `bash` for read-only use), and children with an effective reasoning effort SHALL additionally load a temporary extension that applies that level to the child session before its first turn.

##### Scenario: Fresh child runs in the parent session cwd
- GIVEN a fresh dispatch
- WHEN the child starts
- THEN the process working directory and the Tau `--cwd` flag both carry the parent session's working directory

##### Scenario: Recursion guard
- GIVEN a child process carries the recursion environment guard
- WHEN the subagent extension is explicitly loaded despite disabled discovery
- THEN its setup registers neither `task` nor `task_resume`

##### Scenario: Resumed child argv omits the cwd flag
- GIVEN a `task_resume` call whose session verification passed
- WHEN child argv is built
- THEN the argv carries no `--cwd` flag
- AND the argv keeps the fresh-run flags and extensions

#### Requirement: Subagent configuration file
<!-- Only the changed parts. The sync preserves existing content not mentioned. The reasoning-effort key renames from `reasoningEffort` to `reasoning_effort`; the stale camelCase key is now an unknown key and follows the existing unknown-key diagnostic rule. The file locations, per-key project shadowing, value rules, diagnostics, and configPaths/configDiagnostics reporting stay unchanged. -->

The file SHALL support a `[defaults]` table (provider, model, `reasoning_effort` fallbacks for every agent) and `[agents.<name>]` tables with the same keys. Values SHALL be non-empty strings; `reasoning_effort` SHALL be one of `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, normalized case-insensitively. Unknown keys, wrong-typed tables, empty strings, and invalid thinking levels SHALL be dropped with a diagnostic, so a config file that still carries the stale `reasoningEffort` key produces the unknown-key diagnostic, loses that pin, and dispatch proceeds without it until the operator renames the key.

##### Scenario: Stale config key loses its pin with a diagnostic
- GIVEN a config file carries the stale `reasoningEffort` key
- WHEN the config loads
- THEN a diagnostic names the unknown key
- AND the reasoning-effort pin is dropped
- AND dispatch proceeds with the remaining valid configuration

#### Requirement: Tau JSON collection
<!-- Only the changed parts. The sync preserves existing content not mentioned. The provider and model recovery notes no longer tell the caller to omit call-level overrides, because no call-level parameter exists: they direct the caller to the config-file or agent-definition pins. The JSON Lines collection rules, stderr cleaning, excerpt bound, error-message construction, and usage accumulation stay unchanged. -->

If the created error's excerpt contains `Unknown provider:` case-insensitively, the error message SHALL tell the caller to correct the provider pin in the config file or the agent definition and to use an exact provider name from `tau providers`. If the excerpt contains `Model is not configured for provider` case-insensitively, it SHALL tell the caller to correct the model pin in the config file or the agent definition, or to use an exact model ID supported by the provider. Recovery instructions SHALL depend only on the bounded excerpt.

##### Scenario: Provider recovery
- GIVEN the bounded stderr excerpt identifies an unknown provider
- WHEN the runner creates the nonzero-exit error message
- THEN the error message directs the caller to correct the provider pin in the config file or the agent definition
- AND it refers to exact provider names from `tau providers`

##### Scenario: Model recovery
- GIVEN the bounded stderr excerpt identifies a model that is not configured for its provider
- WHEN the runner creates the nonzero-exit error message
- THEN the error message directs the caller to correct the model pin in the config file or the agent definition
- AND it refers to an exact model ID supported by the provider

#### Requirement: Task result envelope
<!-- Only the changed parts. The sync preserves existing content not mentioned. The repair-notes sentence and the "Repair note placement" scenario are deleted: the repair-note mechanism is removed entirely. The pre-session failure causes shrink to a process startup failure or a cancellation before startup, and the "Interactive denial envelope" scenario is deleted with the approval flow. The failure form's id clause loses the fallback wording, because no fallback exists. The envelope form, id semantics, state semantics, inner-tag rules, and verbatim inner content stay unchanged. -->

For every result that starts a child, the model-facing content SHALL be one envelope of the form `<task id="<taskId>" state="completed|error">`. The envelope SHALL wrap one inner `task_result` or `task_error` tag. The `taskId` SHALL be the child's Tau session id. The envelope state SHALL be the process outcome only. `completed` SHALL mean that the child finished and delivered a final assistant message, whatever status marker that message carries inside its text. `error` SHALL mean that the child failed, was cancelled, timed out, or ended with no final assistant message. Child status markers (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`) SHALL stay inside the message text and SHALL NOT change the envelope state.

A successful child SHALL wrap its complete final assistant message in `task_result`. A final assistant message without text SHALL wrap the placeholder `(no output)`. A child in the `error` state SHALL wrap its final assistant message in `task_error`. When no final message exists, the `task_error` tag SHALL wrap the OpenCode failure form `Subagent failed (task_id: <id>): <error>`. In that form, `<id>` is the child's session id.

A pre-session failure is a call that fails before Tau creates the child session. The causes are a process startup failure or a cancellation before startup. A pre-session failure SHALL carry state `error` with no `id` attribute, and its `task_error` tag SHALL wrap the startup or cancellation error text.

The inner content SHALL be the child message verbatim with no escaping. The `id` and `state` attributes SHALL carry the semantics. The envelope tags SHALL be informational. No content SHALL carry a `Note:` line before the envelope.

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

##### Scenario: Verbatim inner content
- GIVEN a child final message contains characters that look like markup
- WHEN the envelope is built
- THEN the inner content is the message text verbatim with no escaping

##### Scenario: Pre-session failure envelope
- GIVEN a child process fails to start
- WHEN the result content is built
- THEN the envelope state is `error` with no `id` attribute
- AND the `task_error` tag wraps the startup error text

##### Scenario: Cancellation before startup envelope
- GIVEN a call is cancelled before the child process starts
- WHEN the result content is built
- THEN the envelope state is `error` with no `id` attribute
- AND the `task_error` tag wraps the cancellation error text

##### Scenario: No notes before the envelope
- GIVEN a child-starting result
- WHEN the content is built
- THEN the content is exactly the envelope
- AND no `Note:` line appears before it

#### Requirement: Content envelope and complete details
<!-- Only the changed parts. The sync preserves existing content not mentioned. The details `agentScope` and `projectAgentsDir` fields leave the schema; every other details field, the schema version, the one-element results array, and all child-result fields keep their existing names. The repair-note field leaves the child result. -->

For every result that starts a child, final `content` SHALL be the task result envelope of the Task result envelope requirement. A fail-closed result SHALL carry the teach-back as its content, no envelope, an empty `results` array, and no `planned` field, because no child starts.

Details SHALL keep `schemaVersion: 2` and the one-element `results` array. A result that starts or attempts a child SHALL carry `planned` with the value 1. The details SHALL carry no agent-scope field and no project-agents-directory field. Details keys keep their existing names; only the listed fields are removed.

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

##### Scenario: Details drop the scope and directory fields
- GIVEN any result of either tool
- WHEN the details are inspected
- THEN the details carry no agent-scope field
- AND the details carry no project-agents-directory field

##### Scenario: Pre-session failure details
- GIVEN a child fails before Tau creates its session
- WHEN the details are inspected
- THEN the entry carries no `taskId`
- AND `planned` is 1

#### Requirement: Progress, cancellation, timeout, and cleanup
<!-- Only the changed parts. The sync preserves existing content not mentioned. The timeout override parameter is `timeout_seconds` on both tools; the mechanism, default, and cap stay unchanged. The partial-update, cancellation, hard-cancellation, and temporary-cleanup rules stay unchanged. -->

Each child SHALL default to a 3600-second timeout, and each call on either tool SHALL accept a `timeout_seconds` override greater than 0 and at most 10800. The extension SHALL emit portable partial results after each accepted assistant or tool-result message of the child and after child completion. A partial result SHALL carry `planned` with the value 1. A partial result's content SHALL carry the `<done>/<planned> done` progress form with the single child: `<done>/1 done`.

##### Scenario: Timeout override at the cap
- GIVEN a call passes `timeout_seconds` with the value 10800
- WHEN the child runs
- THEN the override is accepted and bounds the child

##### Scenario: Timeout override above the cap
- GIVEN a call passes `timeout_seconds` with the value 10801
- WHEN validation runs
- THEN no child starts

#### Requirement: Portable rendering
<!-- Only the changed parts. The sync preserves existing content not mentioned. `task_resume` registers its own call renderer whose label names the resume operation and the requested id and never an agent name. The `task` call-label rule, the single-frame layout, the headline, the icons, the usage lines, and the live-update rules stay unchanged. -->

The `task` call label SHALL be the `description` value when it is non-empty after trimming, and the effective `subagent_type` otherwise. The call label SHALL NOT derive from the task count. The `task_resume` tool SHALL register its own call renderer: its call label SHALL name the resume operation and the requested `task_id`, and SHALL NOT name an agent, because the mapped agent is not a call argument.

##### Scenario: Call label from the description
- GIVEN a `task` call with `description: "Review auth"` and effective `subagent_type` `code-review`
- WHEN the result renders
- THEN the call label is `Review auth`

##### Scenario: Call label falls back to the agent name
- GIVEN a `task` call whose `description` is only whitespace
- WHEN the result renders
- THEN the call label is the effective `subagent_type`

##### Scenario: Resume call label names the operation and the id
- GIVEN a `task_resume` call with `task_id: "abc"`
- WHEN the call renders
- THEN the call label names the resume operation and the id `abc`
- AND the label names no agent

#### Requirement: Tool description roster
<!-- Only the changed parts. The sync preserves existing content not mentioned. The session-start roster widens from the bundled and user layers to all layers, and the exclusions reverse: rosters and `task` teach-backs name project agents. The `task_id`-reuse usage note names `task_resume` as the continuation tool. The roster line format, annotations, default rule, when-not-to-use section, dispatch threshold, fallback-to-bundled rule, and remaining usage notes stay unchanged. -->

The tool description SHALL carry a one-liner, the agent roster with tool-policy annotations, the default selection rule, a when-not-to-use section, and usage notes. The `subagent_type` parameter description SHALL keep the roster. Each roster line SHALL render in the form `- <name>: <description> (Tools: <policy>)`.

The annotation SHALL render from the resolved definition's effective profile. The `general-purpose` profile SHALL render `Tools: all`. The `read-only` profile SHALL render `Tools: read`. The `review` profile SHALL render `Tools: read, bash`, where the review instructions govern `bash` use. For the unshadowed bundled definitions, `general-purpose` and `implementation` SHALL render `Tools: all`. `read-only` SHALL render `Tools: read`. `code-review` and `document-review` SHALL render `Tools: read, bash`.

The description SHALL state that omitting `subagent_type` selects `general-purpose`. The usage notes SHALL state these rules:

- Several tasks are several `task` calls in one message.
- Delegated work is not duplicated.
- The prompt must be self-contained.
- The result names the `task_id` that a later `task_resume` call can reuse to continue the same subagent session.
- The caller states whether the child writes code or does research and how to verify the result.

The description SHALL keep the dispatch-threshold rule. The rule is: delegate only substantive multi-step work that benefits from an isolated context window, or long-running work that must not block this session. It SHALL keep the prohibitions: never delegate simple reads, searches, commands, or small edits, and never dispatch a task and then do the same work. It SHALL keep the prompt-guideline sentences, including the self-contained prompt requirement.

The description roster and the `subagent_type` description roster SHALL be static per session. They SHALL list the agents discovered at session start from the bundled, user, and project layers. Discovery is anchored at the session cwd. Name resolution SHALL follow the collision precedence of the Agent definition discovery requirement. The roster SHALL fall back to the bundled agents when discovery fails at session start. Teach-back rosters on `task` SHALL list the same agents, including the project agents.

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
- AND the notes state that a later `task_resume` call can reuse the result's `task_id`
- AND the notes state the verification-statement rule

##### Scenario: Roster scope at session start
- GIVEN project agents exist and a session starts
- WHEN the roster is built
- THEN the roster lists the bundled, user, and project agents discovered at session start

##### Scenario: Discovery failure falls back to bundled
- GIVEN discovery fails at session start
- WHEN the roster is built
- THEN the roster lists the bundled agents

##### Scenario: Teach-back roster includes project agents
- GIVEN a `task` teach-back that lists agents
- WHEN it renders
- THEN it lists the same bundled, user, and project agents as the description roster

#### Requirement: Concurrent task calls
<!-- Only the changed parts. The sync preserves existing content not mentioned. The parallelism, no-cap, and independence rules extend to `task_resume` calls, and the approval step leaves the independent-dispatch sentence. -->

Several calls of one task tool in one assistant message SHALL run concurrently. Each call SHALL be validated and dispatched independently. Each tool SHALL set no cap on the number of its calls in one message. Each result SHALL carry its own envelope. One call's failure SHALL NOT stop the others.

##### Scenario: Parallel dispatch
- GIVEN two `task` calls in one assistant message
- WHEN both run
- THEN both children are active in parallel
- AND each result carries its own envelope

##### Scenario: Parallel resumes
- GIVEN two `task_resume` calls in one message that carry different `task_id` values
- WHEN both run
- THEN both resumed children are active in parallel
- AND each result carries its own envelope

##### Scenario: Independent failure
- GIVEN two task calls in one message and one child fails
- WHEN both finish
- THEN the failed call carries its error envelope
- AND the other result is intact

##### Scenario: No call cap
- GIVEN an assistant message with three task calls of the same tool
- WHEN dispatch runs
- THEN all three calls dispatch their children

#### Requirement: Same-task_id exclusion
<!-- Only the changed parts. The sync preserves existing content not mentioned. Only `task_resume` carries `task_id`, so the lock applies to `task_resume` ids. The non-blocking rule from the proposal's risk treatment is stated. The process-safe lock, the fail-closed loser contract, and the lock's task-calls-only scope stay unchanged. -->

Two concurrent `task_resume` calls that carry the same `task_id` SHALL NOT both run. Exactly one SHALL start its child. The other SHALL fail closed with a teach-back that names the same-id conflict. The losing call's result SHALL carry the fail-closed result contract of the Content envelope and complete details requirement. The exclusion SHALL be process-safe: a lock keyed by `task_id` SHALL coordinate parent processes on the machine that hosts the session store. The lock SHALL apply to `task_resume` ids. The exclusion SHALL be non-blocking: the losing call SHALL fail closed immediately and SHALL NOT wait for the winning call's child to finish.

##### Scenario: Same-id pair in one message
- GIVEN two `task_resume` calls in one message carry the same `task_id`
- WHEN both run
- THEN one result carries the child envelope
- AND the other result is a fail-closed teach-back that names the same-id conflict
- AND the losing result carries no envelope, an empty `results` array, and no `planned` field

##### Scenario: Losing call does not wait
- GIVEN two `task_resume` calls carry the same `task_id`
- WHEN one call holds the lock while its child runs
- THEN the other call fails closed immediately
- AND it does not wait for the winner's timeout

##### Scenario: Cross-process same-id exclusion
- GIVEN two parent processes on the machine that hosts the session store
- WHEN both dispatch a `task_resume` call with the same `task_id`
- THEN exactly one child starts
- AND the other call fails closed

#### Requirement: Pinned child sessions
<!-- Only the changed parts. The sync preserves existing content not mentioned. The fallback sentence is replaced by the fail-closed resume: a resume of a session that was never persisted fails closed. The maintenance steps gain the session-agent mapping entry deletion. The pinned-session id semantics, the subagent role, the `tau sessions --all` visibility, and the accumulation rules stay unchanged. -->

Every fresh run SHALL create a pinned child session. The tool SHALL generate a new session id for every fresh child. The tool SHALL record it as the child's `taskId` on the child result, in the details entry, and as the envelope `id`. The child session SHALL carry the subagent role, so it stays out of the default `tau sessions` listing and lists under `tau sessions --all`. The runner SHALL record the id for every fresh-child attempt, including an attempt that fails after startup. When tau never persisted the session record, a later resume with that id SHALL fail closed per the Fail-closed resume requirement.

Child sessions accumulate in the Tau session store with no retention. The accepted recovery for unwanted child sessions is manual store maintenance while no tau process uses the store. The store root is `~/.tau/sessions/`, with one directory per parent project, one `index.jsonl` per project directory, and one `<session-id>.jsonl` transcript per session. Each index line records the session's `id` and its transcript `path`. The maintenance steps:

1. Find the child's line by `id` in the project `index.jsonl` files under the store root.
2. Stop the tau processes that use the store.
3. Delete the transcript file that the line's `path` names.
4. Delete the child's line from that `index.jsonl`.
5. Delete the child's entry from the session-agent mapping.
6. Verify with `tau sessions --all` that the child no longer lists.

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
- GIVEN the operator deletes a child's transcript file, its `index.jsonl` line, and its mapping entry while no tau process uses the store
- WHEN a later `task_resume` call names that id
- THEN the id matches no session
- AND the call fails closed with the teach-back that directs the caller to `task` for a fresh child

### REMOVED Requirements

#### Requirement: task interface and validation

The single flat `task` tool and its camelCase field surface are removed. The two-tool snake_case surface of the Two-tool task surface requirement replaces them, and the Cross-tool field rejection and Fail-closed validation requirements replace the flat requirement's validation content. The surviving unchanged content re-adds there: the background teach-back, the unknown-field teach-backs, the fail-closed result contract, the single-task-per-call rule, and the result arriving when the child finishes. No tool SHALL carry the removed flat parameter surface, and no camelCase parameter name SHALL exist on either tool.

##### Scenario: Flat tool no longer registered
- GIVEN the extension loads in a session
- WHEN the tool surface is read
- THEN no tool carries the removed flat parameter surface with `cwd`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, or `timeoutSeconds`
- AND only the two tools of the Two-tool task surface requirement are registered

#### Requirement: Explicit project-agent approval

The per-call project-agent approval flow is removed. Project-layer definitions SHALL dispatch without per-call approval, their names and descriptions SHALL appear in the roster, and no confirmation UI or approval parameter SHALL exist on either tool. The operator runs the tools inside a secure sandbox and accepts repository-controlled agent prompts as dispatch input. The Fixed dispatch environment and Agent definition discovery requirements carry the replacement behavior.

##### Scenario: No approval flow
- GIVEN a session with project-layer definitions
- WHEN a `task` call names a project-layer agent
- THEN dispatch proceeds with no confirmation UI step
- AND no approval parameter exists on either tool

#### Requirement: Unknown task_id fallback

The fresh-child fallback for an unknown or non-subagent `task_id`, its repair notes, and the unknown-session retry-as-fresh-child behavior are removed. Every resume failure SHALL fail closed per the Fail-closed resume requirement, and the repair-note mechanism SHALL stay removed per the Fail-closed validation requirement. No resume failure SHALL start a fresh child.

##### Scenario: No fresh fallback child
- GIVEN a resume whose id matches no session
- WHEN the call executes
- THEN no fresh child starts
- AND no repair note appears
- AND the result carries the fail-closed contract of the Fail-closed resume requirement
