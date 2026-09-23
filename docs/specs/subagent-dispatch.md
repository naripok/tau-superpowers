# Subagent Dispatch

## Purpose

The `task` tool delegates complete units of work to isolated Tau subprocesses through one flat interface: every call carries exactly one task as one flat object, and parallel work uses several `task` calls in one message, which Tau schedules concurrently. Every fresh child runs in a pinned Tau session, and a later call can resume that session with `task_id`. Parent-model content is one task envelope wrapping the child's complete final assistant message, never tool calls, thinking, or earlier messages, and with no heading extraction, while structured details retain the complete accepted wire messages. Per-subagent provider, model, and thinking-effort values resolve at call, then a `superpowers-subagent.toml` config file (`[agents.<name>]` and `[defaults]` sections), then agent definitions, then the parent session's active provider, model, and thinking level.

This is the canonical description of current behavior. See the [Tau `task` tool reference](../../skills/using-superpowers/references/tau-tools.md) for copyable calls and the [README](../../README.md) for installation.

## Requirements


### Requirement: Tau-discoverable installation

The package SHALL keep one canonical top-level `skills/` tree. The installer SHALL install individual skills under `~/.tau/skills` and the extension under `~/.tau/extensions/superpowers-subagent` as real directory copies under delete propagation with the install excludes. The install excludes are `.git`, `.venv`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, and `.worktrees`. The installer SHALL preflight every destination and the rsync dependency before it changes any destination. The installer SHALL stop without changing any destination when a destination conflicts or when rsync is unavailable. The installer SHALL stop without changing any destination when the `~/.tau/skills` or `~/.tau/extensions` base directory is a symlink, dangling or resolving anywhere. A real or absent base directory passes this check. A base directory under a symlinked `~/.tau` passes this check when the base itself is a real directory or absent. When a copy fails partway, the installer SHALL report the failure and exit nonzero, and a later run SHALL make the affected entry match its source. A checkout SHALL support explicit extension loading with `tau -e extensions/superpowers-subagent` and SHALL NOT expose executable code through project `.tau/extensions` by default.

#### Scenario: Checkout discovery

- GIVEN Tau runs in an approved repository checkout
- WHEN the extension is explicitly loaded with `tau -e extensions/superpowers-subagent`
- THEN Tau registers one tool named `task`
- AND Tau discovers no project skills from this checkout

#### Scenario: Prompt threshold

- GIVEN the task tool is registered
- WHEN its always-visible prompt surface (description, snippet, and guidelines) is read
- THEN it states that subagents exist for substantive multi-step work that benefits from an isolated context window or for long-running work that must not block the parent session
- AND it forbids dispatching simple reads, searches, commands, and small edits the parent can perform itself
- AND it forbids dispatching work the parent is about to perform itself, because a subagent replaces the parent's tool calls for its task

#### Scenario: Copy install

