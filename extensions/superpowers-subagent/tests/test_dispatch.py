from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from tau_agent.messages import AssistantMessage, TextContent

from superpowers_subagent.config import AgentOverrides, SubagentConfig
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
        # Effective values mirror utils.effective_provider_model and
        # utils.effective_reasoning_effort (call, config-agent, agent,
        # config-defaults, then parent-session precedence); keep both in sync.
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        task = kwargs["task"]
        if task == "timeout":
            await asyncio.sleep(0.005)
        else:
            await asyncio.sleep(0.02)
        agent = kwargs["agent"]
        config_overrides = kwargs.get("config_overrides")
        config_defaults = kwargs.get("config_defaults")
        provider = _first_specified(
            kwargs.get("provider_override"),
            _override_provider(config_overrides),
            agent.provider,
            _override_provider(config_defaults),
            kwargs.get("parent_provider"),
        )
        model = _first_specified(
            kwargs.get("model_override"),
            _override_model(config_overrides),
            agent.model,
            _override_model(config_defaults),
            kwargs.get("parent_model"),
        )
        reasoning_effort = _first_specified(
            kwargs.get("reasoning_effort_override"),
            _override_reasoning(config_overrides),
            agent.reasoning_effort,
            _override_reasoning(config_defaults),
            kwargs.get("parent_reasoning_effort"),
        )
        result = ChildResult(
            agent=agent.name,
            agent_source=agent.source,
            task=task,
            cwd=str(resolve_child_cwd(kwargs["default_cwd"], kwargs["cwd_override"])),
            exit_code=0,
            provider=provider,
            model=model,
            reasoning_effort=reasoning_effort,
        )
        if task == "fail":
            result.exit_code = 1
            result.error_message = "planned failure"
        elif task == "timeout":
            result.exit_code = -15
            result.timed_out = True
            result.stop_reason = "error"
            result.error_message = "planned timeout"
        elif task == "review":
            text = (
                "analysis\n"
                "## Code Review\n"
                "**Verdict:** Approved with fixes\n- point\n"
                "## Summary\n"
                "summary for review\n**Status: DONE**"
            )
            result.messages.append(
                AssistantMessage(content=[TextContent(text=text)], stop_reason="stop")
            )
            result.stop_reason = "stop"
            result.status = parse_status(text, failed=False)
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


