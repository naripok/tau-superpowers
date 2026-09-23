# Proposal: Two-tool task dispatch with fail-closed validation

Selected workflow depth: High-risk.

Terms used throughout:

- Fail closed means the tool rejects the call, starts no child, and returns a teach-back as the result content.
- A teach-back is a rejection result whose content names the valid values and the exact next call.
- A child is one isolated Tau subagent process.
- A child session is the Tau session that persists one subagent's messages and tool outputs. One fresh run creates one child session. A resume run launches a new child process against an existing child session.
- A subagent is the logical agent across one or more child runs.
- `task` is the tool that dispatches a new child.
- `task_resume` is the tool that continues an existing child session.
- A pin is a provider, model, or reasoning-effort value set in the subagent config file or an agent-definition frontmatter. A call-level override is a value passed as a task-call argument. This change removes every call-level override; pins remain.
- The roster is the model-visible agent list: bundled and user agents only.
- The envelope is the model-facing `<task ...>` result wrapper.
- A repair note is the removed `Note:` line that the current surface prints before an envelope to report a tolerated caller mistake. This change removes the mechanism.

## Intent

The OpenCode-aligned flat `task` surface landed, and models still misuse it. They invent values for optional fields the schema advertises. One recorded instance: a dispatch supplied invented `provider` and `model` values, which validation stopped; the retry supplied `task_id: "nonexistent"`, which the runner interpreted as permission to start a fresh child. The task completed, but the request no longer meant what the caller wrote. The failure pattern repeats with strong frontier models, so prompt guidance cannot compensate for what the schema advertises.

The root cause has two parts. The single flat schema shows resume and override fields on every call, including calls that must not use them. The runner converts a failed resume into a fresh child, so an invented resume id silently changes the operation instead of failing.

This change splits new dispatch from resume into two tools, shrinks both schemas, renames every parameter to snake_case, removes every call-level provider, model, and reasoning-effort override, and fails closed on every invalid argument and every resume failure. A normal new-child call keeps a short, obvious shape. An explicit resume either resumes the requested session or fails without starting another child.

## Baseline Evidence

Baseline branch: living-spec domain. The living spec is `docs/specs/subagent-dispatch.md`. Synchronization happens in the finishing stage per the workflow.

