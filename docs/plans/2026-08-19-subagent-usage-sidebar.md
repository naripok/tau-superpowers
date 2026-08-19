# Subagent Usage Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggregate subagent token usage and cost across task calls within the active session and display the running totals in a `subagents` sidebar section directly below the `usage` section.

**Architecture:** An extension-owned `SubagentUsageTracker` is fed through an optional observer hook on `TaskDispatcher`: every live update replaces an in-flight snapshot (child usage is cumulative per child), and each call's final result commits exactly once. A guarded wrapper around the TUI's internal sidebar content builder (`tau_coding.tui.widgets._build_sidebar_content` — the single choke point for sidebar sections) splices the new section in below `usage`. Any seam failure disables only the display; aggregation, dispatch, and rendering stay untouched.

**Tech Stack:** Python 3.14, Tau extension API (`tau_agent`, `tau_coding`), Rich primitives owned by the TUI, pytest, ruff, mypy strict.

**Standards:** Apply the shared code standards in every task: DRY, low cyclomatic complexity, type safety, no unnecessary abstractions or fallbacks, no hacks or workarounds, informative docstrings, documentation of current state only.

**Feature spec:** `docs/design/2026-08-19-subagent-usage-sidebar-spec.md`

**Delta spec:** `docs/design/2026-08-19-subagent-usage-sidebar-delta.md`

**Note:** updating the living spec (`docs/specs/subagent-dispatch.md`) with the accepted delta happens in the finishing step, not in this plan.

---

## Environment and commands

All commands run from `extensions/superpowers-subagent/` (the extension checkout). The Tau packages (`tau_agent`, `tau_coding`, `rich`, `pydantic`) live outside the project venv, so tests and type-checks need their paths:

```bash
# run one test file
PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest tests/test_FILE.py -q

# run the whole suite
PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest -q

# lint and format
.venv/bin/ruff check superpowers_subagent tests
.venv/bin/ruff format --check superpowers_subagent tests

# strict type check (uses the Tau interpreter to resolve the tau packages)
.venv/bin/mypy --python-executable /opt/tau/bin/python superpowers_subagent
```

Baseline before this feature: 131 tests pass, ruff and mypy clean.

---

## Task 1: Session-scoped usage tracker

**Files:**
- Create: `extensions/superpowers-subagent/superpowers_subagent/usage.py`
- Create: `extensions/superpowers-subagent/tests/test_usage.py`

**Delta requirement:** ADDED "Session-scoped subagent usage aggregation"

- [ ] **Step 1: Write the failing tests**

Create `tests/test_usage.py`:

```python
"""Tracker tests for session-scoped subagent usage aggregation.

These tests pin the "Session-scoped subagent usage aggregation" delta
requirement: snapshot replacement semantics, exactly-once commits, zero-usage
children, partial usage after process failure, rebind resets, and cost
handling.
"""

from __future__ import annotations

from superpowers_subagent.models import ChildResult, UsageStats
from superpowers_subagent.usage import SubagentUsageTotals, SubagentUsageTracker


def _child(
    *,
    input: int = 0,
    output: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    cost: float = 0.0,
    timed_out: bool = False,
) -> ChildResult:
    return ChildResult(
        agent="implementation",
        agent_source="bundled",
        task="work",
        cwd="/workspace",
        exit_code=1 if timed_out else 0,
        timed_out=timed_out,
        usage=UsageStats(
            input=input,
            output=output,
            cache_read=cache_read,
            cache_write=cache_write,
            cost=cost,
        ),
    )


def test_tracker_starts_empty() -> None:
    """Prove a fresh tracker reports no usage and no runs."""
    tracker = SubagentUsageTracker()

    totals = tracker.totals

    assert totals.runs == 0
    assert totals.input_tokens == 0
    assert totals.output_tokens == 0
    assert totals.cached_input_tokens == 0
    assert totals.cache_write_tokens == 0
    assert totals.cost == 0.0
    assert totals.has_usage is False


def test_live_updates_replace_the_snapshot() -> None:
    """Prove live snapshots replace rather than accumulate: a child's usage is
    cumulative over its own messages, so totals must show the latest values
    without double counting."""
    tracker = SubagentUsageTracker()

    tracker.update("call-1", [_child(input=100, output=50)], final=False)
    tracker.update("call-1", [_child(input=150, output=80)], final=False)

    totals = tracker.totals
    assert totals.runs == 1
    assert totals.input_tokens == 150
    assert totals.output_tokens == 80


def test_commit_folds_each_call_once() -> None:
    """Prove each call's final result is committed exactly once and calls
    accumulate across the session."""
    tracker = SubagentUsageTracker()

    tracker.update("call-1", [_child(input=100, output=50, cost=0.01)], final=True)
    tracker.update(
        "call-2",
        [_child(input=200, output=100), _child(input=50, output=25)],
        final=True,
    )

    totals = tracker.totals
    assert totals.runs == 3
    assert totals.input_tokens == 350
    assert totals.output_tokens == 175
    assert totals.cost == 0.01


def test_snapshot_cleared_on_commit() -> None:
    """Prove a committed call no longer contributes through the snapshot: the
    snapshot is cleared so the displayed totals cannot double-count it."""
    tracker = SubagentUsageTracker()
    child = _child(input=100, output=50)

    tracker.update("call-1", [child], final=False)
    tracker.update("call-1", [child], final=True)

    assert tracker.totals.input_tokens == 100
    assert tracker.totals.runs == 1


def test_discard_pending_drops_snapshot() -> None:
    """Prove a call that ends without committing discards its in-flight
    snapshot, leaving only the committed totals."""
    tracker = SubagentUsageTracker()
    tracker.update("call-1", [_child(input=100, output=50)], final=True)

    tracker.update("call-2", [_child(input=500, output=250)], final=False)
    tracker.discard_pending("call-2")

    totals = tracker.totals
    assert totals.input_tokens == 100
    assert totals.output_tokens == 50
    assert totals.runs == 1


def test_zero_usage_children_contribute_nothing() -> None:
    """Prove children with no reported usage or cost add no tokens, cost, or
    run count, so never-started children cannot inflate the section."""
    tracker = SubagentUsageTracker()
    empty = _child()

    tracker.update("call-1", [_child(input=100, output=50), empty], final=True)

    totals = tracker.totals
    assert totals.runs == 1
    assert totals.input_tokens == 100


def test_partial_usage_children_are_included() -> None:
    """Prove a timed-out child keeps its partial usage: tokens were really
    consumed even though the child never completed."""
    tracker = SubagentUsageTracker()

    tracker.update("call-1", [_child(input=60, output=30, timed_out=True)], final=True)

    assert tracker.totals.input_tokens == 60
    assert tracker.totals.runs == 1


def test_reset_clears_everything() -> None:
    """Prove a session-rebind reset returns the tracker to its initial state,
    committed totals and in-flight snapshot alike."""
    tracker = SubagentUsageTracker()
    tracker.update("call-1", [_child(input=100, output=50)], final=True)
    tracker.update("call-2", [_child(input=10, output=5)], final=False)

    tracker.reset()

    assert tracker.totals == SubagentUsageTotals()


def test_prompt_tokens_include_cached_and_written() -> None:
    """Prove the displayed input figure includes cached and cache-written
    tokens, mirroring the session usage section's input definition."""
    tracker = SubagentUsageTracker()

    tracker.update("call-1", [_child(input=100, cache_read=50, cache_write=10)], final=True)

    assert tracker.totals.prompt_tokens == 160
    assert tracker.totals.input_tokens == 100


def test_cost_reported_only_when_nonzero() -> None:
    """Prove cost accumulates only from children that actually reported it."""
    tracker = SubagentUsageTracker()

    tracker.update(
        "call-1",
        [_child(input=100, output=50, cost=0.0), _child(input=200, output=100, cost=0.5)],
        final=True,
    )

    assert tracker.totals.cost == 0.5


def test_concurrent_calls_keep_separate_snapshots() -> None:
    """Prove two in-flight calls each keep their own snapshot: committing or
    discarding one call never drops the other call's in-flight display."""
    tracker = SubagentUsageTracker()

    tracker.update("call-a", [_child(input=100, output=50)], final=False)
    tracker.update("call-b", [_child(input=200, output=100)], final=False)

    totals = tracker.totals
    assert totals.runs == 2
    assert totals.input_tokens == 300

    tracker.update("call-a", [_child(input=150, output=80)], final=True)

    totals = tracker.totals
    assert totals.input_tokens == 350
    assert totals.runs == 2

    tracker.discard_pending("call-b")

    assert tracker.totals.input_tokens == 150
    assert tracker.totals.runs == 1


def test_discard_unknown_call_is_a_noop() -> None:
    """Prove discarding an unknown call key leaves all snapshots intact."""
    tracker = SubagentUsageTracker()
    tracker.update("call-a", [_child(input=100, output=50)], final=False)

    tracker.discard_pending("unknown-call")

    assert tracker.totals.input_tokens == 100
    assert tracker.totals.runs == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest tests/test_usage.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'superpowers_subagent.usage'`