def _first_specified(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def _override_provider(overrides: Any) -> Any:
    return overrides.provider if overrides is not None else None


def _override_model(overrides: Any) -> Any:
    return overrides.model if overrides is not None else None


def _override_reasoning(overrides: Any) -> Any:
    return overrides.reasoning_effort if overrides is not None else None


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
        for name in ("general-purpose", "read-only", "implementation", "code-review")
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


class UsageCalls:
    """Record every observer feed in call order so tests can assert final-commit
    counts and the children carried by the last commit."""

    def __init__(self) -> None:
        self.calls: list[tuple[list[ChildResult], bool]] = []

    def record(self, children: Sequence[ChildResult], final: bool) -> None:
        self.calls.append((list(children), final))

    @property
    def final_count(self) -> int:
        return sum(final for _children, final in self.calls)

    @property
    def last_children(self) -> list[ChildResult]:
        return self.calls[-1][0]


def test_validation_requires_a_non_empty_tasks_array() -> None:
    with pytest.raises(ValidationFailure) as absent:
        validate_arguments({})
    assert "tasks array" in str(absent.value)

    with pytest.raises(ValidationFailure) as empty:
        validate_arguments({"tasks": []})
    assert "tasks array" in str(empty.value)


def test_validation_rejects_non_list_tasks_as_array_error() -> None:
    for arguments in ({"tasks": "not-a-list"}, {"tasks": {"agent": "a", "task": "x"}}):
        with pytest.raises(ValidationFailure) as excinfo:
            validate_arguments(arguments)
        assert str(excinfo.value) == "tasks must be an array"


def test_validation_rejects_removed_mode_fields_as_unknown() -> None:
    for arguments in (
        {"agent": "general-purpose"},
        {"task": "work"},
        {"cwd": "src"},
        {"chain": [{"agent": "a", "task": "x"}]},
        {
            "agent": "general-purpose",
            "task": "work",
            "tasks": [{"agent": "a", "task": "x"}],
        },
        {"tasks": [{"agent": "a", "task": "x"}], "chain": [{"agent": "a", "task": "y"}]},
    ):
        with pytest.raises(ValidationFailure) as excinfo:
            validate_arguments(arguments)
        assert "unknown field(s)" in str(excinfo.value)

    with pytest.raises(ValidationFailure) as both:
        validate_arguments(
            {
                "agent": "a",
                "task": "x",
                "tasks": [{"agent": "a", "task": "x"}],
            }
        )
    assert "unknown field(s): agent, task" in str(both.value)


def test_validation_rejects_more_than_eight_tasks() -> None:
    with pytest.raises(ValidationFailure) as excinfo:
        validate_arguments({"tasks": [{"agent": "a", "task": "x"}] * 9})
    assert "at most 8" in str(excinfo.value)


@pytest.mark.parametrize(
    "arguments",
    [
        {"tasks": [{"agent": "", "task": "x"}]},
        {"tasks": [{"agent": "a", "task": ""}]},
        {"tasks": [{"agent": "a", "task": "x", "cwd": 5}]},
        {"tasks": [{"agent": "a", "task": "x", "extra": True}]},
        {"tasks": [{"agent": "a", "task": "x"}], "agentScope": "invalid"},
        {"tasks": [{"agent": "a", "task": "x"}], "confirmProjectAgents": 1},
        {"tasks": [{"agent": "a", "task": "x"}], "provider": ""},
        {"tasks": [{"agent": "a", "task": "x"}], "model": ""},
        {"tasks": [{"agent": "a", "task": "x"}], "reasoningEffort": "max"},
        {"tasks": [{"agent": "a", "task": "x"}], "reasoningEffort": ""},
        {"tasks": [{"agent": "a", "task": "x"}], "reasoningEffort": 5},
        {"tasks": [{"agent": "a", "task": "x"}], "timeoutSeconds": 0},
        {"tasks": [{"agent": "a", "task": "x"}], "timeoutSeconds": 3601},
        {"tasks": [{"agent": "a", "task": "x"}], "extra": True},
    ],
)
def test_validation_rejects_invalid_items_and_common_options(arguments: dict[str, Any]) -> None:
    with pytest.raises(ValidationFailure):
        validate_arguments(arguments)


def test_validation_accepts_items_and_independent_overrides() -> None:
    request = validate_arguments(
        {
            "description": "  brief  ",
            "tasks": [
                {"agent": " worker ", "task": "complete prompt", "cwd": "src"},
                {"agent": "read-only", "task": "second prompt"},
            ],
            "provider": " provider  name ",
            "model": " org/ model-id ",
            "reasoningEffort": " XHIGH ",
            "timeoutSeconds": 2.5,
        }
    )
    assert len(request.items) == 2
    assert request.items[0].agent == "worker"
    assert request.items[0].task == "complete prompt"
    assert request.items[0].cwd == "src"
    assert request.items[1].cwd is None
    assert request.provider == "provider  name"
    assert request.model == "org/ model-id"
    assert request.reasoning_effort == "xhigh"
    assert request.timeout_seconds == 2.5


@pytest.mark.parametrize("field", ("provider", "model"))
@pytest.mark.parametrize(
    "value",
    (
        "default",
        " DEFAULT ",
        "DeFaUlT",
        "inherit",
        " INHERIT ",
        "InHeRiT",
        "auto",
        " AUTO ",
        "AuTo",
    ),
)
def test_validation_rejects_reserved_literal_override_placeholders(field: str, value: str) -> None:
    """Prove provider and model placeholders fail after whitespace and case normalization."""

    with pytest.raises(ValidationFailure) as excinfo:
        validate_arguments({"tasks": [{"agent": "a", "task": "x"}], field: value})

    message = str(excinfo.value)
    assert field in message
    assert f"{field} must be an exact literal override" in message
    assert "omit" in message


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ("provider", "model"))
@pytest.mark.parametrize(
    "value",
    (
        "default",
        " DEFAULT ",
        "DeFaUlT",
        "inherit",
        " INHERIT ",
        "InHeRiT",
        "auto",
        " AUTO ",
        "AuTo",
    ),
)
async def test_reserved_literal_override_returns_validation_result_without_child(
    tmp_path: Path, field: str, value: str
) -> None:
    """Prove rejected provider and model placeholders return normally before a child starts."""

    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute(
        {"tasks": [{"agent": "general-purpose", "task": "work"}], field: value}
    )

    assert result.text.startswith(f"Invalid parameters: {field}")
    assert f"{field} must be an exact literal override" in result.text
    assert "omit" in result.text
    assert result.details["results"] == []
    assert runner.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ("provider", "model"))
