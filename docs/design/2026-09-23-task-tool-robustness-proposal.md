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
- The roster is the model-visible agent list: bundled and user agents. Project-layer definitions are unreachable through the tools and never appear in any roster.
- The envelope is the model-facing `<task ...>` result wrapper.
- A repair note is the removed `Note:` line that the current surface prints before an envelope to report a tolerated caller mistake. This change removes the mechanism.
- The session-agent mapping is the extension-owned durable file that records the agent name for every child session a fresh `task` call starts, so a later `task_resume` call can recover the agent without repeating `subagent_type`.

## Intent

The OpenCode-aligned flat `task` surface landed, and models still misuse it. They invent values for optional fields the schema advertises. One recorded instance: a dispatch supplied invented `provider` and `model` values, which validation stopped; the retry supplied `task_id: "nonexistent"`, which the runner interpreted as permission to start a fresh child. The task completed, but the request no longer meant what the caller wrote. The failure pattern repeats with strong frontier models, so prompt guidance cannot compensate for what the schema advertises.

The root cause has two parts. The single flat schema shows resume, override, and environment fields on every call, including calls that must not use them. The runner converts a failed resume into a fresh child, so an invented resume id silently changes the operation instead of failing.

This change splits new dispatch from resume into two minimal tools, removes every call-level provider, model, and reasoning-effort override, fixes the dispatch environment (spawn cwd and agent layers), and fails closed on every invalid argument and every resume failure. The operator runs the tools inside a secure sandbox, so the per-call scope and approval machinery is overhead without a defense payoff; subagent guidance belongs in the dispatch prompt, and subagent behavior is predictable. A normal new-child call keeps a short, obvious shape. An explicit resume either resumes the requested session or fails without starting another child.

## Baseline Evidence

Baseline branch: living-spec domain. The living spec is `docs/specs/subagent-dispatch.md`. Synchronization happens in the finishing stage of the finishing-a-development-branch skill.

