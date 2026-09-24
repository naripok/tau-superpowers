from pathlib import Path

from tau_agent.messages import AssistantMessage, TextContent, ThinkingContent, ToolCall, UserMessage

from superpowers_subagent.config import AgentOverrides
from superpowers_subagent.models import AgentConfig, SessionSelection
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


def test_effective_provider_model_prefers_config_agent_over_agent_definition(
    tmp_path: Path,
) -> None:
    """Prove a config [agents.<name>] pin shadows the agent definition's
    frontmatter pins at the top of the resolution chain, per field."""

    pinned = AgentConfig(
        name="pinned",
        description="Pinned",
        system_prompt="",
        source="user",
        file_path=tmp_path / "pinned.md",
        provider="agent-provider",
        model="agent/model",
    )

    assert effective_provider_model(
        pinned, config_overrides=AgentOverrides(provider="config-provider", model="config/model")
    ) == ("config-provider", "config/model")
    # A config section that pins one side leaves the agent definition's other
    # pin in place: resolution is per field.
    assert effective_provider_model(
        pinned, config_overrides=AgentOverrides(model="config/model")
    ) == ("agent-provider", "config/model")


def test_effective_provider_model_agent_definition_beats_config_defaults_and_parent(
    tmp_path: Path,
) -> None:
    """Prove the agent definition's frontmatter pins beat config [defaults],
    which beat the parent session, on an independent per-key basis."""

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
        pinned,
        config_defaults=AgentOverrides(provider="default-provider", model="default/model"),
        parent_provider="parent-provider",
        parent_model="parent-model",
    ) == ("agent-provider", "agent/model")
    assert effective_provider_model(
        plain,
        config_defaults=AgentOverrides(provider="default-provider"),
        parent_provider="parent-provider",
        parent_model="parent-model",
    ) == ("default-provider", "parent-model")


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
        plain, parent_provider="openai", parent_model="gpt-5.6-sol"
    ) == ("openai", "gpt-5.6-sol")


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

    assert effective_provider_model(
        model_pinned, parent_provider="openai", parent_model="gpt-5.6-sol"
    ) == ("openai", "agent/model")
    assert effective_provider_model(
        provider_pinned, parent_provider="openai", parent_model="gpt-5.6-sol"
    ) == ("agent-provider", "gpt-5.6-sol")


def test_effective_reasoning_effort_prefers_config_agent_over_agent_definition(
    tmp_path: Path,
) -> None:
    """Prove a config [agents.<name>] reasoning_effort pin shadows the agent
    definition's frontmatter pin."""

    pinned = AgentConfig(
        name="pinned",
        description="Pinned",
        system_prompt="",
        source="user",
        file_path=tmp_path / "pinned.md",
        reasoning_effort="xhigh",
    )

    assert (
        effective_reasoning_effort(
            pinned, config_overrides=AgentOverrides(reasoning_effort="medium")
        )
        == "medium"
    )


def test_effective_reasoning_effort_agent_definition_beats_config_defaults_and_parent(
    tmp_path: Path,
) -> None:
    """Prove the agent definition's reasoning_effort pin beats config [defaults]
    and the parent session, and config [defaults] beats the parent session."""

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

    assert (
        effective_reasoning_effort(pinned, config_defaults=AgentOverrides(reasoning_effort="low"))
        == "xhigh"
    )
    assert (
        effective_reasoning_effort(
            plain,
            config_defaults=AgentOverrides(reasoning_effort="low"),
            parent_reasoning_effort="xhigh",
        )
        == "low"
    )


def test_effective_reasoning_effort_falls_back_to_parent_session(tmp_path: Path) -> None:
    """Prove an unpinned child inherits the parent session's thinking level, and
    a child with no pin anywhere resolves nothing."""

    plain = AgentConfig(
        name="plain",
        description="Plain",
        system_prompt="",
        source="user",
        file_path=tmp_path / "plain.md",
    )

    assert effective_reasoning_effort(plain, parent_reasoning_effort="medium") == "medium"
    assert effective_reasoning_effort(plain) is None


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
        config_overrides=empty,
        config_defaults=empty,
        parent_provider="parent-provider",
        parent_model="parent-model",
    ) == ("parent-provider", "parent-model")
    assert effective_reasoning_effort(plain, config_overrides=empty, config_defaults=empty) is None


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


def test_build_tau_argv_fresh_session_pins_session_id_and_role(tmp_path: Path) -> None:
    """Prove a fresh SessionSelection inserts --session-id and --session-role
    immediately after --no-approve, keeps --cwd, and keeps every later flag and
    the task positional in the baseline order."""
    argv = build_tau_argv(
        executable="tau",
        cwd=tmp_path,
        prompt_path=tmp_path / "prompt.md",
        task="Do the work",
        provider="provider-a",
        model="namespace/model-a",
        policy_path=tmp_path / "policy.py",
        thinking_policy_path=tmp_path / "thinking_policy.py",
        session=SessionSelection(id="a" * 32),
    )

    assert argv == [
        "tau",
        "--mode",
        "json",
        "--no-extensions",
        "--no-approve",
        "--session-id",
        "a" * 32,
        "--session-role",
        "subagent",
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


def test_build_tau_argv_resumed_session_uses_session_and_drops_cwd(tmp_path: Path) -> None:
    """Prove a resumed SessionSelection inserts --session immediately after
    --no-approve and emits no --session-id, --session-role, or --cwd, because
    tau runs the child in the session's recorded cwd."""
    argv = build_tau_argv(
        executable="tau",
        cwd=tmp_path,
        prompt_path=tmp_path / "prompt.md",
        task="Do the work",
        provider="provider-a",
        model="namespace/model-a",
        policy_path=tmp_path / "policy.py",
        thinking_policy_path=tmp_path / "thinking_policy.py",
        session=SessionSelection(id="c" * 32, resume=True),
    )

    assert argv == [
        "tau",
        "--mode",
        "json",
        "--no-extensions",
        "--no-approve",
        "--session",
        "c" * 32,
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


def test_build_tau_argv_without_session_reproduces_baseline(tmp_path: Path) -> None:
    """Prove session=None reproduces the baseline argv exactly, so existing
    callers observe no change."""
    kwargs = {
        "executable": "tau",
        "cwd": tmp_path,
        "prompt_path": tmp_path / "prompt.md",
        "task": "Do the work",
        "provider": None,
        "model": None,
    }

    argv = build_tau_argv(**kwargs, session=None)

    assert argv == build_tau_argv(**kwargs)
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
        "Do the work",
    ]
