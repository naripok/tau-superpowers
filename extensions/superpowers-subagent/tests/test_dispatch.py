from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from tau_agent.messages import AssistantMessage, TextContent

from superpowers_subagent.dispatch import TaskDispatcher, ValidationFailure, validate_arguments
from superpowers_subagent.models import (
    AgentConfig,
    ChildResult,
    DiscoveryResult,
)
from superpowers_subagent.utils import parse_status, resolve_child_cwd


class FakeUi:
    def __init__(self, *, has_ui: bool = False, answer: bool = False) -> None:
        self.has_ui = has_ui
        self.answer = answer
        self.confirmations: list[tuple[str, str]] = []

    async def confirm(self, title: str, message: str, *, timeout: float | None = None) -> bool:
        del timeout
        self.confirmations.append((title, message))
        return self.answer


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.active = 0
        self.max_active = 0

    async def run(self, **kwargs: Any) -> ChildResult:
        self.calls.append(kwargs)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        task = kwargs["task"]
        if task == "timeout":
            await asyncio.sleep(0.005)
        else:
            await asyncio.sleep(0.02)
        agent = kwargs["agent"]
        result = ChildResult(
            agent=agent.name,
            agent_source=agent.source,
            task=task,
            cwd=str(resolve_child_cwd(kwargs["default_cwd"], kwargs["cwd_override"])),
            exit_code=0,
            provider=kwargs["provider_override"] or agent.provider,
            model=kwargs["model_override"] or agent.model,
            step=kwargs["step"],
        )
        if task == "fail":
            result.exit_code = 1
            result.error_message = "planned failure"
        elif task == "timeout":
            result.exit_code = -15
            result.timed_out = True
            result.stop_reason = "error"
            result.error_message = "planned timeout"
        else:
            status = "BLOCKED" if task == "semantic-blocked" else "DONE"
            text = f"full output for {task}\n## Summary\nsummary for {task}\n**Status: {status}**"
            result.messages.append(
                AssistantMessage(content=[TextContent(text=text)], stop_reason="stop")
            )
            result.stop_reason = "stop"
            result.status = parse_status(text, failed=False)
            if kwargs["on_message"] is not None:
                kwargs["on_message"](result)
        self.active -= 1
        return result


def make_discovery(tmp_path: Path, *, source: str = "bundled") -> DiscoveryResult:
    agents = tuple(
        AgentConfig(
            name=name,
            description=name,
            system_prompt="",
            source=source,  # type: ignore[arg-type]
            file_path=tmp_path / f"{name}.md",
            provider="agent-provider" if name == "general-purpose" else None,
            model="agent-model" if name == "general-purpose" else None,
        )
        for name in ("general-purpose", "read-only")
    )
    project_dir = tmp_path / ".tau" / "agents" if source == "project" else None
    return DiscoveryResult(
        agents=agents,
        project_agents_dir=project_dir,
        diagnostics=("one diagnostic",),
    )


def make_dispatcher(
    tmp_path: Path,
    runner: FakeRunner,
    *,
    ui: FakeUi | None = None,
    source: str = "bundled",
) -> TaskDispatcher:
    discovery = make_discovery(tmp_path, source=source)
    return TaskDispatcher(
        default_cwd=tmp_path,
        ui=ui or FakeUi(),
        runner=runner,  # type: ignore[arg-type]
        discovery_fn=lambda _cwd, _scope: discovery,
    )


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"agent": "general-purpose"},
        {"agent": " ", "task": "work"},
        {"tasks": []},
        {"chain": []},
        {
            "agent": "general-purpose",
            "task": "work",
            "tasks": [{"agent": "read-only", "task": "review"}],
        },
        {"tasks": [{"agent": "a", "task": "x"}] * 9},
        {"tasks": [{"agent": "", "task": "x"}]},
        {"chain": [{"agent": "a", "task": ""}]},
        {"agent": "a", "task": "x", "agentScope": "invalid"},
        {"agent": "a", "task": "x", "confirmProjectAgents": 1},
        {"agent": "a", "task": "x", "provider": ""},
        {"agent": "a", "task": "x", "timeoutSeconds": 0},
        {"agent": "a", "task": "x", "timeoutSeconds": 3601},
        {"agent": "a", "task": "x", "extra": True},
    ],
)
def test_validation_rejects_invalid_modes_and_common_options(arguments: dict[str, Any]) -> None:
    with pytest.raises(ValidationFailure):
        validate_arguments(arguments)


def test_validation_accepts_single_and_independent_overrides() -> None:
    request = validate_arguments(
        {
            "agent": " worker ",
            "task": "complete prompt",
            "cwd": "src",
            "provider": "provider",
            "model": "org/model",
            "timeoutSeconds": 2.5,
        }
    )
    assert request.mode == "single"
    assert request.items[0].agent == "worker"
    assert request.items[0].cwd == "src"
    assert request.provider == "provider"
    assert request.model == "org/model"
    assert request.timeout_seconds == 2.5


