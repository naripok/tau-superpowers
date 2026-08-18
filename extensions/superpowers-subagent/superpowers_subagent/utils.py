"""Pure output, status, and invocation helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from tau_agent.messages import AgentMessage, AssistantMessage, TextContent

from .config import AgentOverrides
from .models import AgentConfig, SubagentStatus

_SUMMARY_HEADING = re.compile(r"^[\t ]*## Summary[\t ]*\r?$", re.MULTILINE)
#: Exact review-section headings that, when followed by an exact `## Summary`,
#: are relayed to the parent together with it. Kept as a set so future review
#: kinds only extend this list.
_REVIEW_HEADINGS: frozenset[str] = frozenset({"## Code Review", "## Document Review"})
_REVIEW_HEADING = re.compile(
    r"^[\t ]*(?:"
    + "|".join(re.escape(heading) for heading in sorted(_REVIEW_HEADINGS))
    + r")[\t ]*\r?$",
    re.MULTILINE,
)
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

    Reviewers return actionable points under an exact review heading (e.g.
    `## Code Review` or `## Document Review`) followed by an exact
    `## Summary` heading; both sections are needed by the controller, so when
    both headings exist with the summary at or after the review, content
    starts at the last review heading. Otherwise the regular
    summary-or-fallback rule applies.
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
    *,
    config_overrides: AgentOverrides | None = None,
    config_defaults: AgentOverrides | None = None,
    parent_provider: str | None = None,
    parent_model: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve provider and model independently per side at call, config-agent,
    agent-definition, config-defaults, then parent-session precedence."""

    return (
        provider_override
        or (config_overrides.provider if config_overrides is not None else None)
        or agent.provider
        or (config_defaults.provider if config_defaults is not None else None)
        or parent_provider,
        model_override
        or (config_overrides.model if config_overrides is not None else None)
        or agent.model
        or (config_defaults.model if config_defaults is not None else None)
        or parent_model,
    )


def effective_reasoning_effort(
    agent: AgentConfig,
    reasoning_effort_override: str | None,
    *,
    config_overrides: AgentOverrides | None = None,
    config_defaults: AgentOverrides | None = None,
    parent_reasoning_effort: str | None = None,
) -> str | None:
    """Resolve the reasoning effort at call, config-agent, agent-definition,
    config-defaults, then parent-session thinking-level precedence."""

    return (
        reasoning_effort_override
        or (config_overrides.reasoning_effort if config_overrides is not None else None)
        or agent.reasoning_effort
        or (config_defaults.reasoning_effort if config_defaults is not None else None)
        or parent_reasoning_effort
    )


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
