# Proposal: OpenCode-aligned task interface

Selected workflow depth: High-risk.

Terms used throughout: a teach-back is a rejection or repair tool result whose content names the valid values and the exact next step. Fail closed means the tool rejects the call and starts no child.

## Revision

Revised 2026-09-21 from the 2026-09-18 draft after operator review. Three decisions supersede the draft:

1. **Resume is in scope.** The draft deferred OpenCode's `task_id` session resume. The tau CLI supports pinned child session ids (`--session-id`), resume (`--session`), and a subagent role tag (`--session-role`), verified by smoke tests recorded under Baseline Evidence. This revision adds `task_id` as a Required Outcome.
2. **No depth config.** The draft replaced the recursion guard with a configurable `[defaults] depth` budget and nested dispatch. The operator wants no recursive subagents. The binary recursion guard stays exactly as it is, and the config file gains no new keys.
3. **The `tasks` array is removed.** The draft kept the array for parallel dispatch beside a new flat form. The operator wants OpenCode's model: the tool takes exactly one task per call, and parallel dispatch is multiple `task` tool calls in one assistant message. The flat form is the only form.

The 2026-09-18 draft's Outcomes 3 (array retention), 7 (agent-index envelope id), 8 (depth budget), 9 (array/flat conflict rules), and 10 (child-side approval escape) are therefore dropped or replaced.

## Intent

Models arrive at the `task` tool with training data from four harnesses. Claude Code, ZCode, Codex, and OpenCode all dispatch one agent per call with a flat argument object. OpenCode even names the tool `task`, like ours. Tau is the only harness with a `tasks` array. The recorded session data shows the result: the most common invalid first call is a flat object, and the first dispatch fails on the majority of sessions.

This change makes the flat form the only form. Field names unify to the OpenCode vocabulary, the tool adopts the OpenCode result envelope, and the tool adopts OpenCode's resumable subagent sessions: every child runs in a pinned Tau session, the result names its `task_id`, and a later call can continue that same child session instead of starting fresh.

## Baseline Evidence

Selected baseline branch: living-spec domain. The living spec is `docs/specs/subagent-dispatch.md`.

Current behavior (baseline, before this change):

- One tool named `task`. Every call takes `tasks`: 1 to 8 items, each `{agent, task, cwd?}`. Two or more items run in parallel, at most 4 active, results in input order (`docs/specs/subagent-dispatch.md`, "Requirement: task interface and validation"). This proposal removes the array; see Required Outcome 1 and Required Outcome 3.
- Top-level `agent`, `task`, `cwd`, and `chain` are rejected as unknown fields. This proposal accepts `agent` and `task` as deprecated aliases with repair notes; see Required Outcome 2. `chain` stays rejected.
- Placeholder overrides (`default`, `inherit`, `auto`) for `provider`, `model`, and `reasoningEffort` are treated as omitted with a repair note. Kept.
- Literal provider and model overrides fail fast against the scoped catalog. Kept.
- The tool schema embeds the agent roster in the `agent` parameter description. Kept, moved to `subagent_type` and extended per Required Outcome 4.
- Result content: one child returns the bare final message; several children return a counts line plus one section per child. This proposal replaces the content shape with the task envelope; see Required Outcome 5. Structured `details` stays schemaVersion 2 with a one-element `results` array. Kept.
- Children never register the `task` tool: the runner sets `TAU_SUPERPOWERS_SUBAGENT=1` and `setup()` exits early, and the child argv passes `--no-extensions`. Kept unchanged; see Required Outcome 10.

Consumers of the call contract: 14 files under the counting basis (a file embeds the call JSON or names the `agent` or `task` field of the call contract): `README.md`, the living spec, `skills/using-superpowers/references/tau-tools.md`, and 11 skill files. The Impact section lists these 11 files plus `subagent-driven-development/SKILL.md`, which instructs agent selection in prose. The change updates all 15. Tests: 267 pass at `b833ebd`.

Evidence for the change:

