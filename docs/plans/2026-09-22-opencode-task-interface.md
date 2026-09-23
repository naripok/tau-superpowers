# OpenCode-aligned task interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Execute this plan task-by-task with the skill the workflow depth selects: executing-plans for Bounded, subagent-driven-development for Standard or High-risk. The controller marks every checkbox of a task `[x]` in the plan file when the task completes its gate, and records each flip in one tracking commit named `docs(plan): mark <plan-file-stem> Task N complete`.

**Goal:** Make the `task` tool take exactly one flat task per call, adopt the OpenCode result envelope, and support `task_id` resume of pinned child sessions.

**Architecture:** One surface, one code path. Validation parses the flat object and fails closed with teach-backs. Every fresh child runs in a pinned Tau session (`--session-id` plus `--session-role subagent`), every resume reconnects an existing child session (`--session`), and model-facing result content is one task envelope wrapping the child's final message.

**Tech Stack:** Python 3.14, pytest with pytest-asyncio, mypy strict, ruff. The extension runs inside Tau and spawns `tau` child processes in JSON mode.

**Standards:** Apply the shared code standards in every task: DRY, minimal implementation (YAGNI), low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only, writing-unambiguous-text prose.

**Feature spec:** `docs/design/2026-09-18-opencode-task-interface-spec.md` (the behavioral contract; approved version at commit `88f3ae6`)

**Approved proposal:** `docs/design/2026-09-18-opencode-task-interface-proposal.md` (intent, scope, binding architecture, constraints, non-goals, acceptance, and risk treatment; the exact operator-approved version at commit `8c32f7e`)

---

## Commands

Run every check from `extensions/superpowers-subagent/`. The extension imports Tau packages (`tau_agent`, `tau_coding`) from the installed runtime, so `PYTHONPATH` must include the Tau site-packages directory.

```bash
cd extensions/superpowers-subagent
export PYTHONPATH=/opt/tau/lib/python3.14/site-packages
V=/home/tau/venvs/superpowers/bin/python

$V -m pytest -q                # full suite; baseline is 267 passing at commit b833ebd
$V -m pytest tests/test_dispatch.py -q   # one file
$V -m mypy                     # strict; targets configured in pyproject.toml
$V -m ruff check .
$V -m ruff format --check .
```

The tool venv `/home/tau/venvs/superpowers` holds pytest, pytest-asyncio, mypy, and ruff. Recreate it with `uv venv /home/tau/venvs/superpowers --python 3.14` and `uv pip install --python /home/tau/venvs/superpowers/bin/python pytest pytest-asyncio mypy ruff` when missing.

Every task ends with all five checks passing. Expected suite count after all tasks: 267 baseline tests adjusted by each task's stated test changes, all passing.

## High-risk obligation mapping

| Obligation | Mapped to |
| --- | --- |
| Compatibility: breaking schema change, all consumers updated in-branch | Tasks 4, 5, and 7 update the model surface, the schema, and every in-repo consumer file listed in the proposal Impact section |
| Migration: operator re-installs the extension and skills, then restarts sessions | Task 7 documents the re-install and restart in the README |
| Rollout: extension version stays 0.1.0; behavior changes after session restart | Task 5 check asserts `pyproject.toml` still reads version 0.1.0 |
| Rollback: revert branch commits, re-install prior extension and skills, restart; pinned child sessions need no cleanup | Retained as a plan-review check: the plan touches only extension, skills, and docs, so a branch revert restores the prior surface. The README (Task 7) states that child sessions persist harmlessly |
| Observability: `taskId` on results and details, `tau sessions --all` listing | Tasks 1, 2, and 4 add the field and record it in tests. The listing behavior itself is Tau behavior: Task 2 proves the `--session-role subagent` argv that tags child sessions out of the default listing, and the capability transcript (docs/design/evidence/opencode-task-interface/tau-capability/transcript.txt) records that `tau sessions --all` lists role-tagged sessions while the default listing omits them |
| Recovery: quiescent store maintenance | Task 2 preserves the documented procedure in the spec. Task 7 documents it in the README |
| Risk treatments: no call cap, storage accumulation, resumed-run usage undercount, direct `tau --session` overlap, consent boundary, recursion closed | The no-call cap is tested in Task 4 (three concurrent calls all dispatch). Recursion closure keeps its existing runner tests. The resumed-run usage undercount rests on the unchanged collection contract (existing runner tests) plus the Task 2 resume tests showing details carry only the new turn's stream. The remaining accepted exposures are operator-facing statements carried by Task 7's README additions |

## Preservation mapping

Established unchanged baseline behavior gets regression checks only, never change work. The following keep their existing tests passing untouched:

- Config file loading, merging, and diagnostics (`config.py`, `test_config.py`)
- Agent discovery, frontmatter parsing, and layer precedence (`discovery.py`, `test_discovery.py`)
- Catalog scoping and override errors (`catalog.py`, `test_catalog.py`)
- Usage tracking and sidebar contract (`usage.py`, `sidebar.py`, `test_usage.py`, `test_sidebar.py`)
- Cost estimation (`costing.py`, `test_costing.py`)
- Child collection, timeout, cancellation, hard-kill, and temporary-file cleanup (`runner.py` internals, existing `test_runner.py` tests)
- Resume authorization: the spec requires possession-based authorization with no per-caller authorization and no auditing. There is nothing to implement. Tasks 2 and 3 preserve this scope by adding no access checks, and the Task 3 constraint text restates it

