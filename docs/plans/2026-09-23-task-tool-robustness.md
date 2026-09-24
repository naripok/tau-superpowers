# Two-tool task dispatch with fail-closed validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Execute this plan task-by-task with the skill the workflow depth selects: executing-plans for Bounded, subagent-driven-development for Standard or High-risk. The controller marks every checkbox of a task `[x]` in the plan file when the task completes its gate, and records each flip in one tracking commit named `docs(plan): mark <plan-file-stem> Task N complete`.

**Goal:** Replace the flat `task` tool with two minimal tools, `task` and `task_resume`, that fail closed on every invalid argument, remove every call-level provider, model, and reasoning-effort override, fix the dispatch environment, and recover the resume agent from a new session-agent mapping.

**Architecture:** One execution core, two registrations. `setup()` registers `task` and `task_resume`, each with its own schema, description, and prompt guidelines. Both execute through the `TaskDispatcher`, whose `ParsedRequest` carries an explicit mode. The runner keeps the fresh and resume paths and drops every fallback. A new extension-owned mapping module records the agent for every child session before the child spawns, and resume verification reads it first.

**Tech Stack:** Python 3.14, pytest with pytest-asyncio, mypy strict, ruff. The extension runs inside Tau and spawns `tau` child processes in JSON mode.

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-unambiguous-text prose.

**Feature spec:** `docs/design/2026-09-23-task-tool-robustness-spec.md` (the behavioral contract. approved at commit `6df40f1`)

**Approved proposal:** `docs/design/2026-09-23-task-tool-robustness-proposal.md` (intent, scope, binding architecture, constraints, non-goals, acceptance, and risk treatment. the exact operator-approved version at commit `ea73145`, content sha256 `ebf41f7278d3cff1292ace152334a902cb195140ae1edaf448a53dfdb00af131`)

---

## Commands

Run every check from `extensions/superpowers-subagent/`. The extension imports Tau packages (`tau_agent`, `tau_coding`) from the installed runtime, so `PYTHONPATH` must include the Tau site-packages directory.

```bash
cd extensions/superpowers-subagent
TAU_PYTHON=$(sed -n '1s/^#!//p' "$(command -v tau)")
TAU_SITE_PACKAGES=$("$TAU_PYTHON" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest -q
PYTHONPATH="$TAU_SITE_PACKAGES" uv run mypy
uv run ruff check .
uv run ruff format --check .
```

Baseline before Task 1: 352 passed at commit `93d87e3`. The immutable baseline transcript is `docs/design/evidence/task-tool-robustness/baseline-tests/transcript.txt`.

Gate rule for the suite count: a task's gate replaces superseded tests only where this plan names the replacement. The gate count must equal the previous gate count minus the tests that the task states it replaces, plus the task's new tests. Any unexplained drop fails the task's gate.

## High-risk obligation mapping

| Obligation | Mapped to |
| --- | --- |
| Compatibility: breaking parameter-surface change, every consumer updated in-branch, no legacy tool or alias | Task 5 (removed parameters fail closed), Task 6 (two-tool surface), Task 7 (every consumer file in the proposal Impact list) |
| Migration: operator re-installs the extension and skills and restarts sessions. pre-change sessions have no mapping entries, so their resumes fail closed. stale `reasoningEffort` keys keep working with a diagnostic and a dropped pin | Task 2 (config diagnostic), Task 4 (fail-closed resume), Task 7 (README operator notes state all three) |
| Rollout: extension version stays 0.1.0. behavior changes after session restart | Task 9 check asserts `pyproject.toml` still reads `version = "0.1.0"` |
| Rollback: revert branch commits, re-install the prior extension and skills, restart. the mapping file survives as inert state the prior surface ignores | Task 7 documents the rollback note in the README. the plan touches only extension code, skills, and docs, so a branch revert restores the prior surface |
| Observability: envelope and `details.results[].taskId` record every child session id. `tau sessions --all` lists child sessions. the mapping is an inspectable JSON file. a post-implementation transcript is recorded | Tasks 4, 6 (behavior and tests), Task 9 (transcript in the baseline format) |
| Recovery: quiescent store maintenance gains the mapping-entry deletion step | Task 7 (README operator notes carry the six-step procedure) |
| Risk treatment: no call cap | Task 6 preserves the existing no-cap test and extends it to `task_resume` |
| Risk treatment: camelCase priors (`timeoutSeconds`, `agentScope`, `reasoningEffort`) | Task 5 and Task 6 (teach-back wording), Task 8 (agent-facing evaluation measures the residual rate) |
| Risk treatment: mapping state (new durable file, corruption, stale entries) | Task 1 (module), Task 4 (write-before-spawn, fail-closed lookup), Task 7 (README operator note) |
| Risk treatment: stale-id cost, resumed-run usage undercount, direct `tau --session` overlap, resume definition drift, cross-project resume of a project-layer mapped agent, fixed spawn cwd, project-agent exposure, different-agent resume removal | Accepted operator exposures. Task 7 states each in the README. The undercount and the direct-overlap behavior keep their existing tests unchanged |

## Preservation mapping

Established unchanged baseline behavior gets regression checks only, never change work. The following keep their existing tests passing untouched:

- Envelope form, id semantics, state semantics, verbatim inner content, pre-session failure envelopes (`dispatch.py` envelope code, existing tests)
- Child status markers, progress form `<done>/1 done`, partial updates, cancellation, timeout mechanism, hard-kill and temporary-file cleanup, stdout JSONL collection, usage accumulation, stderr excerpt bounding (`runner.py` internals, existing `test_runner.py` tests)
- Same-id lock mechanics (`locking.py`, `test_locking.py`)
- Catalog scoping core and catalog snapshot construction (`catalog.py` scoping code, `test_catalog.py`. Task 5 rewords two error strings only)
- Config loading, merging, per-key shadowing, unknown-key diagnostics, `configPaths` and `configDiagnostics` reporting (`config.py`, `test_config.py`. Task 2 renames one key)
- Discovery layer precedence, skip diagnostics, frontmatter parsing (`discovery.py`, `test_discovery.py`. Tasks 3 and 5 make the named changes)
- Usage tracking and sidebar contract (`usage.py`, `sidebar.py`, `test_usage.py`, `test_sidebar.py`)
- Cost estimation (`costing.py`, `test_costing.py`)
- Result-frame rendering, icons, usage lines, live updates (`rendering.py`, `test_rendering.py`. Task 6 adds the resume call renderer only)
- Child argv construction for fresh and resumed runs (`utils.py` `build_tau_argv`, existing `test_utils.py` tests)
- Recursion guard behavior (`extension.py` guard, existing tests. The existing `test_setup_refuses_recursive_registration` assertion needs no edit: it proves neither tool registers)
- Resume continuation semantics: retained context, resume-variant isolation sentence, recorded creation cwd, timeout bounding, usage covering the resumed run only (`runner.py`, existing `test_runner.py` and `test_runtime_integration.py` tests, updated only where the plan names the change)

## Requirement and acceptance coverage

| Spec requirement | Tasks |
| --- | --- |
| ADDED Two-tool task surface | Task 4, Task 5, Task 6 |
| ADDED Cross-tool field rejection | Task 6 |
| ADDED Fail-closed validation | Task 4, Task 5, Task 6 |
| ADDED Session-agent mapping | Task 1, Task 4 |
| ADDED Fail-closed resume | Task 4, Task 6 |
| ADDED Fixed dispatch environment | Task 3, Task 5 |
| ADDED Per-tool descriptions | Task 6 |
| ADDED Clean-cut consumer update | Task 2, Task 7 |
| MODIFIED task_id resume | Task 4, Task 6 |
| MODIFIED Resume working directory | Task 4 (preservation checks), Task 5 (no `cwd` parameter) |
| MODIFIED Agent definition discovery | Task 3 |
| MODIFIED Provider, model, and reasoning-effort overrides | Task 5 |
| MODIFIED Isolated Tau child invocation | Task 4, Task 5, Task 6 (two-tool registration; the existing recursion-guard test `test_setup_refuses_recursive_registration` needs no edit) |
| MODIFIED Subagent configuration file | Task 2 |
| MODIFIED Tau JSON collection | Task 4 |
| MODIFIED Task result envelope | Task 4, Task 5 |
| MODIFIED Content envelope and complete details | Task 4, Task 5 |
| MODIFIED Progress, cancellation, timeout, and cleanup | Task 6 |
| MODIFIED Portable rendering | Task 6 |
| MODIFIED Tool description roster | Task 3, Task 6 |
| MODIFIED Concurrent task calls | Task 6 |
| MODIFIED Same-task_id exclusion | Task 6 |
| MODIFIED Pinned child sessions | Task 4, Task 7 |
| REMOVED task interface and validation | Task 5, Task 6 |
| REMOVED Explicit project-agent approval | Task 5 |
| REMOVED Unknown task_id fallback | Task 4 |

Acceptance examples 1 to 14 map to Tasks 3 to 6 and Task 8: example 1 (minimal fresh call) to Task 6. example 2 (code-review dispatch) to Task 6. example 3 (valid resume) to Tasks 4 and 6. example 4 (`task` with `task_id`) to Task 6. example 5 (unknown resume) to Tasks 4 and 6. example 6 (resume without `task_id`) to Task 6. example 7 (`cwd` on `task`) to Tasks 5 and 6. example 8 (`timeoutSeconds`) to Task 6. example 9 (project-layer dispatch and roster) to Tasks 3 and 5. example 10 (same-id resume pair) to Task 6. example 11 (unconfigured provider pin) to Task 5. example 12 (missing mapping entry) to Task 4. example 13 (background on both tools) to Task 6. example 14 (resume `timeout_seconds` 7200) to Task 6. Task 8 measures examples 1, 3, 5, and 8 end to end through a real model.

