"""Pure output, status, and invocation helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from tau_agent.messages import AgentMessage, AssistantMessage, TextContent

from .models import AgentConfig, SubagentStatus

_SUMMARY_HEADING = re.compile(r"^[\t ]*## Summary[\t ]*\r?$", re.MULTILINE)
_REVIEW_HEADING = re.compile(r"^[\t ]*## Code Review[\t ]*\r?$", re.MULTILINE)
_STATUS_MARKER = re.compile(
    r"(?:\*\*)?Status:\s*"
    r"(DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED|DONE)"
    r"(?:\*\*)?\b",
    re.IGNORECASE,
)


def final_output(messages: list[AgentMessage]) -> str:
    """Concatenate text blocks from the last assistant message."""

    for message in reversed(messages):
        if isinstance(message, AssistantMessage):
            return "".join(
                block.text for block in message.content if isinstance(block, TextContent)
            )
    return ""


def summary_section(text: str) -> str:
    """Return the last exact `## Summary` section, or all output as fallback."""

    matches = list(_SUMMARY_HEADING.finditer(text))
    if not matches:
        return text
    return text[matches[-1].start() :]


def content_section(text: str) -> str:
    """Return the parent-facing content for one child's final output.

    Reviewers return actionable points under an exact `## Code Review` heading
    followed by an exact `## Summary` heading; those sections are both needed
    by the controller, so when both headings exist with the summary at or
    after the review, content starts at the last `## Code Review` heading.
    Otherwise the regular summary-or-fallback rule applies.
    """

    review_matches = list(_REVIEW_HEADING.finditer(text))
    summary_matches = list(_SUMMARY_HEADING.finditer(text))
    if review_matches and summary_matches:
        if summary_matches[-1].start() >= review_matches[-1].start():
            return text[review_matches[-1].start() :]
    return summary_section(text)


def parse_status(text: str, *, failed: bool) -> SubagentStatus:
    """Use the final supported status marker, with an outcome-aware default."""

    matches = list(_STATUS_MARKER.finditer(text))
    if matches:
        return cast(SubagentStatus, matches[-1].group(1).upper())
    return "BLOCKED" if failed else "DONE"


def resolve_child_cwd(default_cwd: Path, override: str | None) -> Path:
    """Resolve a child cwd relative to the parent session cwd."""

    if override is None:
        return default_cwd.expanduser().resolve()
    candidate = Path(override).expanduser()
    if not candidate.is_absolute():
        candidate = default_cwd / candidate
    return candidate.resolve()


def effective_provider_model(
    agent: AgentConfig,
    provider_override: str | None,
    model_override: str | None,
) -> tuple[str | None, str | None]:
    """Resolve provider and model independently at call then agent precedence."""

    return provider_override or agent.provider, model_override or agent.model


def effective_reasoning_effort(
    agent: AgentConfig,
    reasoning_effort_override: str | None,
) -> str | None:
    """Resolve the reasoning effort at call then agent precedence."""

    return reasoning_effort_override or agent.reasoning_effort


def build_tau_argv(
    *,
    executable: str,
    cwd: Path,
    prompt_path: Path,
    task: str,
    provider: str | None,
    model: str | None,
    policy_path: Path | None = None,
    thinking_policy_path: Path | None = None,
) -> list[str]:
    """Build safe Tau child argv with every option before positional prompt input."""

    argv = [
        executable,
        "--mode",
        "json",
        "--no-extensions",
        "--no-approve",
        "--cwd",
        str(cwd),
        "--append-system-prompt",
        str(prompt_path),
    ]
    if policy_path is not None:
        argv.extend(["-e", str(policy_path)])
    if thinking_policy_path is not None:
        argv.extend(["-e", str(thinking_policy_path)])
    if provider is not None:
        argv.extend(["--provider", provider])
    if model is not None:
        argv.extend(["--model", model])
    argv.append(task)
    return argv