Existing tests that assert the superseded tasks-array surface are replaced inside Tasks 4 and 5. No other existing test changes behavior.

---

### Task 1: Additive session plumbing in models and utils

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/models.py` — add `SessionSelection` and additive `ChildResult` fields
- Modify: `extensions/superpowers-subagent/superpowers_subagent/utils.py` — teach `build_tau_argv` session selection
- Test: `extensions/superpowers-subagent/tests/test_models.py`
- Test: `extensions/superpowers-subagent/tests/test_utils.py`

**Spec or proposal source:** Spec ADDED "Pinned child sessions" (id recording), spec MODIFIED "Isolated Tau child invocation" (argv shape), proposal Approach "Pinned child sessions" and "Resume".

**Proposal constraints:** The tool name stays `task`. The recursion guard stays binary. Every fresh child gets a new generated session id. This task is additive: no caller changes behavior yet, and the full suite stays green.

**Interface:**

- `@dataclass(frozen=True, slots=True) class SessionSelection:` in `models.py`
  - `id: str` — the Tau session id. Fresh children carry a 32-character UUID hex value. Resume carries the existing session id exactly as recorded.
  - `resume: bool = False` — `False` pins a new session. `True` reconnects an existing session.
- `ChildResult` gains two fields with defaults so every existing construction site stays valid:
  - `task_id: str | None = None` — the child's Tau session id. `None` means no Tau session exists, which is the pre-session failure case only.
  - `notes: tuple[str, ...] = ()` — repair notes for model-facing content. Never serialized into details.
- `ChildResult.to_dict()` — when `task_id` is not `None`, add `"taskId": self.task_id` after `"agentSource"`. When `task_id` is `None`, emit no `taskId` key. `notes` never appears in `to_dict` output.
- `build_tau_argv(*, executable, cwd, prompt_path, task, provider, model, policy_path = None, thinking_policy_path = None, session: SessionSelection | None = None) -> list[str]`
  - `session is None`: argv is byte-for-byte the current baseline argv.
  - `session.resume` is `False`: insert `"--session-id", session.id, "--session-role", "subagent"` immediately after `"--no-approve"`. Keep the `"--cwd", str(cwd)` pair.
  - `session.resume` is `True`: insert `"--session", session.id` immediately after `"--no-approve"`. Emit no `--session-id`, no `--session-role`, and no `--cwd` flag. tau runs the child in the session's recorded cwd.
  - All other flags, extensions, overrides, and the positional task stay in the current order.

**Behavior:**

- Additive only. `dispatch.py` and `runner.py` compile and pass unchanged because the new parameters default to `None` and the new fields default to `None` and `()`.
- `SessionSelection` carries no behavior. It is the typed argv contract shared by the runner in Task 2.

**Tests must prove:**

- `test_models.py`: `to_dict` emits `taskId` equal to the session id when `task_id` is set, omits `taskId` when `task_id` is `None`, and never emits a `notes` key even when notes are set.
- `test_utils.py`: `build_tau_argv` with a fresh `SessionSelection` emits `--session-id <id>` and `--session-role subagent` after `--no-approve`, keeps `--cwd`, and keeps the task positional last. With a resumed `SessionSelection` it emits `--session <id>`, no `--session-id`, no `--session-role`, and no `--cwd`. With `session=None` it reproduces the baseline argv exactly.

**Check:** the five commands in the Commands section. Expected: all pass, and the previously failing new tests now pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent && git commit -m "feat: additive session plumbing for pinned child runs"`