---

### Task 1: Session-agent mapping module

**Files:**
- Create: `extensions/superpowers-subagent/superpowers_subagent/mapping.py` — the durable session-id to agent-name mapping and its process-safe write path
- Modify: `extensions/superpowers-subagent/superpowers_subagent/locking.py` — add a blocking exclusive-file-lock helper shared with the mapping
- Test: `extensions/superpowers-subagent/tests/test_mapping.py`
- Test: `extensions/superpowers-subagent/tests/test_locking.py`

**Spec or proposal source:** Spec ADDED "Session-agent mapping" (file location, dedicated lock, atomic write-and-rename, corrupted-file handling, lookup). Proposal Approach "Session-agent mapping".

**Proposal constraints:** The mapping lives at `~/.tau/superpowers-subagent-sessions.json`, a sibling of `superpowers-subagent.toml`. The lock uses the same file-lock mechanism as the same-id lock. Writes serialize through a dedicated process-safe mapping lock held across each read-modify-write cycle. Each write lands through atomic write-and-rename. A corrupted or unreadable file rebuilds from an empty map on write and counts as a missing entry on read. The mapping is append-only across normal operation. No caller changes behavior in this task. the full suite stays green.

**Interface:**
- `MAPPING_FILENAME: str` — the constant `"superpowers-subagent-sessions.json"`.
- `default_mapping_path() -> Path` — returns `TauPaths().home / MAPPING_FILENAME`. It resolves `Path.home()` per call, never at import time, so tests can redirect `HOME`.
- `class MappingWriteError(OSError)` — raised when a mapping entry cannot be persisted: the lock file cannot be created or opened, the directory cannot be created or written, or the rename fails. A corrupted or unreadable existing mapping file is not a write failure. it rebuilds.
- `read_mapping_entry(session_id: str, *, mapping_path: Path | None = None) -> str | None` — returns the mapped agent name for `session_id`. Returns `None` when the file is missing, unreadable, or corrupted, or when the id has no entry. A corrupted file means failed JSON decoding, failed Unicode decoding, a non-object top level, or a non-string value.
- `write_mapping_entry(session_id: str, agent_name: str, *, mapping_path: Path | None = None) -> None` — performs a read-modify-write of the whole file under the mapping lock and lands it through atomic write-and-rename. The mapping path defaults to `default_mapping_path()`. The lock file is `<mapping_path>.lock`, created if missing. The JSON format is one object whose keys are session ids and whose values are agent-name strings, serialized with `json.dumps(..., indent=2, sort_keys=True)` plus a trailing newline.
- `locking.exclusive_lock(path: Path) -> AbstractContextManager[None]` — acquires a blocking `fcntl.flock` exclusive lock on `path`, creating the file when missing with the same `O_RDWR | O_CREAT | O_CLOEXEC` flags as `same_id_lock`. It blocks until the lock is held and releases on context exit. Refactor `same_id_lock` to share the file-open and held-lock internals with this helper. its non-blocking signature and behavior stay unchanged.

**Behavior:**
- `write_mapping_entry("s1", "code-review")` on a missing file creates the file with exactly one entry.
- A second `write_mapping_entry("s2", "read-only")` preserves the `s1` entry: the write is a read-modify-write, not an overwrite.
- Two threads calling `write_mapping_entry` concurrently keep both entries, because the blocking lock serializes the read-modify-write cycles.
- When the existing file contains corrupted content, `write_mapping_entry` rebuilds it from an empty map plus the new entry, and `read_mapping_entry` returns `None` for every pre-existing id.
- When the mapping directory cannot be written, `write_mapping_entry` raises `MappingWriteError` and starts no rewrite.
- `read_mapping_entry` on a missing file returns `None` and creates nothing.

**Tests must prove:**
- A written entry reads back as the agent name
- A second write preserves the first entry
- Two concurrent writes keep both entries
- A corrupted file rebuilds from an empty map plus the new entry on write
- A corrupted file reads as a missing entry
- An unwritable mapping directory raises `MappingWriteError`
- A missing file reads as `None` without creating anything
- `default_mapping_path()` returns `~/.tau/superpowers-subagent-sessions.json` with `HOME` redirected
- `exclusive_lock` blocks until held and releases on context exit (a second acquire from another thread succeeds only after release)

**Check:** the four Commands-section commands. Expected: all pass.

- [x] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [x] Implement the interface and behavior
- [x] Run verification (tests, lint, type check)
- [x] Commit: `git add extensions/superpowers-subagent/superpowers_subagent/mapping.py extensions/superpowers-subagent/superpowers_subagent/locking.py extensions/superpowers-subagent/tests/test_mapping.py extensions/superpowers-subagent/tests/test_locking.py && git commit -m "feat: add session-agent mapping module"`

### Task 2: Config-file reasoning-effort key rename

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/config.py` — rename the reasoning-effort key
- Modify: `extensions/superpowers-subagent/superpowers-subagent.example.toml` — renamed key and four-layer precedence comment
- Test: `extensions/superpowers-subagent/tests/test_config.py`
- Test: `extensions/superpowers-subagent/tests/test_runtime_integration.py`

**Spec or proposal source:** Spec MODIFIED "Subagent configuration file" (key mandate renames to `provider`, `model`, `reasoning_effort`. the stale camelCase key follows the existing unknown-key diagnostic rule). Proposal Required Outcome 4 and Approach "Key rename".

**Proposal constraints:** The config-file and frontmatter keys are `provider`, `model`, and `reasoning_effort`. A config file that still carries `reasoningEffort` produces the unknown-key diagnostic, loses that pin, and dispatch proceeds without it until the operator renames the key. The example file ships renamed, with its precedence comment reduced to the four-layer chain of Required Outcome 4. No other config behavior changes.

**Interface:**
- `config._VALID_KEYS` — before: `{"provider", "model", "reasoningEffort"}`. After: `{"provider", "model", "reasoning_effort"}`.
- `config._parse_overrides(table, path, section, diagnostics)` — reads the `reasoning_effort` key with `_parse_thinking_level` and reports the section label `f"{section}.reasoning_effort"`. Before: it read `reasoningEffort`. Unknown keys, wrong-typed tables, empty strings, and invalid thinking levels keep the existing drop-with-diagnostic behavior.

**Behavior:**
- A config file with `reasoning_effort = "high"` under `[defaults]` or `[agents.<name>]` resolves the pin exactly as `reasoningEffort` did before.
- A config file that carries `reasoningEffort = "high"` produces the diagnostic `Subagent config <path>: ignoring unknown key <section>.reasoningEffort`, drops the pin, and keeps every other valid key.
- The example TOML comment block states the four-layer chain: config `[agents.<name>]`, agent-definition frontmatter, config `[defaults]`, parent session. Every `reasoningEffort` occurrence in the file becomes `reasoning_effort`.

**Tests must prove:**
- A `reasoning_effort` value resolves under `[defaults]` and under `[agents.<name>]` (replaces the tests that use the camelCase key)
- A stale `reasoningEffort` key produces the unknown-key diagnostic and loses only that pin (replaces the camelCase-key tests. the diagnostic text asserts the stale key name)

This task replaces the `test_config.py` tests that assert the camelCase key. It also updates `tests/test_runtime_integration.py::test_real_runtime_inherits_parent_thinking_level_and_config_overrides`, whose config fixture writes `reasoningEffort = "high"`: the fixture renames the key to `reasoning_effort`, and the test's assertions keep the runtime's own child-record key `reasoningEffort` unchanged. No other existing test changes.

**Check:** the four Commands-section commands. Expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent/superpowers_subagent/config.py extensions/superpowers-subagent/superpowers-subagent.example.toml extensions/superpowers-subagent/tests/test_config.py extensions/superpowers-subagent/tests/test_runtime_integration.py && git commit -m "feat: rename the config reasoning-effort key to reasoning_effort"`