- Operator-attested input (not re-derivable from the repository): session recordings on this machine show 284 recorded `task` calls, of which 43 used a flat `{agent, task}` object, 1 placed `timeoutSeconds` inside an item, and the first dispatch failed on the majority of observed sessions. The recordings are sandbox session logs and carry no stable path; treat the counts as operator-attested motivation, not as repository evidence.
- Inspectable upstream sources for the external interfaces: OpenCode `task` tool (`anomalyco/opencode`, branch `dev`, `packages/opencode/src/tool/task.ts`, `tool/task.txt`, `tool/registry.ts`); Claude Code `Agent` tool (`@anthropic-ai/claude-code` 2.1.276, `sdk-tools.d.ts`); ZCode `Agent` tool (`zcode-app-cli` 3.12.3-26, extracted runtime `vendor/zcode.cjs`); Codex `spawn_agent` (`openai/codex`, branch `main`, `codex-rs/core/src/tools/handlers/multi_agents_spec.rs`). All four dispatch one agent per call with a flat argument object. OpenCode names the tool `task`, resumes subagent sessions through a `task_id` that is the child session id, and gates background dispatch behind an experimental flag.
- Repository evidence: the extension validator rejects every flat shape tested (`dispatch.py`, `validate_arguments`); the child argv passes `--no-extensions` and loads only generated policy extensions (`utils.py`, `build_tau_argv`); the recursion guard env var is `TAU_SUPERPOWERS_SUBAGENT` (`runner.py`).
- Tau capability evidence, verified on this machine against the installed Tau 0.3 CLI:
  - `tau --session-id <id>` pins the session id of a new print-mode session; `--session-role subagent` tags it out of the default session listing (visible with `tau sessions --all`).
  - `tau --session <id>` resumes a session in print mode; the resumed JSON stream carries only the new turn's messages, and the resumed assistant usage confirms the prior turns were loaded as context (input tokens include the earlier exchange).
  - `tau --session <missing-id>` exits with code 2 and prints `Unknown session: <id>` on stderr, a detectable clean failure.
- Concurrency evidence: Tau's `AgentTool.execution_mode` defaults to `"parallel"` (`tau_agent/tools.py`), so multiple `task` tool calls in one assistant message execute concurrently. The dispatcher, runner, and usage tracker hold no per-call mutable state that two concurrent dispatches share: the tracker keys by tool-call id, and the runner's run state is method-local.

Material discrepancy: no source conflict. The current spec and code agree. The recorded flat-form calls came from model priors, not from a hidden supported form.

## Required Outcomes

1. The tool takes exactly one task per call: `prompt` (required, non-empty), `subagent_type` (optional), `description` (optional display label), `task_id` (optional), and `cwd` (optional). An omitted or whitespace-only `subagent_type` selects `general-purpose`; a whitespace-only value produces a repair note naming the canonical field. The common options stay: `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`, all top-level.
2. The deprecated names `agent` and `task` are accepted as aliases for `subagent_type` and `prompt` respectively. Each tolerated use produces a repair note that names the canonical field. Different fields use either spelling independently: a call that uses a deprecated spelling for one field and the canonical spelling for a different field is valid and produces one repair note per deprecated spelling. A call that carries both spellings of one field fails closed with a teach-back that names the canonical field.
3. A call that carries `tasks` fails closed with a teach-back that names the flat form and states that several tasks are several `task` calls in one message. `chain` and `command` remain unknown-field rejections. `background` fails closed with a dedicated teach-back stating that background dispatch is not supported in this harness and that the call returns when the child finishes.
4. The tool description carries the agent roster with tool-policy annotations, the default selection rule, a when-not-to-use section, and usage notes in the OpenCode layout: several tasks are several `task` calls in one message; delegated work is not duplicated; the prompt must be self-contained; the result names the `task_id` a later call can reuse to continue the same subagent session; the caller states whether the child writes code or does research and how to verify it. The `subagent_type` parameter description keeps the roster.
5. Model-facing result content is one task envelope: `<task id="<taskId>" state="completed|error">` wrapping a `task_result` or `task_error` tag. `taskId` is the child's Tau session id. A child that succeeded carries state `completed` and wraps its complete final assistant message, or the placeholder `(no output)` when that message has no text, in `task_result`. A child that failed, was cancelled, or timed out carries state `error` and wraps its final assistant message when one exists, or its error text otherwise, in `task_error`. Repair notes keep their current position as `Note:` lines before the envelope. Structured `details` stay schemaVersion 2: a one-element `results` array plus `planned: 1`, and each result gains `taskId`. There is no counts line and no multi-section form anywhere, because one call yields at most one child.
6. A call with `task_id` resumes that child session instead of creating one: the child keeps its previous messages and tool outputs, the call's `prompt` is the new user turn, and the content relays the new final assistant message. `task_id` requires `subagent_type` to name the same agent that owns the session; a call with `task_id` and no `subagent_type` fails closed with a teach-back. The agent body and profile policy extensions are regenerated for the resumed run; the appended prompt uses a resume variant of the isolation sentence that states the session's own prior turns are the child's earlier work on this task. Effective provider, model, reasoning effort, and `cwd` resolve exactly as in a fresh call and apply to the resumed run. `timeoutSeconds` bounds the resumed run. Usage in details covers the resumed run only.
7. A call whose `task_id` matches no session starts a fresh child with a new session id and produces a repair note stating that the id matched no session. The failure content of other child failures names `task_id` in the OpenCode form so the controller can resume: `Subagent failed (task_id: <id>): <error>`.
8. Several `task` calls in one assistant message run concurrently. Each call is validated, approved, and dispatched independently; each result carries its own envelope; no call waits for another, and one call's failure does not stop the others.
9. Per-call lifecycle is unchanged: the 3600-second default timeout with a positive call override no greater than 3600, cancellation that terminates and then kills the child, temporary prompt and policy file cleanup on every exit path, and streamed partial updates from the single child's accepted messages.
10. Recursion stays closed: children never register the `task` tool. The binary recursion guard (`TAU_SUPERPOWERS_SUBAGENT` plus `--no-extensions` in the child argv) stays unchanged. The subagent config file gains no new keys.
11. The project-agent approval boundary is unchanged: requested definitions that resolve to the project layer require interactive approval or `confirmProjectAgents: false`, exactly as today.