### Task 2: Pinned sessions, resume, and fallbacks in the runner

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/runner.py` — session pinning, resume verification, fallbacks, resume prompt variant
- Modify: `extensions/superpowers-subagent/tests/fixtures/fake_tau.py` — record argv and simulate session failures
- Modify: `extensions/superpowers-subagent/tests/test_runner.py`
- Modify: `extensions/superpowers-subagent/tests/test_runtime_integration.py`

**Spec or proposal source:** Spec ADDED "Pinned child sessions", "task_id resume", "Resume working directory", "Unknown task_id fallback". Spec MODIFIED "Isolated Tau child invocation". Proposal Approach "Pinned child sessions", "Resume", and "Unknown task_id".

**Proposal constraints:** Children never register the `task` tool. The recursion guard environment variable and `--no-extensions` stay in the child argv. The runner reuses the established stderr-excerpt matching mechanism. Usage in details covers the resumed run only. The capability evidence pins the CLI flags: `tau --session-id <id> --session-role subagent --mode json` for fresh runs, `tau --session <id> --mode json` for resume, and `tau --session <missing-id>` exits 2 with `Unknown session: <id>` on stderr.

**Interface:**

- `TauChildRunner.__init__(self, executable: str = "tau", *, paths: TauPaths | None = None) -> None` — `paths` flows into the session-store lookup. `None` constructs the default `TauPaths()` (the real user store). Tests inject a redirected store.
- `TauChildRunner.run(...)` gains one keyword parameter: `resume_session_id: str | None = None`. All existing parameters keep their meaning. New behavior:
  - Generate `fresh_id = uuid.uuid4().hex` for every `run` call.
  - When `resume_session_id` is `None`: run one fresh invocation with `SessionSelection(id=fresh_id, resume=False)`. Set `result.task_id = fresh_id` and `result.cwd = str(resolved_cwd)` where `resolved_cwd = resolve_child_cwd(default_cwd, cwd_override)`.
  - When `resume_session_id` is set: verify through the store first. `record = SessionManager(self.paths).get_session(resume_session_id)`.
    - `record is None`: emit the unknown-session note, then run a fresh invocation with `SessionSelection(id=fresh_id, resume=False)`. Set `result.task_id = fresh_id` and `result.cwd = str(resolved_cwd)`.
    - `record.role != SUBAGENT_SESSION_ROLE`: emit the not-a-task-child note, then run a fresh invocation as in the missing-record case.
    - Otherwise: run one resumed invocation with `SessionSelection(id=resume_session_id, resume=True)`. Set `result.task_id = record.id` and `result.cwd = str(record.cwd)`. When `cwd_override` is not `None`, also emit the recorded-cwd note.
  - Runtime fallback: after a resumed invocation ends, when the invocation did not succeed and `_stderr_excerpt(result.stderr)` matches `unknown session:` case-insensitively, retry exactly once as a fresh invocation with `SessionSelection(id=fresh_id, resume=False)` and the call's `resolved_cwd`. The retry result replaces the failed attempt. Its `task_id` is `fresh_id`, its `cwd` is `str(resolved_cwd)`, and its `notes` are exactly the unknown-session note.
- Failure classification of pre-session causes stays inside the fresh-invocation path:
  - Pre-spawn cancellation (`_is_cancelled` before `create_subprocess_exec`) and `OSError`/`ValueError` from `create_subprocess_exec` leave `task_id` as `None`. These are the spec's pre-session failures: no Tau session exists.
  - Once the child process is spawned, `task_id` stays `fresh_id` on every later failure, including timeout, kill, and nonzero exit.
- Repair notes, pinned exact strings. The runner appends them to `result.notes` in this order:
  - Unknown session: `f"task_id {task_id} matched no session, so a fresh child started."`
  - Not a task child: `f"task_id {task_id} is not a task child session, so a fresh child started."`
  - Recorded cwd: `"The resumed run uses the session's recorded cwd."`
  - The runtime retry carries only the unknown-session note. It never carries the recorded-cwd note, because the retry runs as a fresh child in the call's cwd.
- `compose_child_prompt(agent: AgentConfig, *, resumed: bool = False) -> str` — when `resumed` is `True`, the first section of `_SHARED_INSTRUCTIONS` reads exactly:
  - `This session continues an earlier delegated task: the session's own prior turns are your earlier work on this task. Rely on them, this prompt, and the task input; you do not have the controller's conversation history. Do not invoke ambient user skills. That instruction is behavioral guidance, not a security boundary.`
  - Everything else in `_SHARED_INSTRUCTIONS`, the profile sections, and the agent-body joining rules stay unchanged.
- Refactor shape: extract the current `run` body after argument resolution into one private helper that takes the child's working directory, the `SessionSelection`, and the same overrides, and runs one child invocation. The fresh and fallback paths pass the resolved call cwd. The resume path passes the verified record's cwd, so the subprocess spawn directory matches the recorded cwd and the argv carries no `--cwd`. All collection, timeout, cancellation, hard-kill, stderr, and temporary-file logic moves unchanged. `run` keeps only session selection, verification, fallback, and note assembly. Import `SUBAGENT_SESSION_ROLE` from `tau_coding.session_manager` instead of writing the literal a second time. Keep the recursion-guard environment injection unchanged.

**Behavior:**

- Every fresh child argv now pins the session: `--session-id <fresh_id> --session-role subagent`. Every resume argv reconnects: `--session <task_id>` with no `--cwd`.
- The resume check reads the real Tau session store, so resume works within and across parent sessions and falls back cleanly on a cleaned-up store.
- Timeout, cancellation, kill, message collection, usage accumulation, malformed-line counting, and temporary-file cleanup behave exactly as before. Only argv, prompt text, and the new fields change.

**Tests must prove:**

- Fresh pinning: the fake tau receives `--session-id` with a 32-character hex value and `--session-role subagent`, and the result records that id as `task_id`.
- Resume argv: with a store record whose role is `subagent`, the fake tau receives `--session <id>`, no `--session-id`, no `--session-role`, no `--cwd`, and keeps `--no-extensions`, `--no-approve`, policy extensions, overrides, and the positional task.
- Verification failure on a missing record: the run falls back to a fresh child with a new id, and `result.notes` carries the unknown-session note.
- Verification failure on a wrong-role record (role `None` or another role): same fallback with the not-a-task-child note.
- Resume cwd: a resume call with `cwd_override` carries the recorded-cwd note, the result `cwd` equals the record's cwd, and the store record keeps its creation cwd. A resume call without `cwd_override` carries no cwd note.
- Runtime fallback: a fake tau that accepts `--session` and then exits 2 printing `Unknown session: <id>` on stderr produces one retry as a fresh child, a result whose `task_id` is the fresh id, and notes equal to the unknown-session note only.
- Resume under a different agent: a resume call naming a different `subagent_type` runs that agent's composed prompt and policy extensions against the same session.
- Resume usage: the details usage accumulates only the new turn's messages, not the prior turns.
- Cross-project resume: a store record whose project directory differs from the runner's cwd still verifies and resumes.
- No retry on other failures: a fake tau that exits 2 printing a different message produces no second invocation.
- Pre-session failure: a pre-spawn cancelled signal and a spawn `OSError` produce a result with `task_id is None`.
- Resume prompt variant: `compose_child_prompt(agent, resumed=True)` contains the pinned resume sentence and not the baseline isolation sentence. `resumed=False` reproduces the baseline text.
- Resumed-run settings: with `resumed=True` the runner still writes the profile policy extension and the thinking policy extension, and still appends the system prompt file, proving the regenerated settings ride the resumed run.
- Integration tests: update the fake-tau fixture to accept and log the new session flags, and update assertions that inspect child argv. Add one integration test that pins a session and resumes it through the full extension path.

**Check:** the five commands in the Commands section. Expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent && git commit -m "feat: pin child sessions and resume by task_id"`