### Task 3: Agent discovery fixed to all layers

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/discovery.py` — all-layer discovery, frontmatter key rename, stale-key diagnostic
- Modify: `extensions/superpowers-subagent/superpowers_subagent/extension.py` — the session-start roster discovers all layers
- Modify: `extensions/superpowers-subagent/superpowers_subagent/dispatch.py` — the discovery callable loses the scope argument. teach-back rosters list all layers
- Modify: `extensions/superpowers-subagent/superpowers_subagent/catalog.py` — the discovery call loses the scope argument
- Test: `extensions/superpowers-subagent/tests/test_discovery.py`
- Test: `extensions/superpowers-subagent/tests/test_extension.py`
- Test: `extensions/superpowers-subagent/tests/test_dispatch.py`
- Test: `extensions/superpowers-subagent/tests/test_catalog.py`

**Spec or proposal source:** Spec ADDED "Fixed dispatch environment" (discovery fixed to all layers), MODIFIED "Agent definition discovery" (three-layer structure stays, `reasoningEffort` frontmatter key renames to `reasoning_effort`, stale-key diagnostic exception, roster names project agents), MODIFIED "Tool description roster" (session-start roster widens to all layers. teach-back rosters include project agents).

**Proposal constraints:** Discovery is fixed to all layers: bundled agents, `~/.tau/agents` definitions, and the nearest ancestor `.tau/agents` definitions, with the collision precedence of the baseline (project replaces user, user replaces bundled). No per-call control narrows or widens discovery. The stale key produces a discovery diagnostic, the pin is dropped, and the definition otherwise loads. Other unknown frontmatter keys stay ignored without a diagnostic. All developer-facing text follows the writing-unambiguous-text skill.

**Interface:**
- `discover_agents(cwd: Path, *, bundled_dir: Path | None = None, user_dir: Path | None = None) -> DiscoveryResult` — before: took a `scope: AgentScope` parameter and selected layers from it. After: always discovers the bundled layer, the user layer, and the nearest ancestor project layer, and applies the collision precedence. The `scope` parameter is removed.
- `discovery._agent_from_metadata(metadata, body, source, path, diagnostics: list[str]) -> AgentConfig` — gains a `diagnostics` list parameter. It reads the reasoning-effort pin from `reasoning_effort`. When `metadata` carries the stale `reasoningEffort` key, it appends a diagnostic that names the file and the stale key, drops that pin, and loads the definition with its remaining metadata. Any other unknown metadata key stays ignored.
- `extension._agent_roster(cwd)` — calls `discover_agents` without a scope. The docstring states that the roster covers the bundled, user, and project layers.
- `dispatch.DiscoveryFn` — before: `Callable[[Path, AgentScope], DiscoveryResult]`. After: `Callable[[Path], DiscoveryResult]`.
- `dispatch._teach_back_roster(dispatcher)` — before: discovered at call time at user scope and filtered out project agents. After: returns `dispatcher.roster_text`, the static session-start roster, so the teach-back roster lists the same agents as the description roster. The docstring states the static session-start roster.
- `dispatch.TaskDispatcher.__init__(...)` — gains a `roster_text: str` parameter stored on the instance. `extension.execute_task` passes the session-start `roster_text` it already computes.
- `catalog.scoped_catalog_snapshot` — calls `discover_agents(cwd)` without a scope. No other catalog change.

**Behavior:**
- Discovery from a cwd whose nearest ancestor has `.tau/agents` includes those project agents, and a project definition replaces a user or bundled definition with the same name.
- Discovery from a cwd with no ancestor `.tau/agents` behaves as before: bundled plus user layers.
- A definition carrying `reasoningEffort: high` loads with a diagnostic that names the stale key, and its reasoning-effort pin is `None`.
- A definition carrying an unknown key other than `reasoningEffort` loads with no diagnostic.
- The session-start roster and every `task` teach-back roster list the bundled, user, and project agents discovered at session start, and the teach-back roster equals the description roster text.

**Tests must prove:**
- All three layers are discovered without a scope argument, and the collision precedence holds (replaces the scope-selection tests in `test_discovery.py`)
- The stale frontmatter key produces the diagnostic, drops the pin, and keeps the remaining metadata
- Another unknown frontmatter key stays ignored without a diagnostic
- The session-start roster includes a project-layer agent when one exists (new `test_extension.py` test pinning a project `.tau/agents` directory)
- A `task` teach-back roster names a project-layer agent (new `test_dispatch.py` test whose fake dispatcher carries a session-start roster naming a project agent)

This task replaces the `test_discovery.py` scope-selection tests, `tests/test_extension.py::test_roster_scope_excludes_project_agents` (the exclusion it asserts is reversed), `tests/test_dispatch.py::test_unknown_agent_with_both_scope_teaches_back_without_project_agents`, and `tests/test_dispatch.py::test_unknown_agent_with_project_scope_teaches_back_user_roster` (both assert scope selection that no longer exists), and updates the `test_extension.py` and `test_dispatch.py` helpers that pass a scope to discovery fakes or construct a `TaskDispatcher`. It also updates `tests/test_discovery.py::test_invalid_agent_files_are_skipped_with_diagnostics`: its stale-key fixture (`reasoningEffort: turbo`) now loads with a diagnostic and a dropped pin instead of being skipped, and its valid-pin fixture renames to `reasoning_effort` and keeps resolving. No other existing test changes.

**Check:** the four Commands-section commands. Expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent/superpowers_subagent/discovery.py extensions/superpowers-subagent/superpowers_subagent/extension.py extensions/superpowers-subagent/superpowers_subagent/dispatch.py extensions/superpowers-subagent/superpowers_subagent/catalog.py extensions/superpowers-subagent/tests/ && git commit -m "feat: fix agent discovery to all layers"`