@pytest.mark.asyncio
async def test_invalid_call_returns_normal_tool_result_with_schema_details(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute({})

    assert "Invalid parameters" in result.text
    assert "general-purpose (bundled)" in result.text
    assert result.details["schemaVersion"] == 1
    assert result.details["results"] == []
    assert runner.calls == []


@pytest.mark.asyncio
async def test_single_returns_summary_content_and_complete_wire_messages(tmp_path: Path) -> None:
    runner = FakeRunner()
    updates = []
    result = await make_dispatcher(tmp_path, runner).execute(
        {
            "agent": "general-purpose",
            "task": "implement",
            "model": "call/model",
        },
        on_update=updates.append,
    )

    assert result.text == "## Summary\nsummary for implement\n**Status: DONE**"
    details = result.details
    assert details["schemaVersion"] == 1
    assert details["discoveryDiagnostics"] == ["one diagnostic"]
    assert details["results"][0]["messages"][0]["role"] == "assistant"
    assert details["results"][0]["provider"] == "agent-provider"
    assert details["results"][0]["model"] == "call/model"
    assert len(updates) == 2


@pytest.mark.asyncio
async def test_parallel_limits_concurrency_and_preserves_input_order(tmp_path: Path) -> None:
    runner = FakeRunner()
    tasks = [{"agent": "general-purpose", "task": f"task-{index}"} for index in range(8)]

    result = await make_dispatcher(tmp_path, runner).execute({"tasks": tasks})

    assert runner.max_active == 4
    assert [item["task"] for item in result.details["results"]] == [
        f"task-{index}" for index in range(8)
    ]
    assert result.text.startswith("Parallel: 8/8 succeeded")
    assert result.text.index("summary for task-0") < result.text.index("summary for task-7")


@pytest.mark.asyncio
async def test_parallel_timeout_stops_queued_work_and_retains_ordered_slots(tmp_path: Path) -> None:
    runner = FakeRunner()
    tasks = [
        {"agent": "general-purpose", "task": task}
        for task in ("timeout", "one", "two", "three", "queued")
    ]

    result = await make_dispatcher(tmp_path, runner).execute({"tasks": tasks})

    assert len(runner.calls) == 4
    assert [item["task"] for item in result.details["results"]] == [
        "timeout",
        "one",
        "two",
        "three",
        "queued",
    ]
    assert "not started" in result.details["results"][-1]["errorMessage"].lower()


@pytest.mark.asyncio
async def test_chain_substitutes_complete_previous_output_and_continues_semantic_status(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute(
        {
            "chain": [
                {"agent": "general-purpose", "task": "semantic-blocked"},
                {"agent": "read-only", "task": "Review this:\n{previous}\nAgain {previous}"},
            ]
        }
    )

    assert len(runner.calls) == 2
    previous = (
        "full output for semantic-blocked\n## Summary\nsummary for semantic-blocked\n"
        "**Status: BLOCKED**"
    )
    assert runner.calls[1]["task"] == f"Review this:\n{previous}\nAgain {previous}"
    assert [item["step"] for item in result.details["results"]] == [1, 2]
    assert result.text.startswith("## Summary")


@pytest.mark.asyncio
async def test_chain_stops_on_process_failure(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute(
        {
            "chain": [
                {"agent": "general-purpose", "task": "fail"},
                {"agent": "read-only", "task": "never"},
            ]
        }
    )

    assert len(runner.calls) == 1
    assert result.text == "Chain stopped at step 1 (general-purpose): planned failure"
    assert len(result.details["results"]) == 1


@pytest.mark.asyncio
async def test_project_agents_fail_closed_headless_and_allow_explicit_bypass(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()
    headless = make_dispatcher(tmp_path, runner, source="project")

    rejected = await headless.execute(
        {"agent": "general-purpose", "task": "work", "agentScope": "project"}
    )
    assert "approval required in headless mode" in rejected.text
    assert runner.calls == []

    approved = await headless.execute(
        {
            "agent": "general-purpose",
            "task": "work",
            "agentScope": "project",
            "confirmProjectAgents": False,
        }
    )
    assert approved.text.startswith("## Summary")
    assert len(runner.calls) == 1


@pytest.mark.asyncio
async def test_project_agents_use_ui_confirmation(tmp_path: Path) -> None:
    denied_runner = FakeRunner()
    denied_ui = FakeUi(has_ui=True, answer=False)
    denied = await make_dispatcher(tmp_path, denied_runner, ui=denied_ui, source="project").execute(
        {"agent": "general-purpose", "task": "work", "agentScope": "project"}
    )
    assert denied.text.startswith("Canceled")
    assert denied_runner.calls == []
    assert "general-purpose" in denied_ui.confirmations[0][1]

    allowed_runner = FakeRunner()
    allowed_ui = FakeUi(has_ui=True, answer=True)
    allowed = await make_dispatcher(
        tmp_path, allowed_runner, ui=allowed_ui, source="project"
    ).execute({"agent": "general-purpose", "task": "work", "agentScope": "project"})
    assert allowed.text.startswith("## Summary")
    assert len(allowed_runner.calls) == 1


@pytest.mark.asyncio
async def test_unknown_agent_is_a_structured_failure(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute({"agent": "missing", "task": "work"})

    assert "Unknown agent" in result.text
    child = result.details["results"][0]
    assert child["agentSource"] == "unknown"
    assert child["status"] == "BLOCKED"
    assert runner.calls == []