- [ ] **Step 3: Implement the tracker**

Create `superpowers_subagent/usage.py`:

```python
"""Session-scoped aggregation of delegated subagent token usage and cost."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .models import ChildResult


@dataclass(frozen=True, slots=True)
class SubagentUsageTotals:
    """Cumulative subagent usage for one session, in sidebar display form."""

    runs: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0

    @property
    def has_usage(self) -> bool:
        """Whether any subagent run has reported token usage or cost."""
        return self.runs > 0

    @property
    def prompt_tokens(self) -> int:
        """Prompt input including cached and cache-written tokens.

        Mirrors the session usage section's input figure so the subagents
        section reads consistently next to it.
        """
        return self.input_tokens + self.cached_input_tokens + self.cache_write_tokens


def _add_child(totals: SubagentUsageTotals, child: ChildResult) -> SubagentUsageTotals:
    """Return ``totals`` plus one child's usage; zero-usage children add nothing."""
    usage = child.usage
    consumed = usage.input + usage.output + usage.cache_read + usage.cache_write
    if consumed <= 0 and usage.cost <= 0:
        return totals
    return SubagentUsageTotals(
        runs=totals.runs + 1,
        input_tokens=totals.input_tokens + usage.input,
        cached_input_tokens=totals.cached_input_tokens + usage.cache_read,
        cache_write_tokens=totals.cache_write_tokens + usage.cache_write,
        output_tokens=totals.output_tokens + usage.output,
        cost=totals.cost + usage.cost,
    )


class SubagentUsageTracker:
    """Aggregate child usage across task calls within the active session.

    Each in-flight call keeps its own snapshot of the latest child results
    (per-child usage is cumulative, so a snapshot is never additive); tool call
    ids are unique, so concurrent dispatch calls cannot collide. A call's final
    result commits once and drops that call's snapshot, an uncommitted call
    discards its own snapshot through ``discard_pending``, and a session rebind
    resets everything.
    """

    def __init__(self) -> None:
        self._committed = SubagentUsageTotals()
        self._active: dict[str, tuple[ChildResult, ...]] = {}

    def update(self, call_key: str, children: Sequence[ChildResult], final: bool) -> None:
        """Replace a call's in-flight snapshot, or commit its children once."""
        if final:
            for child in children:
                self._committed = _add_child(self._committed, child)
            self._active.pop(call_key, None)
        else:
            self._active[call_key] = tuple(children)

    def discard_pending(self, call_key: str) -> None:
        """Drop one call's in-flight snapshot; committed totals are untouched."""
        self._active.pop(call_key, None)

    def reset(self) -> None:
        """Clear all totals for a new, resumed, or branched session."""
        self._committed = SubagentUsageTotals()
        self._active = {}

    @property
    def totals(self) -> SubagentUsageTotals:
        """Committed totals plus every active call's latest snapshot."""
        totals = self._committed
        for children in self._active.values():
            for child in children:
                totals = _add_child(totals, child)
        return totals
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest tests/test_usage.py -q`
Expected: 12 passed

- [ ] **Step 5: Lint, format, and type-check**

Run: `.venv/bin/ruff check superpowers_subagent tests`
Expected: `All checks passed!`

Run: `.venv/bin/ruff format --check superpowers_subagent tests`
Expected: no files listed as needing formatting (run `ruff format superpowers_subagent tests` if any are)

Run: `.venv/bin/mypy --python-executable /opt/tau/bin/python superpowers_subagent`
Expected: `Success: no issues found in 10 source files`