### Task 3: Process-safe same-task_id lock

**Files:**
- Create: `extensions/superpowers-subagent/superpowers_subagent/locking.py` — non-blocking process-safe lock keyed by task id
- Test: `extensions/superpowers-subagent/tests/test_locking.py`

**Spec or proposal source:** Spec ADDED "Same-task_id exclusion". Proposal Approach (lock paragraph) and Risks "Concurrency".

**Proposal constraints:** The exclusion is process-safe and coordinates parent processes on the machine that hosts the session store. The losing call fails closed. A direct `tau --session` resume by another process is not prevented. No behavior beyond exclusion is authorized.

**Interface:**

- `def same_id_lock(task_id: str, *, locks_dir: Path | None = None) -> AbstractContextManager[None] | None` in `locking.py`
  - Returns a context manager that holds the lock for the duration of the `with` block, or `None` when another call already holds the lock for the same id.
  - `task_id` is the trimmed effective id. The lock file name is `hashlib.sha256(task_id.encode("utf-8")).hexdigest() + ".lock"`, so arbitrary user text maps to one portable file name.
  - `locks_dir` defaults to `TauPaths().sessions_dir / "locks"`. Create the directory on demand with `parents=True`.
  - Acquisition uses `fcntl.flock` with `LOCK_EX | LOCK_NB` on a freshly opened file descriptor. It never blocks the event loop.
  - Acquisition failure (`BlockingIOError`) returns `None`. The fd stays open and locked until the context manager exits, which unlocks and closes it. A dead process releases the lock through the kernel.
  - Use the non-blocking acquire inside the synchronous context-manager `__enter__`. The dispatcher calls it directly from async code; because the acquire never blocks, no async wrapper is needed.

**Behavior:**

- Two concurrent calls that carry the same trimmed `task_id` cannot both hold the lock, in one process or across processes.
- Distinct ids hold distinct locks and never conflict.
- The lock coordinates task-tool calls only. Nothing in the module inspects sessions or processes.

**Tests must prove:**

- Same process, same id: the first `same_id_lock` call returns a context manager, and a second call before release returns `None`.
- Same process after release: a third call acquires again.
- Distinct ids: both acquire at once.
- Cross-process: a subprocess holds the lock and sleeps, the parent's acquire returns `None`, then the parent acquires after the subprocess exits.
- Filename safety: a task id containing `/`, spaces, and unicode maps to one stable hex file name and acquires.

**Check:** the five commands in the Commands section. Expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent && git commit -m "feat: process-safe same-task_id lock"`

### Task 4: Flat dispatch surface with the task envelope

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/dispatch.py` — flat validation, teach-backs, envelope, single-child dispatch
- Modify: `extensions/superpowers-subagent/superpowers_subagent/models.py` — remove the superseded `TaskItem`
- Test: `extensions/superpowers-subagent/tests/test_dispatch.py`

**Spec or proposal source:** Spec MODIFIED "task interface and validation", "Agent definition discovery", "Content envelope and complete details", "Provider, model, and reasoning-effort overrides", "Progress, cancellation, timeout, and cleanup". Spec ADDED "Task result envelope", "Concurrent task calls", "Same-task_id exclusion". Spec REMOVED: none.

**Proposal constraints:** The per-call options are exactly the eleven named fields. Child status markers live inside messages. The result of a `task` call arrives when the child finishes. Fail closed on unknown fields, background, invalid values, unknown agents, and a lost same-id race. The usage tracker, sidebar, and renderer contracts hold through one-element sequences. `planned` carries the value 1 whenever a child starts or is attempted.

**Interface:**