Current call surface, `extensions/superpowers-subagent/superpowers_subagent/extension.py`, `_task_parameters()`: one flat `task` tool. `prompt` is the only required argument. Ten optional properties sit beside it: `subagent_type`, `description`, `task_id`, `cwd`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`.

Fallback behavior, `runner.py`, `TauChildRunner.run()`:

- A `task_id` that matches no session-store record starts a fresh child and prepends the repair note "matched no session, so a fresh child started."
- A record whose role is not the subagent role starts a fresh child with the matching note.
- A resumed run whose Tau process reports `Unknown session:` on stderr retries once as a fresh child with the same note.

Coercion behavior, `dispatch.py`: a case-insensitive `default`, `inherit`, or `auto` value on `provider`, `model`, or `reasoningEffort` coerces to omitted with a repair note.

Operator-attested failure instance, not re-derivable from the repository: during routine delegation, the controller supplied invented optional `provider` and `model` values. Validation stopped that call before launch. On the retry the controller supplied `task_id: "nonexistent"`. The extension started a fresh child. The misuse survives current schema descriptions and prompt guidelines, which already say to omit overrides on normal calls. Treat the instance as motivation, not as repository evidence.

Capability evidence, session metadata: Tau's `SessionRecordModel` (`tau_coding/session_manager.py`) records id, path, cwd, model, provider_name, inference_provider, title, role, created_at, and updated_at, and its model config ignores extra keys. The extension cannot recover an agent identity from the session store. The proposed session-agent mapping supplies that identity through extension-owned state instead.

Capability evidence, multi-tool registration: `register_tool` (`tau_coding/extensions/runtime.py`) keys tools by name, and the first registration per name wins. One extension can register several differently named tools, and each tool carries its own schema, description, and prompt guidelines.

Baseline test suite: 352 tests pass at commit `93d87e3`, the master HEAD this branch starts from. The immutable transcript is `docs/design/evidence/task-tool-robustness/baseline-tests/transcript.txt`. The earlier transcript `docs/design/evidence/opencode-task-interface/baseline-tests/transcript.txt` (267 tests at commit `b833ebd`) predates the flat-surface commits and evidences an older surface, so this proposal cites the fresh run for the starting state.

Material baseline discrepancy and its resolution: two recorded requirements dissolve or reverse under this change, and the finishing-stage living-spec sync records both on the basis of this approved proposal.

First, the placeholder-coercion rule: the living spec and `dispatch.py` currently agree that a case-insensitive `default`, `inherit`, or `auto` placeholder on `provider`, `model`, or `reasoningEffort` coerces to omitted with a repair note. This change removes the coerced parameters entirely, so the requirement dissolves. The rejection-versus-coercion discrepancy recorded during the previous interface change was already resolved by the spec sync at commit `06ff6b6`.

Second, the per-session agent-owner prohibition: the living spec's task_id-resume requirement states "The tool SHALL NOT record a per-session agent owner" and includes the "Resume under a different agent" scenario, in which a resume runs a different `subagent_type` than the session's origin. This change reverses that recorded decision deliberately: the session store cannot carry an agent identity, the operator-attested misuse record requires a recoverable identity for `task_resume`, and requiring the caller to repeat `subagent_type` re-creates a misuse surface. The reverse is the session-agent mapping of Required Outcome 6, and the different-agent resume capability is removed with it. The operator approves this reversal as part of this proposal.

Consumer evidence for the environment parameters: this repository ships no project agents and no project `.tau` directory, so no in-repo consumer uses the project layer, `agent_scope` values other than the default, or an explicit `confirmProjectAgents` value. The current surface's own default behavior is the fixed environment this proposal requires: omission of `cwd` spawns the child in the parent session cwd, and omission of `agent_scope` selects the user layer.

## Required Outcomes

1. Two tools, one execution core. `task` dispatches a new child. `task_resume` continues an existing child session. Both run through the same validation, dispatch, locking, envelope rendering, and runner code. Each call carries exactly one task.

2. Every parameter is snake_case. The complete parameter surface is:

   - `task`: `prompt` (required), `subagent_type`, `description`, `timeout_seconds`.
   - `task_resume`: `prompt` (required), `task_id` (required).

   `subagent_type` omission selects `general-purpose`; a non-empty string names an agent from the roster. `description` is a display label with no behavioral effect. `timeout_seconds` is greater than 0, at most 10800, and defaults to 3600. `task_id` must be a non-empty string from an earlier task result. Validation trims surrounding whitespace on `subagent_type` and `task_id` as the baseline does, the trimmed value is effective, and a value empty after trimming fails closed.

3. Each tool rejects the other tool's fields and every removed field. A `task` call with `task_id` fails closed with a teach-back that names `task_resume`. A `task_resume` call with `subagent_type`, `description`, `timeout_seconds`, or `cwd` fails closed as an unknown field.

4. No call-level `provider`, `model`, or reasoning-effort parameter exists on either tool. Children resolve provider, model, and thinking level from, highest first: the config file `[agents.<name>]` section, the agent-definition frontmatter, the config file `[defaults]` section, then the parent session's active provider, model, and thinking level. Config-file and frontmatter pins remain fail-fast validated against the provider catalog before any child starts, and the failure lists the valid options. The catalog fail-fast teach-back and the runner's child-exit recovery notes no longer reference call-level parameters, because no such parameter exists: they direct the caller to correct the config pin or the agent definition.

5. The dispatch environment is fixed. A fresh child spawns in the parent session's working directory; no `cwd` parameter exists, and a child that needs another directory changes its own directory or receives absolute paths in its prompt. Agent discovery is fixed to the user layer: bundled agents and `~/.tau/agents` definitions. The project layer is unreachable through the tools, and the `agent_scope` and `confirm_project_agents` parameters (today's `agentScope` and `confirmProjectAgents`) and the project-agent approval flow are removed.

6. The session-agent mapping recovers the resume agent. Every fresh dispatch writes the child session id and its agent name to the session-agent mapping at `~/.tau/superpowers-subagent-sessions.json` before the child process spawns, and a failed or impossible write fails the dispatch closed, so no child ever starts without a mapping entry. Mapping writes serialize through a dedicated process-safe mapping lock held across each read-modify-write cycle, so concurrent fresh dispatches cannot lose an entry. A `task_resume` call looks up the mapped agent name, re-discovers that agent's definition by name at resume time, and regenerates the resume-variant prompt. A missing mapping entry, a missing session record, a non-subagent role, a Tau-process unknown-session diagnostic, or a mapped name that no discoverable agent provides each fails closed.

7. Resume fails closed. Under every failure condition of Required Outcome 6, the result starts zero children. The failed result carries the teach-back as its content, no envelope, an empty `results` array, and no `planned` field. The result preserves the requested id, states that no child started, and directs the caller to `task` for a fresh child. A successful resume stays pinned to the original session and its recorded cwd.

8. Validation fails closed everywhere. Unknown fields, wrong types, empty required values, and out-of-range timeouts fail closed with teach-backs on both tools. No value is coerced, silently dropped, or reinterpreted. A removed override field, such as `reasoningEffort`, gets the unknown-field teach-back with wording that names the removal and directs the caller to the config-file or agent-definition pins. A removed environment field, such as `cwd` or `agentScope`, gets the unknown-field teach-back with wording that states the fixed behavior. The repair-note mechanism is removed entirely.

9. Each tool's schema description, tool description, and prompt guidelines describe only that tool's supported shape. `task` shows the minimal new-child example, the inheritance default, and the fixed environment. `task_resume` shows the two-field continuation shape and names the session-agent mapping as the source of the resumed agent. The roster appears on both tools, because both resolve an agent identity.

10. Unchanged contracts: the result envelope and its id semantics, details schemaVersion 2 with the one-element results array, child status markers, cancellation, the timeout mechanism with the default 3600 seconds applying to a resumed run, the same-id lock applied to `task_resume` ids, the recursion guard, the dedicated background teach-back on both tools, and `tau sessions --all` visibility.

11. Clean-cut consumer update. Every in-repo consumer updates in the same branch: the skills and reviewer prompts that embed task-call examples, the README, the `tau-tools.md` reference, and the example config file. No legacy tool, no alias, and no deprecation window exists. The README task sections announce the removed behaviors in the same change.

## Acceptance Examples

1. A call `{"prompt": "Find caching options"}` dispatches one `general-purpose` child that inherits the parent session's provider, model, and thinking level and spawns in the parent session's working directory.
2. A call `{"description": "Review auth", "prompt": "Review the auth module", "subagent_type": "code-review"}` dispatches one `code-review` child.
3. A call `{"prompt": "Now re-check the authz paths.", "task_id": "<id from the earlier result>"}` to `task_resume` resumes that child session as the agent recorded in the session-agent mapping. The envelope id is unchanged, the child retains its earlier context, and the run executes in the session's recorded cwd.
4. A call `{"prompt": "A", "task_id": "<some id>"}` to `task` fails closed, starts zero children, and its teach-back names `task_resume` as the resume tool.
5. A call `{"prompt": "A", "task_id": "nonexistent"}` to `task_resume` fails closed, starts zero children, preserves the text `nonexistent`, states that no child started, and directs the caller to `task` for a fresh child.
6. A call `{"prompt": "A"}` to `task_resume` fails closed: `task_id` is required.
7. A call `{"prompt": "A", "cwd": "/tmp/other"}` to `task` fails closed. The teach-back names `cwd` as an unknown field and states that a fresh child spawns in this session's working directory.
8. A call `{"prompt": "A", "timeoutSeconds": 60}` to `task` fails closed. The teach-back names `timeoutSeconds` as an unknown field and shows `timeout_seconds`.
9. A call whose `subagent_type` names only a project-layer definition fails closed with the roster teach-back, which lists the bundled and user agents and no project agent.
10. Two `task_resume` calls in one message that carry the same `task_id` produce one child result and one fail-closed same-id teach-back for the other call.
11. A config pin that names an unconfigured provider fails the call closed before any child starts, and the teach-back lists the configured providers and directs the caller to the config pin or agent definition.
12. A `task_resume` call whose `task_id` has no session-agent mapping entry, for example after the mapping file was deleted, fails closed, starts zero children, and directs the caller to `task` for a fresh child.
13. A call with `"background": true` on either tool fails closed with the dedicated background teach-back.

## Scope

**In scope:**

- The two-tool registration, per-tool schemas, descriptions, and prompt guidelines in `extension.py`, including removal of the confirmation-UI wiring.
- Per-tool validation, mode split, teach-backs, repair-note removal, and removal of the project-approval flow in `dispatch.py`.
- Fail-closed resume, fallback removal, stderr-diagnostic handling, session-agent mapping writes, and parent-cwd spawn in `runner.py`.
- The session-agent mapping file and its read, write, and fail-closed lookup behavior.
- User-layer-fixed discovery for the tools, the snake_case rename of the config-file reasoning-effort key in `config.py`, and the same rename plus the stale-frontmatter-key diagnostic in `discovery.py`.
- The call-override layer removal in `utils.py` resolution helpers, the cwd-override removal, and the repair-note and details-field removal in `models.py`: `ChildResult.notes` and the details `agentScope` and `projectAgentsDir` fields leave the schema, and no in-repo reader uses any of the three.
- Unit, registration, schema, and runtime-integration test updates.
- Consumer updates: README task sections, precedence list, custom-agent sections, and operator notes; `skills/using-superpowers/references/tau-tools.md`; the example config file; and every skill or reviewer prompt that embeds a task-call example.

**Out of scope:**

- Background dispatch. Tau exposes no seam for returning a tool result later.
- Bundled agent names and profiles.
- Provider catalog construction and credential handling. The catalog fail-fast keeps its current scope.
- The details schema version, usage tracking, the sidebar, and result rendering beyond note removal.
- Nested dispatch in any form. The recursion guard stays binary.
- Living-spec synchronization. It happens in the finishing stage of the finishing-a-development-branch skill, which records the coercion-rule dissolution and the agent-owner-prohibition reversal named in Baseline Evidence.

## Constraints

- The tool names are `task` and `task_resume`.
- The parameter surfaces are exactly Required Outcome 2's lists. No other parameter exists on either tool.
- No call-level provider, model, or reasoning-effort override exists.
- No per-call cwd, agent-layer, or approval control exists. Discovery is fixed to the user layer, and fresh children spawn in the parent session cwd.
- The config-file and frontmatter keys are `provider`, `model`, and `reasoning_effort`.
- Children never register `task` or `task_resume`.
- All developer-facing text follows the writing-unambiguous-text skill.

## Approach

One execution core, two registrations. `setup()` registers `task` and `task_resume`, each with its own schema, description, and prompt guidelines. Both execute through the `TaskDispatcher`, whose `ParsedRequest` carries an explicit mode. Validation is per tool: `task` rejects `task_id` before other argument validation, and `task_resume` requires it. Unknown fields fail closed per tool, which rejects each tool's absent fields automatically.

The runner keeps the fresh and resume paths and drops every fallback. Resume verifies the session record and the session-agent mapping first: a missing record, a non-subagent role, a missing mapping entry, a mapped name that no discoverable agent provides, and a Tau-process `Unknown session:` diagnostic each return a failed result under the fail-closed contract of Required Outcome 7. The repair-note fields, the fallback notes, and the recorded-cwd note die with them, because `cwd` no longer exists on resume calls.

Fixed environment: `resolve_child_cwd` loses its override and always returns the parent session cwd, which the fresh child's argv passes as `--cwd`. Discovery for the tools always resolves the user layer, so `agentScope` plumbing, the project-approval flow, and the confirmation-UI parameter leave the dispatch path together.

Session-agent mapping: a new extension-owned JSON file at `~/.tau/superpowers-subagent-sessions.json`, a sibling of the existing `superpowers-subagent.toml`, maps child session ids to agent names. The write happens before the child process spawns, under the fresh session id, so a mapping entry exists for every child that starts; a failed or impossible write fails the dispatch closed with the standard fail-closed contract. A write is a read-modify-write of the whole file held under a dedicated process-safe mapping lock, the same file-lock mechanism as the same-id lock, and lands through atomic write-and-rename, so concurrent fresh dispatches serialize and a concurrent reader sees the file whole. A write that cannot read the file because it is unreadable or corrupted rebuilds it from an empty map: lost entries only downgrade those sessions to fail-closed resumes, never to unintended children. The same-id lock stays irrelevant to mapping writes: it keys resumed ids, and resumes never write the mapping. Reads happen on resume before the session-record check. The mapping is append-only across normal operation; the documented store-maintenance cleanup gains one step, deleting the entry beside the transcript and index line. A corrupted file read on resume is treated as a missing entry and fails closed. An entry whose session never started is stale and harmless, because the session-record check fails first.

Resolution simplification: `effective_provider_model` and `effective_reasoning_effort` lose the call-override layer. The precedence chain becomes config `[agents.<name>]`, then agent-definition frontmatter, then config `[defaults]`, then the parent session. The catalog fail-fast keeps validating the resolved pair before launch.

Key rename: the config-file and frontmatter key `reasoningEffort` becomes `reasoning_effort`. The config parser reports an unknown key as a diagnostic and the dispatch proceeds without the pin, so an operator config file that still carries `reasoningEffort` loses that pin with a diagnostic until the operator updates the file. Discovery applies the same treatment to an agent definition, and the diagnostic covers only the stale `reasoningEffort` key: other unknown frontmatter keys keep the living spec's ignore rule. The stale key produces a discovery diagnostic and the pin is dropped, so neither stale location loses its pin silently. The example config file ships renamed, with its precedence comment reduced to the four-layer chain of Required Outcome 4.

Descriptions: `task` leads with the minimal example, the inheritance rule, and the fixed environment; `task_resume` leads with the two-field continuation shape and the mapping as the agent source. Both carry the roster and the when-not-to-use guidance. The shared prompt-guideline text keeps the dispatch threshold, the self-contained-prompt requirement, and the single-task-per-call rule, split so each tool's guidelines reference only that tool. `task_resume` registers its own call renderer: its label names the resume operation and the requested id, never an agent name, because the mapped agent is not a call argument.

Verification beyond the unit suite: a small scripted agent-facing evaluation runs against the provider and model pairs the harness configures at evaluation time, per the catalog snapshot the extension validates against, with tasks for ordinary new dispatch, valid resume, unknown resume, and a camelCase remnant field. It records the emitted tool name and JSON arguments, the validation failures, and the number of launched children. The key measures are fewer unnecessary optional fields on ordinary calls and zero accidental launches after a failed resume. Results are reported separately from the unit-test outcome.

Alternatives considered:

- Keeping `agent_scope` and `confirm_project_agents`. Rejected by operator decision: the operator runs the tools inside a secure sandbox, the repo ships no project agents, and the fixed user layer makes subagent behavior predictable while removing the approval machinery and its prompt-surface cost.
- Keeping `cwd`. Rejected by operator decision: children spawn in the parent session cwd and can change their own directory; a per-call cwd re-creates a field models invent values for.
- Requiring `subagent_type` on `task_resume`. Rejected by operator decision: the initial `task` call already configured the agent, so repeating it burdens every resume and re-creates a misuse surface. The session-agent mapping supplies the identity instead.
- Recording the agent identity in the Tau session store. Rejected: `SessionRecordModel` carries no agent field and ignores extra keys, so the check is not implementable without an upstream Tau change, which is out of scope.
- Encoding the agent name in the child session's title. Rejected: the title is user-visible state in `tau sessions` listings, and parsing semantics out of display text is fragile.
- A third `task_advanced` tool for the uncommon controls. Rejected by operator decision: every former advanced control has a durable home in the config file or an agent definition, and a third tool re-grows the surface this change shrinks.
- A nested advanced-options object on `task`. Rejected: nesting re-creates field invention one level down, on a shape the model must guess.
- Keeping the placeholder coercion. Rejected: with the override parameters removed, coercion has no subject, and fail-closed gives the model the exact correction instead of a tolerated guess.
- A one-release deprecated legacy tool. Rejected by operator decision: the consumers are the model surface and in-repo Markdown, all updated in the same branch, and a legacy alias keeps the misleading surface alive for exactly the models this change protects.

## Impact

- Code: `extension.py` (two registrations, schemas, descriptions, guidelines, no confirmation-UI wiring), `dispatch.py` (mode split, parameter surface, teach-backs, notice and approval-flow removal), `runner.py` (fail-closed resume, fallback removal, mapping writes, parent-cwd spawn), a new session-agent mapping module, `config.py` and `discovery.py` (key rename and stale-key diagnostics, user-layer tool discovery), `utils.py` (override-layer and cwd-override removal), `models.py` (repair-note field removal), `rendering.py` (resume call-label renderer). `catalog.py` (fail-fast teach-back wording only), `locking.py`, `usage.py`, and `sidebar.py` need no other changes.
- Tests: the fallback tests in `test_runner.py` and `test_dispatch.py` flip to fail-closed expectations; the project-approval tests are removed with the flow. `test_extension.py` asserts the two-tool registration and per-tool schemas. New tests cover the session-agent mapping's write, lookup, and fail-closed paths. `test_runtime_integration.py` covers both tools end to end.
- Config: `superpowers-subagent.example.toml` renames the reasoning-effort key and updates its precedence comment to the four-layer chain of Required Outcome 4. An operator config file that still carries `reasoningEffort` produces an unknown-key diagnostic and the dispatch proceeds without that pin, until the operator updates the file. An agent definition that still carries the stale frontmatter key produces a discovery diagnostic and loses that pin, until the operator updates the definition.
- New state: the session-agent mapping file appears at `~/.tau/superpowers-subagent-sessions.json`. It accumulates one entry per child session, and the store-maintenance cleanup procedure gains the mapping-entry step.
- Docs: `README.md` task sections, the selection-precedence list, the custom-agents sections (user layer only), the isolation notes, and the operator notes including the cleanup procedure; the README announcements of removed behaviors include the resumed-run timeout cap and the different-agent resume removal; `skills/using-superpowers/references/tau-tools.md`.
- Skills: every file that embeds a task-call example or dispatch instructions. These are `dispatching-parallel-agents/SKILL.md`, `subagent-driven-development/SKILL.md`, `subagent-driven-development/implementer-prompt.md`, `subagent-driven-development/implementation-reviewer-prompt.md`, `requesting-code-review/SKILL.md`, `requesting-code-review/code-reviewer.md`, `writing-skills/testing-skills-with-subagents.md`, `writing-skills/examples/skill-testing-example.md`, `brainstorming/feature-spec-author-prompt.md`, `brainstorming/proposal-document-reviewer-prompt.md`, `brainstorming/spec-document-reviewer-prompt.md`, `writing-plans/plan-document-reviewer-prompt.md`, and `finishing-a-development-branch/living-spec-document-reviewer-prompt.md`.
- Install: the installer copies the extension and skills. A re-install syncs every consumer, and a session restart loads the new surface.

## Risks

**Compatibility:** the parameter-surface change is breaking for every current caller of the flat `task` schema. The consumers are the model surface and the bundled skills, dispatch templates, and reviewer prompts. This change updates every consumer in the same branch. The consumer inventory is the Impact section's file list. The operator attests that no consumer exists outside this repository. The installer syncs every consumer on re-install.

**Project-agent removal:** repositories that define agents under `.tau/agents` lose tool access to them. Recovery is moving the definition to the user layer `~/.tau/agents`, which the tools always discover. Detection is the roster teach-back naming the missing agent. The operator attests that this repository ships no project agents and accepts the removal; the sandbox, not the tool surface, is the operator's security boundary.

**Fixed spawn cwd:** a child that must operate in another directory changes its own directory or works from absolute paths supplied in the prompt. Detection is a child reporting blocked work that a different cwd unblocks. Recovery is passing the paths or instructions in the prompt. The operator accepts this, because predictability outweighs per-call flexibility.

**Mapping state:** the session-agent mapping is new durable extension state. A deleted or corrupted mapping turns resumes of still-live sessions fail-closed, never into fresh children; a corrupted file rebuilds on the next write. A failed mapping write fails the fresh dispatch closed before any child starts, so no child exists unmapped. Stale entries for cleaned-up sessions are harmless, because the session-record check fails first. Accumulation parallels the documented child-session accumulation, and the cleanup procedure gains the mapping step. The operator accepts the new state file.

**Resumed-run timeout cap:** the current surface allows a `timeoutSeconds` override on a resumed run, up to 10800 seconds. This change removes it, and a resumed run uses the default 3600 seconds; no timeout pin exists in the config-file key set. Detection is a resumed run that times out at 3600 seconds. Recovery is resuming the same session with a more focused prompt, which continues the retained context. The operator accepts the cap, because a per-call timeout on resume re-creates a call-level override.

**Different-agent resume removal:** the current surface allows a resume to run a different `subagent_type` than the session's origin; the living spec records that capability. This change removes it: the resume agent is the mapped one, and the initial `task` call owns the agent choice for the session's lifetime. Recovery is a fresh `task` call with the wanted agent. The operator accepts the removal, because repeating the agent re-creates a misuse surface.

**Stale-id cost:** a resume id whose session a cleanup removed now costs one failed call instead of silently starting a fresh child. The teach-back names the recovery: call `task` for a fresh child. The operator accepts this cost, because preserving the request's meaning is the intent of Required Outcome 7.

**camelCase priors:** models trained on camelCase harness schemas send `timeoutSeconds`, `agentScope`, or `reasoningEffort`. For `timeoutSeconds`, the unknown-field teach-back names the snake_case field, and acceptance example 8 covers the shape. For `agentScope` and `reasoningEffort`, no snake_case successor exists: the teach-back states that the call-level capability was removed and, for `reasoningEffort`, directs the caller to the config-file or agent-definition pins, per Required Outcome 8. The agent-facing evaluation measures the residual rate.

**Resume availability:** resume depends on the Tau session store keeping child sessions and on the session-agent mapping keeping entries. A cleaned-up store or a deleted mapping turns a resume into a fail-closed result, never a fresh child. Usage in details still covers the resumed run only, so totals across resumed children undercount the earlier turns. This undercount stays documented behavior.

**Concurrency:** the tool sets no cap on the number of task calls in one message. The operator accepts the residual burst risk, as in the current surface. The same-id lock applies to `task_resume` ids. A direct `tau --session` resume by another process bypasses that lock. The operator accepts that overlap.

**Migration:** the operator re-installs the extension and skills and restarts sessions. The Tau session store needs no migration, because pinned child sessions are ordinary sessions. Sessions created before this change have no mapping entries, so their resumes fail closed with the teach-back that directs the caller to `task`. Operator config files and agent definitions that still carry the `reasoningEffort` key keep working with a diagnostic and a dropped pin until the operator renames the key to `reasoning_effort`.

**Rollback:** the trigger is a failed acceptance check or a regression the implementation stage's implement-test-fix loop cannot resolve. The steps are a revert of the branch commits, a re-install of the prior extension and skills, and a session restart. The rollback steps touch no session state: both the prior and the new surface treat pinned child sessions as ordinary store sessions, so they need no cleanup.

**Observability:** the envelope and `details.results[].taskId` record every child session id, and `tau sessions --all` lists every child session with its model and cwd. The session-agent mapping is a plain JSON file an operator can inspect. The implementation records a fresh baseline transcript for the new surface alongside the existing one.

**Security:** the project-agent approval flow is removed, and the consent boundary becomes the fixed user-layer scope: only bundled and operator-controlled user definitions are dispatchable, and repository-controlled agent definitions are unreachable through the tools regardless of project trust. The operator runs the tools inside a secure sandbox and accepts that a child's prompt remains task-controlled input, a property unchanged from the current surface.

## Assumptions

- The operator runs the task tools inside a secure sandbox, so repo-controlled inputs are not the last line of defense.
- The operator re-installs the extension and skills and restarts sessions to pick up the new surface.
- No task-tool consumer exists outside this repository.
- Tau renders multiple extension tools with their own schemas and guidelines. The runtime source supports it, and a registration test covers it.
- Models treat the two tool descriptions as separate surfaces. The agent-facing evaluation validates the residual misuse rate.

## Unresolved Decisions

None.