### Task 4: Fail-closed resume, mapping wiring, and repair-note removal

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/runner.py` — resume verification fails closed, no fresh fallbacks, no stderr retry, pin-directed recovery notes
- Modify: `extensions/superpowers-subagent/superpowers_subagent/models.py` — remove the `ChildResult.notes` field
- Modify: `extensions/superpowers-subagent/superpowers_subagent/dispatch.py` — mapping write before spawn, mapping lookup before the session-record check, `ResumeFailure` handling, envelope-only content
- Test: `extensions/superpowers-subagent/tests/conftest.py` — gains the shared `isolated_home` fixture moved from `test_dispatch.py`
- Test: `extensions/superpowers-subagent/tests/test_runner.py`
- Test: `extensions/superpowers-subagent/tests/test_models.py`
- Test: `extensions/superpowers-subagent/tests/test_dispatch.py`
- Test: `extensions/superpowers-subagent/tests/test_runtime_integration.py`

**Spec or proposal source:** Spec ADDED "Fail-closed resume", ADDED "Session-agent mapping" (write-before-spawn, lookup order, fail-closed outcomes), MODIFIED "Task result envelope" (no `Note:` lines), MODIFIED "Tau JSON collection" (pin-directed recovery notes), REMOVED "Unknown task_id fallback". Proposal Required Outcomes 6, 7, 8 and Approach "One execution core" and "Session-agent mapping".

**Proposal constraints:** Every fresh dispatch writes the mapping entry before the child process spawns. a failed or impossible write fails the dispatch closed. A `task_resume` call reads the mapping first and then checks the session record, in that order. Every resume failure starts zero children. In the Tau-process unknown-session condition, the attempted process's immediate CLI failure counts as no child, performs no agent work, starts no session, and its diagnostic folds into the teach-back. No result carries a `Note:` line. The flat surface keeps its current parameters in this task. only resume behavior and note rendering change.

**Interface:**
- `models.SessionSelection` — the existing baseline dataclass (`models.py`, fields `id: str` and `resume: bool = False`), repointed: id generation moves from the runner to the dispatcher, and the runner takes `session: SessionSelection` instead of `resume_session_id`. `resume` false runs a fresh child pinned to `id`; `resume` true resumes the recorded session `id`. The runner never generates a session id.
- `runner.ResumeFailure(ValueError)` — raised when a resume request fails closed. `str(exc)` is the reason text for the teach-back.
- `runner.TauChildRunner.run(...)` — before: took `resume_session_id: str | None`, generated the fresh session id internally, and fell back to a fresh child on a missing record, a wrong role, or an unknown-session stderr diagnostic. After: takes `session: SessionSelection` (from `models`) and no longer generates ids or falls back. `session.resume` false runs a fresh child pinned to `session.id`. `session.resume` true verifies the session record through `SessionManager(self.paths).get_session(session.id)` first: a missing record or a non-subagent role raises `ResumeFailure`. A resumed run whose process fails and whose bounded stderr excerpt matches the existing unknown-session pattern raises `ResumeFailure` carrying that excerpt. The other parameters keep their current names in this task.
- `runner._child_exit_error(result)` — the recovery sentences change. The unknown-provider sentence directs the caller to correct the provider pin in the config file or the agent definition and to use an exact provider name from `tau providers`. The model sentence directs the caller to correct the model pin in the config file or the agent definition, or to use an exact model ID supported by the provider. No sentence tells the caller to omit a call-level parameter.
- `models.ChildResult` — the `notes` field is removed. `to_dict` keeps its current shape.
- `dispatch.TaskDispatcher._dispatch_child(...)` — for a fresh run, generates the fresh session id with `uuid.uuid4().hex`, calls `write_mapping_entry(fresh_id, agent.name)` before the runner call, and builds `SessionSelection(id=fresh_id)`. A `MappingWriteError` from the write returns the fail-closed result described below. For a resume run, builds `SessionSelection(id=request.task_id, resume=True)`. It wraps the runner call: `ResumeFailure` returns the fail-closed result described below.
- `dispatch.TaskDispatcher.execute(...)` — when the call carries `task_id`, it calls `read_mapping_entry(request.task_id)` before agent resolution. A missing entry returns the fail-closed result. The mapped name resolves through `discovery.by_name()`. an unresolvable mapped name returns the fail-closed result. The call's own `subagent_type` no longer selects the resume agent and no longer keys the config layers: the resume path calls `self._config_layers(mapped_name)` and passes the mapped agent through the catalog pin check, so the mapped agent's `[agents.<name>]` config section and its definition pins resolve exactly as in a fresh call.
- `dispatch._result_content`, `dispatch._call_content` — removed. Call content is `build_envelope(result)` directly.
- New private helper `dispatch._resume_fail_closed(task_id: str | None, reason: str, scope: AgentScope, discovery) -> AgentToolResult` — builds the fail-closed result. `task_id` is the requested id on a resume and `None` on a fresh dispatch's mapping-write failure, where the content omits the id-preservation clause and states that the mapping write failed and no child started. Resume content: preserves the requested id, states that no child started, states the reason, directs the caller to `task` for a fresh child, names the three `task_resume` fields (`prompt` required, `task_id` required, `timeout_seconds` optional), and names the session-agent mapping as the source of the resumed agent. It lists no agents and carries no envelope. The `scope` parameter is transient: it feeds the details schema while `agentScope` still exists, and Task 5 removes the parameter with the field. The field list is transient too: at this commit the surface is flat, so the teach-back names `task_id` and `timeoutSeconds` (the fields that exist here) and states that continuing a child session pairs `task_id` with `subagent_type`; Task 6 restates the content to the three `task_resume` fields. The fail-closed result contract is the content as teach-back, no envelope, an empty `results` array, and no `planned` field.

**Behavior:**
- A fresh dispatch writes the mapping entry before the child process spawns. The mapping entry maps the fresh session id to the effective agent name.
- A mapping write failure returns the fail-closed contract: content names the mapping file, states that the write failed and that no child started. The runner is never called.
- A resume reads the mapping entry first. A missing entry or a corrupted mapping file fails closed with the id preserved and the reason stated, before the session-record check runs.
- A resume whose mapped name no discoverable agent provides fails closed before any child starts.
- A mapping entry whose session id has no session record fails the call closed at the session-record check, before any child starts. The stale entry is harmless.
- A resume of a missing session record or a non-subagent role raises `ResumeFailure` inside the runner and returns the fail-closed contract. No fresh child starts.
- A resume whose process fails immediately with the Tau unknown-session diagnostic returns the fail-closed contract with the diagnostic folded into the content. No fresh child starts and no retry runs.
- A successful resume stays pinned to the original session and its recorded cwd, and its result carries the normal envelope.
- No result of either path carries a `Note:` line.

**Tests must prove:**
- The mapping entry exists before the child process spawns: a fake runner records that `read_mapping_entry` finds the fresh id at run time (replaces nothing. new test)
- A failed mapping write fails the dispatch closed with the runner never called (new test)
- A resume resolves the agent from the mapping and ignores the call's `subagent_type` (new test)
- A missing mapping entry fails closed with the id preserved (new test. its fixture includes a session record for the id, so the never-called runner proves that the mapping lookup precedes the session-record check)
- An unmappable mapped name fails closed (new test)
- A resume applies the mapped agent's `[agents.<name>]` config section: the child's effective pin comes from the mapped name's config leg, not from the call's `subagent_type` (new test)
- A mapping entry with no session record fails closed at the session-record check before any child starts (new test)
- A missing session record raises `ResumeFailure` and starts no fresh child (replaces `test_runner_missing_record_falls_back_to_a_fresh_child`)
- A non-subagent role raises `ResumeFailure` and starts no fresh child (replaces `test_runner_wrong_role_record_falls_back_to_a_fresh_child`)
- The unknown-session diagnostic raises `ResumeFailure` carrying the diagnostic, with no retry child (replaces `test_runner_retries_once_as_a_fresh_child_on_unknown_session`)
- A resumed run uses the session's recorded cwd and carries no note (replaces `test_runner_resumed_run_uses_the_recorded_cwd_and_notes_it` and merges `test_runner_resumed_run_without_cwd_override_carries_no_cwd_note`)
- The runner's fresh-child tests pass the session id through `SessionSelection` (updates `test_runner_pins_every_fresh_child_to_a_new_subagent_session` and `test_runner_resumes_verified_subagent_session_without_cwd_flag`)
- The child-exit recovery sentences name the config pin or the agent definition and never name a call-level parameter (updates the recovery-note tests)
- No result carries a `Note:` line
- Only the failed-write test monkeypatches `dispatch.write_mapping_entry` in the `dispatch` namespace with a raising fake backed by `tmp_path`. The before-spawn test keeps the real mapping functions under the `isolated_home` redirect and uses a fake runner that calls the real `read_mapping_entry` at run time, so the proof shows the real mapping file contains the entry before the child spawns. `dispatch.py` imports `read_mapping_entry` and `write_mapping_entry` from `.mapping` at module level, which fixes the monkeypatch seam. (replaces `test_runner_notes_surface_as_note_lines_before_the_envelope` and the `test_models.py` notes test)
- `test_runner_does_not_retry_other_resumed_failures` keeps its unrecognized-diagnostic and no-second-invocation assertions and deletes its `result.notes == ()` assertion, which the removed `ChildResult.notes` field breaks (count-neutral update)

This task replaces the named fallback and note tests above (`test_runner_missing_record_falls_back_to_a_fresh_child`, `test_runner_wrong_role_record_falls_back_to_a_fresh_child`, `test_runner_retries_once_as_a_fresh_child_on_unknown_session`, `test_runner_resumed_run_uses_the_recorded_cwd_and_notes_it` merged with `test_runner_resumed_run_without_cwd_override_carries_no_cwd_note`, `test_runner_notes_surface_as_note_lines_before_the_envelope`, and the `test_models.py` notes test) and updates the runner-call helper tests that pass `resume_session_id`. It also replaces `tests/test_dispatch.py::test_task_id_reaches_the_runner_as_the_resume_session` (asserts the removed `resume_session_id` kwarg; replaced by the `SessionSelection(id=..., resume=True)` test), replaces `tests/test_runtime_integration.py::test_runtime_resumed_unknown_session_falls_back_to_a_fresh_child` (the fallback it asserts is removed; replaced by the unknown-id fail-closed runtime test), and updates the recovery-sentence assertion in `tests/test_runtime_integration.py::test_runtime_exposes_actionable_unknown_provider_failure_and_retains_stderr` to the pin-directed wording, and deletes the `result.notes == ()` assertion at `tests/test_runtime_integration.py:676` inside `test_runtime_pins_a_session_and_resumes_it`, which the removed `ChildResult.notes` field breaks (count-neutral; the test itself survives until Task 6). The `isolated_home` fixture move is count-neutral test infrastructure. No other existing test changes.

**Check:** the four Commands-section commands. Expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent/superpowers_subagent/runner.py extensions/superpowers-subagent/superpowers_subagent/models.py extensions/superpowers-subagent/superpowers_subagent/dispatch.py extensions/superpowers-subagent/tests/ && git commit -m "feat: wire the session-agent mapping and fail closed on resume"`