- Remove: `MAX_TASKS`, `MAX_CONCURRENCY`, the slot-pool worker structure in `_run_children`, `_parse_items`, `_unknown_agent_result`, `_not_started_result`, and the `TaskItem` import. Remove `TaskItem` from `models.py` in this task, because this task is the last user of the last list-shaped surface.
- `DEFAULT_TIMEOUT_SECONDS = 3600.0` stays the default. Add `MAX_TIMEOUT_SECONDS = 10800.0`. Validation accepts `0 < timeout_seconds <= MAX_TIMEOUT_SECONDS`. The rejection message reads `timeoutSeconds must be greater than 0 and at most 10800`.
- `ParsedRequest` becomes the flat request:
  - `prompt: str` — verbatim call prompt.
  - `subagent_type: str` — the effective agent name after trimming. Omission resolves to `general-purpose`.
  - `description: str | None`
  - `task_id: str | None` — trimmed effective id used for session lookup, the lock, and repair notes.
  - `cwd: str | None`
  - `agent_scope: AgentScope`, `confirm_project_agents: bool`, `provider: str | None`, `model: str | None`, `reasoning_effort: str | None`, `timeout_seconds: float`, `notices: tuple[str, ...] = ()`.
- `validate_arguments(arguments) -> ParsedRequest` rules:
  - Allowed keys are exactly `prompt`, `subagent_type`, `description`, `task_id`, `cwd`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`. Any other key raises `ValidationFailure(f"unknown field(s): {', '.join(sorted(unknown))}")`.
  - `background` present raises `ValidationFailure` with the message `background dispatch is not supported in this harness. The result of a task call arrives when the child finishes; use several task calls in one message to run children in parallel.` The teach-back content adds the roster and the flat example.
  - `prompt` required: missing, non-string, or empty after strip raises `ValidationFailure("prompt requires a non-empty string")`. The prompt is stored verbatim.
  - `subagent_type` optional: non-string or empty after strip raises `ValidationFailure("subagent_type requires a non-empty string when present")`. Store the trimmed value.
  - `description` optional string. `task_id` optional: non-string or empty after strip raises `ValidationFailure("task_id requires a non-empty string when present")`. Store the trimmed value. `cwd` optional string.
  - Cross-field rule: when `task_id` is present and `subagent_type` was absent from the arguments, raise `ValidationFailure("task_id requires subagent_type: pass the agent whose prompt the resumed run uses")`. The teach-back content names both fields.
  - `agentScope` must be `user`, `project`, or `both`, else `ValidationFailure("agentScope must be `user`, `project`, or `both`")`. `confirmProjectAgents` must be a boolean.
  - `provider` and `model` keep `_optional_literal_override` exactly: trim, reject empty-after-trim with the omission explanation, coerce case-insensitive `default`, `inherit`, `auto` to omitted with the repair note. `reasoningEffort` keeps `_optional_thinking_level` exactly.
  - `timeoutSeconds` keeps the number checks (no bool, int or float) with the new cap.
- `TaskDispatcher.execute` flow, in order:
  1. Lenient scope read, discovery, config diagnostics merge (unchanged).
  2. `validate_arguments`; on `ValidationFailure` return the fail-closed teach-back result.
  3. Eligibility: `request.subagent_type` absent from the discovered agents returns the fail-closed teach-back result whose content is `Invalid parameters: unknown agent '<name>'` plus the roster and the flat example. No child starts.
  4. Catalog override check for the one effective pair, using `effective_provider_model` with the config chain. Drop the `tasks[{index}]: ` prefix. Unknown agents never reach this check.
  5. Project approval, unchanged baseline logic, with two result-shape changes:
     - Headless without approval: fail-closed teach-back result. Content keeps the current message that names the project agents directory. Details carry an empty `results` array and no `planned`.
     - Interactive denial: pre-session failure result. Build one `ChildResult` with `agent=request.subagent_type`, `task=request.prompt`, `cwd=str(resolve_child_cwd(self.default_cwd, request.cwd))`, `error_message="Canceled: project-local agents were not approved."`, `status="BLOCKED"`, and `task_id=None`. Content is the envelope of that result. Details carry that one entry and `planned` 1. No child starts.
  6. Same-id lock: when `request.task_id` is not `None`, acquire `same_id_lock(request.task_id)`. `None` returns the fail-closed teach-back result whose content names the conflict: `Invalid parameters: another running task call already holds task_id '<id>'. Wait for that call to finish or use a different task_id.` The lock context wraps the child run and releases in a `finally`. Test isolation: `locking.py` computes its default locks directory per acquisition, so tests redirect it by monkeypatching `HOME` to a temporary directory before constructing the dispatcher. No dispatcher parameter is added.
  7. Single-child dispatch: call `self.runner.run(...)` once with `resume_session_id=request.task_id`, the resolved overrides, and `on_message` wired to partial updates. No worker pool and no slots.
- Envelope content builder in `dispatch.py`:
  - `def build_envelope(result: ChildResult) -> str` — renders the model-facing envelope for one child result.
  - `has_final = any(isinstance(message, AssistantMessage) for message in result.messages)`. `state = "completed"` when `result.succeeded and has_final`, else `"error"`.
  - Opening tag: `<task id="{result.task_id}" state="{state}">` when `task_id` is not `None`, else `<task state="{state}">`.
  - Completed body: `<task_result>` wrapping `final_output(result.messages)` or `(no output)` when the final message has no text.
  - Error body, in this order: when a final assistant message exists, `<task_error>` wraps its text or `(no output)` when textless. When no final message exists and `task_id` is not `None`, `<task_error>` wraps `Subagent failed (task_id: {result.task_id}): {result.error_message or "unknown error"}`. When no final message exists and `task_id` is `None`, `<task_error>` wraps `result.error_message` verbatim.
  - Inner content is verbatim. No escaping.
- `_result_content(result, notes)` — render `Note: {note}` lines from the merged `notes` tuple, one blank line, then `build_envelope(result)`. The caller merges the two note sources in one place: `(*request.notices, *result.notes)`. Match the baseline note assembly shape.
- Partial updates: content is `f"{done}/1 done"` where `done` is 1 when the single child result is terminal (`exit_code != 1 or error_message is not None`) and 0 otherwise. Details keep `planned` 1 and the current results array. Usage observer wiring is unchanged.
- Final details: `results=[child_result]`, `planned=1`, additive `taskId` from Task 1. Pre-session denial entry carries no `taskId`. Fail-closed results (validation, eligibility, catalog, headless approval, lock loss) carry `results=[]` and no `planned`, exactly as the baseline `_tool_result(results=[])` does.
- Teach-back roster: render `_roster` from the discovered agents filtered to `source in {"bundled", "user"}`, keeping the baseline `name (source): description` form joined by `; `. The source suffix stays, because the filter already excludes project agents. Project agent names and descriptions never appear. `_invalid_parameters_content` keeps the session-inheritance and thinking-level lines and ends with the one flat example line `Example: {"prompt": "Find caching options"}`.

**Behavior:**

- One call runs exactly one child. Two or more `task` calls in one assistant message run concurrently through Tau's parallel tool scheduling, each with its own dispatcher and envelope.
- The envelope state is the process outcome only. Child status markers stay inside the wrapped message text.
- The catalog, config, discovery, usage, and sidebar seams keep their current call shapes through one-element sequences.

**Tests must prove:**

- Flat validation teach-backs: unknown field (`mode`), `background`, missing or empty `prompt`, whitespace `subagent_type`, whitespace `task_id`, `task_id` without `subagent_type` (teach-back names both fields), non-boolean `confirmProjectAgents`, invalid `agentScope`, timeout at 0 and negative, timeout above 10800, timeout accepted at 10800 and at 3600 default. Each asserts no child started and the teach-back content elements.
- Fail-closed result contract: content is the teach-back, details `results` empty, no `planned` key, and no envelope in content.
- Placeholder coercion and whitespace-only overrides: notes surface as `Note:` lines before the envelope; whitespace-only rejects with both content statements.
- Eligibility: an unknown `subagent_type` fails closed with a roster listing and no project agent named, including when `agentScope` is `both`.
- Project approval: headless failure carries the directory-naming teach-back with empty results and no `planned`; interactive approval proceeds; interactive denial carries the no-id error envelope, a details entry without `taskId`, and `planned` 1.
- Envelope states: completed with message text, completed with a textless final message (`(no output)`), error with a final message, error textless final (`(no output)` in `task_error`), error without a final message (OpenCode form with the id), pre-session failure without the id attribute, cancellation before startup (a task_id-less cancelled result renders the error envelope with no id attribute wrapping the cancellation text), a `BLOCKED`-marked final message inside a `completed` envelope, verbatim content with markup-like characters, `Note:` placement.
- Default selection: a valid call with only `prompt` dispatches one `general-purpose` child.
- Details: schemaVersion 2, one entry whose `taskId` equals the envelope id, `planned` 1, and the full baseline field list preserved.
- Concurrency: three concurrent `execute` calls with distinct ids all complete with their own envelopes; one failing child leaves the others intact.
- Same-id exclusion: two concurrent `execute` calls with the same `task_id` produce one child result and one fail-closed teach-back with no envelope, empty results, and no `planned`.
- Catalog: an unsupported override fails closed with the catalog message and no `tasks[` prefix.
- Partial updates: content `<done>/1 done` while running and after completion, `planned` 1, envelope only on the final result.

**Check:** the five commands in the Commands section. Expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent && git commit -m "feat: flat single-object task surface with result envelope"`

### Task 5: OpenCode-aligned extension tool surface

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/extension.py` — schema, description, guidelines, roster scope
- Test: `extensions/superpowers-subagent/tests/test_extension.py`

**Spec or proposal source:** Spec MODIFIED "task interface and validation" (schema), ADDED "Tool description roster". Spec MODIFIED "Provider, model, and reasoning-effort overrides" (guidance), "Progress, cancellation, timeout, and cleanup" (schema maximum).

**Proposal constraints:** The tool name is `task`. The bundled agents are `general-purpose`, `read-only`, `implementation`, `code-review`, and `document-review`. Rosters list bundled and user agents only, anchored at the session cwd, static per session, with the bundled fallback. Project agents stay out of every roster. The extension version stays 0.1.0.

**Interface:**

- `_PROFILE_ANNOTATIONS: dict[str, str] = {"general-purpose": "all", "read-only": "read", "review": "read, bash"}` — the profile-to-annotation mapping.
- `_agent_roster(cwd: Path | None) -> str` changes:
  - Discover with scope `"user"` (bundled plus user only), not `"both"`.
  - Render one line per discovered agent in sorted name order: `- {name}: {one_line(description)} (Tools: {annotation})` where `annotation` is `_PROFILE_ANNOTATIONS[agent.profile]`.
  - On discovery failure return `""` as before.
  - The fallback when discovery returns empty or fails is the static bundled roster with the same line format:
    - `- general-purpose: General-purpose subagent with full tool access. (Tools: all)`
    - `- implementation: Implementation subagent for code, tests, and verification. (Tools: all)`
    - `- read-only: Read-only subagent for named-file investigation. (Tools: read)`
    - `- code-review: Adversarial read-only code reviewer. (Tools: read, bash)`
    - `- document-review: Adversarial read-only document reviewer. (Tools: read, bash)`
- `_task_parameters()` returns the flat schema:
  - `type` object, `additionalProperties` false, `required` `["prompt"]`.
  - `prompt`: string, `minLength` 1, description `The child's task. The prompt is preserved verbatim.`
  - `subagent_type`: string, `minLength` 1, description names the agent selection rule and carries the roster text.
  - `description`: string, description `Short orchestration label for display. No behavioral effect.`
  - `task_id`: string, `minLength` 1, description `Resume a previous child session: pass the task_id from an earlier task result to continue the same subagent session instead of starting a fresh one. Requires subagent_type.`
  - `cwd`: string, description `Working directory for a fresh child. Omission uses this session's cwd. Ignored on a resumed run.`
  - `agentScope`, `confirmProjectAgents`: keep the current definitions and descriptions.
  - `provider`: description gains the coercion sentence: `A default, inherit, or auto placeholder is coerced to omitted with a repair note.` The exact-name rule and fail-fast statements stay.
  - `model`: description gains the same coercion sentence. The exact-model-ID rule and fail-fast statements stay.
  - `reasoningEffort`: description gains the same coercion sentence. The level list and fallback chain stay.
  - `timeoutSeconds`: `{"type": "number", "exclusiveMinimum": 0, "maximum": 10800, "default": 3600}` with the current description.
  - No `tasks` property remains.
- The tool description follows the OpenCode layout in this order:
  1. One-liner: `Dispatch work to an isolated Tau subagent. Delegate substantive multi-step work that benefits from an isolated context window, or long-running work that must not block this session.`
  2. The annotated roster lines from `_agent_roster`.
  3. Default rule: `Omit subagent_type to select general-purpose.`
  4. When-not-to-use: `Simple reads, searches, commands, and small edits are your own tool calls, and you never dispatch work you are about to perform yourself. Never dispatch a task and then do the same work.`
  5. Usage notes, each one bullet:
     - `Several tasks are several task calls in one message. Use separate calls for conditional sequences where a later step depends on an earlier result.`
     - `Delegated work is not duplicated.`
     - `Make each prompt self-contained: children run in isolated sessions with no access to this conversation.`
     - `The result names the task_id that a later call can reuse to continue the same subagent session.`
     - `State whether the child writes code or does research and how to verify the result.`
     - `Project-controlled agent prompts require explicit approval.`
- `prompt_guidelines` keeps the current six retained rules, with these changes:
  - Remove the `Always pass the tasks array` guideline.
  - Add `Pass exactly one task per call. Several tasks are several task calls in one message; use separate task-tool calls for conditional sequences where a later step depends on an earlier result.`
  - Add `The result carries the child's task_id. Pass it as task_id on a later call, with the same subagent_type, to continue that child session instead of starting a fresh one.`
  - Add `State whether the child writes code or does research and how to verify the result.`
  - Update the override guideline's last sentence to state the coercion: `the tool treats them as omitted with a repair note.` The threshold, prohibition, agent-picking, and status-marker guidelines stay.

**Behavior:**

- The schema rejects unknown properties before the tool runs. The description teaches the flat form, the roster, the default, the exclusions, and resume.
- The roster is computed once at setup and stays static for the session, including its annotations.

**Tests must prove:**

- The schema has `required ["prompt"]`, no `tasks` property, `timeoutSeconds` maximum 10800 and default 3600, and `additionalProperties` false.
- The `provider`, `model`, and `reasoningEffort` schema descriptions each state that a `default`, `inherit`, or `auto` placeholder is coerced to omitted with a repair note.
- The description contains the five roster lines with annotations in the pinned format, the default-rule sentence, the when-not-to-use text, and the usage-note statements for multi-call parallelism, `task_id` reuse, and verification.
- A user definition that shadows a bundled name changes that line's annotation to the resolved definition's profile.
- Discovery failure falls back to the static annotated bundled roster.
- `prompt_guidelines` carries the four changed guidelines and no longer mentions the tasks array.
- `pyproject.toml` still reads `version = "0.1.0"`.

**Check:** the five commands in the Commands section. Expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent && git commit -m "feat: OpenCode-aligned task tool surface"`

### Task 6: Description-first call label in rendering

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/rendering.py` — call label rule
- Test: `extensions/superpowers-subagent/tests/test_rendering.py`

**Spec or proposal source:** Spec MODIFIED "Portable rendering".

**Proposal constraints:** The label is the description when it is non-empty after trimming, and the effective `subagent_type` otherwise. The label never derives from the task count.

**Interface:**

- `render_task_call(arguments)`:
  - When `arguments.get("description")` is a string whose trimmed value is non-empty, the label is the description value as given, collapsed by `_one_line` for display.
  - Otherwise the label is the effective `subagent_type`: the trimmed value of `arguments.get("subagent_type")` when it is a non-empty string after trimming, else `general-purpose`.
  - Remove `_call_label` and its task-count logic. Keep the `▸ Task · ` prefix and the `escape` call.

**Behavior:**

- The rendered call line shows the caller's label or the effective agent name. The rendered line never contains Rich tags from user text.

**Tests must prove:**

- A description call renders the description.
- A call without `description` renders the effective `subagent_type`.
- A whitespace-only `description` falls back to the effective `subagent_type`.
- A call without either field renders `general-purpose`.
- No `tasks`-count label appears anywhere.

**Check:** the five commands in the Commands section. Expected: all pass.

- [ ] Write the failing tests for the behaviors above. Run them and check that each fails for the expected reason
- [ ] Implement the interface and behavior
- [ ] Run verification (tests, lint, type check)
- [ ] Commit: `git add extensions/superpowers-subagent && git commit -m "feat: description-first task call label"`

### Task 7: Consumer documentation across README, reference, and skills

**Files:**
- Modify: `README.md` — task tool section
- Modify: `skills/using-superpowers/references/tau-tools.md`
- Modify: `skills/dispatching-parallel-agents/SKILL.md`
- Modify: `skills/subagent-driven-development/SKILL.md`
- Modify: `skills/subagent-driven-development/implementer-prompt.md`
- Modify: `skills/subagent-driven-development/implementation-reviewer-prompt.md`
- Modify: `skills/requesting-code-review/SKILL.md`
- Modify: `skills/requesting-code-review/code-reviewer.md`
- Modify: `skills/writing-skills/testing-skills-with-subagents.md`
- Modify: `skills/writing-skills/examples/skill-testing-example.md`
- Modify: `skills/brainstorming/feature-spec-author-prompt.md`
- Modify: `skills/brainstorming/proposal-document-reviewer-prompt.md`
- Modify: `skills/brainstorming/spec-document-reviewer-prompt.md`
- Modify: `skills/writing-plans/plan-document-reviewer-prompt.md`
- Modify: `skills/finishing-a-development-branch/living-spec-document-reviewer-prompt.md`

**Spec or proposal source:** Proposal Scope "In scope" (consumer updates) and Impact (file list). Spec ADDED "Tool description roster" and "task_id resume" (consumer-facing statements). Spec MODIFIED "task interface and validation".

**Proposal constraints:** Multi-child examples become several `task` calls in one message. No deprecated aliases and no historical framing: documents describe current behavior only. All developer-facing text follows the writing-unambiguous-text skill.

**Interface:** Documentation only. No code or schema changes. Every task call example in these files uses the flat form with the OpenCode field names: `prompt`, `subagent_type`, `description`, `task_id`, `cwd`, `agentScope`, `confirmProjectAgents`, `provider`, `model`, `reasoningEffort`, `timeoutSeconds`.

**Behavior:** Each file's task-call examples and instructions describe:

- One task per call, several calls per message for parallel work, and separate calls for conditional sequences.
- `subagent_type` optional with the `general-purpose` default.
- The envelope content form and the `taskId` on results and details.
- `task_id` resume: pass the earlier result's `task_id` with `subagent_type` to continue the same child session.
- The 3600-second default timeout and the 10800-second cap.
- The catalog fail-fast and override-guidance statements keep their current meaning, with placeholders coerced to omitted.

README additions in the task tool section: the re-install and restart migration step, the statement that child sessions accumulate in the Tau session store and that cleanup is the quiescent store-maintenance procedure from the feature spec, the no-call-cap risk acceptance, the resumed-run usage undercount, the rollback note that a branch revert never reads pinned child sessions and needs no cleanup, the statement that a direct `tau --session` resume bypasses the task-tool lock and the operator accepts that overlap, and the statement that the approval prompt is the consent boundary for repository-controlled project agents.

**Tests must prove:** No runtime behavior changes. The check is a reference scan.

**Check:**

```bash
cd /workspace/.worktrees/opencode-task-interface
rg -n '"tasks"' README.md skills/ && exit 1 || echo "no tasks-array call examples"
rg -n 'tasks\s*=\s*\[' README.md skills/ && exit 1 || echo "no python tasks-array examples"
cd extensions/superpowers-subagent && export PYTHONPATH=/opt/tau/lib/python3.14/site-packages && /home/tau/venvs/superpowers/bin/python -m pytest -q
```

Expected: the greps find no tasks-array call examples in consumers, and the suite still passes. Eyeball each edited file for current-state-only wording.

- [ ] Apply the flat-form rewrite to every listed file
- [ ] Run the check commands
- [ ] Commit: `git add README.md skills && git commit -m "docs: flat task surface across consumers"`

---

## Final verification

Run from `extensions/superpowers-subagent/` after Task 7:

```bash
export PYTHONPATH=/opt/tau/lib/python3.14/site-packages
V=/home/tau/venvs/superpowers/bin/python
$V -m pytest -q && $V -m mypy && $V -m ruff check . && $V -m ruff format --check .
```

Expected: every test passes, mypy strict is clean, and ruff is clean. Then the controller proceeds to final whole-change review per the High-risk gate.