- [ ] **Step 6: Commit**

```bash
git add superpowers_subagent/usage.py tests/test_usage.py
git commit -m "feat: session-scoped subagent usage tracker"
```

---

## Task 2: Dispatcher usage observer

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/dispatch.py`
- Modify: `extensions/superpowers-subagent/tests/test_dispatch.py`

**Delta requirement:** ADDED "Session-scoped subagent usage aggregation" (live snapshots and exactly-once per-call commits driven by the dispatcher)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_dispatch.py`:

```python
@pytest.mark.asyncio
async def test_single_dispatch_feeds_usage_observer(tmp_path: Path) -> None:
    """Prove single dispatch delivers live snapshots and exactly one final
    commit carrying the completed child, so the tracker never double counts."""

    calls: list[tuple[list[ChildResult], bool]] = []
    runner = FakeRunner()
    dispatcher = make_dispatcher(
        tmp_path,
        runner,
        usage_observer=lambda children, final: calls.append((list(children), final)),
    )

    result = await dispatcher.execute(
        {"agent": "general-purpose", "task": "task-one"}, signal=None, on_update=None
    )

    assert calls, "observer was never fed"
    finals = [final for _children, final in calls]
    assert finals.count(True) == 1
    assert finals[-1] is True
    final_children, _ = calls[-1]
    assert len(final_children) == 1
    assert final_children[0].task == "task-one"
    # Aggregation must not alter the result: content and details stay intact.
    assert result.text.strip()
    details = result.details
    assert details is not None and details["schemaVersion"] == 1
    assert len(details["results"]) == 1
    assert len(details["results"][0]["messages"]) == 1


@pytest.mark.asyncio
async def test_parallel_dispatch_commits_all_children_once(tmp_path: Path) -> None:
    """Prove parallel dispatch feeds snapshots while children complete and one
    final commit with every result in input order."""

    calls: list[tuple[list[ChildResult], bool]] = []
    runner = FakeRunner()
    dispatcher = make_dispatcher(
        tmp_path,
        runner,
        usage_observer=lambda children, final: calls.append((list(children), final)),
    )
    items = [
        {"agent": "general-purpose", "task": f"parallel-{index}"}
        for index in range(4)
    ]

    await dispatcher.execute({"tasks": items}, signal=None, on_update=None)

    finals = [final for _children, final in calls]
    assert finals.count(True) == 1
    final_children, _ = calls[-1]
    assert [child.task for child in final_children] == [f"parallel-{index}" for index in range(4)]
    assert any(final is False for _children, final in calls), "no live snapshot was fed"


@pytest.mark.asyncio
async def test_chain_dispatch_commits_accumulated_steps_once(tmp_path: Path) -> None:
    """Prove chain dispatch feeds one final commit containing every completed
    step, with live snapshots along the way."""

    calls: list[tuple[list[ChildResult], bool]] = []
    runner = FakeRunner()
    dispatcher = make_dispatcher(
        tmp_path,
        runner,
        usage_observer=lambda children, final: calls.append((list(children), final)),
    )

    await dispatcher.execute(
        {
            "chain": [
                {"agent": "general-purpose", "task": "chain-one"},
                {"agent": "read-only", "task": "chain-two"},
            ]
        },
        signal=None,
        on_update=None,
    )

    finals = [final for _children, final in calls]
    assert finals.count(True) == 1
    final_children, _ = calls[-1]
    assert [child.task for child in final_children] == ["chain-one", "chain-two"]
    assert any(final is False for _children, final in calls), "no live snapshot was fed"


@pytest.mark.asyncio
async def test_validation_failure_never_feeds_usage_observer(tmp_path: Path) -> None:
    """Prove a request rejected before dispatch produces no usage observations."""

    calls: list[tuple[list[ChildResult], bool]] = []
    runner = FakeRunner()
    dispatcher = make_dispatcher(
        tmp_path,
        runner,
        usage_observer=lambda children, final: calls.append((list(children), final)),
    )

    await dispatcher.execute({"agent": "general-purpose"}, signal=None, on_update=None)

    assert calls == []


@pytest.mark.asyncio
async def test_unknown_agent_commits_zero_usage_child(tmp_path: Path) -> None:
    """Prove an unknown-agent failure still commits once with a zero-usage
    child, which the tracker ignores rather than counting as a run."""

    calls: list[tuple[list[ChildResult], bool]] = []
    runner = FakeRunner()
    dispatcher = make_dispatcher(
        tmp_path,
        runner,
        usage_observer=lambda children, final: calls.append((list(children), final)),
    )

    await dispatcher.execute(
        {"agent": "no-such-agent", "task": "work"}, signal=None, on_update=None
    )

    finals = [final for _children, final in calls]
    assert finals.count(True) == 1
    final_children, _ = calls[-1]
    assert final_children[0].agent == "no-such-agent"
    assert final_children[0].usage.input == 0
    assert final_children[0].usage.cost == 0.0
```

Also update `make_dispatcher` in `tests/test_dispatch.py` to accept and forward the new option:

```python
def make_dispatcher(
    tmp_path: Path,
    runner: FakeRunner,
    *,
    ui: FakeUi | None = None,
    source: str = "bundled",
    parent_provider: str | None = None,
    parent_model: str | None = None,
    parent_reasoning_effort: str | None = None,
    config: SubagentConfig | None = None,
    usage_observer: Any = None,
) -> TaskDispatcher:
    discovery = make_discovery(tmp_path, source=source)
    return TaskDispatcher(
        default_cwd=tmp_path,
        ui=ui or FakeUi(),
        runner=runner,  # type: ignore[arg-type]
        discovery_fn=lambda _cwd, _scope: discovery,
        parent_provider=parent_provider,
        parent_model=parent_model,
        parent_reasoning_effort=parent_reasoning_effort,
        config=config,
        usage_observer=usage_observer,
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest tests/test_dispatch.py -q`
Expected: FAIL — the 5 new tests AND every pre-existing test that builds a dispatcher through `make_dispatcher` fail with `TypeError: TaskDispatcher.__init__() got an unexpected keyword argument 'usage_observer'` (Step 1 already wired `make_dispatcher` to pass the observer).

- [ ] **Step 3: Implement the observer**

