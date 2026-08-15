from __future__ import annotations

from typing import Any

from superpowers_subagent.extension import setup
from superpowers_subagent.runner import RECURSION_GUARD


class FakeTau:
    def __init__(self) -> None:
        self.tools: list[Any] = []

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
