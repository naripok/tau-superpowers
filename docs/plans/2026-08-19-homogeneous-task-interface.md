# Homogeneous Task Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `task` tool's single/parallel/chain modes with one homogeneous `tasks`-array interface, surface each child's complete final assistant message (no heading extraction), unify rendering on a frame of self-contained child components, and add dispatch-threshold guidance so parents stop delegating trivial or duplicate tool calls.

**Architecture:** The extension keeps one bounded-concurrency child runner; dispatch branches nowhere on "mode" — a call is a list of 1–8 items, where one item runs one child and two or more run in parallel (max four active). Parent-model content and TUI rendering are both built from the same per-child building block: the child's complete final assistant message. Details drop `mode`/`step` and move to `schemaVersion: 2`.

**Tech Stack:** Python 3.14 (mypy strict, ruff), Tau extension API (`tau_agent`, `tau_coding`), pytest + pytest-asyncio, Markdown skills/docs.

**Standards:** Apply the shared code standards in every task: DRY, low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only.

**Feature spec:** none — this change was specified directly by the operator. The behavioral contract is the **Requirements** section below; every task traces to it. The living spec `docs/specs/subagent-dispatch.md` is updated to match in Task 3.

**Context:** No brainstorming artifacts (proposal/spec/worktree) exist for this change. Before Task 1, create a feature branch in the checkout: `git checkout -b feature/homogeneous-task-interface`. Never implement on the default branch.

---

## Requirements (the contract)