Edit `superpowers_subagent/dispatch.py`:

1. Import `Sequence`:

```python
from collections.abc import Callable, Mapping, Sequence
```

2. Add the observer type alias next to the other module constants (above `class ConfirmationUi`):

```python
MAX_PARALLEL_TASKS = 8
MAX_CONCURRENCY = 4
DEFAULT_TIMEOUT_SECONDS = 3600.0

UsageObserver = Callable[[Sequence[ChildResult], bool], None]
```

3. Extend `TaskDispatcher.__init__` (keep all existing parameters, add one):

```python
    def __init__(
        self,
        *,
        default_cwd: Path,
        ui: ConfirmationUi,
        runner: TauChildRunner | None = None,
        discovery_fn: DiscoveryFn = discover_agents,
        parent_provider: str | None = None,
        parent_model: str | None = None,
        parent_reasoning_effort: str | None = None,
        config: SubagentConfig | None = None,
        usage_observer: UsageObserver | None = None,
    ) -> None:
        self.default_cwd = default_cwd
        self.ui = ui
        self.runner = runner or TauChildRunner()
        self.discovery_fn = discovery_fn
        self.parent_provider = parent_provider
        self.parent_model = parent_model
        self.parent_reasoning_effort = parent_reasoning_effort
        self.config = config
        self.usage_observer = usage_observer
```

4. Commit exactly once per call in `execute()` — replace this block:

```python
        if request.mode == "single":
            results = await self._run_single(request, discovery, agents, signal, on_update)
        elif request.mode == "parallel":
            results = await self._run_parallel(request, discovery, agents, signal, on_update)
        else:
            results = await self._run_chain(request, discovery, agents, signal, on_update)
```

with:

```python
        if request.mode == "single":
            results = await self._run_single(request, discovery, agents, signal, on_update)
        elif request.mode == "parallel":
            results = await self._run_parallel(request, discovery, agents, signal, on_update)
        else:
            results = await self._run_chain(request, discovery, agents, signal, on_update)
        if self.usage_observer is not None:
            self.usage_observer(results, True)
```

5. Feed live snapshots from `_emit_update` — change its signature and body:

```python
def _emit_update(
    callback: ToolUpdateCallback | None,
    content: str,
    request: ParsedRequest,
    discovery: DiscoveryResult,
    results: list[ChildResult],
    *,
    config: SubagentConfig | None = None,
    config_diagnostics: tuple[str, ...] | None = None,
    usage_observer: UsageObserver | None = None,
) -> None:
    """Feed a live usage snapshot, then deliver the update to the frontend."""
    if usage_observer is not None:
        usage_observer(results, False)
    if callback is None:
        return
    callback(
        _tool_result(
            content,
            mode=request.mode,
            scope=request.agent_scope,
            discovery=discovery,
            config=config,
            config_diagnostics=config_diagnostics,
            results=results,
            planned=len(request.items),
        )
    )
```

6. Pass the observer at all five `_emit_update` call sites — add `usage_observer=self.usage_observer,` as the last argument of each call. The five call sites become (in `_run_single`, `_run_parallel`, and `_run_chain` respectively):

```python
        def update(result: ChildResult) -> None:
            _emit_update(
                on_update,
                _single_content(result, running=True),
                request,
                discovery,
                [result],
                config=self.config,
                config_diagnostics=self._config_diagnostics,
                usage_observer=self.usage_observer,
            )

        result = await self._run_item(
            item=item,
            agents=agents,
            request=request,
            signal=signal,
            on_message=update,
        )
        _emit_update(
            on_update,
            _single_content(result),
            request,
            discovery,
            [result],
            config=self.config,
            config_diagnostics=self._config_diagnostics,
            usage_observer=self.usage_observer,
        )
        return [result]
```

```python
        def emit() -> None:
            results = current_results()
            complete = sum(_is_terminal_slot(result) for result in results)
            _emit_update(
                on_update,
                f"Parallel: {complete}/{len(slots)} done",
                request,
                discovery,
                results,
                config=self.config,
                config_diagnostics=self._config_diagnostics,
                usage_observer=self.usage_observer,
            )
```

```python
            def update(result: ChildResult, *, current_step: int = step) -> None:
                _emit_update(
                    on_update,
                    f"Chain: step {current_step}/{len(request.items)} running",
                    request,
                    discovery,
                    [*results, result],
                    config=self.config,
                    config_diagnostics=self._config_diagnostics,
                    usage_observer=self.usage_observer,
                )

            result = await self._run_item(
                item=item,
                agents=agents,
                request=request,
                signal=signal,
                step=step,
                on_message=update,
            )
            results.append(result)
            _emit_update(
                on_update,
                f"Chain: step {step}/{len(request.items)} complete",
                request,
                discovery,
                results,
                config=self.config,
                config_diagnostics=self._config_diagnostics,
                usage_observer=self.usage_observer,
            )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest tests/test_dispatch.py -q`
Expected: all pass, including the 5 new tests.

- [ ] **Step 5: Lint, format, and type-check**

Run: `.venv/bin/ruff check superpowers_subagent tests`
Expected: `All checks passed!`

Run: `.venv/bin/ruff format --check superpowers_subagent tests`
Expected: no files listed as needing formatting

Run: `.venv/bin/mypy --python-executable /opt/tau/bin/python superpowers_subagent`
Expected: `Success: no issues found in 10 source files`

- [ ] **Step 6: Commit**

```bash
git add superpowers_subagent/dispatch.py tests/test_dispatch.py
git commit -m "feat: dispatcher feeds session usage observer"
```

---

## Task 3: Guarded sidebar section

**Files:**
- Create: `extensions/superpowers-subagent/superpowers_subagent/sidebar.py`
- Create: `extensions/superpowers-subagent/tests/test_sidebar.py`

**Delta requirement:** ADDED "Sidebar subagent usage section" and "Unavailable sidebar display degrades safely"

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sidebar.py`:

```python
"""Sidebar seam tests for the accumulated subagent usage section.

These tests pin the "Sidebar subagent usage section" and "Unavailable sidebar
display degrades safely" delta requirements: placement directly below usage,
hide and omission rules, and guarded degradation of the display path.

The runtime-integration tests run the extension's real install path in this
same pytest process, so the core sidebar builder may already carry a wrapper
when these tests run; helpers here always resolve the pristine builder.
"""