## Acceptance Examples

1. A call `{"description": "Review auth", "prompt": "Review the auth module", "subagent_type": "code-review"}` dispatches one `code-review` child. On success the content is one `<task id="<taskId>" state="completed"><task_result>...final message...</task_result></task>` envelope. On failure without a final message the inner tag is `task_error` and its body is the child error text. `details.results` holds one entry whose `taskId` equals the envelope id.
2. A call `{"prompt": "Find caching options"}` with no `subagent_type` dispatches one `general-purpose` child. A whitespace-only `subagent_type` behaves as omitted, with a repair note that names the canonical field.
3. A call `{"agent": "code-review", "task": "Review the diff"}` dispatches one `code-review` child and produces two repair notes: one naming `subagent_type` and one naming `prompt`.
4. A call `{"prompt": "A", "task": "B"}` fails. The teach-back names the conflict and the canonical field `prompt`.
5. A call `{"tasks": [{"agent": "general-purpose", "task": "Fix tests"}]}` fails closed. The teach-back names the flat form and states that several tasks are several `task` calls in one message.
6. A call `{"background": true, "prompt": "A"}` fails closed with the background teach-back. The tool result arrives when the child finishes.
7. The first call of example 1 returns an envelope whose id is the child session id. A later call `{"prompt": "Now re-check the authz paths", "subagent_type": "code-review", "task_id": "<that id>"}` resumes the same child: the child retains its earlier review context, and the content is the new final message in a completed envelope with the same id.
8. A call with `task_id` set to an id that matches no session starts a fresh child and produces a `Note:` line stating that the id matched no session, before the envelope.
9. A call with `task_id` and no `subagent_type` fails closed with a teach-back that names both fields.
10. Two `task` calls in one assistant message run concurrently: both children are active in parallel, each result renders as its own row with its own envelope, and one child's failure leaves the other's result intact.
11. The tool description contains the roster lines in the form `- general-purpose: <description> (Tools: <policy>)`, the sentence about the `general-purpose` default, a when-not-to-use section, and the multi-call parallelism and `task_id` reuse usage notes.

## Scope

**In scope:**

- Flat-only call surface, alias acceptance, conflict detection, repair notes, and teach-backs in the extension.
- Removal of the `tasks` array: validator, concurrency pool, slots, and the multi-child content forms.
- Task envelope for model-facing result content, with the child session id as the envelope id.
- Pinned child sessions and `task_id` resume: `--session-id`, `--session-role`, and `--session` argv plumbing, the resume-variant isolation sentence, unknown-session fallback, and `taskId` on results and details.
- Tool description and prompt-guideline restructure; roster with tool-policy annotations.
- Updates to the README, the `tau-tools.md` reference, the skill dispatch templates, and the reviewer prompts that embed call examples.
- Unit and extension test updates for every behavior above.

**Out of scope:**

- `background` async dispatch. Tau exposes no seam for returning a tool result later or injecting a message into the running parent session; the field fails closed with a teach-back.
- Per-child tool selection, and the OpenCode built-in agent names (`build`, `plan`, `general`, `explore`).
- Changes to bundled agent names, profiles, discovery, or the project-agent approval flow.
- Changes to the details schema version, the usage tracking, the sidebar, or the catalog fail-fast, beyond the additive `taskId` field.
- Nested dispatch in any form. The recursion guard stays binary; no depth configuration exists.
- Living-spec synchronization. It happens in the finishing stage per the workflow.