- GIVEN no destination exists for a skill the source provides or for the extension
- WHEN the installer runs
- THEN each destination exists as a real directory whose content matches its source under the install excludes
- AND each copy contains none of the excluded development paths: `.git`, `.venv`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.worktrees`
- AND the extension copy keeps its `tests` directory and `pyproject.toml`

#### Scenario: Idempotent re-install

- GIVEN a completed install whose source matches the installed content under the install excludes
- WHEN the installer runs again
- THEN the managed destinations keep their content
- AND the output reports the entries as unchanged

#### Scenario: Symlink migration

- GIVEN a destination name that the source provides
- AND that destination is a symlink that resolves into the source repository
- WHEN the installer runs
- THEN the installer removes the symlink and installs a real directory copy
- AND the source repository content is unchanged

#### Scenario: Copy take-over

- GIVEN a destination name that the source provides
- AND that destination is a real directory that no stamp records
- WHEN the installer runs
- THEN the installer replaces the content with the source copy under delete propagation
- AND the output lists every removed and updated path

#### Scenario: User installation collision

- GIVEN a destination name that the source provides
- AND that destination is a symlink that does not resolve into the source repository, or is a file that is neither a directory nor a symlink
- WHEN the installer preflights the destinations
- THEN installation stops before changing any destination
- AND that destination is not replaced
- AND a recorded stamp does not exempt that destination from this stop

#### Scenario: Symlinked base directory stops the install

- GIVEN the `~/.tau/skills` or `~/.tau/extensions` base directory is a symlink, dangling or resolving anywhere
- WHEN the installer runs
- THEN the installer exits nonzero before changing any destination
- AND the error names each symlinked base directory
- AND the error states the remedy: remove the symlink or replace it with a real directory, then run the installer again

#### Scenario: Base error precedes a destination conflict

- GIVEN the `~/.tau/skills` base directory is a symlink
- AND the extension destination is a regular file
- WHEN the installer runs
- THEN the error names the symlinked base directory
- AND the error names no destination conflict
- AND the installer exits nonzero before changing any destination

#### Scenario: No migration for a repository base link

- GIVEN the `~/.tau/skills` base directory is a symlink into the source repository
- WHEN the installer runs
- THEN installation stops before changing any destination
- AND the source repository content is unchanged

#### Scenario: Missing rsync dependency

- GIVEN rsync is not available on PATH
- WHEN the installer runs
- THEN it exits nonzero before changing any destination
- AND every destination keeps its pre-install state

#### Scenario: Partway failure repair

- GIVEN a previous run reported a partway copy failure for an entry
- WHEN the installer runs again
- THEN the affected entry matches its source under the install excludes

#### Scenario: Clone without extension approval

- GIVEN a user only clones the repository
- WHEN Tau starts without a user installation or explicit extension path
- THEN no executable project extension is discovered from this checkout


### Requirement: Managed-entry deletion

The installer SHALL remove an installed entry that a recorded stamp lists as managed when the source no longer provides that entry. The installer SHALL also remove a symlink destination that resolves into the source repository when the source provides no entry under its name. Within a managed entry, the installer SHALL delete destination paths that the source does not provide. The installer SHALL NOT remove a destination that no stamp records and whose name matches no source entry, except a symlink that resolves into the source repository.

#### Scenario: Removed entry

- GIVEN a stamp records an installed entry whose source no longer exists
- WHEN the installer runs
- THEN the installer removes that destination
- AND the output reports the removal

#### Scenario: Source file deletion propagates

- GIVEN a stamp records a managed entry
- AND the source of that entry no longer contains a file that the destination contains
- WHEN the installer runs
- THEN the destination no longer contains that file

#### Scenario: Repository link without source entry removed

- GIVEN a symlink destination resolves into the source repository
- AND the source provides no entry under its name
- WHEN the installer runs
- THEN the installer removes that symlink

#### Scenario: Foreign destination untouched

- GIVEN `~/.tau/skills` contains a directory that no stamp records and whose name matches no source entry
- WHEN the installer runs
- THEN that destination keeps its content

### Requirement: Install stamp

The installer SHALL write a stamp file at `~/.tau/.tau-superpowers-install` after each successful install. The stamp SHALL record the source repository path, the source git SHA with a dirty marker when the source tree has uncommitted changes or a none marker when the source tree has no git metadata, the install time in UTC, and the managed destination list. The stamp SHALL decide which installed entries the installer removes.

#### Scenario: Stamp records git state

- GIVEN the source tree has git metadata
- WHEN the installer completes and the stamp is read
- THEN the stamp records a git SHA
- AND the stamp records a dirty marker when the source tree has uncommitted changes
- AND the stamp records the install time in UTC

#### Scenario: Stamp records no git metadata

- GIVEN the source tree has no git metadata
- WHEN the installer completes and the stamp is read
- THEN the stamp records the none marker

#### Scenario: Stamp records a clean tree

- GIVEN the source tree has git metadata with no uncommitted changes
- WHEN the installer completes and the stamp is read
- THEN the stamp records a git SHA
- AND the stamp records no dirty marker

### Requirement: Staleness check

The installer SHALL support `install.sh --check`. The check SHALL compare installed content against the source tree at the source path recorded in the stamp, with the same rules and excludes as installation. A managed destination that does not exist is a difference. A stamp-recorded entry whose source no longer exists is a difference. The check performs the content comparison only and performs no destination preflights, no base-directory preflights, and no reference scan. The check SHALL change nothing and SHALL exit 0 on a match. The check SHALL exit 1 and print every differing path when content differs. The check SHALL exit 1 when the stamp is missing. The check SHALL exit 1 and report the recorded source path when no source tree exists at that path.

#### Scenario: Fresh check passes

- GIVEN installed content matches the source under the install excludes
- WHEN `install.sh --check` runs
- THEN it exits 0 and changes nothing

#### Scenario: Stale content fails

- GIVEN an installed file differs from its source file
- WHEN `install.sh --check` runs
- THEN it exits 1 and prints the differing path
- AND it changes nothing

#### Scenario: Missing stamp fails

- GIVEN no stamp file exists
- WHEN `install.sh --check` runs
- THEN it exits 1 and reports the missing stamp

#### Scenario: Unavailable source fails

- GIVEN the source tree is not available at the recorded source path
- WHEN `install.sh --check` runs
- THEN it exits 1 and reports the recorded source path

#### Scenario: Comparison uses the recorded source

- GIVEN installed content matches the source tree at the recorded source path
- AND the running checkout is a different checkout
- WHEN `install.sh --check` runs
- THEN it exits 0

#### Scenario: Check compares through a symlinked base

- GIVEN a completed install
- AND the `~/.tau/skills` base directory is a symlink to a real directory that holds the installed skills content
- WHEN `install.sh --check` runs
- THEN the check compares the installed content through the resolved path
- AND the check exits 0 when the content matches the source
- AND the check exits 1 when the content under the link target differs from the source

### Requirement: Installed self-containment

The installed resources SHALL be self-contained. A skill SHALL carry every non-workflow file that the agent must read while using the skill inside its own skill directory, a sibling installed skill directory, or elsewhere inside the installed tree. The workflow artifact paths `docs/design/`, `docs/specs/`, and `docs/plans/` of the project under work are not carried resources. A reference whose text begins with one of those three paths is a workflow reference. A workflow reference is not checkout-only.

The repository SHALL provide a pre-commit hook that scans the Markdown files of every skill and the extension for path references written as backticked paths or Markdown link targets. The scan checks file targets only. A path that names a directory is never checkout-only. A reference is checkout-only when a file exists at its path inside the source checkout, resolved against the referencing file's directory or against the source root, and no file exists at that path resolved against the referencing file's installed directory, the referencing resource's installed directory, any sibling installed skill directory, or the installed tree root. The referencing resource is the skill or the extension that owns the referencing file. The installed side is evaluated against the tree that this install produces. The evaluation does not use the current state of `~/.tau`. The installed tree root is `~/.tau`. A reference whose target exists nowhere is not checkout-only. The hook SHALL reject the commit when the scan finds a checkout-only reference, and its output SHALL name the offending file and reference. The hook SHALL scan the staged content of the commit. The installer test suite SHALL run the same scan and SHALL fail when the scan finds a checkout-only reference.

#### Scenario: Carried references resolve

- GIVEN the installed configuration without the source checkout
- WHEN every non-workflow file-target reference whose target exists inside the source checkout is resolved against the referencing file's installed directory, the referencing resource's installed directory, sibling installed skill directories, and the installed tree root
- THEN each target exists inside the installed configuration tree

#### Scenario: Sibling skill reference resolves

- GIVEN an installed skill references a file in a sibling installed skill directory
- WHEN that reference is resolved from the installed location
- THEN the target exists inside the installed configuration tree

#### Scenario: Extension file reference resolves

- GIVEN a Markdown file inside the installed extension references a file that the install places in the extension's installed directory
- WHEN that reference is resolved from the extension's installed directory
- THEN the target exists inside the installed configuration tree

#### Scenario: Workflow artifact paths are not carried resources

- GIVEN a skill directs the agent to `docs/design/`, `docs/specs/`, or `docs/plans/` of the project under work
- WHEN the scan runs on that skill
- THEN the scan does not flag those references

#### Scenario: Commit with a checkout-only reference fails

- GIVEN a staged skill file contains a relative path reference whose target exists only inside the source checkout
- WHEN the pre-commit hook runs
- THEN the hook rejects the commit
- AND the output names the offending file and reference

#### Scenario: Nowhere-resolving reference does not fail the scan

- GIVEN a skill file contains a path reference whose target exists neither inside the source checkout nor inside the installed configuration tree
- WHEN the scan runs on that skill
- THEN the scan does not report that reference

#### Scenario: Shipped resources carry no checkout-only references

- GIVEN the repository as shipped
- WHEN the scan runs on the skills and the extension
- THEN no checkout-only reference is found

### Requirement: task interface and validation

A `task` call SHALL carry exactly one task as one flat object. The fields SHALL be exactly `prompt`, `subagent_type`, `description`, `task_id`, `cwd`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, and `timeoutSeconds`. The tool SHALL run exactly one child per call.

- `prompt` SHALL be a required non-empty string. It is the child's task. The tool SHALL preserve it verbatim.
- `subagent_type` SHALL be optional. When present, it SHALL be a string whose trimmed value is non-empty and names an eligible agent. Validation SHALL trim surrounding whitespace, and the trimmed value SHALL be the effective name. Omission SHALL select `general-purpose`. A name that no eligible agent provides SHALL fail closed with a teach-back that lists the roster. A value that is empty after trimming SHALL fail closed with a teach-back that states `subagent_type` requires a non-empty string when present.
- `description` SHALL be an optional string. It is a display label with no behavioral effect.
- `task_id` SHALL be optional. A present value SHALL be a string that is non-empty after trimming, or the call SHALL fail closed with a teach-back. No format check SHALL exist beyond that. The trimmed value SHALL be the effective `task_id` for session lookup, for the same-id lock, and for repair notes. A well-formed value that matches no session SHALL fall back per the Unknown task_id fallback requirement. `task_id` requires `subagent_type`: a call with `task_id` and no `subagent_type` SHALL fail closed with a teach-back that names both fields.
- `cwd` SHALL be an optional string directory path. Omission SHALL resolve to the parent session cwd. A relative path SHALL resolve against the parent session cwd. Any path SHALL expand `~` and SHALL then resolve canonically to an absolute path. On a resumed run, the Resume working directory requirement SHALL govern instead.
- `agentScope` SHALL be one of `user`, `project`, `both`. It selects the agent layers. The bundled layer always applies. `user` adds the user agents directory `~/.tau/agents`. `project` adds the nearest ancestor directory `.tau/agents` found by walking up from the parent session cwd. `both` adds both. On a name collision, a later layer replaces an earlier one: project replaces user, and user replaces bundled. Omission SHALL select `user`. Another value SHALL fail closed.
- `confirmProjectAgents` SHALL be a boolean. Omission SHALL select `true`.
- `provider` and `model` SHALL be optional literal string overrides. They SHALL use the trimming, placeholder coercion, and resolution chain of the Provider, model, and reasoning-effort overrides requirement.
- `reasoningEffort` SHALL be one of `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, with the same trimming, placeholder coercion, and resolution chain. The chain ends at the parent session's thinking level.
- `timeoutSeconds` SHALL be a number greater than 0 and at most 10800. Omission SHALL select 3600.