from __future__ import annotations

import builtins
import io
from pathlib import Path
from typing import Any

import tau_coding.tui.widgets as widgets
from rich.console import Console
from rich.text import Text
from tau_coding.session_stats import SessionStats
from tau_coding.tui.config import TAU_DARK_THEME

from superpowers_subagent.models import ChildResult, UsageStats
from superpowers_subagent.sidebar import _inject_section, install
from superpowers_subagent.usage import SubagentUsageTotals, SubagentUsageTracker


class FakeSession:
    """Minimal SessionSummarySource stand-in for the sidebar content builder."""

    session_title = "Test session"
    session_stats = SessionStats(
        turn_count=3,
        tool_call_count=6,
        input_tokens=12000,
        cached_input_tokens=2000,
        cache_write_tokens=500,
        output_tokens=4000,
        latest_prompt_tokens=12000,
        latest_cached_input_tokens=2000,
        estimated_cost=0.12,
    )
    auto_compact_token_threshold = None
    context_files = ()
    tools = ()
    skills = ()
    prompt_templates = ()
    extension_names = ("superpowers-subagent",)
    cwd = Path("/workspace")
    provider_name = "openai"
    model = "gpt-5.6-sol"
    thinking_level = "high"
    context_window_tokens = 200_000
    has_provider_context_usage = False
    # All remaining attributes needed by the narrow-layout renderer come from
    # the SessionSummarySource protocol; the renderer reads cwd, provider_name,
    # model, thinking level, context usage, and auto-compaction threshold.


def _child(*, input: int, output: int, cost: float = 0.0) -> ChildResult:
    return ChildResult(
        agent="implementation",
        agent_source="bundled",
        task="work",
        cwd="/workspace",
        exit_code=0,
        usage=UsageStats(input=input, output=output, cost=cost),
    )


def _section_titles(content: Any) -> list[str]:
    """Section headers in render order; the leading title block has none."""
    titles: list[str] = []
    for section in content.summary_sections:
        if not hasattr(section, "renderables") or not section.renderables:
            continue
        header = section.renderables[0].renderable
        if isinstance(header, Text):
            titles.append(header.plain)
    return titles


def _section_body(content: Any, title: str) -> Text:
    """Body text of the sidebar section with the given title."""
    sections = [
        section for section in content.summary_sections if getattr(section, "renderables", None)
    ]
    titles = [section.renderables[0].renderable.plain for section in sections]
    body = sections[titles.index(title)].renderables[1].renderable
    assert isinstance(body, Text)
    return body


# NOTE: ``summary_sections`` begins with a Padding title block that
# ``_section_titles`` filters out, so body lookups must use the filtered
# ``sections``/``titles`` pair, never raw ``summary_sections`` indices.


def _base_content() -> Any:
    """A pristine sidebar summary built by the real core builder."""
    return _pristine_builder()(FakeSession(), theme=TAU_DARK_THEME)


def _pristine_builder() -> Any:
    """The true core builder, unwrapping a wrapper left by an earlier test."""
    original = widgets._build_sidebar_content
    if getattr(original, "_superpowers_subagent_wrapper", False):
        return original.__wrapped__
    return original


def test_injection_places_section_below_usage() -> None:
    """Prove the injected section sits directly below the usage section and
    shows the run count plus accumulated totals in the usage section's style."""
    tracker = SubagentUsageTracker()
    tracker.update([_child(input=16000, output=4000, cost=0.05)], final=True)

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    titles = _section_titles(content)
    assert titles.index("subagents") == titles.index("usage") + 1
    body = _section_body(content, "subagents")
    assert "1 run" in body.plain
    assert "16k in" in body.plain
    assert "4k out" in body.plain
    assert "$0.05" in body.plain


def test_injection_counts_in_flight_runs() -> None:
    """Prove totals include the running call's latest snapshot with its runs
    counted, per the in-flight display contract."""
    tracker = SubagentUsageTracker()
    tracker.update([_child(input=16000, output=4000)], final=True)
    tracker.update([_child(input=10000, output=2000)], final=False)

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    body = _section_body(content, "subagents")
    assert "2 runs" in body.plain
    assert "26k in" in body.plain
    assert "6k out" in body.plain


def test_injection_omits_cost_when_unreported() -> None:
    """Prove the section keeps runs and tokens but no cost value when no child
    reported a cost."""
    tracker = SubagentUsageTracker()
    tracker.update([_child(input=16000, output=4000)], final=True)

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    body = _section_body(content, "subagents")
    assert "1 run" in body.plain
    assert "$" not in body.plain


def test_empty_totals_leave_content_unchanged() -> None:
    """Prove no subagents section appears until a run reports usage."""
    base = _base_content()

    content = _inject_section(base, SubagentUsageTotals(), TAU_DARK_THEME, widgets)

    assert content is base
    assert "subagents" not in _section_titles(content)


def test_no_usage_section_prevents_injection() -> None:
    """Prove a summary without a usage section never gains a subagents section."""
    content = widgets._SidebarContent(
        summary_sections=(
            widgets._sidebar_section("activity", Text("x"), theme=TAU_DARK_THEME),
        ),
        skills=Text(""),
        prompts=Text(""),
        extensions=Text(""),
    )
    tracker = SubagentUsageTracker()
    tracker.update([_child(input=100, output=50)], final=True)

    assert _inject_section(content, tracker.totals, TAU_DARK_THEME, widgets) is content


def test_narrow_layout_omits_section() -> None:
    """Prove the narrow-layout session summary never shows the subagents
    section even with the seam installed: it is rendered by core's own
    renderer, which the seam does not touch."""
    tracker = SubagentUsageTracker()
    tracker.update([_child(input=100, output=50)], final=True)
    try:
        install(tracker)

        output = io.StringIO()
        Console(file=output, width=100).print(
            widgets.render_compact_session_info(FakeSession(), theme=TAU_DARK_THEME)
        )

        assert "subagents" not in output.getvalue()
    finally:
        widgets._build_sidebar_content = _pristine_builder()