## Constraints

- The tool name stays `task`.
- The bundled agents stay `general-purpose`, `read-only`, `implementation`, `code-review`, and `document-review`.
- Per-call overrides stay: `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`, top level only.
- Child result statuses (`DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`) stay inside the child final messages.
- The recursion guard stays binary: children never register the `task` tool, and the child argv keeps `--no-extensions`.
- The subagent config file (`superpowers-subagent.toml`) keeps its current keys exactly.
- All developer-facing text follows the writing-unambiguous-text skill.

## Approach

One surface, one code path: every valid call normalizes to a single child invocation. Validation parses the flat object, maps the deprecated aliases, applies the `general-purpose` default, and rejects every other shape with the teach-backs of Required Outcomes 2, 3, and 9 (examples 3–9). The concurrency pool, input-order slots, and the multi-child content builder are deleted; `MAX_TASKS` and `MAX_CONCURRENCY` disappear.

**Pinned child sessions.** `build_tau_argv` gains `--session-id <uuid4-hex>` and `--session-role subagent` for every fresh child. The generated id is the child's `taskId`, recorded on the `ChildResult`, in the details entry, and as the envelope id. The `--session-role` tag keeps child sessions out of the default `tau sessions` listing so a session full of subagent runs stays readable.

**Resume.** When the call carries `task_id`, the runner passes `--session <task_id>` instead of `--session-id`, regenerates the agent body prompt with the resume-variant isolation sentence, and passes the profile policy, thinking policy, overrides, `--cwd`, and recursion-guard environment exactly as in a fresh run. Only the new turn's events stream, so collection, usage, and final-message extraction work unchanged; usage in details covers the resumed run.

**Unknown task_id.** `tau --session <missing>` exits with code 2 and `Unknown session:` on stderr. The runner reuses its established stderr-excerpt matching (the same mechanism as the `Unknown provider:` and `Model is not configured for provider` recovery notes): when the cleaned excerpt matches `Unknown session:` case-insensitively, the runner retries once as a fresh child with a new session id and the dispatch emits the repair note of Required Outcome 7. Any other failure surfaces as today.

**Envelope.** `_result_content` collapses to the single-child form of Required Outcome 5. The counts line, the multi-section join, and the bare-final-message form disappear. `details` keeps schemaVersion 2 and the one-element `results` array, so the usage tracker, sidebar, and renderer contracts hold; each result gains the additive `taskId` field, and `planned` stays `1`.

**Tool surface.** The description restructure copies the OpenCode layout that models know: one-liner, roster with tool-policy annotations, default rule, when-not-to-use, usage notes. Our threshold language and prohibitions stay, plus the multi-call parallelism and `task_id` reuse notes. The tool does not set `execution_mode`, so Tau's parallel default already gives Required Outcome 8; concurrent dispatches share no mutable state, and the tracker keys by tool-call id.

Alternatives considered:

- Keeping the array beside the flat form (the 2026-09-18 draft). Rejected by the operator: two shapes mean two validation paths, two content forms, and teach-backs that must police their combination, for a surface models do not ask for.
- A `depth` config for nested dispatch (the 2026-09-18 draft). Rejected by the operator: the operator wants no recursive subagents, and the binary guard is simpler and already proven.
- Treating an unknown `task_id` as a hard failure. Rejected: it burns the call on a stale id the controller cannot recover, and OpenCode's tested behavior starts a child instead; the repair note keeps the fallback visible.
- Requiring `subagent_type` always, as OpenCode's schema does. Rejected: the `general-purpose` default rescues the recorded flat-form priors with no loss, because the roster names the default in the schema and description.
- Accepting `command` and `background` silently. Rejected: `command` is OpenCode plumbing with no Tau meaning and stays an unknown field; `background` would silently serialize what the model expects to parallelize, so it gets a dedicated teach-back.

## Impact