### Task 5: Call-level parameters and per-call environment control removed

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/utils.py` — resolution helpers lose the call-override layer. `resolve_child_cwd` removed
- Modify: `extensions/superpowers-subagent/superpowers_subagent/runner.py` — the run signature loses the override and cwd parameters. fresh children always spawn in the parent session cwd
- Modify: `extensions/superpowers-subagent/superpowers_subagent/catalog.py` — the fail-fast function becomes pin-directed. renamed
- Modify: `extensions/superpowers-subagent/superpowers_subagent/models.py` — `AgentScope` and the details scope and directory fields removed
- Modify: `extensions/superpowers-subagent/superpowers_subagent/discovery.py` — stops reporting `project_agents_dir`
- Modify: `extensions/superpowers-subagent/superpowers_subagent/dispatch.py` — removed fields fail closed. the project-approval flow and confirmation UI wiring removed. the request model slims
- Modify: `extensions/superpowers-subagent/superpowers_subagent/extension.py` — stops passing the UI object. the schema drops the removed properties
- Test: `extensions/superpowers-subagent/tests/test_utils.py`
- Test: `extensions/superpowers-subagent/tests/test_runner.py`
- Test: `extensions/superpowers-subagent/tests/test_models.py`
- Test: `extensions/superpowers-subagent/tests/test_discovery.py`
- Test: `extensions/superpowers-subagent/tests/test_dispatch.py`
- Test: `extensions/superpowers-subagent/tests/test_extension.py`
- Test: `extensions/superpowers-subagent/tests/test_runtime_integration.py`

**Spec or proposal source:** Spec ADDED "Fail-closed validation" (removed override and environment fields get dedicated teach-back wording), ADDED "Fixed dispatch environment" (no `cwd` parameter. spawn in the parent session cwd. the approval flow removed), MODIFIED "Provider, model, and reasoning-effort overrides" (four-layer chain. catalog fail-fast directs to the pins), MODIFIED "Content envelope and complete details" (no agent-scope field, no project-agents-directory field), REMOVED "Explicit project-agent approval". Proposal Required Outcomes 4, 5, 8 and Approach "Fixed environment", "Resolution simplification", "Key rename" (discovery side landed in Task 3).

**Proposal constraints:** No call-level `provider`, `model`, or reasoning-effort parameter exists. No per-call cwd, agent-layer, or approval control exists. The resolution chain is, highest first: config `[agents.<name>]`, agent-definition frontmatter, config `[defaults]`, parent session. Catalog and config pins stay fail-fast validated before any child starts, and the failure lists the valid options. The catalog fail-fast teach-back directs the caller to correct the config pin or the agent definition. No value is coerced, silently dropped, or reinterpreted. The details carry no agent-scope field and no project-agents-directory field. all other details keys keep their existing names.

**Interface:**
- `utils.effective_provider_model(agent, *, config_overrides=None, config_defaults=None, parent_provider=None, parent_model=None) -> tuple[str | None, str | None]` — before: took `provider_override` and `model_override` positional arguments. After: the two override parameters are removed. The chain is config-agent, agent-definition, config-defaults, parent session.
- `utils.effective_reasoning_effort(agent, *, config_overrides=None, config_defaults=None, parent_reasoning_effort=None) -> str | None` — before: took `reasoning_effort_override`. After: removed.
- `utils.resolve_child_cwd` — removed. The runner resolves the fresh cwd as `default_cwd.expanduser().resolve()` inline.
- `runner.TauChildRunner.run(...)` — loses `cwd_override`, `provider_override`, `model_override`, and `reasoning_effort_override`. A fresh child always spawns in `default_cwd.expanduser().resolve()` and passes it as `--cwd`. A resumed child keeps the session's recorded cwd.
- `dispatch.TaskDispatcher._catalog_override_error` — renamed to `_catalog_pin_error` and calls the renamed `catalog.provider_model_pin_error` without the request's override values.
- `catalog.provider_model_pin_error(provider, model, *, parent_provider, parent_model, snapshot) -> str | None` — renamed from `provider_model_override_error`. The unknown-provider failure lists the configured providers and directs the caller to correct the provider pin in the config file or the agent definition, naming `tau providers` for exact names. The unknown-model failure lists the configured models and directs the caller to correct the model pin in the config file or the agent definition, or to use an exact model ID supported by the provider. No sentence tells the caller to omit a call-level parameter. The conservative pass-through behavior (no snapshot, no provider, or the parent session's own pair passes) stays unchanged. Module docstrings state pin validation, not override validation.
- `models.AgentScope` — removed. `details_dict(...)` loses the `agent_scope` and `project_agents_dir` parameters. the serialized keys `agentScope` and `projectAgentsDir` disappear. `DiscoveryResult.project_agents_dir` is removed. `discovery.discover_agents` stops passing it.
- `dispatch.ParsedRequest` — loses the fields `cwd`, `agent_scope`, `confirm_project_agents`, `provider`, `model`, `reasoning_effort`, and `notices`. It keeps `prompt`, `subagent_type`, `description`, `task_id`, and `timeout_seconds`.
- `dispatch._ALLOWED_FIELDS` — becomes `{"prompt", "subagent_type", "description", "task_id", "timeoutSeconds"}`.
- `dispatch._REMOVED_FIELD_SENTENCES: dict[str, str]` — maps each removed field name to its teach-back sentence. For `provider`, `model`, and `reasoningEffort`: the sentence names the removal of the call-level override and directs the caller to the config-file pin (`superpowers-subagent.toml`, `[defaults]` or `[agents.<name>]`) or the agent-definition frontmatter. For `cwd`, `agentScope`, and `confirmProjectAgents`: the sentence names the removal of the call-level capability, states that a fresh child spawns in this session's working directory, and states that discovery covers all agent layers. The unknown-field teach-back appends the matching sentence for every removed field in the unknown list.
- `dispatch.validate_arguments` — the unknown-field check rejects the six removed fields with the sentence-augmented teach-back. The placeholder-coercion helpers `_optional_literal_override` and `_optional_thinking_level`, the `_RESERVED_OVERRIDE_PLACEHOLDERS` constant, `_scope_for_discovery`, `_project_approval`, and the `ConfirmationUi` protocol are removed. The `TaskDispatcher` constructor loses the `ui` parameter.
- `dispatch._invalid_parameters_content(error, dispatcher)` — drops the two override sentences (the "omit provider, model, and reasoningEffort" inheritance sentence and the "reasoningEffort, when passed, must be one of" literal sentence). The inheritance sentence states the four-layer chain. The roster stays the session-start static roster of Task 3. Task 6 replaces this composer with the mode-aware form.
- `dispatch.TaskDispatcher._fail_closed` and `dispatch._resume_fail_closed` — lose the transient `scope` parameter, removed together with the details field.
- `extension.setup` — stops passing `ui=tau.context.ui`. `_task_parameters` drops the six removed properties and their descriptions. the remaining flat properties stay until Task 6.

**Behavior:**
- A call carrying `provider`, `model`, `reasoningEffort`, `cwd`, `agentScope`, or `confirmProjectAgents` fails closed, starts no child, and the teach-back names the field and carries the removed-field sentence for that field.
- A removed field alongside another invalid argument still gets the removed-field teach-back, because the unknown-field check runs before the value checks.
- A child resolves provider, model, and thinking level from the config-agent pin, the agent-definition frontmatter, the config-defaults pin, then the parent session. No call-level value participates.
- A fresh child spawns in the parent session's working directory. the child's process cwd and the Tau `--cwd` flag both carry it.
- A project-layer definition dispatches with no confirmation step and no approval parameter.
- The details of every result carry no `agentScope` and no `projectAgentsDir` key.
- A config pin naming an unconfigured provider fails the call closed before any child starts, and the teach-back lists the configured providers and directs the caller to the config pin or the agent definition.

**Tests must prove:**
- Each of the six removed fields fails closed with its dedicated sentence (new `test_dispatch.py` tests. `cwd` and `agentScope` assert the fixed-behavior sentences, `reasoningEffort` asserts the pin sentence)
- The resolution chain is config-agent, agent-definition, config-defaults, parent session, with no override leg (updates the `test_utils.py` resolution tests)
- A fresh child spawns in the parent session cwd and the argv carries it as `--cwd` (updates the runner tests that passed `cwd_override`)
- The runner signature carries no override parameters (updates every `test_runner.py` call helper)
- The catalog pin failures list the options and direct to the config pin or the agent definition, and never instruct omission (asserted by the rebuilt `test_unknown_provider_fails_fast_before_children` and `test_unsupported_model_fails_fast_before_children` in `test_dispatch.py`; `dispatch.py` imports the renamed `catalog.provider_model_pin_error`)
- The details carry no `agentScope` and no `projectAgentsDir` (updates the `test_models.py` and `test_dispatch.py` details-shape tests)
- A project-layer agent dispatches with no confirmation and no UI call (replaces the four project-approval tests: `tests/test_dispatch.py::test_validation_rejects_non_boolean_confirm_project_agents`, `tests/test_dispatch.py::test_project_agents_fail_closed_headless_and_allow_explicit_bypass`, `tests/test_dispatch.py::test_project_agents_use_ui_confirmation`, and `tests/test_runtime_integration.py::test_project_agent_approval_uses_headless_fail_closed_and_public_ui_confirmation` are deleted)
- The flat schema advertises no removed property (updates the `test_extension.py` property-set assertion to the five surviving flat fields)

This task deletes the named override, placeholder, cwd, and approval tests in `test_dispatch.py` (`test_validation_treats_reserved_placeholders_as_omitted`, `test_reserved_placeholders_dispatch_children_without_overrides`, `test_whitespace_literal_overrides_require_non_empty_string_and_prevent_children`, `test_non_string_literal_overrides_require_string_and_prevent_children`, `test_cwd_resolves_against_the_parent_session_cwd`, `test_trimmed_literal_overrides_reach_child_configuration`, `test_call_reasoning_override_beats_parent_thinking_level`, `test_validation_rejects_non_boolean_confirm_project_agents`, `test_project_agents_fail_closed_headless_and_allow_explicit_bypass`, `test_project_agents_use_ui_confirmation`, `test_validation_rejects_invalid_agent_scope`, and the `agentScope` and `confirmProjectAgents` entries of `TEACH_BACK_CASES`, which remove two parametrized cases of `test_invalid_calls_fail_closed_with_teach_back`), deletes `tests/test_extension.py::test_task_schema_defines_literal_override_contract` (asserts schema constraints of the removed properties; the new property-set test covers the surviving five), deletes `tests/test_runtime_integration.py::test_project_agent_approval_uses_headless_fail_closed_and_public_ui_confirmation`, and updates the details-shape assertions named above. It also updates: `tests/test_dispatch.py::test_validation_description_and_cwd_are_optional_strings` (the `request.cwd` and `cwd must be a string` assertions are deleted, the description-optional assertion stays, renamed `test_validation_description_is_an_optional_string`), `tests/test_dispatch.py::test_validation_accepts_a_fully_populated_flat_call` (passes only the five surviving flat fields and asserts the surviving `ParsedRequest` fields), and `tests/test_dispatch.py::test_unknown_provider_fails_fast_before_children` with `::test_unsupported_model_fails_fast_before_children` (rebuilt on config-pin fixtures: the catalog failure triggers through a config `[agents.<name>]` pin, and the asserted sentences become the pin-directed wording). It also makes the forced count-neutral updates: `tests/test_dispatch.py:28` drops `resolve_child_cwd` from its module-level import (the import breaks collection after the removal), the `FakeRunner._initial_result` helper at `tests/test_dispatch.py:86` rebuilds its cwd line on `kwargs["default_cwd"]` (fresh children report the parent cwd), `tests/test_dispatch.py::test_completed_envelope_relays_the_complete_final_message` rebuilds its call fixture on the surviving fields and its child-record assertions on the parent-cwd pin while keeping its envelope and details assertions, the `DiscoveryResult(...)` constructions at `tests/test_dispatch.py:194`, `:213`, `:224` and `tests/test_extension.py:257` drop the removed `project_agents_dir=` kwarg, `make_dispatcher` at `tests/test_dispatch.py:248` drops its `ui=` argument, and the `run_resumed` helper at `tests/test_runtime_integration.py:622` drops the `cwd_override`, `provider_override`, `model_override`, and `reasoning_effort_override` kwargs (count-neutral). No other existing test changes.

**Check:** the four Commands-section commands. Expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent/ && git commit -m "feat: remove call-level task parameters and fix the dispatch environment"`