def test_install_wraps_builder_and_injects() -> None:
    """Prove the installed wrapper injects the section into real sidebar
    builds, reading the tracker's current totals."""
    tracker = SubagentUsageTracker()
    tracker.update([_child(input=16000, output=4000, cost=0.05)], final=True)
    try:
        install(tracker)

        content = widgets._build_sidebar_content(FakeSession(), theme=TAU_DARK_THEME)

        body = _section_body(content, "subagents")
        assert "$0.05" in body.plain
    finally:
        widgets._build_sidebar_content = _pristine_builder()


def test_reinstall_replaces_previous_wrapper() -> None:
    """Prove reinstalling replaces the previous generation's wrapper instead of
    wrapping it again, so the builder never grows a wrapper chain."""
    try:
        install(SubagentUsageTracker())
        first = widgets._build_sidebar_content
        install(SubagentUsageTracker())
        second = widgets._build_sidebar_content

        assert second is not first
        assert second.__wrapped__ is _pristine_builder()
    finally:
        widgets._build_sidebar_content = _pristine_builder()


def test_missing_builder_skips_install() -> None:
    """Prove an unavailable seam leaves the module untouched and never raises."""
    pristine = _pristine_builder()
    try:
        widgets._build_sidebar_content = None  # type: ignore[attr-defined]

        install(SubagentUsageTracker())

        assert widgets._build_sidebar_content is None
    finally:
        widgets._build_sidebar_content = pristine


def test_install_import_failure_degrades_silently(monkeypatch: Any) -> None:
    """Prove a Tau version without the TUI widgets module never breaks install
    (the print-mode branch of degrade-safely)."""
    real_import = builtins.__import__

    def deny_tui(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "tau_coding.tui.widgets":
            raise ImportError("no TUI in this build")
        return real_import(name, *args, **kwargs)

    pristine = _pristine_builder()
    monkeypatch.setattr(builtins, "__import__", deny_tui)
    install(SubagentUsageTracker())
    widgets._build_sidebar_content = pristine


def test_display_failure_during_rebuild_returns_original(monkeypatch: Any) -> None:
    """Prove a failure while building the section degrades to the normal
    sidebar summary without raising. The failure is injected into the
    extension's own injection step (the only guarded part of the wrapper),
    never into the core builder."""
    import superpowers_subagent.sidebar as sidebar_module

    tracker = SubagentUsageTracker()
    tracker.update([_child(input=100, output=50)], final=True)
    try:
        install(tracker)

        def explode(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("boom")

        monkeypatch.setattr(sidebar_module, "_inject_section", explode)
        content = widgets._build_sidebar_content(FakeSession(), theme=TAU_DARK_THEME)
        assert "subagents" not in _section_titles(content)
    finally:
        widgets._build_sidebar_content = _pristine_builder()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest tests/test_sidebar.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'superpowers_subagent.sidebar'`

- [ ] **Step 3: Implement the sidebar seam**

Create `superpowers_subagent/sidebar.py`:

```python
"""Guarded sidebar integration showing accumulated subagent usage.

Tau 0.3 exposes no public extension point for sidebar content: the sidebar
summary is built by core from session stats. This module therefore wraps the
TUI's internal sidebar content builder (``tau_coding.tui.widgets``), the one
function through which every sidebar summary is constructed, and splices a
``subagents`` section below the ``usage`` section. Every seam step is guarded:
when an expected part is missing or a build fails, the original summary is
returned unchanged. Aggregation and dispatch never depend on this module.
"""

from __future__ import annotations

import dataclasses
import functools
from typing import Any

from .usage import SubagentUsageTotals, SubagentUsageTracker

_SECTION_TITLE = "subagents"
_USAGE_TITLE = "usage"
_WRAPPER_MARK = "_superpowers_subagent_wrapper"


def install(tracker: SubagentUsageTracker) -> None:
    """Wrap the TUI sidebar content builder to include the tracker's section.

    Reinstalling replaces a wrapper from a previous load generation instead of
    wrapping it again, so the builder never grows a wrapper chain. When the
    seam is missing, nothing is changed.
    """
    try:
        import tau_coding.tui.widgets as widgets
    except Exception:
        return
    original = getattr(widgets, "_build_sidebar_content", None)
    if not callable(original):
        return
    if getattr(original, _WRAPPER_MARK, False):
        original = getattr(original, "__wrapped__", original)
    widgets._build_sidebar_content = _make_wrapper(original, tracker, widgets)


def _make_wrapper(
    original: Any,
    tracker: SubagentUsageTracker,
    widgets: Any,
) -> Any:
    """Build the guarded wrapper bound to one tracker and widgets module."""
    default_theme = widgets.TAU_DARK_THEME

    @functools.wraps(original)
    def wrapped(session: object, *, theme: object = default_theme) -> Any:
        content = original(session, theme=theme)
        try:
            return _inject_section(content, tracker.totals, theme, widgets)
        except Exception:
            return content

    setattr(wrapped, _WRAPPER_MARK, True)
    return wrapped


def _inject_section(
    content: Any,
    totals: SubagentUsageTotals,
    theme: Any,
    widgets: Any,
) -> Any:
    """Return the sidebar content with the subagents section, or input unchanged."""
    if not totals.has_usage:
        return content
    sections = content.summary_sections
    index = _usage_section_index(sections)
    if index is None:
        return content
    section = widgets._sidebar_section(
        _SECTION_TITLE,
        _section_body(totals, theme, widgets),
        theme=theme,
    )
    return dataclasses.replace(
        content,
        summary_sections=(*sections[: index + 1], section, *sections[index + 1 :]),
    )


def _usage_section_index(sections: Any) -> int | None:
    """Index of the sidebar's usage section, found by its header text."""
    for index, section in enumerate(sections):
        try:
            header = section.renderables[0].renderable
        except Exception:
            continue
        if getattr(header, "plain", None) == _USAGE_TITLE:
            return index
    return None


def _section_body(totals: SubagentUsageTotals, theme: Any, widgets: Any) -> Any:
    """Build the section text in the usage section's own style."""
    label = "1 run" if totals.runs == 1 else f"{totals.runs} runs"
    body = widgets.Text(style=theme.completion_description)
    body.append(f"{label} · ")
    body.append(f"{widgets._compact_usage_count(totals.prompt_tokens)} in, ")
    body.append(f"{widgets._compact_usage_count(totals.output_tokens)} out")
    if totals.cost > 0:
        body.append(" · ")
        body.append(widgets._format_cost(totals.cost))
    return body
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest tests/test_sidebar.py -q`
Expected: 11 passed

- [ ] **Step 5: Lint, format, and type-check**

Run: `.venv/bin/ruff check superpowers_subagent tests`
Expected: `All checks passed!`

Run: `.venv/bin/ruff format --check superpowers_subagent tests`
Expected: no files listed as needing formatting

Run: `.venv/bin/mypy --python-executable /opt/tau/bin/python superpowers_subagent`
Expected: `Success: no issues found in 11 source files`

- [ ] **Step 6: Commit**

```bash
git add superpowers_subagent/sidebar.py tests/test_sidebar.py
git commit -m "feat: guarded sidebar section for subagent usage"
```

---

## Task 4: Extension wiring and lifecycle

**Files:**
- Modify: `extensions/superpowers-subagent/superpowers_subagent/extension.py`
- Modify: `extensions/superpowers-subagent/tests/test_extension.py`

**Delta requirement:** ADDED "Session-scoped subagent usage aggregation" (rebind reset, discard-without-commit) and "Unavailable sidebar display degrades safely" (install runs without a UI bridge)

- [ ] **Step 1: Write the failing tests**

Edit `tests/test_extension.py`:

1. Add two imports into the existing import block (the block currently starts with `from __future__ import annotations` and contains `import pytest`, `from tau_agent.tools import AgentToolResult`, `from superpowers_subagent.extension import setup`, and `from superpowers_subagent.runner import RECURSION_GUARD`; keep all of those). Insert exactly these two lines after `from __future__ import annotations`:

```python
import asyncio
import types
```

2. Give `FakeTau` an event registry so `setup` can register the rebind handler — add `self.handlers` and an `on` method:

```python
class FakeTau:
    def __init__(self, *, thinking_level: str | None = None) -> None:
        self.tools: list[Any] = []
        self.context = FakeContext()
        self._runtime = FakeRuntime(thinking_level)
        self.handlers: dict[str, Any] = {}

    def register_tool(self, tool: Any) -> None:
        self.tools.append(tool)

    def on(self, event: str, handler: Any = None) -> Any:
        if handler is None:
            def decorator(decorated: Any) -> Any:
                self.handlers[event] = decorated
                return decorated
            return decorator
        self.handlers[event] = handler
        return handler
```

3. In every existing test that calls `setup(tau)`, add a monkeypatch so setup never touches the real core widget module. For the two tests that do not import `extension_module` yet (`test_setup_registers_exactly_one_task`, `test_setup_refuses_recursive_registration`), their final bodies become:

```python
def test_setup_registers_exactly_one_task(monkeypatch: Any) -> None:
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    import superpowers_subagent.extension as extension_module

    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]

    assert [tool.name for tool in tau.tools] == ["task"]
    tool = tau.tools[0]
    assert tool.label == "task"
    assert tool.parameters["properties"]["tasks"]["maxItems"] == 8
    assert tool.execution_mode == "parallel"
    assert tool.render_call is not None
    assert tool.render_result is not None


def test_setup_refuses_recursive_registration(monkeypatch: Any) -> None:
    monkeypatch.setenv(RECURSION_GUARD, "1")
    import superpowers_subagent.extension as extension_module

    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]

    assert tau.tools == []