An unknown field SHALL fail closed. The teach-back SHALL name the unknown fields, the roster, and one valid flat example. A call that carries `background` SHALL fail closed with the dedicated background teach-back, because background dispatch is not supported in this harness. A value that violates a field's type or range rule SHALL fail closed. The result of a `task` call SHALL arrive when the child finishes. A fail-closed result SHALL carry the teach-back as its content, no envelope, an empty `results` array, and no `planned` field, because no child starts. A headless project-approval failure SHALL fail closed with the teach-back that names the project agents directory. An interactive project-approval denial SHALL cancel the call before any child starts and SHALL carry the pre-session failure contract of the Task result envelope requirement.

#### Scenario: Single-task dispatch

- GIVEN one valid flat call with `prompt` and `subagent_type`
- WHEN `task` executes
- THEN exactly one child runs with the effective agent and the prompt preserved verbatim

#### Scenario: Omitted subagent_type selects the default

- GIVEN a valid call with only `prompt`
- WHEN `task` executes
- THEN one `general-purpose` child runs

#### Scenario: Unknown-field teach-back

- GIVEN a call carries a field outside the allowed field list
- WHEN validation runs
- THEN no child starts
- AND the teach-back names the unknown fields
- AND the teach-back lists the roster
- AND the teach-back shows one valid flat example

#### Scenario: Background teach-back

- GIVEN a call carries `background`
- WHEN validation runs
- THEN no child starts
- AND the dedicated background teach-back states that background dispatch is not supported

#### Scenario: Whitespace subagent_type teach-back

- GIVEN a call passes `" "` as `subagent_type`
- WHEN validation runs
- THEN no child starts
- AND the teach-back states that `subagent_type` requires a non-empty string when present

#### Scenario: Whitespace task_id fails closed

- GIVEN a call passes `" "` as `task_id`
- WHEN validation runs
- THEN no child starts
- AND the teach-back states that `task_id` requires a non-empty string when present

#### Scenario: Missing prompt fails closed

- GIVEN a call omits `prompt` or passes an empty string
- WHEN validation runs
- THEN no child starts
- AND the teach-back states that `prompt` requires a non-empty string

#### Scenario: Non-positive timeout fails closed

- GIVEN a call passes `timeoutSeconds` with the value 0 or a negative number
- WHEN validation runs
- THEN no child starts

#### Scenario: Type-violating common option fails closed

- GIVEN a call passes a non-boolean value as `confirmProjectAgents`
- WHEN validation runs
- THEN no child starts

#### Scenario: Invalid agentScope fails closed

- GIVEN a call passes a value outside `user`, `project`, and `both` as `agentScope`
- WHEN validation runs
- THEN no child starts
- AND the teach-back names the valid `agentScope` values

#### Scenario: Headless project-approval teach-back

- GIVEN a requested name resolves to a project definition
- AND the session runs headless with no explicit `confirmProjectAgents: false`
- WHEN `task` executes
- THEN no child starts
- AND the teach-back names the project agents directory
- AND the result carries no envelope, an empty `results` array, and no `planned` field

#### Scenario: Fresh cwd resolution

- GIVEN a fresh call carries a relative `cwd`
- WHEN the child starts
- THEN the effective directory is the canonically resolved absolute path from the parent session cwd

#### Scenario: Tilde cwd expands

- GIVEN a fresh call carries a `cwd` that starts with `~`
- WHEN the child starts
- THEN the effective directory is the absolute path after `~` expansion and canonical resolution

### Requirement: Agent definition discovery

The extension SHALL discover Markdown agent definitions in three increasing-precedence layers:

1. bundled `extensions/superpowers-subagent/agents/*.md`;
2. user `~/.tau/agents/*.md`;
3. the nearest ancestor `.tau/agents/*.md` from the parent session working directory.

`agentScope: user` SHALL be the default and include bundled plus user definitions. `project` SHALL include bundled plus project definitions. `both` SHALL include all layers. A higher layer SHALL replace an agent with the same name, and final ordering SHALL be lexical.

Definitions SHALL contain scalar YAML frontmatter with non-empty string `name` and `description` values. They MAY contain `profile` (`general-purpose`, `read-only`, or `review`), `provider`, `model`, and `reasoningEffort` (one of `off`, `minimal`, `low`, `medium`, `high`, `xhigh`); profile SHALL default to `general-purpose`. Unknown metadata SHALL be ignored. Malformed, unreadable, incomplete, empty optional, unknown-profile, or unknown-reasoning-effort definitions SHALL be skipped with diagnostics that do not expose the body.

The bundled definitions are `general-purpose`, `read-only`, `implementation` (general-purpose profile), `code-review` (review profile, strict `## Code Review` report format ending in the status line), and `document-review` (review profile, strict `## Document Review` report format ending in the status line). They set no frontmatter provider, model, or reasoning-effort values, so they fall through to the configuration file and parent-session values described under the overrides requirement.

A requested name that no eligible agent provides SHALL fail closed with a teach-back that lists the roster. The teach-back SHALL NOT name project agents, and no child SHALL start.

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

#### Scenario: Unknown requested agent teach-back

- GIVEN a requested name is not eligible in the selected scope
- WHEN validation runs
- THEN no child starts
- AND the teach-back lists the roster
- AND the teach-back names no project agent

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
- AND the teach-back names the project agents directory
- AND the result carries no envelope, an empty `results` array, and no `planned` field

#### Scenario: Scope without project selection

- GIVEN project scope is enabled but every requested name resolves to bundled or user definitions
- WHEN `task` executes
- THEN no project-agent confirmation is required

### Requirement: Isolated Tau child invocation

Each child SHALL run as a separate Tau JSON-mode process with safe argv and no shell. Every fresh child SHALL receive a generated session id with `--session-id` and the subagent role with `--session-role`, alongside `--no-extensions`, `--no-approve`, `--cwd`, and a temporary `--append-system-prompt` file before the positional delegated task. A resumed child SHALL omit `--cwd` and SHALL otherwise use the fresh-run argv and prompt construction, because the resumed run uses the session's recorded cwd. A resumed child SHALL reconnect by the existing session id through `--session` instead of pinning a new session id. Discovered child extensions and protected project resources SHALL be disabled, and a recursion guard SHALL prevent `task` registration if the extension is explicitly loaded in a child. Read-only and review children SHALL additionally load a temporary profile policy extension permitting exactly their profile's tools (`read` only, or `read` plus `bash` for read-only use), and children with an effective reasoning effort SHALL additionally load a temporary extension that applies that level to the child session before its first turn.

Tau 0.3 exposes no CLI flag or extension-hook seam for a child's startup thinking level, so the generated extension calls the child session's own `set_thinking_level` API at `session_start`, reaching the bound session through the extension runtime view. The level is validated against the effective provider/model catalog; when it is unavailable, the child SHALL print a `[superpowers-subagent] could not apply reasoning effort ...` diagnostic to `stderr` and continue at its ambient level.