### Task 6: Two-tool registration and per-tool surface

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/dispatch.py` — explicit mode, per-tool field sets, per-tool teach-backs, `timeout_seconds`, same-id lock on resume only
- Modify: `extensions/superpowers-subagent/superpowers_subagent/extension.py` — two registrations with per-tool schemas, descriptions, and prompt guidelines
- Modify: `extensions/superpowers-subagent/superpowers_subagent/rendering.py` — the resume call renderer
- Test: `extensions/superpowers-subagent/tests/test_dispatch.py`
- Test: `extensions/superpowers-subagent/tests/test_extension.py`
- Test: `extensions/superpowers-subagent/tests/test_rendering.py`
- Test: `extensions/superpowers-subagent/tests/test_runtime_integration.py`

**Spec or proposal source:** Spec ADDED "Two-tool task surface", "Cross-tool field rejection", "Per-tool descriptions". MODIFIED "task_id resume" (`timeout_seconds`), "Progress, cancellation, timeout, and cleanup" (`timeout_seconds` on both tools), "Portable rendering" (resume call renderer), "Concurrent task calls", "Same-task_id exclusion", "Tool description roster" (usage notes name `task_resume`). REMOVED "task interface and validation". Proposal Required Outcomes 1, 2, 3, 9, 10 and Approach "Descriptions".

**Proposal constraints:** The tool names are `task` and `task_resume`. The parameter surfaces are exactly: `task` carries `prompt` (required), `subagent_type`, `description`, `timeout_seconds`. `task_resume` carries `prompt` (required), `task_id` (required), `timeout_seconds`. No other parameter exists on either tool, and every parameter name is snake_case. `task_resume` teach-backs name its three fields and the mapping and list no agents. Each tool's schema description, tool description, and prompt guidelines describe only that tool's supported shape. Children never register `task` or `task_resume`.

**Interface:**
- `dispatch.RequestMode = Literal["fresh", "resume"]`.
- `dispatch.ParsedRequest` — gains `mode: RequestMode` as its first field.
- `dispatch.validate_arguments(arguments: Mapping[str, JSONValue], mode: RequestMode) -> ParsedRequest` — per-tool validation. It raises `ValidationFailure` carrying only the reason text; it has no roster and no parent-session access. Order: the `background` check first. then, on `task` only, the `task_id` rejection. then the unknown-field check against that tool's field set. then `prompt`. then the mode-specific fields. then `timeout_seconds`. The mode-specific fields are: on `task`, optional `subagent_type` (trimmed, non-empty when present, default `general-purpose`) and optional `description` (string). on `resume`, required `task_id` (trimmed, non-empty, effective for the session lookup and the same-id lock; the required-field failure states exactly: `task_id is required and requires a non-empty string`).
- `dispatch._invalid_parameters_content(error: str, dispatcher: TaskDispatcher, mode: RequestMode) -> str` — replaces the flat-surface composer and is the composition point for every validation teach-back: `TaskDispatcher._fail_closed` catches the reason-only `ValidationFailure` and calls it with the mode. On `task` the content is the reason, the session-start static roster (`dispatcher.roster_text` of Task 3), the inheritance-default sentence, and one valid `task` example. On `resume` the content is the reason, the three field names (`prompt` required, `task_id` required, `timeout_seconds` optional), the session-agent mapping name, and no roster.
- `dispatch._TASK_FIELDS = frozenset({"prompt", "subagent_type", "description", "timeout_seconds"})` and `dispatch._RESUME_FIELDS = frozenset({"prompt", "task_id", "timeout_seconds"})`. The flat `_ALLOWED_FIELDS` and the `timeoutSeconds` spelling are removed.
- `dispatch.TaskDispatcher.execute(arguments, *, mode: RequestMode, signal=None, on_update=None)` — validates with the mode. on `resume`, performs the mapping lookup and the mapped-agent resolution of Task 4. the fresh path writes the mapping entry before spawn.
- `dispatch._run_locked` — acquires the same-id lock only when `request.mode == "resume"`.
- The dedicated reason sentences, all raised as reason-only `ValidationFailure` messages and composed by `_invalid_parameters_content(error, dispatcher, mode)`, which appends the mode context (on `task`: the session-start roster, the inheritance-default sentence, and the example; on `resume`: the three fields and the mapping, no roster). One exception: the background check returns its dedicated content directly in `execute`, bypassing the composer (the background teach-back carries no roster):
  - The background teach-back (both tools, checked first): states that background dispatch is not supported in this harness, that the result arrives when the child finishes, and that several calls of the same tool in one message run children in parallel.
  - The `task_id`-on-`task` teach-back: names `task_id` as not a `task` parameter and names `task_resume` as the tool that continues a child session, with one `task_resume` example carrying `prompt` and `task_id`.
  - The `timeoutSeconds` teach-back (both tools): names `timeoutSeconds` as an unknown field and shows `timeout_seconds`.
  - The removed-field sentences of Task 5 apply to both tools' unknown-field teach-backs.
  - The unknown-field teach-back on `task`: names the unknown fields, lists the all-layer roster, states the inheritance default, and shows one valid `task` example (`{"prompt": "Find caching options"}`).
  - The unknown-field teach-back on `task_resume`: names the unknown fields, names the three fields `prompt` (required), `task_id` (required), `timeout_seconds`, names the session-agent mapping file as the source of the resumed agent, and lists no agents.
  - The generic argument teach-back (missing or mistyped values, out-of-range timeout, unknown agent name): on `task` it keeps the current shape of reason, roster, inheritance sentence, and example. on `resume` it states the reason, names the three fields, and names the mapping, and lists no agents.
- `extension._task_tool_parameters(roster_text)` and `extension._resume_tool_parameters()` — two JSON schemas, both `"type": "object"` with `"additionalProperties": false`. The `task` schema requires `["prompt"]` and carries `prompt` (string, `minLength` 1, preserved verbatim), `subagent_type` (string, `minLength` 1, optional agent name with the roster and the default rule), `description` (string, display label with no behavioral effect), and `timeout_seconds` (number, `exclusiveMinimum` 0, `maximum` 10800, `default` 3600, per-child timeout in seconds). The `resume` schema requires `["prompt", "task_id"]` and carries `prompt` (same contract), `task_id` (string, `minLength` 1, the child session id from an earlier task result), and `timeout_seconds` (same contract).
- `extension.setup` — two `register_tool` calls. The `task` tool: label `task`, `prompt_snippet` stating new-child dispatch, `render_call=render_task_call`, `render_result=render_task_result`. The `resume` tool: label `task_resume`, `prompt_snippet` stating session continuation, `render_call=render_resume_call`, `render_result=render_task_result`. Both execute through shared closures that pass `mode` to the dispatcher. The description contracts:
  - The `task` description contains, in order: the dispatch-threshold one-liner. the minimal new-child example. the inheritance default (an unpinned child resolves to the parent session's provider, model, and thinking level, and durable pins live in the config file or an agent definition). the fixed environment (spawn in this session's working directory, all-layer discovery). the annotated all-layer roster. the default-selection rule (omitting `subagent_type` selects `general-purpose`). a when-not-to-use section (simple reads, searches, commands, and small edits are the caller's own tool calls. never dispatch a task and then do the same work). the usage notes (several calls run children in parallel, delegated work is not duplicated, self-contained prompts, the result's `task_id` is reusable by a later `task_resume` call, and the caller states whether the child writes code or does research and how to verify the result). and a one-line pointer that `task_resume` continues an existing child session with its `task_id`.
  - The `task_resume` description contains: a continuation one-liner. the continuation example with `task_id` and `timeout_seconds`. and the statement that the resumed agent comes from the session-agent mapping `~/.tau/superpowers-subagent-sessions.json`, so the call carries no agent name. It carries no roster.
  - The `task` prompt guidelines cover: the dispatch threshold and the prohibition on delegating simple reads, searches, commands, or small edits. the prohibition on dispatching work the caller is about to perform itself. one task per call with several calls running in parallel and separate calls for conditional sequences. the self-contained-prompt requirement. the result's `task_id` passing to `task_resume` (never "with the same subagent_type"). the code-or-research and verification statement. agent selection by task type. the statement that children inherit this session's provider, model, and thinking level unless pinned in the config file or an agent definition, with no call-level override. and handling `BLOCKED` and `NEEDS_CONTEXT` (a fresh `task` call for `BLOCKED`, `task_resume` for `NEEDS_CONTEXT`).
  - The `task_resume` prompt guidelines cover: resuming only to continue the same subagent's work, with a fresh `task` call for a different agent. one task per call with several `task_resume` calls running in parallel and same-id calls conflicting. the prompt being the new user turn and self-contained. the result carrying the same `task_id` for further resumes. `timeout_seconds` bounding the resumed run. the dispatch threshold and prohibitions. and handling `BLOCKED` and `NEEDS_CONTEXT`.
- `rendering.render_resume_call(arguments: Mapping[str, JSONValue]) -> str` — returns `f"▸ Task · resume {escape(task_id)}"` when `task_id` is a non-empty string, and `"▸ Task · resume"` otherwise. The label names the resume operation and the requested id and never names an agent. It contains no Rich markup beyond what `render_task_call` uses.

**Behavior:**
- The extension registers exactly two task tools, named `task` and `task_resume`, each with its own schema, description, and prompt guidelines.
- A `task` call carrying `task_id` fails closed with the `task_resume` teach-back, before any other argument validation. A call carrying both `background` and `task_id` gets the background teach-back.
- A `task_resume` call carrying `subagent_type`, `description`, `cwd`, or any other field outside its three fails closed as an unknown field, with the resume teach-back shape.
- A `task_resume` call without `task_id`, or with a whitespace-only `task_id`, fails closed stating that `task_id` is required.
- `timeout_seconds` on both tools accepts numbers greater than 0 and at most 10800 and defaults to 3600. The value 10800 is accepted and 10801 fails closed.
- Two `task_resume` calls with the same `task_id` produce one child result and one fail-closed same-id teach-back that names the conflict and the id, names the three `task_resume` fields and the session-agent mapping, lists no agents, carries no envelope, an empty `results` array, and no `planned` field, and does not wait for the winner.
- Several calls of either tool in one message run concurrently, each with its own envelope, with no cap.
- The recursion guard registers neither tool.

**Tests must prove:**
- Exactly two tools register, named `task` and `task_resume`, each with its own schema and description (replaces the one-tool registration test)
- The `task` schema carries exactly its four properties and the `resume` schema exactly its three, all snake_case, with the `resume` schema requiring `task_id` (replaces the flat property-set test from Task 5)
- The `task` description contains the minimal example, the inheritance default, the fixed environment, the roster, the default rule, the when-not-to-use section, and the `task_resume` pointer (updates the description tests and replaces `tests/test_extension.py::test_task_prompt_requires_omitted_or_exact_literal_overrides`, whose asserted guidelines are rewritten)
- The `resume` description contains the continuation shape and the mapping statement and carries no roster line (new test)
- Each tool's prompt guidelines reference only that tool's surface (new test)
- `task` rejects `task_id` with the `task_resume` teach-back, and background beats `task_id` (replaces `tests/test_dispatch.py::test_validation_task_id_requires_subagent_type_and_names_both_fields` and `::test_task_id_without_subagent_type_teach_back_names_both_fields`, which assert the removed task-id-requires-subagent_type rule)
- The background teach-back fires on `task_resume` too, not only on `task` (extends `test_background_teach_back_names_the_parallel_alternative` to the resume tool)
- Two `task_resume` calls with different ids run concurrently and both children start (extends the parallel-execution test helper to resume calls)
- `task_resume` rejects `subagent_type`, `description`, and `cwd` as unknown fields with no roster in the content (new tests)
- `timeout_seconds` validates on both tools and `timeoutSeconds` fails closed naming `timeout_seconds` (replaces the `timeoutSeconds` validation tests)
- Whitespace `subagent_type` and whitespace `task_id` fail closed with their stated reasons (updates the existing trim tests to the two-tool surface)
- The same-id exclusion applies to two `task_resume` calls and the loser fails closed immediately (updates `test_same_task_id_calls_exclude_each_other`)
- A `task_resume` call that omits `task_id` fails closed (new test)
- `render_resume_call` names the resume operation and the requested id and never an agent (new test. the baseline task-label tests persist unchanged)
- End to end through the real extension runtime: a fresh `task` dispatch, a `task_resume` continuation of that session with the mapped agent, and an unknown-id `task_resume` that fails closed with zero children (updates `load_task_tool` to return both tools and replaces `test_runtime_pins_a_session_and_resumes_it`'s flat-call shape)
- Every `validate_arguments` and `TaskDispatcher.execute` call site in the unit tests gains the mode argument, every `FakeDispatcher.execute` double in `tests/test_extension.py` (the classes at lines 446, 491, 536, 579, and 679) gains the same `mode` keyword parameter, the resume-call fixtures Task 4 added (`subagent_type` was required by the flat validation) drop `subagent_type` so they stay valid `task_resume` calls, and the `TEACH_BACK_CASES` entry at `tests/test_dispatch.py:621–623` (`{"prompt": "work", "task_id": "task-1"}` expecting `task_id requires subagent_type`) is deleted: on `task` the new task-rejects-`task_id` test covers the behavior, and on `task_resume` the arguments are a valid call (count −1 at this task's gate, all other updates count-neutral)

This task replaces the flat-surface tests named above — including `tests/test_extension.py::test_prompt_guidelines_carry_flat_surface_rules`, replaced by the per-tool guidelines tests — and updates the runtime-integration helpers that build flat calls, including the `"timeoutSeconds"` → `"timeout_seconds"` key rename in the call built by `tests/test_runtime_integration.py::test_runtime_terminates_child_on_timeout_or_cancellation_and_retains_partial_messages` (count-neutral). No other existing test changes.

**Check:** the four Commands-section commands. Expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent/ && git commit -m "feat: register the two-tool task surface"`