Current call surface, `extensions/superpowers-subagent/superpowers_subagent/extension.py`, `_task_parameters()`: one flat `task` tool. `prompt` is the only required argument. Ten optional properties sit beside it: `subagent_type`, `description`, `task_id`, `cwd`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`.

Fallback behavior, `runner.py`, `TauChildRunner.run()`:

- A `task_id` that matches no session-store record starts a fresh child and prepends the repair note "matched no session, so a fresh child started."
- A record whose role is not the subagent role starts a fresh child with the matching note.
- A resumed run whose Tau process reports `Unknown session:` on stderr retries once as a fresh child with the same note.

Coercion behavior, `dispatch.py`: a case-insensitive `default`, `inherit`, or `auto` value on `provider`, `model`, or `reasoningEffort` coerces to omitted with a repair note.

Operator-attested failure instance, not re-derivable from the repository: during routine delegation, the controller supplied invented optional `provider` and `model` values. Validation stopped that call before launch. On the retry the controller supplied `task_id: "nonexistent"`. The extension started a fresh child. The misuse survives current schema descriptions and prompt guidelines, which already say to omit overrides on normal calls. Treat the instance as motivation, not as repository evidence.

Capability evidence, session metadata: Tau's `SessionRecordModel` (`tau_coding/session_manager.py`) records id, path, cwd, model, provider_name, inference_provider, title, role, created_at, and updated_at, and its model config ignores extra keys. The extension therefore cannot record or recover an agent identity for a session. `task_resume` keeps requiring `subagent_type`, and no agent-mismatch check is implementable in this change.

Capability evidence, multi-tool registration: `register_tool` (`tau_coding/extensions/runtime.py`) keys tools by name, and the first registration per name wins. One extension can register several differently named tools, and each tool carries its own schema, description, and prompt guidelines.

Baseline test suite: 352 tests pass at commit `93d87e3`, the master HEAD this branch starts from. The immutable transcript is `docs/design/evidence/task-tool-robustness/baseline-tests/transcript.txt`. The earlier transcript `docs/design/evidence/opencode-task-interface/baseline-tests/transcript.txt` (267 tests at commit `b833ebd`) predates the flat-surface commits and evidences an older surface, so this proposal cites the fresh run for the starting state.

Material baseline discrepancy and its resolution: none remains. The living spec and `dispatch.py` currently agree: a case-insensitive `default`, `inherit`, or `auto` placeholder on `provider`, `model`, or `reasoningEffort` coerces to omitted with a repair note, and the spec records that coercion rule. The rejection-versus-coercion discrepancy from the 2026-09-18 proposal was resolved by the spec sync at commit `06ff6b6`. This change removes the coerced parameters entirely, so the placeholder-coercion requirement dissolves; the finishing-stage living-spec sync records the new surface.

## Required Outcomes

1. Two tools, one execution core. `task` dispatches a new child. `task_resume` continues an existing child session. Both run through the same validation, dispatch, locking, envelope rendering, and runner code. Each call carries exactly one task.

2. Every parameter is snake_case. The complete parameter surface is:

   - `task`: `prompt` (required), `subagent_type`, `description`, `cwd`, `agent_scope`, `confirm_project_agents`, `timeout_seconds`.
   - `task_resume`: `prompt` (required), `task_id` (required), `subagent_type` (required), `agent_scope`, `confirm_project_agents`, `timeout_seconds`.

   Parameter semantics carry over from the current surface unchanged, except where a later outcome replaces them. On `task`, `subagent_type` omission selects `general-purpose`. On `task_resume`, `subagent_type` is required: the resumed run applies the requested agent's prompt and profile in addition to the session's retained turns, so omission fails closed with a teach-back that names both fields. `description` is a display label with no behavioral effect; `cwd` resolves relative to the parent session cwd; `agent_scope` selects the agent layers with `user` as the default; `confirm_project_agents` defaults to `true`; `timeout_seconds` is greater than 0, at most 10800, and defaults to 3600; `task_id` must be a non-empty string from an earlier task result.

3. Each tool rejects the other tool's fields. A `task` call with `task_id` fails closed with a teach-back that names `task_resume`. A `task_resume` call with `cwd` or `description` fails closed as an unknown field. A resumed run always uses the session's recorded cwd, so `cwd` has no resume meaning.

4. No call-level `provider`, `model`, or reasoning-effort parameter exists on either tool. Children resolve provider, model, and thinking level from, highest first: the config file `[agents.<name>]` section, the agent-definition frontmatter, the config file `[defaults]` section, then the parent session's active provider, model, and thinking level. Config-file and frontmatter pins remain fail-fast validated against the provider catalog before any child starts, and the failure lists the valid options. The catalog fail-fast teach-back and the runner's child-exit recovery notes no longer reference call-level parameters, because no such parameter exists: they direct the caller to correct the config pin or the agent definition.

5. Resume fails closed. An unknown `task_id`, a session record whose role is not the subagent role, and a resumed run whose Tau process reports an unknown session each return a failed result that starts zero children. The failed result carries the teach-back as its content, no envelope, an empty `results` array, and no `planned` field. The result preserves the requested id, states that no child started, and directs the caller to `task` for a fresh child. A successful resume stays pinned to the original session and its recorded cwd.

6. Validation fails closed everywhere. Unknown fields, wrong types, empty required values, and out-of-range timeouts fail closed with teach-backs on both tools. No value is coerced, silently dropped, or reinterpreted. A field whose capability this change removed, such as `reasoningEffort`, gets the unknown-field teach-back with wording that names the removal and directs the caller to the config-file or agent-definition pins. The repair-note mechanism is removed entirely.

7. Each tool's schema description, tool description, and prompt guidelines describe only that tool's supported shape. `task` shows the minimal new-child example and the inheritance default. `task_resume` shows the continuation shape and requires a `task_id` from an earlier result. The roster appears on both tools, because both resolve `subagent_type`.

8. Unchanged contracts: the result envelope and its id semantics, details schemaVersion 2 with the one-element results array, child status markers, cancellation, timeout, the same-id lock applied to `task_resume` ids, the recursion guard, the dedicated background teach-back on both tools, the project-agent approval flow, and `tau sessions --all` visibility.

9. Clean-cut consumer update. Every in-repo consumer updates in the same branch: the skills and reviewer prompts that embed task-call examples, the README, the `tau-tools.md` reference, and the example config file. No legacy tool, no alias, and no deprecation window exists. The README task sections announce the removed behaviors in the same change.

## Acceptance Examples

1. A call `{"prompt": "Find caching options"}` dispatches one `general-purpose` child that inherits the parent session's provider, model, and thinking level.
2. A call `{"description": "Review auth", "prompt": "Review the auth module", "subagent_type": "code-review"}` dispatches one `code-review` child.
3. A call `{"prompt": "Now re-check the authz paths.", "subagent_type": "code-review", "task_id": "<id from the earlier result>"}` to `task_resume` resumes that child session. The envelope id is unchanged, the child retains its earlier context, and the run executes in the session's recorded cwd.
4. A call `{"prompt": "A", "task_id": "<some id>"}` to `task` fails closed, starts zero children, and its teach-back names `task_resume` as the resume tool.
5. A call `{"prompt": "A", "subagent_type": "code-review", "task_id": "nonexistent"}` to `task_resume` fails closed, starts zero children, preserves the text `nonexistent`, states that no child started, and directs the caller to `task` for a fresh child.
6. A call `{"prompt": "A", "subagent_type": "code-review"}` to `task_resume` fails closed: `task_id` is required.
7. A call `{"prompt": "A", "task_id": "<id>"}` to `task_resume` fails closed: `subagent_type` is required on resume.
8. A call `{"prompt": "A", "timeoutSeconds": 60}` to `task` fails closed. The teach-back names `timeoutSeconds` as an unknown field and shows `timeout_seconds`.
9. Two `task_resume` calls in one message that carry the same `task_id` produce one child result and one fail-closed same-id teach-back for the other call.
10. A config pin that names an unconfigured provider fails the call closed before any child starts, and the teach-back lists the configured providers and directs the caller to the config pin or agent definition.
11. A call with `"background": true` on either tool fails closed with the dedicated background teach-back.

## Scope

**In scope:**

- The two-tool registration, per-tool schemas, descriptions, and prompt guidelines in `extension.py`.
- Per-tool validation, mode split, teach-backs, and repair-note removal in `dispatch.py`.
- Fail-closed resume, fallback removal, and stderr-diagnostic handling in `runner.py`.
- The snake_case rename of the config-file reasoning-effort key in `config.py`, and the same rename plus the stale-frontmatter-key diagnostic in `discovery.py`.
- The call-override layer removal in `utils.py` resolution helpers, the repair-note field removal in `models.py`, and the note-rendering removal in `dispatch.py`.
- Unit, registration, schema, and runtime-integration test updates.
- Consumer updates: README task sections and precedence list, `skills/using-superpowers/references/tau-tools.md`, the example config file, and every skill or reviewer prompt that embeds a task-call example.

**Out of scope:**

- Background dispatch. Tau exposes no seam for returning a tool result later.
- Bundled agent names, profiles, and discovery mechanics, beyond the frontmatter key rename and its stale-key diagnostic.
- Provider catalog construction and credential handling. The catalog fail-fast keeps its current scope.
- The details schema version, usage tracking, the sidebar, and result rendering beyond note removal.
- Nested dispatch in any form. The recursion guard stays binary.
- Living-spec synchronization. It happens in the finishing stage per the workflow.

## Constraints

- The tool names are `task` and `task_resume`.
- The parameter surfaces are exactly Required Outcome 2's lists. No other parameter exists on either tool.
- No call-level provider, model, or reasoning-effort override exists.
- The config-file and frontmatter keys are `provider`, `model`, and `reasoning_effort`.
- Children never register `task` or `task_resume`.
- All developer-facing text follows the writing-unambiguous-text skill.

## Approach

One execution core, two registrations. `setup()` registers `task` and `task_resume`, each with its own schema, description, and prompt guidelines. Both execute through the `TaskDispatcher`, whose `ParsedRequest` carries an explicit mode. Validation is per tool: `task` rejects `task_id` before anything else, and `task_resume` requires it. Unknown fields fail closed per tool, which rejects each tool's absent fields automatically.

The runner keeps the fresh and resume paths and drops every fallback. Resume verifies the session record first: a missing record, a non-subagent role, and a Tau-process `Unknown session:` diagnostic each return a failed result under the fail-closed contract of Required Outcome 5. The repair-note fields, the fallback notes, and the recorded-cwd note die with them, because `cwd` no longer exists on resume calls.

Resolution simplification: `effective_provider_model` and `effective_reasoning_effort` lose the call-override layer. The precedence chain becomes config `[agents.<name>]`, then agent-definition frontmatter, then config `[defaults]`, then the parent session. The catalog fail-fast keeps validating the resolved pair before launch.

Key rename: the config-file and frontmatter key `reasoningEffort` becomes `reasoning_effort`. The config parser reports an unknown key as a diagnostic and the dispatch proceeds without the pin, so an operator config file that still carries `reasoningEffort` loses that pin with a diagnostic until the operator updates the file. Discovery applies the same treatment to an agent definition, and the diagnostic covers only the stale `reasoningEffort` key: other unknown frontmatter keys keep the living spec's ignore rule. The stale key produces a discovery diagnostic and the pin is dropped, so neither stale location loses its pin silently. The example config file ships renamed, with its precedence comment reduced to the four-layer chain of Required Outcome 4.

Descriptions: `task` leads with the minimal example and the inheritance rule; `task_resume` leads with the continuation shape and the `task_id` source. Both carry the roster and the when-not-to-use guidance. The shared prompt-guideline text keeps the dispatch threshold, the self-contained-prompt requirement, and the single-task-per-call rule, split so each tool's guidelines reference only that tool.

Verification beyond the unit suite: a small scripted agent-facing evaluation runs against the provider and model pairs the harness configures at evaluation time, per the catalog snapshot the extension validates against, with tasks for ordinary new dispatch, valid resume, unknown resume, and a camelCase remnant field. It records the emitted tool name and JSON arguments, the validation failures, and the number of launched children. The key measures are fewer unnecessary optional fields on ordinary calls and zero accidental launches after a failed resume. Results are reported separately from the unit-test outcome.

Alternatives considered:

- A third `task_advanced` tool for the uncommon controls. Rejected by operator decision: every former advanced control has a durable home in the config file or an agent definition, and a third tool re-grows the surface this change shrinks.
- A nested advanced-options object on `task`. Rejected: nesting re-creates field invention one level down, on a shape the model must guess.
- Keeping the placeholder coercion. Rejected: with the override parameters removed, coercion has no subject, and fail-closed gives the model the exact correction instead of a tolerated guess.
- Dropping `subagent_type` on `task_resume` through recorded session metadata. Rejected: the session store records no agent identity and ignores extra keys, so the check is not implementable without an upstream Tau change, which is out of scope.
- A one-release deprecated legacy tool. Rejected by operator decision: the consumers are the model surface and in-repo Markdown, all updated in the same branch, and a legacy alias keeps the misleading surface alive for exactly the models this change protects.

## Impact

- Code: `extension.py` (two registrations, schemas, descriptions, guidelines), `dispatch.py` (mode split, parameter surface, teach-backs, notice removal), `runner.py` (fail-closed resume, fallback removal), `config.py` and `discovery.py` (key rename and stale-key diagnostics), `utils.py` (override-layer removal), `models.py` (repair-note field removal). `catalog.py` (fail-fast teach-back wording only), `locking.py`, `usage.py`, and `sidebar.py` need no other changes.
- Tests: the fallback tests in `test_runner.py` and `test_dispatch.py` flip to fail-closed expectations. `test_extension.py` asserts the two-tool registration and per-tool schemas. `test_runtime_integration.py` covers both tools end to end.
- Config: `superpowers-subagent.example.toml` renames the reasoning-effort key and updates its precedence comment to the four-layer chain of Required Outcome 4. An operator config file that still carries `reasoningEffort` produces an unknown-key diagnostic and the dispatch proceeds without that pin, until the operator updates the file. An agent definition that still carries the stale frontmatter key produces a discovery diagnostic and loses that pin, until the operator updates the definition.
- Docs: `README.md` task sections and the selection-precedence list; `skills/using-superpowers/references/tau-tools.md`.
- Skills: every file that embeds a task-call example or dispatch instructions. These are `dispatching-parallel-agents/SKILL.md`, `subagent-driven-development/SKILL.md`, `subagent-driven-development/implementer-prompt.md`, `subagent-driven-development/implementation-reviewer-prompt.md`, `requesting-code-review/SKILL.md`, `requesting-code-review/code-reviewer.md`, `writing-skills/testing-skills-with-subagents.md`, `writing-skills/examples/skill-testing-example.md`, `brainstorming/feature-spec-author-prompt.md`, `brainstorming/proposal-document-reviewer-prompt.md`, `brainstorming/spec-document-reviewer-prompt.md`, `writing-plans/plan-document-reviewer-prompt.md`, and `finishing-a-development-branch/living-spec-document-reviewer-prompt.md`.
- Install: the installer copies the extension and skills. A re-install syncs every consumer, and a session restart loads the new surface.

## Risks

**Compatibility:** the parameter-surface change is breaking for every current caller of the flat `task` schema. The consumers are the model surface and the bundled skills, dispatch templates, and reviewer prompts. This change updates every consumer in the same branch. The consumer inventory is the Impact section's file list. The operator attests that no consumer exists outside this repository. The installer syncs every consumer on re-install.

**Lost per-call override ergonomics:** a caller who changes a child's provider, model, or thinking level per call today loses that ability. Recovery is a config pin or an agent definition, both catalog-validated before launch. Detection is the operator or the model reporting an unmet need. The operator accepts the reduced flexibility as the price of the smaller schema.

**Stale-id cost:** a resume id whose session a cleanup removed now costs one failed call instead of silently starting a fresh child. The teach-back names the recovery: call `task` for a fresh child. The operator accepts this cost, because preserving the request's meaning is the intent of Required Outcome 5.

**camelCase priors:** models trained on camelCase harness schemas send `timeoutSeconds`, `agentScope`, or `reasoningEffort`. For `timeoutSeconds` and `agentScope`, the unknown-field teach-back names the snake_case field, and acceptance example 8 covers the shape. For `reasoningEffort`, no snake_case successor exists: the teach-back states that the call-level override capability was removed and directs the caller to the config-file or agent-definition pins, per Required Outcome 6. The agent-facing evaluation measures the residual rate.

**Resume availability:** resume depends on the Tau session store keeping child sessions. A cleaned-up store turns a resume into a fail-closed result, never a fresh child. Usage in details still covers the resumed run only, so totals across resumed children undercount the earlier turns. This undercount stays documented behavior.

**Concurrency:** the tool sets no cap on the number of task calls in one message. The operator accepts the residual burst risk, as in the current surface. The same-id lock applies to `task_resume` ids. A direct `tau --session` resume by another process bypasses that lock. The operator accepts that overlap.

**Migration:** the operator re-installs the extension and skills and restarts sessions. The Tau session store needs no migration, because pinned child sessions are ordinary sessions. Operator config files and agent definitions that still carry the `reasoningEffort` key keep working with a diagnostic and a dropped pin until the operator renames the key to `reasoning_effort`.

**Rollback:** the trigger is a failed acceptance check or a regression the fix loop cannot resolve. The steps are a revert of the branch commits, a re-install of the prior extension and skills, and a session restart. The rollback steps touch no session state: both the prior and the new surface treat pinned child sessions as ordinary store sessions, so they need no cleanup.

**Observability:** the envelope and `details.results[].taskId` record every child session id, and `tau sessions --all` lists every child session with its model and cwd. The implementation records a fresh baseline transcript for the new surface alongside the existing one.

**Security:** project agents stay repository-controlled prompt input. Their eligibility surfaces only through the approval flow or an explicit `confirm_project_agents: false`, which the approval prompt or the flag gates per call. The consent boundary is unchanged.

## Assumptions

- The operator re-installs the extension and skills and restarts sessions to pick up the new surface.
- No task-tool consumer exists outside this repository.
- Tau renders multiple extension tools with their own schemas and guidelines. The runtime source supports it, and a registration test covers it.
- Models treat the two tool descriptions as separate surfaces. The agent-facing evaluation validates the residual misuse rate.

## Unresolved Decisions

None.