The appended prompt SHALL preserve the selected agent body and state that the child has no controller conversation history. Its response-format instructions SHALL state that the child's complete final assistant message is relayed verbatim to the controller (earlier messages, tool calls, and thinking are not), SHALL require a self-contained final message covering what was accomplished or found, files read or modified, tests, errors, and concerns, and SHALL require it to end with exactly one supported status marker. The prompt SHALL tell the child not to invoke ambient user skills. Because Tau cannot independently disable user-global skills, that instruction SHALL be documented as behavioral guidance rather than security enforcement.

#### Scenario: Safe default arguments

- GIVEN no provider, model, or profile override
- AND the parent session exposes no provider or model values
- WHEN child argv is built
- THEN neither a shell nor unsupported legacy flags are used
- AND neither `--provider`, `--model`, nor a policy extension is present

#### Scenario: Working directory

- GIVEN a call-specific relative or absolute `cwd`
- WHEN the child starts
- THEN the process working directory and Tau `--cwd` both use the resolved directory
- AND a relative value is resolved from the parent session working directory

#### Scenario: Recursion guard

- GIVEN a child process carries the recursion environment guard
- WHEN the subagent extension is explicitly loaded despite disabled discovery
- THEN its setup does not register `task`

#### Scenario: Resumed child argv omits the cwd flag

- GIVEN a call with `task_id` that passes session verification
- WHEN child argv is built
- THEN the argv carries no `--cwd` flag
- AND the argv keeps the fresh-run flags and extensions

### Requirement: Provider, model, and reasoning-effort overrides

`provider` and `model` SHALL be independent opaque strings at call, config-file, and agent-definition levels. Call-level `provider`, `model`, and `reasoningEffort` fields SHALL be optional literal overrides. Callers SHALL omit them for normal dispatch and inheritance. For call-level provider and model values, validation SHALL trim surrounding whitespace and SHALL reject a value that is empty after trimming. A case-insensitive `default`, `inherit`, or `auto` placeholder SHALL coerce to omitted with a repair note, and resolution SHALL continue at the next lower layer. Validation SHALL preserve all other internal content. A rejected override SHALL prevent every child from starting and explain that omitting the field selects inherited configuration.

Per field, provider and model resolution SHALL fall through call-level value, then the config file's `[agents.<name>]` section, then the agent definition, then the config file's `[defaults]` section, then the parent session's active provider and model, when the parent exposes them. A value at a higher layer SHALL override only the corresponding lower-layer value. Effective values SHALL map directly to Tau's separate `--provider` and `--model` flags; values absent at every level SHALL omit their flags. The extension SHALL NOT split combined values or infer a provider from a slash-containing model identifier.

`reasoningEffort` SHALL resolve at call, then config-file `[agents.<name>]`, then agent-definition, then config-file `[defaults]` precedence, then SHALL fall back to the parent session's active thinking level by default, so unpinned children inherit it. `reasoningEffort` SHALL use the same trimming and placeholder coercion as `provider` and `model`. The effective level SHALL be mapped to the generated child extension described under child invocation and recorded as `reasoningEffort` on the child result. Invalid call values SHALL be rejected before child startup; invalid agent-definition values SHALL skip that definition with a diagnostic; invalid config-file values SHALL be dropped with a config diagnostic. When no level resolves, the child runs at its ambient level and no thinking extension is generated.

The task schema, always-visible prompt guidance, and README SHALL identify all three fields as optional literal overrides. They SHALL tell callers to omit the fields during normal calls and for inheritance, and state that a `default`, `inherit`, or `auto` placeholder is coerced to omitted with a repair note. Provider guidance SHALL require an exact configured provider name from `tau providers`. Model guidance SHALL require an exact model ID supported by the selected provider. Reasoning guidance SHALL list `off`, `minimal`, `low`, `medium`, `high`, and `xhigh`.

#### Scenario: Placeholder coerces to omitted

- GIVEN a call passes `Default` with surrounding whitespace as `provider`
- WHEN validation runs
- THEN the value is treated as omitted
- AND a repair note states the coercion
- AND resolution continues at the next lower layer

#### Scenario: Reasoning-effort placeholder coerces

- GIVEN a call passes `AUTO` as `reasoningEffort`
- AND no config-file or agent-definition reasoning value resolves
- WHEN validation runs
- THEN the value is treated as omitted with a repair note
- AND the effective level resolves down to the parent session's thinking level

#### Scenario: Exact literal override

- GIVEN a task call passes `provider: " openai "` and `model: " vendor/model name "`
- WHEN request validation runs
- THEN `openai` and `vendor/model name` reach child configuration
- AND validation changes no other content

#### Scenario: Whitespace-only override fails closed

- GIVEN a call passes only whitespace as provider or model
- WHEN validation runs
- THEN no child starts
- AND content explains that omitting the field selects inherited configuration
- AND content states that the field requires a non-empty string

#### Scenario: Override guidance states coercion

- GIVEN a caller reads the task schema, always-visible prompt guidance, and README override documentation
- WHEN the caller selects an override
- THEN each source identifies provider, model, and reasoningEffort as optional literal overrides
- AND each source tells the caller to omit the fields during normal calls and for inheritance
- AND each source states that a `default`, `inherit`, or `auto` placeholder is coerced to omitted with a repair note
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

For every result that starts a child, final `content` SHALL be the task result envelope of the Task result envelope requirement. The tool SHALL NOT produce the previous single-child message form or the multi-child section form. A fail-closed result SHALL carry the teach-back as its content, no envelope, an empty `results` array, and no `planned` field, because no child starts.

Details SHALL be JSON with `schemaVersion: 2`, scope, project agent directory, discovery diagnostics, and ordered child results, and SHALL contain no `mode` or `step` fields; non-empty subagent-config file paths and diagnostics SHALL be included as `configPaths` and `configDiagnostics`; a result that starts or attempts a child SHALL carry `planned` with the value 1, and renderers SHALL fall back to the result count when `planned` is absent. Details SHALL keep the one-element `results` array: a child-starting result's `results` holds exactly one entry whose `taskId` equals the envelope `id`. Each child result SHALL contain `agent`, `agentSource`, the additive `taskId` (the child's Tau session id; a pre-session failure entry SHALL carry no `taskId`), effective `task` and `cwd`, `exitCode`, complete accepted wire `messages`, `stderr`, usage fields, `status`, `timedOut`, `cancelled`, and `malformedJsonLines`; applicable `provider`, `model`, `reasoningEffort`, `stopReason`, and `errorMessage` fields SHALL also be included. Failure SHALL be represented through content and these fields because Tau tool results have no portable `isError` property.

#### Scenario: Envelope replaces the prior content forms

- GIVEN a successful fresh child with a final assistant message
- WHEN `task` returns
- THEN content is the envelope with the child session id and state `completed`
- AND no counts line or per-child section appears
- AND details retain every accepted child message

#### Scenario: Fail-closed result shape

- GIVEN a call fails validation
- WHEN the result is built
- THEN content is the teach-back
- AND content carries no envelope
- AND `results` is empty
- AND `planned` is absent

#### Scenario: Failed child without final text

- GIVEN exactly one child fails without final text
- WHEN `task` returns
- THEN the `task_error` tag wraps the OpenCode failure form with the child session id
- AND details retain the child's partial messages and error fields

#### Scenario: Recoverable startup failure

- GIVEN one child fails before it emits a valid assistant message
- AND the bounded cleaned stderr excerpt identifies an invalid provider or model
- WHEN `task` returns
- THEN the `task_error` body includes the Tau diagnostic and matching recovery instruction
- AND structured details retain complete stderr

