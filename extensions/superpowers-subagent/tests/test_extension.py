from __future__ import annotations

import asyncio
import types
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from tau_agent.tools import AgentToolResult

from superpowers_subagent.extension import setup
from superpowers_subagent.runner import RECURSION_GUARD


class FakeContext:
    def __init__(self) -> None:
        self.cwd = Path.cwd()
        self.ui = object()  # type: ignore[assignment]
        self.provider_name = "openai"
        self.model = "gpt-5.6-sol"


class FakeSessionView:
    def __init__(self, thinking_level: str | None = None) -> None:
        self.thinking_level = thinking_level


class FakeRuntime:
    def __init__(self, thinking_level: str | None = None) -> None:
        self.session_view = FakeSessionView(thinking_level)


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


def test_setup_registers_exactly_one_task(monkeypatch: Any) -> None:
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    import superpowers_subagent.extension as extension_module

    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]

    assert [tool.name for tool in tau.tools] == ["task"]
    tool = tau.tools[0]
    assert tool.label == "task"
    assert tool.parameters["required"] == ["tasks"]
    properties = tool.parameters["properties"]
    assert properties["tasks"]["minItems"] == 1
    assert properties["tasks"]["maxItems"] == 8
    # The removed mode fields no longer exist anywhere in the schema.
    for removed in ("agent", "task", "cwd", "chain"):
        assert removed not in properties
    assert tool.execution_mode == "parallel"
    assert tool.render_call is not None
    assert tool.render_result is not None


def test_task_tool_prompt_states_threshold_and_homogeneous_tasks(monkeypatch: Any) -> None:
    """Pin the always-visible tool prompt: dispatch exists only for substantive
    isolated-context or long-running work, never for trivial tool calls the
    parent can perform itself and never as duplicate work, and every call takes
    a homogeneous `tasks` array. Agents see only this prompt at call time, so
    the threshold must live here rather than in the runtime validation."""

    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    import superpowers_subagent.extension as extension_module

    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]

    tool = tau.tools[0]
    # Threshold: substantive work with an isolated context window, or
    # long-running work that must not block the session.
    assert "isolated context" in tool.description
    assert "long-running" in tool.description
    # Prohibitions: no trivial tool-call dispatches, no duplicated work.
    assert "simple reads, searches, commands, and small edits" in tool.description.lower()
    assert "never dispatch work" in tool.description
    # Homogeneous contract: every call takes a tasks array.
    assert "tasks" in tool.description
    assert "one item runs a single child" in tool.description
    assert "two or more run in parallel" in tool.description
    assert tool.prompt_snippet == "Dispatch substantive work to an isolated Tau subagent."
    guidelines = tool.prompt_guidelines
    assert any(
        "isolated context window" in guideline and "long-running" in guideline
        for guideline in guidelines
    )
    assert any("replaces your own tool calls" in guideline for guideline in guidelines)
    assert any("Always pass the `tasks` array" in guideline for guideline in guidelines)
    # The always-visible prompt must carry its own context: agent names are
    # quoted, and the BLOCKED/NEEDS_CONTEXT statuses are defined, not jargon.
    assert any(
        "`implementation`" in guideline and "`code-review`" in guideline for guideline in guidelines
    )
    assert any(
        "BLOCKED means" in guideline and "NEEDS_CONTEXT means" in guideline
        for guideline in guidelines
    )
    blob = tool.description + " " + " ".join(guidelines)
    assert "chain" not in blob
    assert "single mode" not in blob
    assert "mutually exclusive" not in blob


def test_setup_refuses_recursive_registration(monkeypatch: Any) -> None:
    monkeypatch.setenv(RECURSION_GUARD, "1")
    import superpowers_subagent.extension as extension_module

    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]

    assert tau.tools == []


@pytest.mark.asyncio
async def test_execute_task_loads_config_per_call(monkeypatch: Any) -> None:
    """Prove each task call rescans the config file so edits apply without a
    Tau reload, mirroring how discovery rescans agent definitions."""

    import superpowers_subagent.extension as extension_module

    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    captured: dict[str, Any] = {}
    loads = []

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

    class FakeConfig:
        pass

    def fake_load(cwd: Path) -> FakeConfig:
        loads.append(cwd)
        return FakeConfig()

    monkeypatch.setattr(extension_module, "TaskDispatcher", FakeDispatcher)
    monkeypatch.setattr(extension_module, "load_subagent_config", fake_load)
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]
    for _ in range(2):
        await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
            "call", {"tasks": [{"agent": "read-only", "task": "work"}]}, None, None
        )

    assert loads == [Path.cwd(), Path.cwd()]
    assert isinstance(captured["config"], FakeConfig)


