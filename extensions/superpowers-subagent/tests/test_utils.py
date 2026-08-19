from pathlib import Path

from tau_agent.messages import AssistantMessage, TextContent, ThinkingContent, ToolCall, UserMessage

from superpowers_subagent.config import AgentOverrides
from superpowers_subagent.models import AgentConfig
from superpowers_subagent.utils import (
    build_tau_argv,
    effective_provider_model,
    effective_reasoning_effort,
    final_output,
    parse_status,
)


def test_final_output_uses_last_assistant_and_all_text_blocks() -> None:
    messages = [
        UserMessage(content="request"),
        AssistantMessage(content=[TextContent(text="old")]),
        AssistantMessage(
            content=[
                TextContent(text="first"),
                ThinkingContent(thinking="hidden"),
                ToolCall(id="call-1", name="read", arguments={"path": "x"}),
                TextContent(text=" second"),
            ]
        ),
        UserMessage(content="ignored tail"),
    ]

    assert final_output(messages) == "first second"


def test_parse_status_uses_last_case_insensitive_bold_or_plain_marker() -> None:
    output = "**Status: BLOCKED**\nwork continued\nstatus: done_with_concerns"
    assert parse_status(output, failed=False) == "DONE_WITH_CONCERNS"


def test_parse_status_uses_outcome_default() -> None:
    assert parse_status("no marker", failed=False) == "DONE"
    assert parse_status("no marker", failed=True) == "BLOCKED"


def test_provider_and_model_overrides_are_independent_and_opaque(tmp_path: Path) -> None:
    agent = AgentConfig(
        name="worker",
        description="Worker",
        system_prompt="",
        source="user",
        file_path=tmp_path / "worker.md",
        provider="configured-provider",
        model="configured/model",
        reasoning_effort="xhigh",
    )

    assert effective_provider_model(agent, None, "call/provider/model") == (
        "configured-provider",
        "call/provider/model",
    )


def test_effective_provider_model_falls_back_to_parent_session(tmp_path: Path) -> None:
    """Prove unpinned children inherit the parent session's provider and model."""

    plain = AgentConfig(
        name="plain",
        description="Plain",
        system_prompt="",
        source="user",
        file_path=tmp_path / "plain.md",
    )

    assert effective_provider_model(
        plain, None, None, parent_provider="openai", parent_model="gpt-5.6-sol"
    ) == ("openai", "gpt-5.6-sol")


def test_effective_provider_model_prefers_agent_and_call_over_parent(tmp_path: Path) -> None:
    """Prove agent pins and call overrides always beat parent-session values."""

    pinned = AgentConfig(
        name="pinned",
        description="Pinned",
        system_prompt="",
        source="user",
        file_path=tmp_path / "pinned.md",
        provider="agent-provider",
        model="agent/model",
    )
    plain = AgentConfig(
        name="plain",
        description="Plain",
        system_prompt="",
        source="user",
        file_path=tmp_path / "plain.md",
    )

    assert effective_provider_model(
        pinned, None, None, parent_provider="openai", parent_model="gpt-5.6-sol"
    ) == ("agent-provider", "agent/model")
    assert effective_provider_model(
        plain,
        "call-provider",
        "call/model",
        parent_provider="openai",
        parent_model="gpt-5.6-sol",
    ) == ("call-provider", "call/model")


def test_effective_provider_model_falls_back_per_side_when_agent_pins_one_side(
    tmp_path: Path,
) -> None:
    """Prove provider and model fall back independently when an agent pins one side."""

    model_pinned = AgentConfig(
        name="model-pinned",
        description="Model pinned",
        system_prompt="",
        source="user",
        file_path=tmp_path / "model-pinned.md",
        model="agent/model",
    )
    provider_pinned = AgentConfig(
        name="provider-pinned",
        description="Provider pinned",
        system_prompt="",
        source="user",
        file_path=tmp_path / "provider-pinned.md",
        provider="agent-provider",
    )
    plain = AgentConfig(
        name="plain",
        description="Plain",
        system_prompt="",
        source="user",
        file_path=tmp_path / "plain.md",
    )

    assert effective_provider_model(
        model_pinned, None, None, parent_provider="openai", parent_model="gpt-5.6-sol"
    ) == ("openai", "agent/model")
    assert effective_provider_model(
        provider_pinned, None, None, parent_provider="openai", parent_model="gpt-5.6-sol"
    ) == ("agent-provider", "gpt-5.6-sol")
    assert effective_provider_model(
        plain, "call-provider", None, parent_provider="openai", parent_model="gpt-5.6-sol"
    ) == ("call-provider", "gpt-5.6-sol")


def test_effective_reasoning_effort_prefers_call_then_agent(tmp_path: Path) -> None:
    agent = AgentConfig(
        name="worker",
        description="Worker",
        system_prompt="",
        source="user",
        file_path=tmp_path / "worker.md",
        reasoning_effort="xhigh",
    )

    assert effective_reasoning_effort(agent, None) == "xhigh"
    assert effective_reasoning_effort(agent, "medium") == "medium"

    plain = AgentConfig(
        name="plain",
        description="Plain",
        system_prompt="",
        source="user",
        file_path=tmp_path / "plain.md",
    )
    assert effective_reasoning_effort(plain, None) is None
    assert effective_reasoning_effort(plain, "low") == "low"