#### Scenario: Semantic status versus process outcome

- GIVEN a child exits cleanly and reports `BLOCKED`
- WHEN result details are built
- THEN its semantic status is `BLOCKED`
- AND its process outcome can still be successful

#### Scenario: Details carry planned and taskId

- GIVEN a completed fresh child
- WHEN the details are inspected
- THEN `schemaVersion` is 2
- AND `results` holds one entry whose `taskId` equals the envelope `id`
- AND `planned` is 1

#### Scenario: Pre-session failure details

- GIVEN a child fails before Tau creates its session
- WHEN the details are inspected
- THEN the entry carries no `taskId`
- AND `planned` is 1

### Requirement: Progress, cancellation, timeout, and cleanup

The extension SHALL emit portable partial results after each accepted assistant or tool-result message of the child and after child completion. A partial result SHALL carry `planned` with the value 1. A partial result's content SHALL carry the `<done>/<planned> done` progress form with the single child: `<done>/1 done`.

Each child SHALL default to a 3600-second timeout and accept a positive call override no greater than 10800. Cancellation or timeout SHALL terminate the process, wait no more than five seconds, kill it if necessary, preserve partial messages and stderr, and prevent queued work from starting. A hard cancellation of the task executing the dispatch (for example a print-mode SIGINT) SHALL kill any running child process so no child outlives the dispatch. Every temporary prompt, profile policy file, and thinking-policy file SHALL be removed on success and all failure paths.

#### Scenario: Partial updates for one child

- GIVEN a child emits an accepted assistant or tool-result message
- WHEN the update callback runs
- THEN it receives `<done>/1 done` content and schema-versioned partial details with `planned` 1

#### Scenario: Timeout override at the cap

- GIVEN a call passes `timeoutSeconds: 10800`
- WHEN the child runs
- THEN the override is accepted and bounds the child

#### Scenario: Timeout override above the cap

- GIVEN a call passes `timeoutSeconds: 10801`
- WHEN validation runs
- THEN no child starts

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

Any child count SHALL render as one frame: a counts headline (`task · <succeeded>/<total> succeeded` with running/failed/pending clauses when positive, icon `…` while any child runs, else `✗` when any failed, else `✓`) followed by one self-contained child component per child in input order: a header, the streamed work (collapsed: the newest items with a truncation hint; expanded: the full stream), status icons/hints, error, delegated task, and usage counters. A `Total:` aggregate usage line SHALL appear only when more than one child exists. The call label SHALL be the `description` value when it is non-empty after trimming, and the effective `subagent_type` otherwise. The call label SHALL NOT derive from the task count. Rendering SHALL distinguish in-flight children (process not yet reaped) from succeeded and failed ones and SHALL map semantic status to icons (`DONE` ✓, `DONE_WITH_CONCERNS` ⚠, `BLOCKED` ✗, `NEEDS_CONTEXT` ?). Because Tau re-renders the tool row after every accepted child message, expanded and collapsed views SHALL update live from the same details payload. Rendering SHALL NOT add or change parent-model content.

#### Scenario: Call label from the description

- GIVEN a call with `description: "Review auth"` and effective `subagent_type` `code-review`
- WHEN the result renders
- THEN the call label is `Review auth`

#### Scenario: Call label falls back to the agent name

- GIVEN a call whose `description` is only whitespace
- WHEN the result renders
- THEN the call label is the effective `subagent_type`

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

### Requirement: Catalog-based subagent cost estimation

The extension SHALL estimate a USD cost for each accepted child assistant message from Tau's built-in provider catalog rates, using that message's provider, model, and token usage. Prompt tokens SHALL include fresh, cached, and cache-written tokens, and the message's own request size SHALL select the catalog cost tier. One-hour cache-write tokens SHALL be priced at the catalog's one-hour cache-write rate when the catalog distinguishes one-hour writes. A message is priced from the catalog when the estimator applies catalog rates to it. When the catalog has no entry for the message's provider and model, the extension SHALL use that message's provider-reported cost when it is non-zero. When neither source applies, the message SHALL contribute tokens but no cost. When both sources apply to one message, the child's two cost fields each SHALL accumulate their own contribution. Each child result SHALL carry its accumulated estimated cost as an additive usage field serialized as `estimatedCost`. No existing usage field, token total, status, or result content SHALL change because of estimation. The tool's rendered per-child usage line and `Total:` aggregate line SHALL show the combined reported and estimated cost of the child or of all children when it is above zero. The rendered cost SHALL keep the line's existing cost format and SHALL carry the `~` estimate mark before the amount when any estimated cost contributes to it. These lines SHALL NOT carry the incompleteness mark. When the estimator is unavailable or fails for a message, the extension SHALL skip estimation for that message and continue with reported-cost and token accounting unchanged.

The estimator is imported through a guarded seam. Estimates are API-rate equivalents of the catalog rates, matching the meaning of the parent usage section's estimate marker.

#### Scenario: Priced message
- GIVEN a child assistant message whose provider and model exist in the built-in catalog with rates
- WHEN the runner collects the message
- THEN the child's estimated-cost usage field increases by the catalog price of that message's token breakdown

#### Scenario: Per-request tier selection
- GIVEN a catalog model prices prompt tokens above a size threshold at a different rate
- WHEN a child emits two messages whose prompt sizes fall on opposite sides of the threshold
- THEN each message is priced at its own request's tier

#### Scenario: One-hour cache-write pricing split
- GIVEN a catalog that prices one-hour cache writes above other cache writes
- WHEN the runner collects two messages with equal prompt totals but different one-hour and shorter-write splits
- THEN each message is priced at its own split

#### Scenario: Priced message ignores reported cost
- GIVEN a catalog-priced message that also carries a non-zero provider-reported cost
- WHEN the runner collects the message
- THEN the child's estimated-cost usage field increases by the catalog price of that message's token breakdown
- AND the child's reported-cost usage field increases by the reported amount

#### Scenario: Unpriced provider with reported cost
- GIVEN a message whose provider and model are absent from the catalog
- AND the message carries a non-zero provider-reported cost
- WHEN the runner collects the message
- THEN the child's estimated-cost usage field does not change
- AND the child's reported-cost usage field increases by the reported amount

#### Scenario: Unpriced provider without reported cost
- GIVEN a message whose provider and model are absent from the catalog
- AND the message carries no provider-reported cost
- WHEN the runner collects the message
- THEN the message contributes its tokens to the child's usage
- AND neither cost field changes

#### Scenario: Additive details field
- GIVEN a completed child with estimated cost
- WHEN the task details are inspected
- THEN the child's usage contains the `estimatedCost` field
- AND every previously existing usage field equals the same call without estimation

#### Scenario: Rendered usage line shows estimated cost
- GIVEN two completed children with non-zero token usage whose messages were priced from the catalog
- WHEN the tool result renders
- THEN each per-child usage line shows that child's combined cost with the `~` prefix
- AND the `Total:` aggregate line shows the children's combined cost with the `~` prefix

#### Scenario: Rendered usage line reported-only cost
- GIVEN two completed children whose only cost contribution is provider-reported
- WHEN the tool result renders
- THEN each per-child usage line shows the cost without the `~` prefix
- AND the `Total:` aggregate line shows the cost without the `~` prefix

#### Scenario: Estimator unavailable
- GIVEN the estimator seam is missing or raises for a message
- WHEN the runner collects the message
- THEN the child still reports its token totals and any reported cost
- AND no error propagates to the task result