```

For the three `test_execute_task_*` tests (which already `import superpowers_subagent.extension as extension_module` at the top), add exactly one line after that import:

```python
    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
```

4. Append the three new tests:

```python
@pytest.mark.asyncio
async def test_execute_task_wires_tracker_as_usage_observer(monkeypatch: Any) -> None:
    """Prove the task tool feeds the session usage tracker from the dispatcher
    and registers a session_start handler for rebind resets."""

    import superpowers_subagent.extension as extension_module

    captured: dict[str, Any] = {}

    class FakeDispatcher:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def execute(
            self,
            arguments: Mapping[str, Any],
            signal: Any = None,
            on_update: Any = None,
        ) -> AgentToolResult:
            del arguments, signal, on_update
            return AgentToolResult(content=[])

    monkeypatch.setattr(extension_module, "TaskDispatcher", FakeDispatcher)
    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]
    # The dispatcher is constructed per call, so a call must run before the
    # captured kwargs exist.
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call", {"agent": "general-purpose", "task": "work"}, None, None
    )

    assert callable(captured["usage_observer"])
    assert "session_start" in tau.handlers


def test_reset_tracker_on_rebind_reasons() -> None:
    """Prove totals reset only for new, resumed, or branched sessions, not at
    startup or reload, so the accumulation stays scoped to the active session."""

    from superpowers_subagent.extension import _reset_tracker_on_rebind
    from superpowers_subagent.models import ChildResult, UsageStats
    from superpowers_subagent.usage import SubagentUsageTracker

    tracker = SubagentUsageTracker()
    tracker.update(
        [
            ChildResult(
                agent="a",
                agent_source="bundled",
                task="t",
                cwd="/w",
                exit_code=0,
                usage=UsageStats(input=10, output=5),
            )
        ],
        True,
    )

    _reset_tracker_on_rebind(tracker, types.SimpleNamespace(reason="startup"))
    assert tracker.totals.runs == 1
    _reset_tracker_on_rebind(tracker, types.SimpleNamespace(reason="reload"))
    assert tracker.totals.runs == 1
    _reset_tracker_on_rebind(tracker, types.SimpleNamespace(reason="resume"))
    assert tracker.totals.runs == 0


