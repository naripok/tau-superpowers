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


class FakeTau:
    def __init__(self) -> None:
        self.tools: list[Any] = []
        self.context = FakeContext()

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
async def test_execute_task_passes_parent_session_provider_and_model(
    monkeypatch: Any,
) -> None:
    """The task tool binds the parent session's active provider/model to dispatch."""

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
    assert captured["default_cwd"] == Path.cwd()