@pytest.mark.asyncio
async def test_execute_task_passes_parent_session_provider_and_model(
    monkeypatch: Any,
) -> None:
    """Prove the task tool binds the parent session's active provider and model to
    dispatch, so unpinned children inherit them unless the call or agent pins them."""

    import superpowers_subagent.extension as extension_module

    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
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
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-1", {"tasks": [{"agent": "general-purpose", "task": "work"}]}, None, None
    )

    assert captured["parent_provider"] == "openai"
    assert captured["parent_model"] == "gpt-5.6-sol"
    assert captured["parent_reasoning_effort"] is None
    assert captured["default_cwd"] == Path.cwd()

    tau.context.provider_name = ""
    tau.context.model = ""
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-2", {"tasks": [{"agent": "general-purpose", "task": "work"}]}, None, None
    )

    assert captured["parent_provider"] is None
    assert captured["parent_model"] is None


@pytest.mark.asyncio
async def test_execute_task_reads_parent_session_thinking_level(monkeypatch: Any) -> None:
    """Prove the task tool forwards the parent session's active thinking level
    through the extension runtime view so unpinned children inherit it."""

    import superpowers_subagent.extension as extension_module

    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
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
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    tau = FakeTau(thinking_level="medium")

    setup(tau)  # type: ignore[arg-type]
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-1", {"tasks": [{"agent": "read-only", "task": "work"}]}, None, None
    )

    assert captured["parent_reasoning_effort"] == "medium"

    # A Tau version without the runtime seam yields None instead of crashing.
    del tau._runtime
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-2", {"tasks": [{"agent": "read-only", "task": "work"}]}, None, None
    )
    assert captured["parent_reasoning_effort"] is None


@pytest.mark.asyncio
async def test_execute_task_wires_tracker_as_usage_observer(monkeypatch: Any) -> None:
    """Prove the dispatcher's usage observer feeds the sidebar tracker and the
    registered session_start handler resets it on rebinds but not otherwise."""

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
            return AgentToolResult(content=[])

    def fake_install(tracker: Any) -> None:
        installed["tracker"] = tracker

    monkeypatch.setattr(extension_module, "TaskDispatcher", FakeDispatcher)
    monkeypatch.setattr(extension_module, "install_sidebar_section", fake_install)
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]
    tracker = installed["tracker"]
    # The dispatcher is constructed per call, so a call must run before the
    # captured kwargs exist.
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call", {"tasks": [{"agent": "general-purpose", "task": "work"}]}, None, None
    )

    assert callable(captured["usage_observer"])
    assert "session_start" in tau.handlers

    tracked = ChildResult(
        agent="a",
        agent_source="bundled",
        task="t",
        cwd="/w",
        exit_code=0,
        usage=UsageStats(input=10, output=5),
    )
    captured["usage_observer"]([tracked], True)
    assert tracker.totals.runs == 1

    handler = tau.handlers["session_start"]
    handler(types.SimpleNamespace(reason="startup"), None)
    assert tracker.totals.runs == 1
    handler(types.SimpleNamespace(reason="reload"), None)
    assert tracker.totals.runs == 1
    handler(types.SimpleNamespace(), None)
    assert tracker.totals.runs == 1
    for reason in ("new", "resume", "branch"):
        handler(types.SimpleNamespace(reason=reason), None)
        assert tracker.totals.runs == 0
        captured["usage_observer"]([tracked], True)
        assert tracker.totals.runs == 1


def test_reset_tracker_on_rebind_reasons() -> None:
    """Prove totals reset only for new, resumed, or branched sessions, not at
    startup or reload, so the accumulation stays scoped to the active session."""

    from superpowers_subagent.extension import _reset_tracker_on_rebind
    from superpowers_subagent.models import ChildResult, UsageStats
    from superpowers_subagent.usage import SubagentUsageTracker

    tracker = SubagentUsageTracker()
    tracker.update(
        "call-1",
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
    calls = 0

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
            nonlocal calls
            calls += 1
            if calls > 1:
                raise asyncio.CancelledError()
            return AgentToolResult(content=[])

    def fake_install(tracker: Any) -> None:
        installed["tracker"] = tracker

    monkeypatch.setattr(extension_module, "TaskDispatcher", FakeDispatcher)
    monkeypatch.setattr(extension_module, "install_sidebar_section", fake_install)
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    tau = FakeTau()
    setup(tau)  # type: ignore[arg-type]
    tracker = installed["tracker"]
    # The dispatcher is built per call, so one benign call under the same tool
    # call id binds and captures the observer that later feeds the pending
    # snapshot; its hard-cancelled twin must be the same call so the finally
    # drops exactly that call's snapshot.
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call", {"tasks": [{"agent": "read-only", "task": "work"}]}, None, None
    )
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
            "call", {"tasks": [{"agent": "read-only", "task": "work"}]}, None, None
        )

    assert tracker.totals.runs == 0
