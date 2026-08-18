from __future__ import annotations

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

    def register_tool(self, tool: Any) -> None:
        self.tools.append(tool)


def test_setup_registers_exactly_one_task(monkeypatch: Any) -> None:
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
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
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]

    assert tau.tools == []


@pytest.mark.asyncio
async def test_execute_task_loads_config_per_call(monkeypatch: Any) -> None:
    """Prove each task call rescans the config file so edits apply without a
    Tau reload, mirroring how discovery rescans agent definitions."""

    import superpowers_subagent.extension as extension_module

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
            "call", {"agent": "read-only", "task": "work"}, None, None
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
        "call-1", {"agent": "general-purpose", "task": "work"}, None, None
    )

    assert captured["parent_provider"] == "openai"
    assert captured["parent_model"] == "gpt-5.6-sol"
    assert captured["parent_reasoning_effort"] is None
    assert captured["default_cwd"] == Path.cwd()

    tau.context.provider_name = ""
    tau.context.model = ""
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-2", {"agent": "general-purpose", "task": "work"}, None, None
    )

    assert captured["parent_provider"] is None
    assert captured["parent_model"] is None


@pytest.mark.asyncio
async def test_execute_task_reads_parent_session_thinking_level(monkeypatch: Any) -> None:
    """Prove the task tool forwards the parent session's active thinking level
    through the extension runtime view so unpinned children inherit it."""

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
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    tau = FakeTau(thinking_level="medium")

    setup(tau)  # type: ignore[arg-type]
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-1", {"agent": "read-only", "task": "work"}, None, None
    )

    assert captured["parent_reasoning_effort"] == "medium"

    # A Tau version without the runtime seam yields None instead of crashing.
    del tau._runtime
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-2", {"agent": "read-only", "task": "work"}, None, None
    )
    assert captured["parent_reasoning_effort"] is None
