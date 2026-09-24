"""Pure output, status, and invocation helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import cast

from tau_agent.messages import AgentMessage, AssistantMessage, TextContent

from .config import AgentOverrides
from .models import AgentConfig, SessionSelection, SubagentStatus

_STATUS_MARKER = re.compile(
    r"(?:\*\*)?Status:\s*"
    r"(DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED|DONE)"
    r"(?:\*\*)?\b",
    re.IGNORECASE,
)


def one_line(text: str, *, limit: int = 120) -> str:
    """Collapse whitespace and clip to ``limit`` characters for tool-surface text."""

    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def final_output(messages: list[AgentMessage]) -> str:
    """Concatenate text blocks from the last assistant message."""

    for message in reversed(messages):
        if isinstance(message, AssistantMessage):
            return "".join(
                block.text for block in message.content if isinstance(block, TextContent)
            )
    return ""


def parse_status(text: str, *, failed: bool) -> SubagentStatus:
    """Use the final supported status marker, with an outcome-aware default."""

    matches = list(_STATUS_MARKER.finditer(text))
    if matches:
        return cast(SubagentStatus, matches[-1].group(1).upper())
    return "BLOCKED" if failed else "DONE"


def effective_provider_model(
    agent: AgentConfig,
    *,
    config_overrides: AgentOverrides | None = None,
    config_defaults: AgentOverrides | None = None,
    parent_provider: str | None = None,
    parent_model: str | None = None,
) -> tuple[str | None, str | None]:
    """Resolve provider and model independently per side at config-agent,
    agent-definition, config-defaults, then parent-session precedence."""

    return (
        (config_overrides.provider if config_overrides is not None else None)
        or agent.provider
        or (config_defaults.provider if config_defaults is not None else None)
        or parent_provider,
        (config_overrides.model if config_overrides is not None else None)
        or agent.model
        or (config_defaults.model if config_defaults is not None else None)
        or parent_model,
    )


def effective_reasoning_effort(
    agent: AgentConfig,
    *,
    config_overrides: AgentOverrides | None = None,
    config_defaults: AgentOverrides | None = None,
    parent_reasoning_effort: str | None = None,
) -> str | None:
    """Resolve the reasoning effort at config-agent, agent-definition,
    config-defaults, then parent-session precedence."""

    return (
        (config_overrides.reasoning_effort if config_overrides is not None else None)
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
    session: SessionSelection | None = None,
) -> list[str]:
    """Build safe Tau child argv with every option before positional prompt input.

    A fresh ``session`` pins the child to a new session id with the subagent
    role. A resumed ``session`` reconnects by id and omits ``--cwd`` because
    tau runs the child in the session's recorded cwd.
    """

    argv = [executable, "--mode", "json", "--no-extensions", "--no-approve"]
    if session is None:
        argv.extend(["--cwd", str(cwd)])
    elif session.resume:
        argv.extend(["--session", session.id])
    else:
        argv.extend(["--session-id", session.id, "--session-role", "subagent", "--cwd", str(cwd)])
    argv.extend(["--append-system-prompt", str(prompt_path)])
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