async def test_whitespace_literal_overrides_require_non_empty_string_and_prevent_children(
    tmp_path: Path, field: str
) -> None:
    """Prove whitespace-only overrides explain omission and never start a child."""

    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute(
        {"tasks": [{"agent": "general-purpose", "task": "work"}], field: "   "}
    )

    assert result.text.startswith(f"Invalid parameters: {field}")
    assert "non-empty string" in result.text
    assert "omit" in result.text
    assert result.details["results"] == []
    assert runner.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ("provider", "model"))
async def test_non_string_literal_overrides_require_string_and_prevent_children(
    tmp_path: Path, field: str
) -> None:
    """Prove wrong-type overrides retain the string error and never start a child."""

    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute(
        {"tasks": [{"agent": "general-purpose", "task": "work"}], field: 3}
    )

    assert result.text.startswith(f"Invalid parameters: {field}")
    assert "must be a string" in result.text
    assert result.details["results"] == []
    assert runner.calls == []


@pytest.mark.asyncio
async def test_invalid_call_returns_normal_tool_result_with_schema_details(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute({})

    assert "Invalid parameters" in result.text
    assert "general-purpose (bundled)" in result.text
    assert result.details["schemaVersion"] == 2
    assert "mode" not in result.details
    assert result.details["results"] == []
    assert runner.calls == []


@pytest.mark.asyncio
async def test_single_item_runs_one_child_and_returns_complete_final_message(
    tmp_path: Path,
) -> None:
    """Prove a one-item call runs one child and relays its complete final
    assistant message verbatim: no summary extraction, no heading rewriting."""

    runner = FakeRunner()
    updates = []
    result = await make_dispatcher(tmp_path, runner).execute(
        {
            "tasks": [{"agent": "general-purpose", "task": "implement", "cwd": "src"}],
            "model": "call/model",
            "reasoningEffort": "medium",
        },
        on_update=updates.append,
    )

    assert result.text == (
        "full output for implement\n## Summary\nsummary for implement\n**Status: DONE**"
    )
    details = result.details
    assert details["schemaVersion"] == 2
    assert "mode" not in details
    assert details["discoveryDiagnostics"] == ["one diagnostic"]
    assert details["planned"] == 1
    child = details["results"][0]
    assert child["messages"][0]["role"] == "assistant"
    assert child["provider"] == "agent-provider"
    assert child["model"] == "call/model"
    assert child["reasoningEffort"] == "medium"
    assert child["cwd"] == str(resolve_child_cwd(tmp_path, "src"))
    assert runner.calls[0]["provider_override"] is None
    assert runner.calls[0]["model_override"] == "call/model"
    assert runner.calls[0]["reasoning_effort_override"] == "medium"
    # Live updates: one from the accepted message, one on completion, one
    # final backfill — the same slot-based path any child count takes. The
    # fixture marks a slot terminal from creation (exitCode 0), so every
    # snapshot already counts it. (The real runner's 0/N live window is
    # pinned by the runtime integration tests.)
    assert len(updates) == 3
    assert [update.text for update in updates] == ["1/1 done", "1/1 done", "1/1 done"]


@pytest.mark.asyncio
async def test_single_item_failure_returns_concise_failure(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute(
        {"tasks": [{"agent": "general-purpose", "task": "fail"}]}
    )

    assert result.text == "Agent general-purpose failed: planned failure"
    assert result.details["results"][0]["status"] == "BLOCKED"


@pytest.mark.asyncio
async def test_single_item_review_result_relays_complete_final_message(tmp_path: Path) -> None:
    """Prove review reports are relayed whole: the Code Review section is not
    extracted, the analysis prefix is not stripped, and no Summary mandate is
    applied on the dispatch side."""

    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute(
        {"tasks": [{"agent": "code-review", "task": "review"}]}
    )

    assert result.text == (
        "analysis\n"
        "## Code Review\n"
        "**Verdict:** Approved with fixes\n- point\n"
        "## Summary\n"
        "summary for review\n**Status: DONE**"
    )
    child = result.details["results"][0]
    assert child["messages"][0]["content"][0]["text"].startswith("analysis")


@pytest.mark.asyncio
async def test_multiple_items_run_in_parallel_with_ordered_sections(tmp_path: Path) -> None:
    """Prove 2+ items dispatch in parallel with bounded concurrency, keep input
    order in results, and produce one per-child section carrying that child's
    complete final message."""

    runner = FakeRunner()
    tasks = [{"agent": "general-purpose", "task": f"task-{index}"} for index in range(8)]

    result = await make_dispatcher(tmp_path, runner).execute({"tasks": tasks})

    assert runner.max_active == 4
    assert [item["task"] for item in result.details["results"]] == [
        f"task-{index}" for index in range(8)
    ]
    assert result.text.startswith("8/8 succeeded")
    assert "Parallel:" not in result.text
    for index in range(8):
        section = (
            f"[general-purpose] (completed)\n\n"
            f"full output for task-{index}\n## Summary\nsummary for task-{index}\n"
            "**Status: DONE**"
        )
        assert section in result.text
    assert result.text.index("summary for task-0") < result.text.index("summary for task-7")


@pytest.mark.asyncio
async def test_failed_child_section_falls_back_to_error_message(tmp_path: Path) -> None:
    """Prove a failed child with no final text contributes its error message as
    the section body, keeping the R5 envelope shape."""

    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute(
        {
            "tasks": [
                {"agent": "general-purpose", "task": "fail"},
                {"agent": "read-only", "task": "fine"},
            ]
        }
    )

    assert result.text.startswith("1/2 succeeded")
    assert "[general-purpose] (failed)\n\nplanned failure" in result.text
    assert "[read-only] (completed)\n\nfull output for fine" in result.text


@pytest.mark.asyncio
async def test_details_use_schema_v2_without_mode_or_step(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute(
        {
            "tasks": [
                {"agent": "general-purpose", "task": "one"},
                {"agent": "read-only", "task": "two"},
            ]
        }
    )

    details = result.details
    assert details["schemaVersion"] == 2
    assert "mode" not in details
    assert details["planned"] == 2
    assert details["agentScope"] == "user"
    for child in details["results"]:
        assert "step" not in child
        assert "mode" not in child


@pytest.mark.asyncio
async def test_parallel_timeout_stops_queued_work_and_retains_ordered_slots(tmp_path: Path) -> None:
    runner = FakeRunner()
    tasks = [
        {"agent": "general-purpose", "task": task}
        for task in ("timeout", "one", "two", "three", "queued")
    ]
    calls = UsageCalls()

    result = await make_dispatcher(tmp_path, runner, usage_observer=calls.record).execute(
        {"tasks": tasks}
    )

    assert len(runner.calls) == 4
    assert [item["task"] for item in result.details["results"]] == [
        "timeout",
        "one",
        "two",
        "three",
        "queued",
    ]
    assert "not started" in result.details["results"][-1]["errorMessage"].lower()
    assert result.text.startswith("3/5 succeeded")

    # The final commit keeps one slot per planned task, including the
    # zero-usage never-started slots produced by the timeout.
    assert calls.final_count == 1
    assert [child.task for child in calls.last_children] == [
        "timeout",
        "one",
        "two",
        "three",
        "queued",
    ]
    queued = calls.last_children[-1]
    assert queued.usage.input == 0
    assert queued.usage.cost == 0.0
    assert any(
        not final and len(children) < len(calls.last_children) for children, final in calls.calls
    ), "no partial live snapshot was fed"


@pytest.mark.asyncio
async def test_project_agents_fail_closed_headless_and_allow_explicit_bypass(
    tmp_path: Path,
) -> None:
    runner = FakeRunner()
    calls = UsageCalls()
    headless = make_dispatcher(tmp_path, runner, source="project", usage_observer=calls.record)

    rejected = await headless.execute(
        {"tasks": [{"agent": "general-purpose", "task": "work"}], "agentScope": "project"}
    )
    assert "approval required in headless mode" in rejected.text
    assert runner.calls == []
    # Headless denial returns before dispatch starts, so it feeds nothing.
    assert calls.calls == []

    approved = await headless.execute(
        {
            "tasks": [{"agent": "general-purpose", "task": "work"}],
            "agentScope": "project",
            "confirmProjectAgents": False,
        }
    )
    assert approved.text.startswith("full output for work")
    assert len(runner.calls) == 1
    assert calls.final_count == 1


@pytest.mark.asyncio
async def test_project_agents_use_ui_confirmation(tmp_path: Path) -> None:
    denied_runner = FakeRunner()
    denied_ui = FakeUi(has_ui=True, answer=False)
    denied = await make_dispatcher(tmp_path, denied_runner, ui=denied_ui, source="project").execute(
        {"tasks": [{"agent": "general-purpose", "task": "work"}], "agentScope": "project"}
    )
    assert denied.text.startswith("Canceled")
    assert denied_runner.calls == []
    assert "general-purpose" in denied_ui.confirmations[0][1]

    allowed_runner = FakeRunner()
    allowed_ui = FakeUi(has_ui=True, answer=True)
    allowed = await make_dispatcher(
        tmp_path, allowed_runner, ui=allowed_ui, source="project"
    ).execute({"tasks": [{"agent": "general-purpose", "task": "work"}], "agentScope": "project"})
    assert allowed.text.startswith("full output for work")
    assert len(allowed_runner.calls) == 1


@pytest.mark.asyncio
async def test_single_uses_parent_provider_and_model_when_agent_is_unpinned(
    tmp_path: Path,
) -> None:
    """Prove dispatch forwards parent values for an unpinned agent."""

    runner = FakeRunner()
    dispatcher = make_dispatcher(
        tmp_path, runner, parent_provider="openai", parent_model="gpt-5.6-sol"
    )

    result = await dispatcher.execute({"tasks": [{"agent": "read-only", "task": "work"}]})

    call = runner.calls[0]
    assert call["parent_provider"] == "openai"
    assert call["parent_model"] == "gpt-5.6-sol"
    assert call["provider_override"] is None
    assert call["model_override"] is None
    assert result.details["results"][0]["provider"] == "openai"
    assert result.details["results"][0]["model"] == "gpt-5.6-sol"


@pytest.mark.asyncio
async def test_single_inherits_parent_thinking_level_by_default(tmp_path: Path) -> None:
    """Prove an unpinned child inherits the parent session's thinking level
    unless the call, config, or agent definition pins one."""

    runner = FakeRunner()
    dispatcher = make_dispatcher(
        tmp_path,
        runner,
        parent_reasoning_effort="medium",
    )

    result = await dispatcher.execute({"tasks": [{"agent": "read-only", "task": "work"}]})

    call = runner.calls[0]
    assert call["parent_reasoning_effort"] == "medium"
    assert call["reasoning_effort_override"] is None
    assert result.details["results"][0]["reasoningEffort"] == "medium"


@pytest.mark.asyncio
async def test_trimmed_literal_overrides_reach_child_configuration(tmp_path: Path) -> None:
    """Prove authoritative provider and model values reach the child trimmed."""

    runner = FakeRunner()
    await make_dispatcher(tmp_path, runner).execute(
        {
            "tasks": [{"agent": "read-only", "task": "work"}],
            "provider": " openai ",
            "model": " vendor/model name ",
            "reasoningEffort": " HIGH ",
        }
    )

    call = runner.calls[0]
    assert call["provider_override"] == "openai"
    assert call["model_override"] == "vendor/model name"
    assert call["reasoning_effort_override"] == "high"


@pytest.mark.asyncio
async def test_call_reasoning_override_beats_parent_thinking_level(tmp_path: Path) -> None:
    """Prove a call-level reasoningEffort overrides parent-session inheritance."""

    runner = FakeRunner()
    dispatcher = make_dispatcher(tmp_path, runner, parent_reasoning_effort="medium")

    result = await dispatcher.execute(
        {"tasks": [{"agent": "read-only", "task": "work"}], "reasoningEffort": "low"}
    )

    assert runner.calls[0]["reasoning_effort_override"] == "low"
    assert result.details["results"][0]["reasoningEffort"] == "low"


@pytest.mark.asyncio
async def test_config_agent_overrides_shadow_agent_definition(tmp_path: Path) -> None:
    """Prove a per-agent config section overrides the selected agent definition
    for the keys it sets, per agent, while unpinned keys still fall through."""

    runner = FakeRunner()
    config = SubagentConfig(
        agents=(
            (
                "general-purpose",
                AgentOverrides(model="config/model", reasoning_effort="high"),
            ),
        )
    )
    dispatcher = make_dispatcher(tmp_path, runner, config=config)

    result = await dispatcher.execute({"tasks": [{"agent": "general-purpose", "task": "work"}]})

    call = runner.calls[0]
    # make_discovery pins provider "agent-provider" and model "agent-model" on
    # general-purpose; the config shadows the model and reasoning only.
    assert call["config_overrides"] == AgentOverrides(model="config/model", reasoning_effort="high")
    child = result.details["results"][0]
    assert child["provider"] == "agent-provider"
    assert child["model"] == "config/model"
    assert child["reasoningEffort"] == "high"


@pytest.mark.asyncio
async def test_config_defaults_apply_to_unpinned_agents_before_parent(
    tmp_path: Path,
) -> None:
    """Prove config defaults supply values for agents that pin nothing, ahead of
    the parent-session fallback."""

    runner = FakeRunner()
    config = SubagentConfig(defaults=AgentOverrides(model="default/model", reasoning_effort="low"))
    dispatcher = make_dispatcher(
        tmp_path,
        runner,
        config=config,
        parent_reasoning_effort="medium",
        parent_provider="openai",
        parent_model="gpt-5.6-sol",
    )

    result = await dispatcher.execute({"tasks": [{"agent": "read-only", "task": "work"}]})

    child = result.details["results"][0]
    assert child["provider"] == "openai"
    assert child["model"] == "default/model"
    assert child["reasoningEffort"] == "low"


@pytest.mark.asyncio
async def test_bundled_agent_pins_survive_empty_config(tmp_path: Path) -> None:
    """Prove bundled pins are preserved when a config file configures other
    agents only, so defaults never leak into pinned agents."""

    runner = FakeRunner()
    config = SubagentConfig(defaults=AgentOverrides(model="default/model", reasoning_effort="low"))
    dispatcher = make_dispatcher(tmp_path, runner, config=config)

    result = await dispatcher.execute({"tasks": [{"agent": "general-purpose", "task": "work"}]})

    # The agent definition pins provider/model on general-purpose, which must
    # beat config defaults (reasoning falls to the default layer).
    child = result.details["results"][0]
    assert child["provider"] == "agent-provider"
    assert child["model"] == "agent-model"
    assert child["reasoningEffort"] == "low"


@pytest.mark.asyncio
async def test_details_carry_config_paths_and_diagnostics(tmp_path: Path) -> None:
    """Prove loaded config files and config diagnostics surface in details so
    operators can see which config applied and why parts were ignored."""

    runner = FakeRunner()
    config = SubagentConfig(
        paths=(tmp_path / ".tau" / "superpowers-subagent.toml",),
        diagnostics=("ignored typo",),
    )

    result = await make_dispatcher(tmp_path, runner, config=config).execute(
        {"tasks": [{"agent": "read-only", "task": "work"}]}
    )

    assert result.details["configPaths"] == [str(tmp_path / ".tau" / "superpowers-subagent.toml")]
    assert result.details["configDiagnostics"] == ["ignored typo"]
    assert runner.calls[0]["config_overrides"] == AgentOverrides()


@pytest.mark.asyncio
async def test_parallel_applies_config_overrides_per_agent(tmp_path: Path) -> None:
    """Prove parallel items each resolve their own config section, leaving
    agents without a section on lower-layer fallback."""

    runner = FakeRunner()
    config = SubagentConfig(agents=(("read-only", AgentOverrides(reasoning_effort="xhigh")),))

    result = await make_dispatcher(tmp_path, runner, config=config).execute(
        {
            "tasks": [
                {"agent": "general-purpose", "task": "one"},
                {"agent": "read-only", "task": "two"},
            ]
        }
    )

    children = result.details["results"]
    assert children[0].get("reasoningEffort") is None
    assert children[1]["reasoningEffort"] == "xhigh"
    assert runner.calls[0]["config_overrides"] == AgentOverrides()
    assert runner.calls[1]["config_overrides"] == AgentOverrides(reasoning_effort="xhigh")


@pytest.mark.asyncio
async def test_config_section_for_unknown_agent_name_adds_diagnostic(
    tmp_path: Path,
) -> None:
    """Prove a config section whose agent name matches no bundled, user, or
    project definition is reported as a diagnostic instead of silently no-oping,
    since a typo here is the most likely config mistake."""

    runner = FakeRunner()
    config = SubagentConfig(agents=(("typo-agent", AgentOverrides(model="never-used")),))

    result = await make_dispatcher(tmp_path, runner, config=config).execute(
        {"tasks": [{"agent": "general-purpose", "task": "work"}]}
    )

    assert result.details["configDiagnostics"] == [
        "Subagent config: [agents.typo-agent] matches no bundled, user, or project agent definition"
    ]


@pytest.mark.asyncio
async def test_config_section_matching_another_scope_is_not_diagnosed(
    tmp_path: Path,
) -> None:
    """Prove a config section for an agent that exists only in the project layer
    is not flagged when the call uses user scope; scope gaps are not typos."""

    runner = FakeRunner()
    bundled = make_discovery(tmp_path, source="bundled")
    project_agent = AgentConfig(
        name="project-worker",
        description="Project worker",
        system_prompt="",
        source="project",  # type: ignore[arg-type]
        file_path=tmp_path / ".tau" / "agents" / "project-worker.md",
    )
    project = DiscoveryResult(
        agents=(project_agent,),
        project_agents_dir=tmp_path / ".tau" / "agents",
        diagnostics=(),
    )

    def scope_aware(_cwd: Path, scope: str) -> DiscoveryResult:
        if scope == "both":
            return DiscoveryResult(
                agents=(*bundled.agents, project_agent),
                project_agents_dir=project.project_agents_dir,
                diagnostics=(),
            )
        if scope == "project":
            return project
        return bundled

    config = SubagentConfig(agents=(("project-worker", AgentOverrides(model="worker-model")),))
    dispatcher = TaskDispatcher(
        default_cwd=tmp_path,
        ui=FakeUi(),
        runner=runner,  # type: ignore[arg-type]
        discovery_fn=scope_aware,
        config=config,
    )

    result = await dispatcher.execute(
        {"tasks": [{"agent": "general-purpose", "task": "work"}], "agentScope": "user"}
    )

    assert result.details.get("configDiagnostics") is None


@pytest.mark.asyncio
async def test_unknown_agent_is_a_structured_failure(tmp_path: Path) -> None:
    runner = FakeRunner()
    result = await make_dispatcher(tmp_path, runner).execute(
        {"tasks": [{"agent": "missing", "task": "work"}]}
    )

    assert result.text.startswith("Agent missing failed: Unknown agent 'missing'")
    child = result.details["results"][0]
    assert child["agentSource"] == "unknown"
    assert child["status"] == "BLOCKED"
    assert runner.calls == []


@pytest.mark.asyncio
async def test_single_dispatch_feeds_usage_observer(tmp_path: Path) -> None:
    """Prove single dispatch delivers live snapshots and exactly one final
    commit carrying the completed child, so the tracker never double counts."""

    calls = UsageCalls()
    runner = FakeRunner()
    dispatcher = make_dispatcher(tmp_path, runner, usage_observer=calls.record)

    result = await dispatcher.execute(
        {"tasks": [{"agent": "general-purpose", "task": "task-one"}]},
        signal=None,
        on_update=None,
    )

    assert calls.calls, "observer was never fed"
    assert calls.final_count == 1
    assert calls.calls[-1][1] is True
    final_children = calls.last_children
    assert len(final_children) == 1
    assert final_children[0].task == "task-one"
    # The observer must not change what the caller receives: the same complete
    # final message and wire details arrive as without it.
    assert result.text == (
        "full output for task-one\n## Summary\nsummary for task-one\n**Status: DONE**"
    )
    details = result.details
    assert details is not None and details["schemaVersion"] == 2
    assert len(details["results"]) == 1
    assert len(details["results"][0]["messages"]) == 1


@pytest.mark.asyncio
async def test_parallel_dispatch_commits_all_children_once(tmp_path: Path) -> None:
    """Prove parallel dispatch feeds snapshots while children complete and one
    final commit with every result in input order."""

    calls = UsageCalls()
    runner = FakeRunner()
    dispatcher = make_dispatcher(tmp_path, runner, usage_observer=calls.record)
    items = [{"agent": "general-purpose", "task": f"parallel-{index}"} for index in range(4)]

    await dispatcher.execute({"tasks": items}, signal=None, on_update=None)

    assert calls.final_count == 1
    final_children = calls.last_children
    assert [child.task for child in final_children] == [f"parallel-{index}" for index in range(4)]
    assert any(not final for _children, final in calls.calls), "no live snapshot was fed"


@pytest.mark.asyncio
async def test_validation_failure_never_feeds_usage_observer(tmp_path: Path) -> None:
    """Prove a request rejected before dispatch produces no usage observations."""

    calls = UsageCalls()
    runner = FakeRunner()
    dispatcher = make_dispatcher(tmp_path, runner, usage_observer=calls.record)

    await dispatcher.execute({"tasks": []}, signal=None, on_update=None)

    assert calls.calls == []


@pytest.mark.asyncio
async def test_unknown_agent_commits_zero_usage_child(tmp_path: Path) -> None:
    """Prove an unknown-agent failure still commits once with a zero-usage
    child, which the tracker ignores rather than counting as a run."""

    calls = UsageCalls()
    runner = FakeRunner()
    dispatcher = make_dispatcher(tmp_path, runner, usage_observer=calls.record)

    await dispatcher.execute(
        {"tasks": [{"agent": "no-such-agent", "task": "work"}]}, signal=None, on_update=None
    )

    assert calls.final_count == 1
    final_children = calls.last_children
    assert final_children[0].agent == "no-such-agent"
    assert final_children[0].usage.input == 0
    assert final_children[0].usage.cost == 0.0


@pytest.mark.asyncio
async def test_usage_observation_precedes_update_delivery(tmp_path: Path) -> None:
    """Prove live usage snapshots are fed before the frontend update callback
    whenever both are present, with the final commit trailing as the sole
    observation after the last update."""

    events: list[str] = []
    runner = FakeRunner()
    dispatcher = make_dispatcher(
        tmp_path,
        runner,
        usage_observer=lambda children, final: events.append("observer"),
    )

    await dispatcher.execute(
        {"tasks": [{"agent": "general-purpose", "task": "task-one"}]},
        signal=None,
        on_update=lambda _report: events.append("update"),
    )

    assert events[0] == "observer"
    for index, event in enumerate(events):
        if event == "update":
            assert index > 0 and events[index - 1] == "observer"
    assert events[-1] == "observer"
    assert events.count("observer") == events.count("update") + 1