def test_effective_reasoning_effort_config_layers_and_parent_fallback(
    tmp_path: Path,
) -> None:
    """Prove the reasoning effort resolves at call, config-agent, agent,
    config-defaults, then parent-session precedence."""

    pinned = AgentConfig(
        name="pinned",
        description="Pinned",
        system_prompt="",
        source="user",
        file_path=tmp_path / "pinned.md",
        reasoning_effort="xhigh",
    )
    plain = AgentConfig(
        name="plain",
        description="Plain",
        system_prompt="",
        source="user",
        file_path=tmp_path / "plain.md",
    )
    agent_config = AgentOverrides(reasoning_effort="medium")
    defaults_config = AgentOverrides(reasoning_effort="low")

    # Call beats config-agent, config-agent beats agent pin, agent beats
    # config-defaults, config-defaults beats the parent session level.
    assert (
        effective_reasoning_effort(
            pinned, "off", config_overrides=agent_config, config_defaults=defaults_config
        )
        == "off"
    )
    assert (
        effective_reasoning_effort(
            pinned, None, config_overrides=agent_config, config_defaults=defaults_config
        )
        == "medium"
    )
    assert (
        effective_reasoning_effort(
            pinned,
            None,
            config_overrides=None,
            config_defaults=defaults_config,
            parent_reasoning_effort="xhigh",
        )
        == "xhigh"
    )
    assert (
        effective_reasoning_effort(
            plain, None, config_defaults=defaults_config, parent_reasoning_effort="xhigh"
        )
        == "low"
    )
    # Nothing else pinned: the parent session thinking level is the default.
    assert effective_reasoning_effort(plain, None, parent_reasoning_effort="medium") == "medium"
    assert effective_reasoning_effort(plain, None) is None


def test_effective_provider_model_config_layers_between_call_and_agent(
    tmp_path: Path,
) -> None:
    """Prove config-agent values sit between the call and agent definition,
    and config-defaults sit between the agent definition and parent fallback,
    on an independent per-key basis."""

    pinned = AgentConfig(
        name="pinned",
        description="Pinned",
        system_prompt="",
        source="user",
        file_path=tmp_path / "pinned.md",
        provider="agent-provider",
        model="agent/model",
    )
    plain = AgentConfig(
        name="plain",
        description="Plain",
        system_prompt="",
        source="user",
        file_path=tmp_path / "plain.md",
    )
    agent_config = AgentOverrides(model="config/model")
    defaults_config = AgentOverrides(provider="default-provider")

    # Config-agent model shadows the agent pin while the agent provider stays.
    assert effective_provider_model(
        pinned,
        None,
        None,
        config_overrides=agent_config,
        config_defaults=defaults_config,
        parent_provider="parent-provider",
        parent_model="parent-model",
    ) == ("agent-provider", "config/model")
    # Config-defaults shadow the parent session fallback for an unpinned agent.
    assert effective_provider_model(
        plain,
        None,
        None,
        config_overrides=None,
        config_defaults=defaults_config,
        parent_provider="parent-provider",
        parent_model="parent-model",
    ) == ("default-provider", "parent-model")
    # A call override still wins over every other layer.
    assert effective_provider_model(
        pinned,
        "call-provider",
        None,
        config_overrides=agent_config,
        config_defaults=defaults_config,
        parent_provider="parent-provider",
        parent_model="parent-model",
    ) == ("call-provider", "config/model")


def test_effective_resolution_ignores_empty_override_objects(tmp_path: Path) -> None:
    """Prove empty config override objects behave exactly like None so a loaded
    config file with no relevant keys never changes resolution."""

    plain = AgentConfig(
        name="plain",
        description="Plain",
        system_prompt="",
        source="user",
        file_path=tmp_path / "plain.md",
    )
    empty = AgentOverrides()

    assert effective_provider_model(
        plain,
        None,
        None,
        config_overrides=empty,
        config_defaults=empty,
        parent_provider="parent-provider",
        parent_model="parent-model",
    ) == ("parent-provider", "parent-model")
    assert (
        effective_reasoning_effort(plain, None, config_overrides=empty, config_defaults=empty)
        is None
    )


def test_build_tau_argv_uses_supported_flags_and_positional_task(tmp_path: Path) -> None:
    argv = build_tau_argv(
        executable="tau",
        cwd=tmp_path,
        prompt_path=tmp_path / "prompt.md",
        task="Do the work",
        provider="provider-a",
        model="namespace/model-a",
        policy_path=tmp_path / "policy.py",
        thinking_policy_path=tmp_path / "thinking_policy.py",
    )

    assert argv == [
        "tau",
        "--mode",
        "json",
        "--no-extensions",
        "--no-approve",
        "--cwd",
        str(tmp_path),
        "--append-system-prompt",
        str(tmp_path / "prompt.md"),
        "-e",
        str(tmp_path / "policy.py"),
        "-e",
        str(tmp_path / "thinking_policy.py"),
        "--provider",
        "provider-a",
        "--model",
        "namespace/model-a",
        "Do the work",
    ]