- **R1 — Homogeneous interface.** The `task` tool accepts exactly one mode field: a required `tasks` array of 1–8 items, each `{agent, task, cwd?}`. Top-level `agent`, `task`, `cwd`, and `chain` are removed from the JSON schema and rejected as unknown fields by validation.
- **R2 — Execution.** One item runs one child; two or more run in parallel with at most four concurrent children, preserving input order in results. Timeout/cancellation semantics are unchanged: the child is terminated, queued work never starts, partial state is retained.
- **R3 — Chain removal.** Chain dispatch, `{previous}` substitution, and `step` numbering are removed from validation, execution, models, the runner, rendering, and details.
- **R4 — Final-message content.** Parent-model content surfaces each child's complete final assistant message: the concatenated text blocks of the last accepted assistant message only — never tool calls, thinking, or earlier messages. No `## Summary` / `## Code Review` / `## Document Review` heading extraction remains anywhere.
- **R5 — Content envelope.** Exactly one result: success → the bare final message (`(no output)` when empty); failure → `Agent <name> failed: <error>`. Two or more results: a `<succeeded>/<total> succeeded` header plus one `[<agent>] (completed|failed)` section per child in input order; a section body is the final message, else the error message, else `(no output)`.
- **R6 — Child contract.** The shared child instructions drop the `## Summary` mandate, keep the four status markers, and state that the complete final message is relayed verbatim to the controller. The bundled `code-review`/`document-review` agents keep their `## Code Review` / `## Document Review` report formats (ending in the status line) but no longer require a `## Summary` section; no agent description may claim mechanical extraction. Status parsing (`parse_status`) is unchanged.
- **R7 — Details schema v2.** Task `details` use `schemaVersion: 2` and contain no `mode` or `step` fields. `planned`, scope, diagnostics, config paths/diagnostics, and the per-child fields are otherwise unchanged.
- **R8 — Unified rendering.** One frame+components view renders any child count: a counts headline, then one self-contained child component per child in input order (status icon, agent, streamed work, task, error, usage), then an aggregate usage line when more than one child exists. The call label derives from the task count. Details with `schemaVersion != 2` render nothing custom.
- **R9 — Dispatch-threshold guidance.** The always-visible prompt surface (tool description, prompt snippet, prompt guidelines) states that subagents are dispatched only for substantive multi-step work that benefits from an isolated context window or for long-running work that must not block the parent session, and forbids (a) dispatching simple reads/searches/commands/small edits the parent can perform with its own tools and (b) dispatching work the parent is about to perform itself (a subagent replaces the parent's tool calls for its task; it never duplicates them). This is prompt-level guidance, not mechanical enforcement.
- **R10 — Skills and docs alignment.** Every skill JSON example uses the `tasks` array; chain mode, `{previous}`, single-mode, and extraction wording are removed from skills, README, the living spec, and `docs/FLOW_DESCRIPTION.md`. Historical `docs/design/` and `docs/plans/` files are intentionally untouched.

## Commands

All extension checks run from `extensions/superpowers-subagent` with the site-packages of the installed `tau` executable on `PYTHONPATH`:

```bash
cd extensions/superpowers-subagent
TAU_PYTHON=$(sed -n '1s/^#!//p' "$(command -v tau)")
TAU_SITE_PACKAGES=$(
  "$TAU_PYTHON" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])'
)
uv sync --all-groups --locked

# Run one test file:
PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest tests/test_dispatch.py
# Full suite:
PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest
# Type check, lint, format check:
PYTHONPATH="$TAU_SITE_PACKAGES" uv run mypy
uv run ruff check .
uv run ruff format --check .
```

Docs/skills tasks have no unit tests; their verification is the `rg` gates listed in each task plus a careful read-through of the changed files.

---

### Task 1: Homogeneous dispatch core, final-message results, schema v2, unified rendering

The details shape couples dispatch output to rendering input (`schemaVersion`, `mode`, `step`), so no smaller split keeps the test suite green between commits; this task is the atomic code change. It covers R1–R9 for all Python code, bundled agent definitions, and extension tests.

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/models.py` — drop `DispatchMode` and `ChildResult.step`; `details_dict` loses `mode`, emits `schemaVersion: 2`
- Modify: `extensions/superpowers-subagent/superpowers_subagent/utils.py` — delete heading-extraction helpers
- Modify: `extensions/superpowers-subagent/superpowers_subagent/dispatch.py` — tasks-only validation, single execution path, final-message content
- Modify: `extensions/superpowers-subagent/superpowers_subagent/extension.py` — schema, description, snippet, guidelines (R1, R9)
- Modify: `extensions/superpowers-subagent/superpowers_subagent/runner.py` — drop `step` param; new Response Format instructions (R6)
- Modify: `extensions/superpowers-subagent/superpowers_subagent/rendering.py` — frame+components renderer, v2 details (R8)
- Modify: `extensions/superpowers-subagent/agents/code-review.md` — strict `## Code Review` report without `## Summary`; verbatim-relay wording (R6)
- Modify: `extensions/superpowers-subagent/agents/document-review.md` — same for `## Document Review` (R6)
- Modify: `extensions/superpowers-subagent/agents/read-only.md` — frontmatter description no longer invites trivial inspection dispatches (R9)
- Test: `extensions/superpowers-subagent/tests/test_dispatch.py`
- Test: `extensions/superpowers-subagent/tests/test_utils.py`
- Test: `extensions/superpowers-subagent/tests/test_extension.py`
- Test: `extensions/superpowers-subagent/tests/test_runner.py`
- Test: `extensions/superpowers-subagent/tests/test_rendering.py`
- Test: `extensions/superpowers-subagent/tests/test_runtime_integration.py`
- Explicitly unchanged: `config.py`, `discovery.py`, `usage.py`, `sidebar.py`, `superpowers-subagent.example.toml`, `tests/conftest.py`, `tests/fixtures/fake_tau.py`, `tests/test_config.py`, `tests/test_discovery.py`, `tests/test_usage.py`, `tests/test_sidebar.py` (usage/sidebar observe `ChildResult` objects and never read `mode`/`step`)

**Spec requirement:** R1, R2, R3, R4, R5, R6, R7, R8, R9 (code and bundled-agent portions).

**Interface:**

`models.py`:
- Delete `DispatchMode = Literal["single", "parallel", "chain"]` (and every import of it).
- `ChildResult`: delete the `step: int | None = None` field and the `"step"` key in `to_dict()`.
- `details_dict(*, agent_scope: AgentScope, project_agents_dir: Path | None, discovery_diagnostics: tuple[str, ...], results: list[ChildResult], planned: int | None = None, config_paths: tuple[Path, ...] = (), config_diagnostics: tuple[str, ...] = ()) -> dict[str, JSONValue]` — same as today minus the `mode` parameter; the emitted dict has `"schemaVersion": 2` and no `"mode"` key. Update the docstring (no `mode`; `planned` rationale unchanged).

`utils.py`:
- Delete `_SUMMARY_HEADING`, `_REVIEW_HEADINGS`, `_REVIEW_HEADING`, `summary_section()`, `content_section()`.
- Keep `final_output(messages) -> str` exactly as is — it already concatenates the text blocks of the last assistant message only, which is the R4 semantics. Keep `parse_status`, `resolve_child_cwd`, `effective_provider_model`, `effective_reasoning_effort`, `build_tau_argv` unchanged.

`dispatch.py`:
- `ParsedRequest` loses the `mode` field: `items`, `agent_scope`, `confirm_project_agents`, `provider`, `model`, `reasoning_effort`, `timeout_seconds`.
- `validate_arguments(arguments: Mapping[str, JSONValue]) -> ParsedRequest`:
  - Allowed fields: `description`, `tasks`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`; anything else (including the removed `agent`/`task`/`cwd`/`chain`) is `unknown field(s): ...`.
  - `tasks` is required: absent or empty → `ValidationFailure` whose message names the contract ("provide a non-empty tasks array …"); not a list → "tasks must be an array"; more than 8 → "at most 8 tasks". Per-item validation is today's `_optional_items` logic applied to `tasks` (non-empty `agent`/`task`, optional string `cwd`, item unknown-field rejection) — the helper may be renamed since only one call site remains.
  - `description`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds` validation is unchanged.
  - Delete the single-mode parsing, the mode-exclusivity logic, and `_mode_hint`.
- Rename `MAX_PARALLEL_TASKS` → `MAX_TASKS` (only call sites are validation and messages).
- `TaskDispatcher.execute`: after the unchanged approval gate, call one execution path for any item count — `results = await self._run_children(request, discovery, agents, signal, on_update)`. Delete `_run_single` and `_run_chain`.
- `_run_parallel` → renamed `_run_children`, logic unchanged (input-ordered slots, `min(MAX_CONCURRENCY, len(items))` workers, `stop_queued` on cancellation/timeout, not-started slot backfill). Its live-update content becomes `f"{complete}/{len(slots)} done"` (no "Parallel:" prefix). Per-message `update` callbacks still feed the usage observer before the frontend update.
- `_run_item`, `_unknown_agent_result`, `_not_started_result`: drop the `step` parameter/field.
- `_final_result(request, discovery, results, *, config, config_diagnostics, planned)` builds content from `results` only, per R5:
  - `len(results) == 1`: success → `final_output(result.messages) or "(no output)"`; failure → `f"Agent {result.agent} failed: {result.error_message or 'see details'}"`.
  - `len(results) > 1`: `f"{succeeded}/{len(results)} succeeded"` + `"\n\n"` + sections joined by `"\n\n\n"`, each section `f"[{result.agent}] ({'completed' if result.succeeded else 'failed'})\n\n{body}"` with `body = final_output(result.messages) or result.error_message or "(no output)"`.
  - Delete `_single_content` and `_summary_or_fallback`.
- `_tool_result` and `_emit_update` lose the `mode` parameter; details come from the new `details_dict`. The validation-failure, headless-denial, and approval-denial early returns keep their current content shapes (minus `mode`).
- Module docstring: validation and parallel orchestration (no "single/parallel/chain").

`extension.py`:
- `_TASK_PARAMETERS`: `"required": ["tasks"]`; `properties` keeps `description`, `tasks` (`minItems: 1`, `maxItems: 8`, unchanged item schema, new description: each item runs as an isolated child; one item runs a single child, two or more run in parallel), `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`. Delete the top-level `agent`, `task`, `cwd`, and `chain` properties.
- Tool `description` (R1 + R9), leading with the threshold: subagents are dispatched for substantive work that benefits from an isolated context window or for long-running work that must not block the session; simple reads, searches, commands, and small edits are the parent's own tool calls; never dispatch work the parent is about to perform itself. Then the call contract: every call takes a `tasks` array — one item runs a single child, two or more run in parallel (max eight, four active), preserving input order; use separate calls for conditional sequences. Keep the bundled-agent and project-approval sentences.
- `prompt_snippet = "Dispatch substantive work to an isolated Tau subagent."`
- `prompt_guidelines` (R9), in order:
  1. Dispatch only substantive multi-step work that benefits from an isolated context window, or long-running work that must not block this session; never dispatch simple reads, searches, commands, or small edits — those are your own tool calls.
  2. A subagent replaces your own tool calls for its task; never dispatch a subagent and then perform the same work yourself.
  3. Always pass `tasks`, even for a single child: one item for one child, several items for parallel work; use separate calls for conditional sequences.
  4. "Include all required context because subagents cannot see this conversation." (unchanged)
  5. Agent choice: `implementation` for implementation work, `code-review` for reviews, `read-only` for substantial read-only investigation of named files (replaces "read-only for plain file inspection").
  6. The provider/model/reasoningEffort guideline (unchanged).
  7. "Handle BLOCKED and NEEDS_CONTEXT reports explicitly." (unchanged)

`runner.py`:
- `TauChildRunner.run`: delete the `step: int | None = None` parameter and its use in the `ChildResult` constructor.
- `_SHARED_INSTRUCTIONS` (R6): keep the `## Delegated Task Rules` section verbatim; replace `## Response Format` with instructions that (a) state the child's complete final assistant message is relayed verbatim to the controller while earlier messages, tool calls, and thinking are not, (b) ask for a self-contained final message covering what was accomplished or found, files read or modified, tests, errors, and concerns, and (c) keep the exact four-bullet status-marker list (`**Status: DONE**`, `DONE_WITH_CONCERNS`, `BLOCKED`, `NEEDS_CONTEXT`). No `## Summary` mandate remains.

`rendering.py` (R7, R8):
- `render_task_call`: `description` override unchanged; otherwise the label derives from the `tasks` list length — `1 child` / `N children` — or `dispatch` when no list is present. Output format unchanged: `▸ Task · {label}`.
- `render_task_result`: return `None` unless `details["schemaVersion"] == 2`; read `results` (list) and `planned`; no `mode`. Empty results → `_empty_render` (content text when non-empty, else `[yellow]•[/yellow] [bold]Task[/bold]`). Non-empty → frame render.
- Frame: `_headline(children, planned) -> str` = `{icon} [bold]task[/bold] · {succeeded}/{total} succeeded` with ` · {failed} failed`, ` · {running} running`, ` · {pending} pending` clauses appended only when positive; icon is `…` while any child is running, else `✗` when any failed, else `✓`. `total` uses `planned` when present (existing `_planned_count` semantics).
- Self-contained child component, one per child in input order:
  - Collapsed: header `─── {agent} {status icon}`; the child's work stream truncated to `COLLAPSED_CHILD_ITEM_COUNT` (or the error line / `(no output)` when there are no items); usage line.
  - Expanded: header; `[dim]Status: {hint}[/dim]` when a hint exists and the child is not running; error line; `[dim]Task:[/dim] {task}`; full work stream; usage line.
  - Component construction is a single helper used for any child count; collapsed components report whether they truncated so the frame can append the existing expand hint.
- Aggregate `_aggregate_usage` `Total:` line only when `len(children) > 1`.
- Delete `_collapsed_single`, `_expanded_single`, `_last_running_step`, `_failed_step`, and the `Step N:` branch of `_child_label` (child label is the agent name, `child {index}` fallback).
- Collapsed/expanded frame layout, status icons/hints, work-item rendering, and usage formatting are otherwise the current multi-child behavior.

Bundled agents (R6, R9):
- `agents/code-review.md`: frontmatter `description` ends "…with a strict `## Code Review` report format." (drop "plus `## Summary`"). The Required Response Format section requires exactly one `## Code Review` section (verdict + Critical/Important/Minor points) ending with the status line; replace "The controller extracts both sections mechanically and relays them to the parent session" with "Your complete final message is relayed verbatim to the controller"; delete the `## Summary` subsection.
- `agents/document-review.md`: identical treatment for `## Document Review`.
- `agents/read-only.md`: frontmatter `description` recast so it cannot license trivial dispatches — e.g. "Read-only subagent for substantial reviews and multi-file investigation of named files. Cannot modify files or run commands." No "code inspection"-style wording that suggests dispatching it for simple reads.
- `agents/general-purpose.md`, `agents/implementation.md`: unchanged (they never mandated `## Summary`).

**Behavior:**
- A call with one item behaves exactly like a parallel call whose worker pool has one worker: one child, live updates with `0/1 done`-style content, final content per R5.
- Validation, approval, unknown-agent, timeout, cancellation, and usage-observer behavior are unchanged apart from the removed `mode`/`step` fields and the new content strings.
- Semantic status (`DONE`/`DONE_WITH_CONCERNS`/`BLOCKED`/`NEEDS_CONTEXT`) parsing, process-failure mapping, and `stderr`/message retention are unchanged.
- Parent-model content never contains tool-call output, thinking, or any assistant message except the last; for the fake-tau fixture child this means content starts with `full output for ...` and never contains `tool output for ...`.

**Tests must prove:**

`tests/test_dispatch.py` (rewrite the mode-related parts; keep the config/approval/observer suites, switching their arguments to `tasks` arrays):
- `test_validation_requires_a_non_empty_tasks_array` — `{}`, `{"tasks": []}`, and a non-list `tasks` are rejected with a message naming the `tasks` contract.
- `test_validation_rejects_removed_mode_fields_as_unknown` — top-level `agent`/`task`/`cwd`/`chain` (alone or beside `tasks`) are unknown fields.
- `test_validation_rejects_invalid_items_and_common_options` (parametrized) — 9 items, empty item `agent`/`task`, non-string item `cwd`, unknown item field, and each invalid common option on a valid one-item base.
- `test_validation_accepts_items_and_independent_overrides` — one item with `cwd` plus call-level provider/model/`reasoningEffort`/`timeoutSeconds` normalization (agent name stripped, `xhigh` lowercased).
- `test_single_item_runs_one_child_and_returns_complete_final_message` — content equals the fixture child's full final text verbatim (`full output for ...\n## Summary\nsummary for ...\n**Status: DONE**`), proving no extraction; details carry the wire messages.
- `test_single_item_failure_returns_concise_failure` — `Agent general-purpose failed: planned failure`.
- `test_multiple_items_run_in_parallel_with_ordered_sections` — concurrency ≤ 4 over 8 items, input order preserved, content starts `8/8 succeeded`, each `[agent] (completed)` section carries that child's full final message.
- `test_failed_child_section_falls_back_to_error_message` — a failed child with no final text contributes its error message as the section body.
- `test_details_use_schema_v2_without_mode_or_step` — `schemaVersion == 2`; no `mode` key; no `step` key in any child result.
- Keep and adapt: timeout-stops-queued-work, headless/UI approval flows, unknown-agent structured failure, config-layering and parent-inheritance tests, usage-observer commit-once/order tests (drop the chain commit test). `FakeRunner` drops its `step` kwarg use.

`tests/test_utils.py`:
- Delete the `summary_section`/`content_section` tests and imports; `final_output`, `parse_status`, precedence, and argv tests are unchanged.

`tests/test_extension.py`:
- `test_setup_registers_exactly_one_task` — additionally: `parameters["required"] == ["tasks"]`, properties contain no `agent`/`task`/`cwd`/`chain`, `tasks` keeps `minItems: 1`/`maxItems: 8`.
- `test_task_tool_prompt_states_threshold_and_homogeneous_tasks` (replaces the exclusivity test) — description states the dispatch threshold (substantive/isolated-context/long-running) and both prohibitions (no trivial tool-call dispatches; no duplicating work between subagent and parent), and the tasks-array contract; snippet is `Dispatch substantive work to an isolated Tau subagent.`; guidelines include the threshold bullet, the anti-duplication bullet, and the always-`tasks` bullet; neither description nor guidelines contain `chain`, `single mode`, or `mutually exclusive`.
- The remaining `execute_task` wiring tests pass `{"tasks": [{"agent": ..., "task": ...}]}` (their fake dispatcher ignores arguments; keep them coherent).

`tests/test_runner.py`:
- `test_compose_prompt_preserves_agent_body_as_prefix` — additionally asserts the new Response Format content (verbatim-relay sentence; the four status markers) and that the prompt does NOT mandate `## Summary`.
- Profile-injection and all other runner tests unchanged.

`tests/test_rendering.py` (fixtures move to `schemaVersion: 2` and drop `mode`/`step`; delete chain tests):
- `test_call_renderer_labels_from_task_count` — description override unchanged; `{"tasks": [{}]}` → `1 child`; three items → `3 children`; empty arguments → `dispatch`.
- `test_frame_renders_single_child_as_one_component` — headline `task · 1/1 succeeded`, one self-contained component (header, streamed work, usage), and no `Total:` line.
- `test_frame_renders_multiple_children_in_order_with_total` — headline counts (`1/2 succeeded · 1 failed`), ordered components, `Total:` aggregate line.
- `test_live_headline_counts_running_and_pending_children` — with `planned: 4` and one running child: `0/4 succeeded · 1 running · 3 pending`.
- `test_expanded_component_shows_task_error_hint_and_full_stream` — status hint, error line, `[dim]Task:[/dim]`, untruncated stream, usage.
- `test_v1_details_return_no_custom_rendering` and the empty-results content-fallback test (fallback bullet no longer carries a mode suffix).
- Keep: status-icon mapping, tool-call/text stream formatting and ordering, truncation + expand hint, usage formatting (these move unchanged onto component/frame fixtures).

`tests/test_runtime_integration.py`:
- `test_real_tau_cli_loads_directory_extension_and_registers_task` — expected line becomes `- task: Dispatch substantive work to an isolated Tau subagent.`.
- `test_real_runtime_executes_single_and_parallel_with_ordered_updates` (renamed) — all calls use `tasks` arrays; the one-item call's text equals the fixture child's complete final message verbatim and never contains `tool output for`; the three-item call's text starts `3/3 succeeded` with input-ordered results; updates remain schema-v2 and ordered; the fake-tau log shows 4 starts total (1 + 3) and read-only policy only for the `read-only` item. The chain portion is deleted.
- `test_coding_session_propagates_task_partial_updates_and_final_message_content` (renamed from `..._small_result_context`) — one-item `tasks` call; the final result text and the controller-visible tool result equal the child's complete final message and contain no tool-call output.
- Failure/timeout/cancellation/approval/thinking-inheritance tests: wrap existing arguments in one-item `tasks` arrays; assertions otherwise unchanged.

**Verify:** `PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest && PYTHONPATH="$TAU_SITE_PACKAGES" uv run mypy && uv run ruff check . && uv run ruff format --check .` — expected: all pass.

- [x] Create the feature branch (`git checkout -b feature/homogeneous-task-interface`) if not already on it
- [x] Write the failing tests for the behaviors above; run them and confirm each fails for the expected reason
- [x] Implement the interface and behavior changes across the six source files and three agent definitions
- [x] Run verification (full suite, mypy, ruff check, ruff format --check)
- [x] Commit: `git add extensions/superpowers-subagent && git commit -m "refactor: homogeneous tasks-only interface with final-message results"`

---

### Task 2: Skills alignment

**Files:**
- Modify: `skills/using-superpowers/references/tau-tools.md` — the canonical `task` reference (R1, R3, R4, R5, R6, R7, R9, R10)
- Modify: `skills/using-superpowers/SKILL.md` — strengthen Simple Operations (R9)
- Modify: `skills/dispatching-parallel-agents/SKILL.md` — trigger description and framing (R9, R10)
- Modify: `skills/requesting-code-review/SKILL.md` — `tasks` example, result wording (R1, R6, R10)
- Modify: `skills/requesting-code-review/code-reviewer.md` — `tasks` example, output format without `## Summary` (R1, R6, R10)
- Modify: `skills/subagent-driven-development/implementer-prompt.md` — `tasks` example (R1, R10)
- Modify: `skills/subagent-driven-development/implementation-reviewer-prompt.md` — `tasks` example, output format without `## Summary` (R1, R6, R10)
- Modify: `skills/subagent-driven-development/SKILL.md` — example cycle (R6, R10)
- Modify: `skills/writing-plans/plan-document-reviewer-prompt.md` — `tasks` example, result/output-format wording (R1, R6, R10)
- Modify: `skills/brainstorming/spec-document-reviewer-prompt.md` — same (R1, R6, R10)
- Modify: `skills/writing-skills/testing-skills-with-subagents.md` — RED/GREEN `tasks` examples, chain/extraction wording (R1, R3, R4, R10)
- Modify: `skills/writing-skills/examples/skill-testing-example.md` — single-mode/chain wording (R3, R10)
- Explicitly unchanged: `executing-plans`, `finishing-a-development-branch` (its `## Summary` is a PR-body template), `receiving-code-review`, `systematic-debugging`, `test-driven-development`, `using-git-worktrees`, `verification-before-completion`, `writing-plans/SKILL.md`, `writing-skills/SKILL.md`, `brainstorming/SKILL.md` — none reference the task-tool modes or extraction.

**Spec requirement:** R1, R3, R4, R6, R9, R10 (skills portion).

**Interface:** N/A — documentation content contracts only.

**Behavior:**

`tau-tools.md` (rewrite the affected sections; everything else stays):
- Intro: the tool launches isolated `tau` subprocesses for one or more delegated tasks (drop "single, parallel, or chained").
- Replace the Single/Parallel/Chain sections with one **Task list** section: `tasks` is required, 1–8 items of `{agent, task, cwd?}`; one item runs a single child, two or more run in parallel (max four concurrently, input-ordered results); each item may carry its own `cwd`. Include one one-item example and one multi-item example.
- Delete the chain section, the `{previous}` description, and the "chain stops / semantic status does not stop the chain" paragraph; conditional loops are expressed as: inspect each result and make separate `task` calls.
- Common Options: replace "In parallel and chain modes, put `cwd` on each item rather than at the top level" — `cwd` only exists per item now.
- Add a short **When to dispatch** section (R9): substantive multi-step work that benefits from an isolated context window, or long-running work that must not block the session; simple reads/searches/commands/small edits are the parent's own tool calls; a subagent replaces the parent's tool calls for its task — never dispatch work you are about to perform yourself.
- Profile table: the `read-only` row's use column becomes substantial multi-file investigation/review of named files (no "inspection of known files" phrasing).
- Review-format paragraph: `code-review` returns a strict `## Code Review` report ending in the status line; `document-review` returns `## Document Review` likewise; the child's complete final message is the result content (delete "plus `## Summary`" and "relays both sections").
- **Results and Status**: content contract per R5 (one child → bare final message or concise failure; several → `<succeeded>/<total> succeeded` header with `[agent] (completed|failed)` sections whose bodies are complete final messages); explicitly: content is only the final assistant message's text — never tool calls, thinking, or earlier messages — and no heading extraction exists. The details block becomes `schemaVersion: 2` with no `mode` and no `step`. Delete "summary-sized" phrasing; `details.results[].messages` remains the place to inspect tool calls and earlier messages.
- The review-call example at the end uses a one-item `tasks` array; its prompt template drops the `## Summary` requirement (strict `## Code Review` + status line).
- Delete the closing "Use chain mode only for unconditional pipelines" sentence; keep the separate-calls guidance for conditional loops.

`using-superpowers/SKILL.md` — Simple Operations section: keep the existing list, and add the two positive dispatch criteria (substantive work that benefits from an isolated context window; long-running work that must not block the session) plus the anti-duplication rule: never dispatch a subagent and then perform the same read/command yourself — dispatch replaces your tool calls for that work.

`dispatching-parallel-agents/SKILL.md` — frontmatter description: "Use when facing 2+ independent substantive tasks that can be worked on without shared state or sequential dependencies". In "Dispatch in Parallel", note the same `tasks` shape with one item dispatches a single child (this skill remains about parallel work).

`requesting-code-review/SKILL.md` — the dispatch JSON becomes `{"tasks": [{"agent": "code-review", "task": "[FILLED PROMPT]"}]}`; the result sentence becomes: the result content is the reviewer's complete final message — the `## Code Review` report ending in the status line.

`requesting-code-review/code-reviewer.md` — same JSON wrap; the strict output format requires exactly one `## Code Review` section (verdict, Critical/Important/Minor, self-contained points) ending with the status line; delete the `## Summary` requirement.

`subagent-driven-development/implementer-prompt.md` — wrap the call-shape JSON in a one-item `tasks` array (its report format already ends in a status line; otherwise unchanged).

`subagent-driven-development/implementation-reviewer-prompt.md` — same JSON wrap; the strict output format drops the `## Summary` section, keeping `## Code Review` (with the Spec Compliance and Code Quality dimensions) ending in the status line.

`subagent-driven-development/SKILL.md` — in the Example Task Cycle, delete the `## Summary ...` line from the reviewer output sketch.

`writing-plans/plan-document-reviewer-prompt.md` and `brainstorming/spec-document-reviewer-prompt.md` — wrap the JSON in one-item `tasks` arrays; replace "The result contains a `## Document Review` section (verdict + findings) followed by a `## Summary`" with: the result content is the reviewer's complete final message — the `## Document Review` report ending in the status line; their strict output formats drop the `## Summary` section.

`writing-skills/testing-skills-with-subagents.md` — RED and GREEN calls use one-item `tasks` arrays; replace "Do not use chain mode: baseline and skill-present trials must be independent, not inherit `{previous}`" with "Give baseline and skill-present trials separate `task` calls so they stay independent"; replace "`task` content is summary-sized, so inspect `details.results[0].messages` when recording the child's exact wording" with: content is the child's complete final message; inspect `details.results[0].messages` when you need tool calls or earlier messages.

`writing-skills/examples/skill-testing-example.md` — "isolated single-mode `task` calls" becomes "isolated `task` calls (a one-item `tasks` array)"; "Do not use chain mode or `{previous}`; trials must remain independent." becomes "Give every trial its own independent call."

**Tests must prove:** N/A — gate on these exact checks instead:
- `rg -n '\{previous\}' skills/` → no matches
- `rg -ni 'chain mode|"chain"|single mode|single-mode' skills/` → no matches
- `rg -n '"agent":' skills/` → every match sits inside a `tasks` array example (manual review of the matches)
- `rg -n 'summary-sized|extracted summary|extracts both sections|plus `## Summary`' skills/` → no matches
- `rg -n '## Summary' skills/subagent-driven-development skills/requesting-code-review skills/writing-plans skills/brainstorming` → no matches (the PR template in finishing-a-development-branch is out of scope)
- `rg -n 'plain file inspection|Inspection of known files' skills/` → no matches
- Read every changed file end-to-end for coherence.

**Verify:** the gates above — expected: clean.

- [x] Apply the content changes to the twelve skill files
- [x] Run the `rg` gates and read each changed file
- [x] Commit: `git add skills && git commit -m "docs: align skills with homogeneous task interface and dispatch threshold"`

---

### Task 3: README and docs alignment

**Files:**
- Modify: `README.md` — `task` extension section (R1, R3, R4, R5, R6, R9, R10)
- Modify: `docs/specs/subagent-dispatch.md` — the living spec (all requirements)
- Modify: `docs/FLOW_DESCRIPTION.md` — flow narrative (R1, R3, R4, R6, R10)
- Explicitly unchanged: `docs/design/*.md`, `docs/plans/*.md` (dated historical records), `install.sh`, `tests/test-install.sh`.

**Spec requirement:** R1–R10 (documentation portion).

**Interface:** N/A — documentation content contracts only.

**Behavior:**

`README.md`:
- Intro bullet: the `task` tool dispatches one or more isolated Tau subprocesses (drop "single, parallel, and chained"); bundled-agents bullet: reviewers return strict `## Code Review` / `## Document Review` reports (drop "+ `## Summary`").
- `## The task Extension` section: state the dispatch threshold in one or two sentences (R9); replace the `### Single` / `### Parallel` / `### Chain` subsections with one `### Task list` subsection documenting the required `tasks` array (1–8 items, per-item `cwd`), one-item and multi-item JSON examples, and the execution semantics (one child per item; 2+ run in parallel, max four active, input order preserved; conditional work uses separate calls). Delete the chain example and the chain-stops paragraph; delete "In single mode, `cwd` is top-level. Parallel and chain items each carry their own optional `cwd`." (`cwd` is per item).
- Result-contract pointer sentence: parent-model content is each child's complete final assistant message (one child → bare message; several → counts header + per-child sections); structured details keep the complete wire messages.
- Verify the "Live TUI visibility" paragraph still matches the renderer (counts headline, per-child components, expand hint, aggregate usage) and adjust wording where it assumes modes.

`docs/specs/subagent-dispatch.md` (living spec — rewrite to describe only the new behavior):
- Purpose: one homogeneous `tasks` interface; final-message content; no chain.
- "Requirement: task modes and validation" → "task interface and validation": required non-empty `tasks` (1–8 items, item schema, per-item `cwd`), removed fields rejected as unknown, ≤4 concurrency, input order; scenarios become Single-item dispatch (one item → one child), Ordered parallel dispatch, and Invalid request (missing/empty/oversized `tasks`, invalid items, unknown fields including the removed mode fields, invalid common options). Delete the three chain scenarios.
- "Requirement: Summary and code-review extraction, and status" → "Requirement: final-message content and status": content is the last accepted assistant message's concatenated text blocks (never tool calls, thinking, or earlier messages); no heading extraction; the child instructions require a self-contained final message ending in one status marker; reviewer agents keep `## Code Review`/`## Document Review` report formats without `## Summary`; status parsing paragraph and its scenarios carry over unchanged.
- "Requirement: Context-small content and complete details" → content contract per R5; details per R7 (`schemaVersion: 2`, no `mode`/`step`); scenarios updated (single success → content is the complete final message; parallel mixed outcome; chain-failure scenario deleted; semantic-status scenario kept).
- "Requirement: Isolated Tau child invocation": the appended-prompt paragraph reflects the new Response Format instructions (verbatim relay, self-contained final message, status markers).
- "Requirement: Progress, cancellation, timeout, and cleanup": updates are per accepted message/completion with `<done>/<planned> done` content and input-ordered slots for any item count.
- "Requirement: Portable rendering": one frame+components view for any child count (R8); live-counts scenario uses `planned`; delete chain/single-mode-specific rendering language.
- Add to the tool-registration/discovery requirement (or the purpose) that the tool's prompt surface states the dispatch threshold (R9) as behavioral guidance.
- "Intentional Port Differences": the opening sentence no longer claims all three dispatch modes are preserved; add rows for the removed chain mode and the removed summary extraction if the table format benefits.
- "Security Boundaries": replace the "Summary extraction is a context-management feature" bullet with the final-message rule (content is only the final assistant message; complete accepted messages remain in `details`).

`docs/FLOW_DESCRIPTION.md`:
- Agent table rows: reviewers return strict `## Code Review` / `## Document Review` reports ending in a status line (drop "+ `## Summary`").
- The "typical reviewer call" JSON uses a one-item `tasks` array.
- Replace "Use parallel mode only for independent work and chain mode only for unconditional pipelines; conditional implement/review/fix loops require separate calls…" with: multiple items in one call run in parallel and must be independent; conditional implement/review/fix loops require separate calls so the controller can inspect each result.
- Pipeline diagram: "final assistant text parsed for last exact ## Summary" becomes "final assistant message becomes parent content".
- Edge-case table row: drop "automatic chain stopping" from the semantic-blocker row (re-dispatch or escalate).
- Closing "Isolation Boundaries" paragraph: "parent content uses the extracted summary when present and complete final output as fallback when absent" becomes: parent content is the child's complete final assistant message; complete accepted messages remain in structured details.

**Tests must prove:** N/A — gate on these exact checks instead:
- `rg -n '\{previous\}' README.md docs/specs/subagent-dispatch.md docs/FLOW_DESCRIPTION.md` → no matches
- `rg -ni 'chain mode|chain dispatch|"chain"' README.md docs/specs/subagent-dispatch.md docs/FLOW_DESCRIPTION.md` → no matches
- `rg -n 'single mode|## Summary|summary-sized|extracted summary|schemaVersion": 1|schemaVersion: 1' README.md docs/specs/subagent-dispatch.md docs/FLOW_DESCRIPTION.md` → no matches
- `rg -n 'schemaVersion' docs/specs/subagent-dispatch.md` → documents `2`
- Read every changed file end-to-end for coherence and internal consistency.

**Verify:** the gates above — expected: clean.

- [x] Apply the content changes to README.md, docs/specs/subagent-dispatch.md, docs/FLOW_DESCRIPTION.md
- [x] Run the `rg` gates and read each changed file
- [x] Commit: `git add README.md docs && git commit -m "docs: align README and specs with homogeneous task interface"`

---

## Self-review notes

- **Coverage:** R1–R8 (code) → Task 1; R9 → Task 1 (extension prompt surfaces, agent description) + Task 2 (skills) + Task 3 (README/spec); R10 → Tasks 2–3. Every requirement has a task and verification.
- **Reverse coverage:** no task introduces behavior outside R1–R10.
- **Atomicity:** Task 1 is one commit because `schemaVersion: 2` and the removed `mode`/`step` fields couple dispatch, rendering, and the runtime tests — no smaller split keeps the suite green. Tasks 2–3 are docs-only and independently verifiable.
- **Standards:** the change deletes more than it adds (one execution path, one rendering path, no extraction helpers); no new abstractions beyond the single child-component helper the operator requested.