#### Scenario: Partial usage keeps estimates
- GIVEN a child times out or is cancelled after emitting priced messages
- WHEN its result finalizes
- THEN the accumulated estimated cost for those messages remains on the child result

### Requirement: Session-scoped subagent usage aggregation

The extension SHALL accumulate each child result's reported token usage, reported cost, and estimated cost into session-scoped totals across task calls. A run SHALL have a determinable cost when at least one of its accepted messages is priced from the catalog or carries a non-zero provider-reported cost. The totals SHALL count an unpriced run: a run that reports non-zero token usage and has no determinable cost. Live partial results SHALL update an in-flight snapshot of the current call's children that replaces the call's previous snapshot. Committing a call's final result SHALL fold it into the committed totals exactly once and SHALL clear that call's in-flight snapshot. A call that ends without a final result being committed SHALL discard that call's in-flight snapshot. The displayed totals at any moment SHALL equal the committed totals plus the latest in-flight snapshot of every active call; concurrent calls SHALL keep separate in-flight snapshots. A run SHALL be a child result that reports non-zero token usage or has a determinable cost. Children whose results report no token usage and have no determinable cost SHALL contribute nothing, including the run count. The accumulation SHALL reset to zero when the active session rebinds to a new, resumed, or branched session. The aggregation SHALL NOT alter task result content, details, statuses, token totals, or any per-child usage field other than the additive estimated-cost field introduced by the estimation requirement, and SHALL NOT alter the tool's portable rendering beyond the rendered cost segment the estimation requirement adds to the per-child usage lines and the `Total:` line.

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
- GIVEN a child never started or reports no token usage and has no determinable cost
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

#### Scenario: Aggregation leaves existing fields unchanged
- GIVEN a task call completes while aggregation and estimation are active
- WHEN the task result, its details, and its per-child usage fields are inspected
- THEN they equal the same call with aggregation and estimation disabled
- AND the additive `estimatedCost` field is the only new usage content

#### Scenario: Estimated cost accumulates across calls
- GIVEN two sequential calls complete with catalog-priced children in the same session
- WHEN the totals are read
- THEN the estimated-cost share equals the sum of both calls' child estimates

#### Scenario: Unpriced runs are counted
- GIVEN a catalog-priced child and a child with token usage but neither catalog rates nor reported cost
- WHEN the totals are read
- THEN the combined cost equals the priced child's cost
- AND the unpriced-run count is one

### Requirement: Sidebar subagent usage section

In a frontend that shows a sidebar summary, the extension SHALL display the current totals (committed plus in-flight) in a `subagents` section positioned immediately below the `usage` section. The section SHALL be omitted when no child reports non-zero token usage and no child has a determinable cost. When the summary contains no `usage` section, the `subagents` section SHALL NOT be injected. The section SHALL present the number of runs and the accumulated input, output, and cost using the same token and cost formatting as the `usage` section, where input SHALL include cached and cache-written tokens as the `usage` section's input does. The section SHALL show a cost value only when at least one run has a determinable cost. The displayed cost SHALL be the sum of reported and estimated cost. A run is estimated from catalog rates when at least one of its accepted messages is priced from the catalog. The cost SHALL carry the estimate marker when at least one run with a determinable cost is estimated from catalog rates, regardless of the estimated amount, and it SHALL carry the incompleteness marker when at least one run is unpriced. The estimate marker SHALL be the `~` prefix, and the incompleteness marker SHALL be the trailing `+`. A run's tokens and run count SHALL be unaffected by its cost being undeterminable. The section SHALL NOT appear in the narrow-layout session summary. Whenever the sidebar summary is rebuilt, the section SHALL reflect the latest committed or in-flight totals.

Tau 0.3 exposes no public sidebar content extension point (the sidebar summary is built by core from session stats), so the display wraps `tau_coding.tui.widgets._build_sidebar_content`, the one function through which every sidebar summary is constructed, and splices the section below the usage section. The seam is version-guarded: when any expected part is missing or a build fails, the original summary is returned unchanged. Mid-run display updates on the sidebar's normal rebuild cadence; a live per-message refresh of subagent totals is intentionally not provided.

#### Scenario: Rebuild shows the section
- GIVEN a completed call whose children include one with a determinable cost
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
- GIVEN no child reports non-zero token usage and no child has a determinable cost
- WHEN the sidebar summary is rebuilt
- THEN no `subagents` section appears

#### Scenario: Estimated cost shown
- GIVEN at least one run's cost is estimated from catalog rates and no run is unpriced
- WHEN the `subagents` section renders
- THEN the cost appears with the `~` prefix and without the trailing `+`

#### Scenario: Incomplete cost marked
- GIVEN at least one run's cost is estimated from catalog rates and at least one run is unpriced
- WHEN the `subagents` section renders
- THEN the cost appears with the `~` prefix and the trailing `+`
- AND the displayed cost equals the sum of the reported and estimated cost of the runs with a determinable cost

#### Scenario: Reported cost with unpriced run
- GIVEN every determinable cost is provider-reported and at least one run is unpriced
- WHEN the `subagents` section renders
- THEN the cost appears with the trailing `+` and without the `~` prefix

#### Scenario: Reported-only cost unmarked
- GIVEN every determinable cost is provider-reported and no run is unpriced
- WHEN the `subagents` section renders
- THEN the cost appears without the `~` prefix and without the trailing `+`

#### Scenario: Cost omitted when undeterminable
- GIVEN children reported token usage but no run has a determinable cost
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

### Requirement: Task result envelope

For every result that starts a child, the model-facing content SHALL be one envelope of the form `<task id="<taskId>" state="completed|error">`. The envelope SHALL wrap one inner `task_result` or `task_error` tag. The `taskId` SHALL be the child's Tau session id. The envelope state SHALL be the process outcome only. `completed` SHALL mean that the child finished and delivered a final assistant message, whatever status marker that message carries inside its text. `error` SHALL mean that the child failed, was cancelled, timed out, or ended with no final assistant message. Child status markers (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`) SHALL stay inside the message text and SHALL NOT change the envelope state.

A successful child SHALL wrap its complete final assistant message in `task_result`. A final assistant message without text SHALL wrap the placeholder `(no output)`. A child in the `error` state SHALL wrap its final assistant message in `task_error`. When no final message exists, the `task_error` tag SHALL wrap the OpenCode failure form `Subagent failed (task_id: <id>): <error>`. In that form, `<id>` is the effective child session id, so it is the fresh id after a fallback.

A pre-session failure is a call that fails before Tau creates the child session. The causes are a process startup failure, a cancellation before startup, or an interactive project-approval denial. A pre-session failure SHALL carry state `error` with no `id` attribute, and its `task_error` tag SHALL wrap the startup, cancellation, or denial error text.

Repair notes SHALL appear as `Note:` lines before the envelope. The inner content SHALL be the child message verbatim with no escaping. The `id` and `state` attributes SHALL carry the semantics. The envelope tags SHALL be informational.

#### Scenario: Completed envelope
- GIVEN a fresh child finishes and delivers a final assistant message
- WHEN the result content is built
- THEN the content is one envelope with state `completed` and the envelope `id` equal to the child session id
- AND the `task_result` tag wraps the complete final assistant message

#### Scenario: Error envelope with a final message
- GIVEN a child times out after it emitted a final assistant message
- WHEN the result content is built
- THEN the envelope state is `error`
- AND the `task_error` tag wraps the complete final assistant message
- AND the envelope `id` is the child session id