- Code: `extension.py` (schema, description, guidelines), `dispatch.py` (validation, alias mapping, teach-backs, envelope content, pool removal), `runner.py` (session argv, resume, unknown-session fallback, resume-variant prompt), `models.py` (`taskId` on `ChildResult` and details), `rendering.py` (single-child frame; call label from `description`/`subagent_type` instead of the task count), `utils.py` (`build_tau_argv`), tests under `extensions/superpowers-subagent/tests/`. `config.py` and `sidebar.py` need no changes.
- Docs: `README.md`, `docs/specs/subagent-dispatch.md` at finishing, `skills/using-superpowers/references/tau-tools.md`.
- Skills: every file that embeds the call shape or the item field names. Counting basis: files that embed the `tasks` array JSON or name the `agent` or `task` field of the call contract. These are `dispatching-parallel-agents/SKILL.md`, `subagent-driven-development/SKILL.md`, `subagent-driven-development/implementer-prompt.md`, `subagent-driven-development/implementation-reviewer-prompt.md`, `requesting-code-review/SKILL.md`, `requesting-code-review/code-reviewer.md`, `writing-skills/testing-skills-with-subagents.md`, `brainstorming/feature-spec-author-prompt.md`, `brainstorming/proposal-document-reviewer-prompt.md`, `brainstorming/spec-document-reviewer-prompt.md`, `writing-plans/plan-document-reviewer-prompt.md`, and `finishing-a-development-branch/living-spec-document-reviewer-prompt.md`. Multi-item `tasks` arrays in these files become several `task` calls in one message.
- Install: the installer copies the extension and skills; a re-install syncs every consumer.
- Sessions: running sessions keep the old schema until restart. New sessions get the new surface. Child sessions accumulate in the Tau session store tagged `subagent`, visible with `tau sessions --all`; resume depends on that store, so a `task_id` from a cleaned-up store falls back per Required Outcome 7.

## Risks

**Compatibility:** models trained on the current array call fail closed until the re-install syncs the skills, and the `tasks` teach-back names the flat form and the multi-call rule. Models trained on OpenCode, Claude Code, ZCode, and Codex get the canonical form. A model that mixes the deprecated and canonical spellings gets a fail-closed teach-back naming the conflict. The residual risk is a model giving up after one failure; every teach-back names the exact next call.

**Concurrency:** the per-call cap of four active children is gone. Parallelism is now the number of `task` calls in one assistant message, with no extension-side cap, matching OpenCode. The bound is the model's own restraint plus Tau's tool scheduling; the per-child 3600-second timeout, cancellation, and kill semantics still apply per call. Resource exhaustion is possible on an extreme burst and self-limits as children finish.

**Resume:** `task_id` resume depends on the Tau session store keeping child sessions. A cleaned-up store turns a resume into a fresh child with a repair note, never a hard failure. Usage in details covers the resumed run only, so session-total accounting from resumed children undercounts the earlier turns; the tracker's session totals remain accurate for fresh children and conservative for resumed ones. This undercount is documented behavior, not a bug.

**Envelope ids:** the envelope id becomes an opaque 32-character session id instead of the draft's short `code-review-0`. The id must be opaque because it is the resume handle; renderers show it truncated.

**Recursion:** children never see the `task` tool, so a child instructed to delegate cannot and must report that in its final message. This is the operator's chosen trade-off and matches the baseline guard.

**Rollout:** the extension version stays 0.1.0 in `pyproject.toml`; the installer reports updated paths. Behavior changes are observable only after a session restart.

**Rollback:** a single revert of the change branch restores the prior surface. Both directions degrade safely: an old extension ignores the new config keys it does not read (there are none new), and a new extension reads an old config file unchanged. No data migration exists; child sessions pinned by the new runner are ordinary Tau sessions that the old runner never touches.

**Observability:** repair notes appear in result content. The envelope and `details.results[].taskId` record every child session id. `tau sessions --all` lists every child session with its model and cwd. The full test suite passes at the baseline commit `b833ebd` (267 tests per pytest). Tests cover every note, teach-back, envelope state, resume path, and the unknown-session fallback.

**Recovery:** none needed. The change holds no persistent state beyond the child sessions Tau already stores.

## Assumptions

- The operator re-installs the extension and skills and restarts sessions to pick up the new surface.
- Tau executes multiple tool calls of one assistant message concurrently (verified: `AgentTool.execution_mode` defaults to `"parallel"`), and concurrent `task` dispatches are safe because the dispatcher is per-call, the runner is re-entrant, and the usage tracker keys by tool-call id.
- The Tau session store persists print-mode sessions with pinned ids long enough for resume within and across parent sessions.
- The TUI renderers and the sidebar read `details` fields and do not parse content text; the one-element `results` array keeps their contracts.
- OpenCode's `background` behavior remains absent; no consumer expects it, and the teach-back covers models that send it.

## Unresolved Decisions

None.
