# Proposal: OpenCode-aligned task interface

Selected workflow depth: High-risk.

Terms used throughout: a teach-back is a rejection or repair tool result whose content names the valid values and the exact next step. Fail closed means the tool rejects the call and starts no child. A child is one isolated Tau subagent process. A child session is the Tau session that backs one child. An eligible agent is any agent the discovery roster returns for the resolved `agentScope`: the bundled agents plus user-directory and project-directory agents. A profile is an agent-definition field with the value `general-purpose`, `read-only`, or `review`, and it selects the child's tool policy. The `general-purpose` profile registers no policy extension, so every Tau tool is available. The `read-only` profile permits the `read` tool only. The `review` profile permits the `read` tool plus instruction-governed `bash`. A tool-policy annotation is a roster line's `Tools: <policy>` label, rendered from the profile. A profile policy extension is the generated child extension that enforces that policy on the child's tool-call events. The extension adds no OS-level isolation. The current guidance is the existing tool description's dispatch-threshold language, its prohibition sentences, and its prompt-guideline sentences. Required Outcome 3 enumerates the retained rules.

## Intent

Models arrive at the `task` tool with training data from four harnesses. Claude Code, ZCode, Codex, and OpenCode all dispatch one agent per call with a flat argument object. OpenCode even names the tool `task`, like ours. The recorded session data shows the result. The most common invalid first call is a flat object. The first dispatch fails on the majority of sessions.

This change makes the flat single-object form the only form. Field names unify to the OpenCode vocabulary. The tool adopts the OpenCode result envelope. The tool also adopts OpenCode's resumable subagent sessions. Every child runs in a pinned Tau session. The result names its `task_id`. A later call can continue that same child session instead of starting a fresh one. The recorded `{agent, task}` key names stay invalid. Their recovery is the unknown-field teach-back, which names the unknown fields and shows one valid flat example.

## Evidence

- Operator-attested input, not re-derivable from the repository: session recordings on this machine show 284 recorded `task` calls. 43 of them used a flat `{agent, task}` object. 1 placed `timeoutSeconds` inside an item. The first dispatch failed on the majority of observed sessions. The recordings are sandbox session logs and carry no stable path. Treat the counts as operator-attested motivation, not as repository evidence.
- Immutable upstream-source snapshots under `docs/design/evidence/opencode-task-interface/`. That directory's `SOURCES.md` records the upstream identities, pinned commits, retrieval date, and SHA-256 checksums:
  - OpenCode `task` tool (`anomalyco/opencode`, branch `dev`, commit `fe3f3a4`): `opencode/task.ts`, `opencode/task.txt`, `opencode/registry.ts`
  - Claude Code `Agent` tool (`@anthropic-ai/claude-code` 2.1.276): `claude-code/sdk-tools.d.ts`
  - ZCode `Agent` tool (`zcode-app-cli` 3.12.3-26, `vendor/zcode.cjs`): the byte-range excerpt `zcode/zcode-agent-tool-excerpt.cjs` plus the full-bundle checksum
  - Codex `spawn_agent` (`openai/codex`, branch `main`, commit `639d247`): `codex/multi_agents_spec.rs`

  All four dispatch one agent per call with a flat argument object. OpenCode names the tool `task`, resumes subagent sessions through a `task_id` that is the child session id, and gates background dispatch behind an experimental flag.
- Tau capability evidence, recorded in the immutable transcript `docs/design/evidence/opencode-task-interface/tau-capability/transcript.txt`. The transcript was captured against the installed Tau CLI. It records each command with its complete output and exit code:
  - `tau --session-id <id>` pins the session id of a new print-mode session. `--session-role subagent` tags that session out of the default `tau sessions` listing, and `tau sessions --all` lists it.
  - `tau --session <id>` resumes a session in print mode. The resumed JSON stream carries only the new turn's messages, and the resumed assistant usage confirms the prior turns were loaded as context.
  - A resumed run honors changed settings: the transcript's resumed-run section proves a session created with `z-ai/glm-5.3-flash` resumed under `z-ai/glm-5.3`, and the complete raw stream in `tau-capability/resume-changed-model.raw.jsonl` records the new model in every event.
  - `tau --session <missing-id>` exits with code 2 and prints `Unknown session: <id>` on stderr. This is a detectable clean failure.
  - The transcript does not separately exercise a changed `--cwd`, the regenerated system-prompt append, or the profile and thinking policy extensions on a resumed run. Those behaviors reuse the fresh run's argv and prompt construction, per the Resume paragraph in Approach. The implementation adds tests that exercise them on a resumed run.