#### Scenario: Error envelope without a final message
- GIVEN a child fails with no final assistant message
- WHEN the result content is built
- THEN the envelope state is `error`
- AND the `task_error` tag wraps `Subagent failed (task_id: <id>): <error>` with the child session id

#### Scenario: Status marker keeps the envelope state
- GIVEN a child exits cleanly and its final message ends with the `BLOCKED` marker
- WHEN the envelope is built
- THEN the envelope state is `completed`
- AND the marker stays inside the wrapped message text

#### Scenario: Final message without text
- GIVEN a successful child whose final assistant message has no text
- WHEN the envelope is built
- THEN the `task_result` tag wraps `(no output)`

#### Scenario: Error final message without text
- GIVEN a child in the error state whose final assistant message has no text
- WHEN the envelope is built
- THEN the `task_error` tag wraps `(no output)`

#### Scenario: Repair note placement
- GIVEN a child-starting result carries a repair note
- WHEN the content is built
- THEN the note appears as a `Note:` line before the envelope

#### Scenario: Verbatim inner content
- GIVEN a child final message contains characters that look like markup
- WHEN the envelope is built
- THEN the inner content is the message text verbatim with no escaping

#### Scenario: Pre-session failure envelope
- GIVEN a child process fails to start
- WHEN the result content is built
- THEN the envelope state is `error` with no `id` attribute
- AND the `task_error` tag wraps the startup error text

#### Scenario: Interactive denial envelope
- GIVEN a requested name resolves to a project definition
- AND the session runs interactively
- WHEN the operator denies the approval request
- THEN the call cancels before any child starts
- AND the envelope state is `error` with no `id` attribute
- AND the `task_error` tag wraps the denial error text
- AND the details entry carries no `taskId` and `planned` is 1

#### Scenario: Cancellation before startup envelope
- GIVEN a call is cancelled before the child process starts
- WHEN the result content is built
- THEN the envelope state is `error` with no `id` attribute
- AND the `task_error` tag wraps the cancellation error text

### Requirement: task_id resume

A call with `task_id` SHALL resume that child session instead of creating one. A resume run SHALL launch a new child process against the existing session. The session SHALL retain its previous messages and tool outputs. The call's `prompt` SHALL be the new user turn. The result content SHALL relay the new final assistant message in an envelope whose `id` is the existing session's id.

`task_id` SHALL require `subagent_type` to name the agent whose prompt the resumed run uses. A call with `task_id` and no `subagent_type` SHALL fail closed with a teach-back that names both fields. The tool SHALL NOT record a per-session agent owner. A `task_id` resumed under a different `subagent_type` SHALL continue that session with the named agent's prompt and policies.

The runner SHALL regenerate the agent body prompt and the profile policy extensions for the resumed run. It SHALL apply the thinking policy, the overrides, and the recursion guard exactly as in a fresh run. The appended prompt SHALL use a resume variant of the isolation sentence. That variant states the session's own prior turns are the child's earlier work on this task. Effective provider, model, and reasoning effort SHALL resolve exactly as in a fresh call and SHALL apply to the resumed run. `timeoutSeconds` SHALL bound the resumed run. Usage in details SHALL cover the resumed run only. Only the new turn's events SHALL stream.

#### Scenario: Resume continues the child session
- GIVEN a prior child session with messages and tool outputs
- WHEN a call carries that `task_id`, a `subagent_type`, and a `prompt`
- THEN a new child process runs against the existing session
- AND the session keeps its earlier messages and tool outputs
- AND the content is the new final assistant message in a completed envelope with the same id

#### Scenario: Resume requires subagent_type
- GIVEN a call carries `task_id` and no `subagent_type`
- WHEN validation runs
- THEN no child starts
- AND the teach-back names `task_id` and `subagent_type`

#### Scenario: Resume under a different agent
- GIVEN a child session started with one agent
- WHEN a call resumes it with a different `subagent_type`
- THEN the resumed run uses the named agent's body prompt and policies

#### Scenario: Resume prompt uses the resume variant
- GIVEN a resumed run
- WHEN the appended prompt is built
- THEN the isolation sentence states the session's own prior turns are the child's earlier work on this task

#### Scenario: Resume overrides and timeout apply
- GIVEN a resume call carries `provider`, `model`, and `timeoutSeconds`
- WHEN the resumed child launches
- THEN the resolved provider and model apply to the resumed run exactly as in a fresh call
- AND `timeoutSeconds` bounds the resumed run

#### Scenario: Resume usage covers the resumed run
- GIVEN a resumed child completes
- WHEN its details usage is read
- THEN the usage covers the resumed run only

### Requirement: Resume working directory

A resumed run SHALL use the session's recorded creation cwd as its working directory. The call's `cwd` SHALL NOT relocate a resumed run. A resume call whose session verification passes and that carries `cwd` SHALL get a repair note that states the resumed run uses the session's recorded cwd. The store record SHALL keep its creation cwd.

#### Scenario: Resume cwd is the recorded cwd
- GIVEN a child session created in one directory
- WHEN a resume call carries a different `cwd`
- THEN the resumed child runs in the session's recorded creation cwd
- AND the result carries the repair note about the recorded cwd

#### Scenario: Store record keeps creation cwd
- GIVEN a resumed run completed
- WHEN the session record is read
- THEN the recorded creation cwd is unchanged

### Requirement: Resume authorization model

Resume authorization SHALL be possession-based. Possession of the `task_id` SHALL authorize the resume. The tool SHALL NOT add per-caller authorization and SHALL NOT add access auditing. A call from any parent session SHALL resume any child session named by its `task_id`, including a parent in a different project. The same-id lock SHALL coordinate task-tool calls only.

The accepted prevention for cross-account exposure is the single-user deployment. A direct resume of a child session by another process is not prevented by the same-id lock. The operator accepts both exposures. The store's file permissions are the operating system's defaults. Tau establishes no permission contract.

#### Scenario: Cross-project resume proceeds
- GIVEN a child session created under one project
- WHEN a parent session in a different project resumes it with its `task_id`
- THEN the resume proceeds like any other resume

#### Scenario: Lock scope is task calls
- GIVEN a task call holds the same-id lock for a session
- WHEN another process resumes that session directly through Tau
- THEN the direct resume is not prevented by the task tool's lock

### Requirement: Unknown task_id fallback

Before resuming, the tool SHALL verify through the Tau session store that the session exists and that its recorded role is the subagent role. A call whose `task_id` matches no session SHALL start a fresh child with a new session id. Its result SHALL carry a repair note that states the id matched no session. A `task_id` that matches a session whose recorded role is not the subagent role SHALL also start a fresh child with a new session id. Its repair note SHALL state that the session is not a task child. A fallback fresh child SHALL follow the fresh-run rules. A fallback child that fails with no final message SHALL produce the OpenCode failure form with the fresh session id.

A resumed child whose Tau invocation fails with a cleaned stderr excerpt matching `Unknown session:` case-insensitively SHALL retry once as a fresh child with a new session id. The retry SHALL run the call's prompt. The retry's result SHALL carry the repair note that states the id matched no session, and its envelope `id` SHALL name the fresh session id. Any other resumed-run failure SHALL surface through the existing error paths with no retry.

#### Scenario: Unknown session falls back
- GIVEN a `task_id` that matches no session in the store
- WHEN the call runs
- THEN a fresh child starts with a new session id
- AND the result carries a `Note:` line that states the id matched no session
- AND the note appears before the envelope