@pytest.mark.asyncio
async def test_execute_task_discards_pending_on_hard_cancellation(monkeypatch: Any) -> None:
    """Prove a hard cancellation of the dispatch propagates and drops the
    in-flight snapshot, so stale partial usage cannot stay displayed."""

    import superpowers_subagent.extension as extension_module
    from superpowers_subagent.models import ChildResult, UsageStats

    captured: dict[str, Any] = {}
    installed: dict[str, Any] = {}

    class FakeDispatcher:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def execute(
            self,
            arguments: Mapping[str, Any],
            signal: Any = None,
            on_update: Any = None,
        ) -> AgentToolResult:
            del arguments, signal, on_update
            raise asyncio.CancelledError()

    def fake_install(tracker: Any) -> None:
        installed["tracker"] = tracker

    monkeypatch.setattr(extension_module, "TaskDispatcher", FakeDispatcher)
    monkeypatch.setattr(extension_module, "install_sidebar_section", fake_install)
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    tau = FakeTau()
    setup(tau)  # type: ignore[arg-type]
    tracker = installed["tracker"]
    captured["usage_observer"](
        [
            ChildResult(
                agent="a",
                agent_source="bundled",
                task="t",
                cwd="/w",
                exit_code=0,
                usage=UsageStats(input=10, output=5),
            )
        ],
        False,
    )
    assert tracker.totals.runs == 1

    with pytest.raises(asyncio.CancelledError):
        await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
            "call", {"agent": "read-only", "task": "work"}, None, None
        )

    assert tracker.totals.runs == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest tests/test_extension.py -q`
Expected: the 3 new tests FAIL: `test_execute_task_wires_tracker_as_usage_observer` with `KeyError: 'usage_observer'` (the old setup never passes a usage observer and the dispatcher is only built per call), `test_reset_tracker_on_rebind_reasons` with `ImportError` (no `_reset_tracker_on_rebind` yet), and `test_execute_task_discards_pending_on_hard_cancellation` with `KeyError: 'tracker'` at `installed["tracker"]` (the old setup never calls `install_sidebar_section`, so the fake install is never invoked). The five modified pre-existing tests still pass (the `install_sidebar_section` attribute is created by the monkeypatch and the old setup never calls it).

- [ ] **Step 3: Implement the wiring**

Edit `superpowers_subagent/extension.py`:

1. Add imports:

```python
from .sidebar import install as install_sidebar_section
from .usage import SubagentUsageTracker
```

2. Add a module constant and the rebind helper above `setup` (`RECURSION_GUARD` already comes from `.runner`; do not redeclare it):

```python
#: Tau session lifecycle reasons that re-scope the session: totals reset on
#: rebinds, but not at startup or /reload (a fresh setup already starts empty).
_REBIND_REASONS: frozenset[str] = frozenset({"new", "resume", "branch"})


def _reset_tracker_on_rebind(tracker: SubagentUsageTracker, event: object) -> None:
    """Reset session-scoped totals when the session rebinds."""
    if getattr(event, "reason", None) in _REBIND_REASONS:
        tracker.reset()
```

Note: `tests/test_runtime_integration.py` loads the real extension in-process, so the real `install_sidebar_section` runs there too and leaves a wrapper on the core builder in the shared pytest process; the sidebar tests resolve the pristine builder explicitly (see `_pristine_builder` in Task 3), so no test ordering dependency exists.

3. Rewire `setup` — after the recursion guard, create the tracker, install the sidebar, register the rebind handler, and pass the tracker to the dispatcher:

```python
def setup(tau: ExtensionAPI) -> None:
    """Register the task tool unless this process is a child."""

    if os.environ.get(RECURSION_GUARD):
        return

    tracker = SubagentUsageTracker()
    install_sidebar_section(tracker)
    runner = TauChildRunner()

    def on_session_start(event: object, _context: object) -> None:
        _reset_tracker_on_rebind(tracker, event)

    # Explicit handler form: ``ExtensionAPI.on``'s return type is a union that
    # includes the two-argument handler itself, so mypy strict rejects the
    # decorator form; passing the handler directly type-checks cleanly.
    tau.on("session_start", on_session_start)

    async def execute_task(
        tool_call_id: str,
        arguments: Mapping[str, JSONValue],
        signal: ToolCancellationToken | None = None,
        on_update: ToolUpdateCallback | None = None,
    ) -> AgentToolResult:
        del tool_call_id

        def observe(children: Sequence[ChildResult], final: bool) -> None:
            tracker.update(tool_call_id, children, final)

        dispatcher = TaskDispatcher(
            default_cwd=tau.context.cwd,
            ui=tau.context.ui,
            runner=runner,
            parent_provider=tau.context.provider_name or None,
            parent_model=tau.context.model or None,
            parent_reasoning_effort=_parent_thinking_level(tau),
            config=load_subagent_config(tau.context.cwd),
            usage_observer=observe,
        )
        try:
            return await dispatcher.execute(arguments, signal=signal, on_update=on_update)
        finally:
            tracker.discard_pending(tool_call_id)

    tau.register_tool(...)
```

The `tau.register_tool(AgentTool(...))` call itself is unchanged.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest tests/test_extension.py -q`
Expected: all pass, including the 3 new tests.

- [ ] **Step 5: Lint, format, and type-check**

Run: `.venv/bin/ruff check superpowers_subagent tests`
Expected: `All checks passed!`

Run: `.venv/bin/ruff format --check superpowers_subagent tests`
Expected: no files listed as needing formatting

Run: `.venv/bin/mypy --python-executable /opt/tau/bin/python superpowers_subagent`
Expected: `Success: no issues found in 11 source files`

- [ ] **Step 6: Commit**

```bash
git add superpowers_subagent/extension.py tests/test_extension.py
git commit -m "feat: wire usage tracker into task dispatch and session lifecycle"
```

---

## Task 5: Whole-suite verification

**Files:** none

**Delta requirement:** all three ADDED requirements (regression gate)

- [ ] **Step 1: Run the full test suite**

Run (from `extensions/superpowers-subagent/`): `PYTHONPATH=/opt/tau/lib/python3.14/site-packages .venv/bin/python -m pytest -q`
Expected: 163 passed (131 baseline + 12 usage + 5 dispatch + 11 sidebar + 3 extension + 1 ordering pin), zero failures.

- [ ] **Step 2: Ruff and mypy**

Run: `.venv/bin/ruff check superpowers_subagent tests && .venv/bin/ruff format --check superpowers_subagent tests && .venv/bin/mypy --python-executable /opt/tau/bin/python superpowers_subagent`
Expected: all three succeed.

- [ ] **Step 3: Confirm the git state**

Run: `git status --short`
Expected: no uncommitted changes in `extensions/superpowers-subagent/` (`docs/` untouched by this feature; the living-spec sync is part of finishing).

- [ ] **Step 4: Commit any remaining drift**

If Steps 1-3 produced changes, commit them (from `extensions/superpowers-subagent/`):

```bash
git add superpowers_subagent tests
cd /workspace
git commit -m "chore: verification fixes for subagent usage sidebar"
```