### Task 7: Consumer documentation update

**Files:**
- Modify: `README.md` — task sections, precedence list, custom-agent sections, operator notes, removed-behavior announcements
- Modify: `skills/using-superpowers/references/tau-tools.md` — the task-tool reference rewritten to the two-tool surface
- Modify: `skills/dispatching-parallel-agents/SKILL.md` — resume instruction names `task_resume`
- Modify: `skills/subagent-driven-development/SKILL.md` — dispatch rule and resume rule
- Modify: `skills/subagent-driven-development/implementer-prompt.md` — check the surrounding prose for flat-surface phrasing
- Modify: `skills/subagent-driven-development/implementation-reviewer-prompt.md` — check the surrounding prose for flat-surface phrasing
- Modify: `skills/requesting-code-review/SKILL.md` — resume sentence
- Modify: `skills/requesting-code-review/code-reviewer.md` — check the surrounding prose for flat-surface phrasing
- Modify: `skills/writing-skills/testing-skills-with-subagents.md` — resume sentence
- Modify: `skills/writing-skills/examples/skill-testing-example.md` — check for flat-surface phrasing
- Modify: `skills/brainstorming/feature-spec-author-prompt.md` — check the surrounding prose for flat-surface phrasing
- Modify: `skills/brainstorming/proposal-document-reviewer-prompt.md` — resume sentence
- Modify: `skills/brainstorming/spec-document-reviewer-prompt.md` — resume sentence
- Modify: `skills/writing-plans/plan-document-reviewer-prompt.md` — resume sentence
- Modify: `skills/finishing-a-development-branch/living-spec-document-reviewer-prompt.md` — resume sentence
- Test: `extensions/superpowers-subagent/tests/test_extension.py` — the README-contract test is deleted together with the README subject matter it asserts

**Spec or proposal source:** Spec ADDED "Clean-cut consumer update" (both scenarios). Proposal Required Outcome 11, Impact section consumer list, and Constraints (developer-facing text follows the writing-unambiguous-text skill).

**Proposal constraints:** Every in-repo consumer updates in the same branch. No legacy tool, no alias, and no deprecation window exists. The README task sections announce the removed behaviors in the same change, including the removal of resuming a session under a different agent. Documentation of current state only: no shipped document describes the removed flat surface, placeholder coercion, repair notes, per-call scope, or the approval flow as current behavior.

**Interface:** Documentation only. The call examples in every shipped document use the two-tool snake_case surface.

**Behavior: README.md**
- The "What You Get" bullets state the two tools, the snake_case surface, the fail-closed validation, the pin-based configuration, and the session-agent mapping file.
- The task-tool section shows a minimal `task` example, the parallel-dispatch examples, and a resume example calling `task_resume` with `prompt` and `task_id`. The options tables become one table per tool, carrying exactly that tool's parameters.
- The result-content paragraph drops the repair-note sentence. The fail-closed behavior (teach-back content, no envelope, empty `results`, no `planned`) is stated for rejected calls.
- The operator notes state: the re-install and restart migration. that sessions created before this change have no mapping entries, so their resumes fail closed and direct the caller to `task`. that a config file or agent definition still carrying `reasoningEffort` keeps working with a diagnostic and a dropped pin until the operator renames it. the six-step store-maintenance procedure with the mapping-entry deletion as its fifth step. that resuming under a different agent was removed and a fresh `task` call is the recovery. that `cwd`, `agentScope`, `confirmProjectAgents`, and the call-level `provider`, `model`, and `reasoningEffort` parameters were removed. that project-layer definitions dispatch without per-call approval and their names appear in the roster. the same-id lock applying to `task_resume` ids. and the rollback note that the mapping file survives rollback as inert state. The operator notes also state the accepted exposures: a stale mapping entry for a deleted session is harmless and inspectable in the mapping file. a resumed run's usage posts to the resumed run only, so the resuming session's usage undercounts. a direct `tau --session <id>` on a child session overlaps with `task_resume` at the caller's own risk. the resumed agent's definition is read at resume time, so an edited definition drifts from the original dispatch. a cross-project resume whose mapped agent is a project-layer definition fails closed, because re-discovery anchors at the resuming session's working directory, and the recovery is a fresh `task` call in that project. and a fresh child always spawns in the parent session's working directory.
- The agents section states that discovery always covers the bundled, user, and project layers with the documented precedence, and drops the scope-selection and approval paragraphs. The frontmatter keys read `provider`, `model`, and `reasoning_effort`.
- The provider-selection section states the four-layer chain and drops the placeholder paragraph. The TOML snippet uses `reasoning_effort`.

**Behavior: tau-tools.md**
- The reference documents both tools: an API section per tool with its own parameter table, the task example, the parallel-dispatch rules, and the resume section calling `task_resume`.
- The resume section states that the resumed agent comes from the session-agent mapping, that a `task_resume` call carries no agent name, and that every resume failure starts zero children and directs the caller to `task`.
- The removed paragraphs go away: the `cwd` resolution paragraphs, the placeholder paragraph, the approval paragraph, the call-level override legs of the resolution chain, and the repair-note sentence. The details shape drops `agentScope` and `projectAgentsDir`.
- The remaining sections (profiles, custom agents, provider selection, child context, results and status, reviews) state current behavior with the renamed `reasoning_effort` key and the four-layer chain.

**Behavior: skill files**
- Sentence replacements named per file. The pattern to replace is the resume instruction of the form "pass its result's `task_id` with `subagent_type`" or "resume that session with `task_id` and `subagent_type`". The replacement passes the result's `task_id` to a `task_resume` call with the new prompt, and carries no agent name.
  - `skills/dispatching-parallel-agents/SKILL.md` line 75: "To continue the same child session, pass its result's `task_id` with `subagent_type`" becomes a `task_resume` instruction.
  - `skills/subagent-driven-development/SKILL.md` line 17: drops "Each call carries one flat task object. Unless the user requests an override, omit `provider`, `model`, and `reasoningEffort`" and states that children inherit the session's provider, model, and thinking level unless a config file or agent definition pins one. Line 18: the resume rule names `task_resume`.
  - `skills/requesting-code-review/SKILL.md` line 45: "a follow-up call can resume that session with `task_id` and `subagent_type`" names `task_resume`.
  - `skills/writing-skills/testing-skills-with-subagents.md` line 43: the resume sentence names `task_resume`.
  - `skills/brainstorming/proposal-document-reviewer-prompt.md` line 18, `skills/brainstorming/spec-document-reviewer-prompt.md` line 18, `skills/writing-plans/plan-document-reviewer-prompt.md` line 18, and `skills/finishing-a-development-branch/living-spec-document-reviewer-prompt.md` line 18: the identical resume sentence names `task_resume`.