- Concurrency evidence: Tau's `AgentTool.execution_mode` defaults to `"parallel"` (`tau_agent/tools.py`), so Tau schedules several `task` calls of one assistant message concurrently. This evidence establishes the scheduling default only. Same-session write safety is a change requirement, covered by the same-id rejection of Required Outcome 7. The dispatcher, runner, and usage tracker hold no per-call mutable state that two concurrent dispatches share. The tracker (`usage.py`) keys by tool-call id, and the runner keeps run state method-local.
- Material baseline discrepancy and its resolution: the living spec requires rejecting the `default`, `inherit`, and `auto` placeholder overrides, while `dispatch.py` coerces them to omitted with a repair note. This change keeps the coercion behavior, because the placeholder intent is unambiguous and coercion keeps the dispatch alive. The finishing-stage living-spec sync updates the spec to the coercion rule.
- Living spec: `docs/specs/subagent-dispatch.md`. Synchronization happens in the finishing stage per the workflow.

## Required Outcomes

1. The tool takes exactly one task per call. The options and their semantics:

   - `prompt`: required non-empty string. The child's task.
   - `subagent_type`: optional non-empty string naming an eligible agent. Omission selects `general-purpose`. A name that no eligible agent provides fails closed with a teach-back.
   - `description`: optional string. Display label only, with no behavioral effect.
   - `task_id`: optional. A present value must be a string and non-empty after trimming, or the call fails closed with a teach-back. No format check exists beyond that. A well-formed value that matches no session falls back per Required Outcome 6.
   - `cwd`: optional string directory path. Omission resolves to the parent session cwd. A relative path resolves against the parent session cwd. Any path, absolute or relative, expands `~` and is then resolved canonically to an absolute path.
   - `agentScope`: one of `user`, `project`, `both`. It selects the agent layers: the bundled layer always applies. `user` adds the user agents directory `~/.tau/agents`. `project` adds the nearest ancestor directory `.tau/agents` found walking up from the parent session cwd. `both` adds both. On a name collision, a later layer replaces an earlier one: project replaces user, and user replaces bundled. Omission selects `user`. Another value fails closed.
   - `confirmProjectAgents`: boolean. Omission selects `true`.
   - `provider` and `model`: optional literal string overrides. Validation trims surrounding whitespace and rejects a value empty after trimming. A case-insensitive `default`, `inherit`, or `auto` placeholder coerces to omitted with a repair note. Resolution order is the call value, then the config-file `[agents.<name>]` section, then the agent definition, then the config-file `[defaults]` section, then the parent session configuration. The `model` must be supported by the resolved provider.
   - `reasoningEffort`: one of `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, with the same trimming, placeholder coercion, and resolution chain, ending at the parent session's thinking level.
   - `timeoutSeconds`: number greater than 0 and at most 10800. Omission selects 3600.

   The config file referenced by these bullets is `superpowers-subagent.toml`. The runner reads the user file `~/.tau/superpowers-subagent.toml` and the nearest ancestor project file `.tau/superpowers-subagent.toml` from the parent session cwd. The sections `[defaults]` and `[agents.<name>]` are optional in each file, and they carry the `provider`, `model`, and `reasoningEffort` keys only. The two files merge per key, and the project file shadows the user file for the keys it sets. An unreadable file, invalid TOML, or an unknown key or section adds a config diagnostic and skips that item.
2. A call with an unknown field fails closed. The teach-back names the unknown fields, the eligible agents, and one valid flat example. `background` fails closed with a dedicated teach-back. Background dispatch is not supported in this harness. The result of a `task` call arrives when the child finishes. A fail-closed validation or approval result carries the teach-back as its content. It carries no envelope, an empty `results` array, and no `planned` field, because no child starts.
3. The tool description carries the agent roster with tool-policy annotations, the default selection rule, a when-not-to-use section, and usage notes in the OpenCode layout. The usage notes state these rules:

   - Several tasks are several `task` calls in one message.
   - Delegated work is not duplicated.
   - The prompt must be self-contained.
   - The result names the `task_id` that a later call can reuse to continue the same subagent session.
   - The caller states whether the child writes code or does research and how to verify the result.

   The `subagent_type` parameter description keeps the roster.

   The annotation values come from the bundled agent profiles. `general-purpose` and `implementation` use the `general-purpose` profile and render `Tools: all`. `read-only` uses the `read-only` profile and renders `Tools: read`. `code-review` and `document-review` use the `review` profile and render `Tools: read, bash`, where the review instructions govern `bash` use. The retained guidance rules, stated in full. The dispatch threshold: delegate only substantive multi-step work that benefits from an isolated context window, or long-running work that must not block this session. The prohibitions: never delegate simple reads, searches, commands, or small edits. Never dispatch a task and then do the same work. The prompt requirement: a self-contained prompt. The usage notes above add the verification-statement requirement.
4. Model-facing result content is one task envelope: `<task id="<taskId>" state="completed|error">` wrapping a `task_result` or `task_error` tag. `taskId` is the child's Tau session id. A child that succeeded carries state `completed` and wraps its complete final assistant message in `task_result`. A final message without text wraps the placeholder `(no output)`. A child that failed, was cancelled, or timed out carries state `error`. Its `task_error` tag wraps the final assistant message. When no final message exists, the tag wraps the OpenCode failure form defined in Required Outcome 6. Repair notes appear as `Note:` lines before the envelope. The envelope tags are informational. The inner content is the child message verbatim with no escaping. The `id` and `state` attributes carry the semantics. Structured `details` are schemaVersion 2: a one-element `results` array plus `planned` with value 1, and each result carries `taskId`.
5. A call with `task_id` resumes that child session instead of creating one. The child keeps its previous messages and tool outputs. The call's `prompt` is the new user turn. The content relays the new final assistant message. `task_id` requires `subagent_type` to name the agent whose prompt the resumed run uses. A call with `task_id` and no `subagent_type` fails closed with a teach-back that names both fields. The runner regenerates the agent body prompt and the profile policy extensions for the resumed run. The appended prompt uses a resume variant of the isolation sentence: the session's own prior turns are the child's earlier work on this task. Effective provider, model, reasoning effort, and `cwd` resolve exactly as in a fresh call and apply to the resumed run. `timeoutSeconds` bounds the resumed run. Usage in details covers the resumed run only. Before resuming, the runner verifies through the Tau session store that the session exists and that its recorded role is the subagent role. A session that fails either check falls back per Required Outcome 6. The call's `subagent_type` names the agent whose body prompt the runner regenerates. The tool records no per-session agent owner, so a `task_id` resumed under a different `subagent_type` continues that session with the named agent's prompt and policies. Authorization for resume is possession-based. Any code running as the same OS user account can list every child session with `tau sessions --all`. That code can resume any child from any parent session, including a parent in a different project. A resumed run can disclose the child's earlier content and add new content to it. The tool adds no per-caller authorization and no access auditing. Detection of cross-project access is therefore unavailable, and the operator accepts that absence. The accepted prevention is the OS account boundary. The session store lives under the running user's home directory. Other local accounts cannot read it without elevated privileges. The accepted recovery is store-maintenance removal: delete the child's entry from the project's `index.jsonl` and delete the child's `.jsonl` file.
6. A call whose `task_id` matches no session starts a fresh child with a new session id. Its result carries a repair note stating that the id matched no session. A `task_id` that matches a session whose recorded role is not the subagent role does the same. Its repair note states that the session is not a task child. A failed child's `task_error` tag wraps its final assistant message when one exists. When no final message exists, the tag wraps the OpenCode form `Subagent failed (task_id: <id>): <error>`. In that form, `<id>` is the effective child session id, so it is the fresh id after a fallback. The envelope `id` attribute names the child session id in every case. A child that fails before Tau creates its session, through process startup failure or cancellation before startup, carries state `error` with no `id` attribute. Its `task_error` tag wraps the startup or cancellation error text. Its details entry carries no `taskId`, and `planned` keeps the value 1.
7. Several `task` calls in one assistant message run concurrently. Each call is validated, approved, and dispatched independently. Each result carries its own envelope. One call's failure does not stop the others. Two concurrent calls that carry the same `task_id` do not both run. Exactly one starts its child, and the other fails closed with a teach-back that names the same-id conflict. The exclusion is process-safe: a lock keyed by `task_id` coordinates parent processes on the machine that hosts the session store. The losing call's result carries the fail-closed contract of Required Outcome 2: teach-back content, no envelope, an empty `results` array, and no `planned` field.
8. Per-call lifecycle: the default timeout is 3600 seconds, and a call override must be greater than 0 and at most 10800. Cancellation terminates the child process, waits no more than five seconds, and kills it if necessary. Cancellation preserves partial messages and stderr and removes every temporary prompt and policy file. Partial updates stream from the single child's accepted messages.
9. Recursion stays closed. Children never register the `task` tool. The binary recursion guard environment variable and `--no-extensions` in the child argv stay in place. The subagent config file supports no keys beyond `provider`, `model`, and `reasoningEffort`.
10. Requested definitions that resolve to the project layer require interactive approval or explicit `confirmProjectAgents: false`. Headless execution without explicit approval fails closed with a teach-back that names the project agents directory.

## Acceptance Examples

1. A call `{"description": "Review auth", "prompt": "Review the auth module", "subagent_type": "code-review"}` dispatches one `code-review` child. On success the content is one `<task id="<taskId>" state="completed"><task_result>...final message...</task_result></task>` envelope. On failure without a final message the inner tag is `task_error` and its body is the OpenCode failure form with the effective child session id. `details.results` holds one entry whose `taskId` equals the envelope id.
2. A call `{"prompt": "Find caching options"}` with no `subagent_type` dispatches one `general-purpose` child.
3. The first call of example 1 returns an envelope whose id is the child session id. A later call `{"prompt": "Now re-check the authz paths", "subagent_type": "code-review", "task_id": "<that id>"}` resumes the same child. The child retains its earlier review context. The content is the new final message in a completed envelope with the same id.
4. A call with `task_id` set to an id that matches no session starts a fresh child with a new session id. The result carries a `Note:` line stating that the id matched no session, before the envelope.
5. A call with `task_id` and no `subagent_type` fails closed with a teach-back that names both fields.
6. A call `{"background": true, "prompt": "A"}` fails closed with the background teach-back.
7. Two `task` calls in one assistant message run concurrently. Both children are active in parallel. Each result renders as its own row with its own envelope. One child's failure leaves the other's result intact. Two calls in one message that carry the same `task_id` produce one child result and one fail-closed same-id teach-back with no envelope.
8. A call `{"mode": "fast", "prompt": "A"}` fails closed. The teach-back names `mode` as an unknown field, lists the eligible agents, and shows one valid flat example.
9. The tool description contains the roster lines in the form `- general-purpose: <description> (Tools: <policy>)`. It contains the sentence about the `general-purpose` default and a when-not-to-use section. It contains the multi-call parallelism and `task_id` reuse usage notes.
10. A call `{"subagent_type": " ", "prompt": "A"}` fails closed with a teach-back that states `subagent_type` requires a non-empty string when present.

## Scope

**In scope:**

- Flat call surface, validation, repair notes, and teach-backs in the extension.
- Task envelope for model-facing result content, with the child session id as the envelope id.
- Pinned child sessions and `task_id` resume: `--session-id`, `--session-role`, and `--session` argv plumbing, the resume-variant isolation sentence, the unknown-session fallback, and `taskId` on results and details.
- Tool description and prompt-guideline restructure with the roster and tool-policy annotations.
- Updates to the README, the `tau-tools.md` reference, the skill dispatch templates, and the reviewer prompts that embed task call examples.
- Unit and extension test updates for every behavior above.

**Out of scope:**

- `background` async dispatch. Tau exposes no seam for returning a tool result later or injecting a message into the running parent session.
- Per-child tool selection, and the OpenCode built-in agent names (`build`, `plan`, `general`, `explore`).
- Changes to bundled agent names, profiles, discovery, or the project-agent approval flow.
- Changes to the details schema version, the usage tracking, the sidebar, or the catalog fail-fast, beyond the additive `taskId` field.
- Nested dispatch in any form. The recursion guard stays binary, and the config file gains no new keys.
- Living-spec synchronization. It happens in the finishing stage per the workflow.

## Constraints

- The tool name is `task`.
- The bundled agents are `general-purpose`, `read-only`, `implementation`, `code-review`, and `document-review`.
- The per-call options are exactly: `prompt`, `subagent_type`, `description`, `task_id`, `cwd`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`.
- Child result statuses (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`) live inside the child final messages.
- Children never register the `task` tool.
- The subagent config file supports only the `provider`, `model`, and `reasoningEffort` keys in its `[defaults]` and `[agents.<name>]` sections.
- All developer-facing text follows the writing-unambiguous-text skill.

## Approach

One surface, one code path. Validation parses the flat object, applies the `general-purpose` default, and rejects every unknown field with the teach-backs of Required Outcome 2. Dispatch runs one child invocation without an input-order slot pool. A process-safe lock keyed by `task_id` rejects a second call that carries an id another call holds. The lock coordinates parent processes on the machine that hosts the session store. The usage tracker, sidebar, and renderer contracts hold through one-element sequences, and `planned` carries the value 1.

**Pinned child sessions.** `build_tau_argv` adds `--session-id <uuid4-hex>` and `--session-role subagent` to every fresh child. The generated id is the child's `taskId`, recorded on the child result, in the details entry, and as the envelope id. The `--session-role` tag keeps child sessions out of the default `tau sessions` listing.

**Resume.** When the call carries `task_id`, the runner first checks the session store. The check covers the session's existence and its recorded subagent role. Either check's failure falls back per Required Outcome 6. The runner then passes `--session <task_id>` instead of `--session-id`. Resume reuses the fresh run's argv and prompt construction. Only the session-selection flag and the isolation-sentence variant differ. The runner regenerates the agent body prompt with the resume-variant isolation sentence. It passes the profile policy, thinking policy, overrides, `--cwd`, and the recursion-guard environment exactly as in a fresh run. Only the new turn's events stream, so collection, usage, and final-message extraction run unchanged.

**Unknown task_id.** `tau --session <missing>` exits with code 2 and prints `Unknown session:` on stderr. The runner reuses its established stderr-excerpt matching, the same mechanism as the `Unknown provider:` and `Model is not configured for provider` recovery notes. When the cleaned excerpt matches `Unknown session:` case-insensitively, the runner retries once as a fresh child with a new session id. The dispatch emits the repair note of Required Outcome 6. Any other failure surfaces through the existing error paths.

**Envelope.** Result content is the single-child envelope of Required Outcome 4 for every result that starts a child. Fail-closed validation and approval results carry the teach-back content of Required Outcome 2 instead. `details` keep schemaVersion 2 and the one-element `results` array, so the usage tracker, sidebar, and renderer contracts hold. Each result gains the additive `taskId` field, and `planned` carries the value 1.

**Tool surface.** The description restructure copies the OpenCode layout that models know: one-liner, roster with tool-policy annotations, default rule, when-not-to-use, usage notes. The threshold language and prohibitions of the current guidance stay, plus the multi-call parallelism and `task_id` reuse notes. The tool does not set `execution_mode`, so the Tau parallel default gives Required Outcome 7.

Alternatives considered:

- The `tasks` array beside the flat form. Rejected: two shapes mean two validation paths and two content forms, for a surface that model priors do not request.
- A configurable dispatch depth for nested dispatch. Rejected: the operator wants no recursive subagents, and the binary recursion guard is simpler and already proven.
- An unknown `task_id` as a hard failure. Rejected: it burns the call on a stale id the controller cannot recover, and OpenCode starts a child instead. The repair note keeps the fallback visible.
- A required `subagent_type`, as the OpenCode schema does. Rejected: an omitted `subagent_type` costs nothing and keeps a one-task call to `prompt` alone. The recorded `{agent, task}` key names stay invalid either way, and their recovery is the unknown-field teach-back.
- Silent acceptance of `command` and `background`. Rejected: `command` is OpenCode plumbing with no Tau meaning. Silent `background` acceptance serializes work that the model expects to run in parallel, so it gets a dedicated teach-back.

## Impact

- Code: `extension.py` (schema, description, guidelines)
- `dispatch.py` (validation, teach-backs, envelope content, single-child dispatch)
- `runner.py` (session argv, resume, unknown-session fallback, resume-variant prompt)
- `models.py` (`taskId` on the child result and details)
- `rendering.py` (single-child frame, call label from `description` and `subagent_type`)
- `utils.py` (`build_tau_argv`)
- tests under `extensions/superpowers-subagent/tests/`
- `config.py` and `sidebar.py` need no changes
- Docs: `README.md`, `docs/specs/subagent-dispatch.md` at finishing, `skills/using-superpowers/references/tau-tools.md`.
- Skills: every file that embeds a task call example or dispatch instructions. These are `dispatching-parallel-agents/SKILL.md`, `subagent-driven-development/SKILL.md`, `subagent-driven-development/implementer-prompt.md`, `subagent-driven-development/implementation-reviewer-prompt.md`, `requesting-code-review/SKILL.md`, `requesting-code-review/code-reviewer.md`, `writing-skills/testing-skills-with-subagents.md`, `writing-skills/examples/skill-testing-example.md`, `brainstorming/feature-spec-author-prompt.md`, `brainstorming/proposal-document-reviewer-prompt.md`, `brainstorming/spec-document-reviewer-prompt.md`, `writing-plans/plan-document-reviewer-prompt.md`, and `finishing-a-development-branch/living-spec-document-reviewer-prompt.md`. Multi-child examples in these files become several `task` calls in one message.
- Install: the installer copies the extension and skills. A re-install syncs every consumer.
- Sessions: child sessions accumulate in the Tau session store tagged `subagent`, visible with `tau sessions --all`. Resume depends on that store, so a `task_id` from a cleaned-up store falls back per Required Outcome 6.

## Risks

**Concurrency:** the tool sets no cap on the number of `task` calls in one message, matching OpenCode. The operator accepts the residual risk: an extreme burst can exhaust machine processes, memory, or provider quota before children finish. Detection is the streaming per-child updates plus `tau sessions --all`. Cancellation is the parent tool call's cancellation, which terminates and kills children per Required Outcome 8. Recovery is the Rollback entry. Two concurrent calls with the same `task_id` cannot both run, per Required Outcome 7.

**Storage:** every fresh call leaves a persistent child session in the Tau session store, and sessions accumulate with no retention. The operator accepts this storage risk. Detection is `tau sessions --all` and the store directory size. Cleanup is manual removal of child session files from the store directory.

**Resume:** `task_id` resume depends on the Tau session store keeping child sessions. A cleaned-up store turns a resume into a fresh child with a repair note, never a hard failure. Usage in details covers the resumed run only, so totals computed across resumed children undercount the earlier turns. This undercount is documented behavior, not a bug.

**Envelope ids:** the envelope id is an opaque 32-character session id. The id must be opaque because it is the resume handle. Renderers show it truncated.

**Compatibility:** the input schema change is breaking for callers of the current `tasks` array. The consumers are the model surface and the bundled skills, dispatch templates, and reviewer prompts. This change updates every consumer in the same branch. The in-repo consumer inventory is the Impact section's file list. The operator attests that no consumer exists outside this repository. The installer syncs every consumer on re-install.

**Migration:** the operator re-installs the extension and skills and restarts sessions. The Tau session store needs no migration, because pinned child sessions are ordinary sessions.

**Rollback:** the trigger is a failed acceptance check or a regression the fix loop cannot resolve. The steps are a revert of the branch commits, a re-install of the prior extension and skills, and a session restart. The session store keeps every pinned child session, the rolled-back surface never reads them, and they need no cleanup.

**Recursion:** children never see the `task` tool. A child instructed to delegate cannot delegate and reports that in its final message. This is the operator's chosen trade-off.

**Rollout:** the extension version stays 0.1.0 in `pyproject.toml`. The installer reports updated paths. Behavior changes are observable only after a session restart.

**Observability:** the envelope and `details.results[].taskId` record every child session id. `tau sessions --all` lists every child session with its model and cwd. The immutable transcript `docs/design/evidence/opencode-task-interface/baseline-tests/transcript.txt` records the baseline suite run at commit `b833ebd`: 267 tests pass. The implementation adds tests that cover every teach-back, envelope state, resume path, the same-id rejection, and the unknown-session fallback.

**Recovery:** rollback per the Rollback entry covers a failed rollout. The change holds no persistent state beyond the child sessions Tau already stores.

## Assumptions

- The operator re-installs the extension and skills and restarts sessions to pick up the new surface.
- Tau executes multiple tool calls of one assistant message concurrently. Concurrent `task` dispatches with distinct ids are safe. The same-id lock covers shared ids across parent processes. The dispatcher is per-call, the runner is re-entrant, and the usage tracker keys by tool-call id.
- The Tau session store persists print-mode sessions with pinned ids long enough for resume within and across parent sessions.
- The TUI renderers and the sidebar read `details` fields and do not parse content text.
- OpenCode's `background` behavior remains absent, and the teach-back covers models that send it.

## Unresolved Decisions

None.