#### Scenario: Non-subagent session falls back
- GIVEN a `task_id` that names a session whose recorded role is not the subagent role
- WHEN the call runs
- THEN a fresh child starts with a new session id
- AND the repair note states that the session is not a task child

#### Scenario: Fallback failure names the fresh id
- GIVEN a fallback fresh child fails with no final message
- WHEN the error envelope is built
- THEN the OpenCode failure form names the fresh session id

#### Scenario: Runtime unknown-session failure falls back
- GIVEN a resume call whose session verification passed
- WHEN the resumed child's Tau invocation fails with a stderr excerpt matching `Unknown session:`
- THEN the runner retries once as a fresh child with a new session id
- AND the fresh child runs the call's prompt
- AND the result carries a `Note:` line that states the id matched no session
- AND the envelope `id` names the fresh session id

#### Scenario: Other resume failures follow the error paths
- GIVEN a resumed child's Tau invocation fails with a stderr excerpt that does not match `Unknown session:`
- WHEN the result is built
- THEN the failure surfaces through the existing error paths
- AND no fresh-child retry starts

### Requirement: Pinned child sessions

Every fresh run SHALL create a pinned child session. The tool SHALL generate a new session id for every fresh child. The tool SHALL record it as the child's `taskId` on the child result, in the details entry, and as the envelope `id`. The child session SHALL carry the subagent role, so it stays out of the default `tau sessions` listing and lists under `tau sessions --all`. The runner SHALL record the id for every fresh-child attempt, including an attempt that fails after startup. When tau never persisted the session record, a later resume with that id SHALL fall back per the Unknown task_id fallback requirement.

Child sessions accumulate in the Tau session store with no retention. The accepted recovery for unwanted child sessions is manual store maintenance while no tau process uses the store. The store root is `~/.tau/sessions/`, with one directory per parent project, one `index.jsonl` per project directory, and one `<session-id>.jsonl` transcript per session. Each index line records the session's `id` and its transcript `path`. The maintenance steps:

1. Find the child's line by `id` in the project `index.jsonl` files under the store root.
2. Stop the tau processes that use the store.
3. Delete the transcript file that the line's `path` names.
4. Delete the child's line from that `index.jsonl`.
5. Verify with `tau sessions --all` that the child no longer lists.

The store manager guards index updates with a process lock and atomic replacement, so editing a quiescent store avoids the race.

#### Scenario: Fresh child session id
- GIVEN a fresh call
- WHEN the child starts
- THEN the child runs in a new pinned session
- AND the child result, the details entry, and the envelope `id` carry that session id as `taskId`

#### Scenario: Child session listing
- GIVEN a completed child session
- WHEN the session listings run
- THEN `tau sessions --all` lists the session
- AND the default `tau sessions` listing omits it

#### Scenario: Failed attempt still records the id
- GIVEN a fresh child that fails after startup
- WHEN the result is built
- THEN the result records the generated session id

#### Scenario: Recovery removes the session
- GIVEN the operator deletes a child's transcript file and its `index.jsonl` line while no tau process uses the store
- WHEN a later call resumes that id
- THEN the id matches no session
- AND the call starts a fresh child with the repair note that the id matched no session

### Requirement: Concurrent task calls

Several `task` calls in one assistant message SHALL run concurrently. Each call SHALL be validated, approved, and dispatched independently. The tool SHALL set no cap on the number of `task` calls in one message. Each result SHALL carry its own envelope. One call's failure SHALL NOT stop the others.

#### Scenario: Parallel dispatch
- GIVEN two `task` calls in one assistant message
- WHEN both run
- THEN both children are active in parallel
- AND each result carries its own envelope

#### Scenario: Independent failure
- GIVEN two `task` calls in one message and one child fails
- WHEN both finish
- THEN the failed call carries its error envelope
- AND the other result is intact

#### Scenario: No call cap
- GIVEN an assistant message with three `task` calls
- WHEN dispatch runs
- THEN all three calls dispatch their children

### Requirement: Same-task_id exclusion

Two concurrent calls that carry the same `task_id` SHALL NOT both run. Exactly one SHALL start its child. The other SHALL fail closed with a teach-back that names the same-id conflict. The losing call's result SHALL carry the fail-closed result contract of the Content envelope and complete details requirement. The exclusion SHALL be process-safe: a lock keyed by `task_id` SHALL coordinate parent processes on the machine that hosts the session store.

#### Scenario: Same-id pair in one message
- GIVEN two `task` calls in one message carry the same `task_id`
- WHEN both run
- THEN one result carries the child envelope
- AND the other result is a fail-closed teach-back that names the same-id conflict
- AND the losing result carries no envelope, an empty `results` array, and no `planned` field

#### Scenario: Cross-process same-id exclusion
- GIVEN two parent processes on the machine that hosts the session store
- WHEN both dispatch a call with the same `task_id`
- THEN exactly one child starts
- AND the other call fails closed

### Requirement: Tool description roster

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

#### Scenario: Roster line format
- GIVEN the bundled definitions
- WHEN the roster renders
- THEN the `general-purpose` line reads `- general-purpose: <description> (Tools: all)`
- AND the `read-only` line renders `Tools: read`
- AND the `code-review` line renders `Tools: read, bash`

#### Scenario: Annotation follows the resolved definition
- GIVEN a user definition shadows a bundled name and carries the `review` profile
- WHEN the roster renders
- THEN that line renders `Tools: read, bash`

#### Scenario: Default rule and when-not-to-use
- GIVEN the tool description
- WHEN a reader reads it
- THEN it contains the sentence that omitting `subagent_type` selects `general-purpose`
- AND it contains a when-not-to-use section

#### Scenario: Usage notes present
- GIVEN the tool description
- WHEN a reader reads the usage notes
- THEN the notes state the multi-call parallelism rule
- AND the notes state the `task_id` reuse rule
- AND the notes state the verification-statement rule

#### Scenario: Roster scope at session start
- GIVEN project agents exist and a session starts
- WHEN the roster is built
- THEN the roster lists the bundled and user agents discovered at session start
- AND the roster names no project agent

#### Scenario: Discovery failure falls back to bundled
- GIVEN user-layer discovery fails at session start
- WHEN the roster is built
- THEN the roster lists the bundled agents

#### Scenario: Teach-back roster excludes project agents
- GIVEN a teach-back that lists agents
- WHEN it renders
- THEN it lists the same bundled and user agents as the description roster
- AND it names no project agent

## Intentional Port Differences

The current Tau implementation uses the lowercase `task` tool name and provides one flat single-object task interface with pinned child sessions, `task_id` resume, one task envelope per child-starting result, complete details, timeout, and cancellation. These differences from the historical pre-Tau implementation are intentional:

| Historical capability | Current Tau behavior |
| --- | --- |
| Three dispatch modes | One flat call: exactly one task per `task` call; parallel work uses several `task` calls in one message under Tau's parallel tool scheduling |
| Sequential output substitution | Removed; conditional sequences use separate calls so the controller can inspect each result |
| Summary/review-section extraction | Removed; content is one task envelope wrapping the child's complete final assistant message, with complete accepted messages retained in `details` |
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
- Parent-model content is one task envelope around the child's complete final assistant message only — tool calls, thinking, and earlier messages are never relayed. Complete accepted messages always remain in `details` and may appear in expanded rendering.
- Installing or explicitly loading the extension executes Python with the same account privileges as Tau; users must inspect code and use external sandboxing or restricted credentials when stronger isolation is required.
