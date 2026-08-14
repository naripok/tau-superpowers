from pathlib import Path

from tau_agent.messages import AssistantMessage, TextContent, ThinkingContent, ToolCall, UserMessage

from superpowers_subagent.models import AgentConfig
from superpowers_subagent.utils import (
    build_tau_argv,
    effective_provider_model,
    final_output,
    parse_status,
    summary_section,
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


def test_summary_section_uses_last_exact_heading_and_preserves_text() -> None:
    output = (
        "## Summary details\nnot a heading match\n"
        "## Summary\nold\n"
        "  ## Summary\t\nfinal\n**Status: DONE**"
    )

    assert summary_section(output) == "  ## Summary\t\nfinal\n**Status: DONE**"


def test_summary_section_falls_back_to_complete_output() -> None:
    output = "Prefix with inline ## Summary text\n### Summary\nbody"
    assert summary_section(output) == output
    assert summary_section("") == ""


def test_summary_section_accepts_crlf_heading_lines() -> None:
    assert summary_section("analysis\r\n## Summary\r\ndone") == "## Summary\r\ndone"


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
    )

    assert effective_provider_model(agent, None, "call/provider/model") == (
        "configured-provider",
        "call/provider/model",
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
        "--provider",
        "provider-a",
        "--model",
        "namespace/model-a",
        "Do the work",
    ]