- Verify-only files, expected to need no change: `skills/subagent-driven-development/implementer-prompt.md`, `skills/subagent-driven-development/implementation-reviewer-prompt.md`, `skills/requesting-code-review/code-reviewer.md`, `skills/brainstorming/feature-spec-author-prompt.md`, and `skills/writing-skills/examples/skill-testing-example.md`. Their JSON call templates carry only `subagent_type` and `prompt`, which stay valid `task` arguments, and their prose carries no removed-field or flat-resume phrasing. If verification finds a removed-surface phrase, fix it with the same `task_resume` instruction pattern.
- All changed prose follows the writing-unambiguous-text skill.

**Tests must prove:** Documentation carries no runtime tests. The one runtime-test disposition: `tests/test_extension.py::test_readme_documents_literal_override_contract` asserts the README "Common Options" override rows and the placeholder paragraph this task rewrites away, so the task deletes it. The gate is the reference scan, a content grep, and the count arithmetic.

**Check:**

```bash
cd /workspace
bash tests/check-references.sh
grep -rn "confirmProjectAgents\|agentScope:" README.md skills/
grep -rn "reasoningEffort" README.md skills/
grep -rn "task_id.*subagent_type\|subagent_type.*task_id" README.md skills/ | grep -v task_resume
grep -rn "Repair notes appear" README.md skills/
cd extensions/superpowers-subagent
TAU_PYTHON=$(sed -n '1s/^#!//p' "$(command -v tau)")
TAU_SITE_PACKAGES=$("$TAU_PYTHON" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest -q
```

Expected: the reference scan passes. The `reasoningEffort` grep matches only the README operator-notes lines that announce the stale-key behavior and the removals, and the `reasoningEffort?` child-result wire field in tau-tools.md's details shape (the wire key survives; only `agentScope` and `projectAgentsDir` drop). The `confirmProjectAgents|agentScope:` grep matches only the README operator-notes line that announces the removals. The remaining two greps print nothing. The suite count is the Task 6 gate count minus the one deleted README-contract test.

- [ ] Update README.md per the behavior list
- [ ] Update tau-tools.md per the behavior list
- [ ] Apply the named sentence replacements and the verify-only checks across the thirteen skill files
- [ ] Run the reference scan, the greps, and the suite
- [ ] Commit: `git add README.md skills/ extensions/superpowers-subagent/tests/test_extension.py && git commit -m "docs: update task-surface consumers to the two-tool surface"`

### Task 8: Agent-facing surface evaluation

**Files:**
- Create: `extensions/superpowers-subagent/scripts/agent_surface_evaluation.py` — scripted evaluation of the model-facing surface against the configured provider
- Create: `docs/design/evidence/task-tool-robustness/agent-surface-evaluation/report.md` — the recorded measures
- Create: `docs/design/evidence/task-tool-robustness/agent-surface-evaluation/raw-events.jsonl` — the raw recorded events

**Spec or proposal source:** Proposal Approach "Verification beyond the unit suite" (retained proposal-owned item) and Risks "camelCase priors" (the agent-facing evaluation measures the residual rate).

**Proposal constraints:** The evaluation runs against the provider and model pairs the harness configures at evaluation time, per the catalog snapshot the extension validates against. It records the emitted tool name and JSON arguments, the validation failures, and the number of launched children. The key measures are fewer unnecessary optional fields on ordinary calls and zero accidental launches after a failed resume. Results are reported separately from the unit-test outcome.

**Interface:**
- `python scripts/agent_surface_evaluation.py --output-dir <dir> [--timeout <seconds>]` — a stdlib-only script that runs four scripted controller sessions and writes `report.md` and `raw-events.jsonl` into the output directory. Default output directory is the repository's evidence directory for this proposal. Default per-session timeout is 600 seconds.
- Each session runs `tau --mode json --no-approve -e extensions/superpowers-subagent "<case prompt>"` as a subprocess with the ambient harness configuration; the script resolves the `-e` extension path against the repository root regardless of the caller's working directory. It parses the stdout JSON lines for assistant tool-call events, and records per case: the tool name of every task-surface call, the complete JSON argument object, every fail-closed teach-back content, and the number of launched children (envelopes with a completed or error state).
- The four cases and their prompts:
  1. `fresh`: "Use the task tool to dispatch one general-purpose subagent. Ask it to report the working directory it runs in. Relay the report, then finish." Measure: the tool name is `task`, and the argument object's keys are a subset of the `task` surface.
  2. `resume`: "Use the task tool to dispatch one general-purpose subagent and ask it to compute one plus one. Then use the task_resume tool to continue that child session and ask it to multiply the result by three. Relay both results." Measure: one fresh child and one resumed child, and `task_resume` receives the `task_id` from the earlier result.
  3. `unknown-resume`: "Use the task_resume tool with task_id set to the exact text nonexistent and the prompt 'Report status.' Wait for the result and relay it verbatim." Measure: zero launched children, and the result content is the fail-closed teach-back that preserves `nonexistent` and directs the caller to `task`.
  4. `camelcase`: "Use the task tool to dispatch one general-purpose subagent. Pass timeoutSeconds with the value 120 as a call argument, exactly that spelling. Relay the result." Measure: zero launched children, and the teach-back names `timeoutSeconds` and shows `timeout_seconds`.
- The script exits 0 when the hard measures hold: case 3 and case 4 record zero launched children. Cases 1 and 2 are recorded without hard thresholds. A case 2 failure to resume is a recorded observation, not a gate. Exit code 1 means a hard measure failed or a session failed to run and fails this task's gate. Exit code 3 means the ambient harness has no configured provider: the report records the blocked state and the gate accepts exit 3 with the blocked report, because the evaluation's value depends on the provider the harness configures and the proposal requires no specific provider.

**Behavior:**
- The report states, per case: the provider and model used, the emitted tool calls with their argument objects, the teach-back contents observed, and the launched-children count. A closing section states the two key measures: the count of optional fields on the ordinary fresh call, and the accidental-launch counts for the failed-resume cases.

**Tests must prove:** No unit tests. The check is the recorded report, the script's exit status, and ruff cleanliness of the new script.

**Check:**

```bash
cd extensions/superpowers-subagent
TAU_PYTHON=$(sed -n '1s/^#!//p' "$(command -v tau)")
TAU_SITE_PACKAGES=$("$TAU_PYTHON" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest -q
uv run ruff check .
uv run ruff format --check .
python scripts/agent_surface_evaluation.py \
  --output-dir ../../docs/design/evidence/task-tool-robustness/agent-surface-evaluation
```

Expected: the suite stays at the Task 7 gate count, ruff is clean, the script exits 0 or exits 3 with the blocked report, and `report.md` records the four cases.

- [ ] Write the evaluation script
- [ ] Run it against the ambient provider and record the report and raw events in the evidence directory
- [ ] Commit: `git add extensions/superpowers-subagent/scripts/ docs/design/evidence/task-tool-robustness/agent-surface-evaluation/ && git commit -m "test: add agent-facing surface evaluation"`

### Task 9: Post-implementation verification evidence

**Files:**
- Create: `docs/design/evidence/task-tool-robustness/post-implementation-tests/transcript.txt` — the full-check transcript in the baseline transcript's format

**Spec or proposal source:** Proposal Risks "Observability" (the implementation records a post-implementation transcript in the same immutable format as the baseline transcript) and Baseline Evidence (the fresh run evidences the starting state. this transcript evidences the finishing state).

**Proposal constraints:** The transcript format matches `docs/design/evidence/task-tool-robustness/baseline-tests/transcript.txt`: header comment lines naming the commit, the capture time in UTC, the command, and the interpreter and pytest versions, then the command output, then a final `[exit=N]` line.

**Interface:** None. This task runs checks and records evidence.

**Behavior:**
- The transcript header names the branch `task-tool-robustness`, the HEAD commit of Task 8, the capture time, the exact commands, and the interpreter and pytest versions.
- The transcript body holds the output of all four Commands-section commands and the Task 7 reference scan.
- The `pyproject.toml` version is `0.1.0`.

**Tests must prove:**
- The full suite, type check, lint, and format check pass at the finishing commit
- The recorded suite count equals the Task 7 gate count (the Task 6 gate count minus the README-contract test Task 7 deleted), because Tasks 7 and 8 touch no runtime code

**Check:**

```bash
cd /workspace
bash tests/check-references.sh
cd extensions/superpowers-subagent
TAU_PYTHON=$(sed -n '1s/^#!//p' "$(command -v tau)")
TAU_SITE_PACKAGES=$("$TAU_PYTHON" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
PYTHONPATH="$TAU_SITE_PACKAGES" uv run pytest -q
PYTHONPATH="$TAU_SITE_PACKAGES" uv run mypy
uv run ruff check .
uv run ruff format --check .
grep -n 'version = "0.1.0"' pyproject.toml
```

Expected: all green, the reference scan passes, and the grep prints the version line.

- [ ] Run all checks and record the transcript in the evidence directory
- [ ] Commit: `git add docs/design/evidence/task-tool-robustness/post-implementation-tests/ && git commit -m "test: record post-implementation verification transcript"`
