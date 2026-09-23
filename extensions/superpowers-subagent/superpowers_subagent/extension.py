"""Tau extension entry point for isolated subagent dispatch."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from tau_agent.tools import (
    AgentTool,
    AgentToolResult,
    ToolCancellationToken,
    ToolUpdateCallback,
)
from tau_agent.types import JSONValue
from tau_coding.extensions import ExtensionAPI

from .catalog import scoped_catalog_snapshot
from .config import load_subagent_config
from .discovery import discover_agents
from .dispatch import TaskDispatcher
from .models import THINKING_LEVELS, ChildResult
from .rendering import render_task_call, render_task_result
from .runner import RECURSION_GUARD, TauChildRunner
from .sidebar import install as install_sidebar_section
from .usage import SubagentUsageTracker
from .utils import one_line

#: Tool-policy annotation per agent profile, rendered in every roster line.
_PROFILE_ANNOTATIONS: dict[str, str] = {
    "general-purpose": "all",
    "read-only": "read",
    "review": "read, bash",
}

#: Static bundled roster used when discovery fails or finds nothing. Pinned to
#: the bundled definitions' one-line descriptions so the tool surface survives
#: discovery problems without depending on discovery.
_BUNDLED_ROSTER = "\n".join(
    (
        "- code-review: Adversarial read-only code reviewer. Use for code quality "
        "review, spec compliance review, and inspection of named files. (Tools: read, bash)",
        "- document-review: Adversarial read-only document reviewer for the design workflow "
        "gates. Use for proposal review, feature-spec review, pl… (Tools: read, bash)",
        "- general-purpose: General-purpose subagent with full tool access. Use for non-trivial "
        "tasks that requires reading and writing files or ru… (Tools: all)",
        "- implementation: Implementation subagent for writing code, tests, and running "
        "verification. Use for one well-scoped implementation task… (Tools: all)",
        "- read-only: Read-only subagent for multi-file investigation of named files. Cannot "
        "modify files or run commands. Use for non-trivia… (Tools: read)",
    )
)

#: Usage notes rendered as bullets at the end of the tool description.
_TASK_USAGE_NOTES: tuple[str, ...] = (
    "Several tasks are several task calls in one message. Use separate calls for "
    "conditional sequences where a later step depends on an earlier result.",
    "Delegated work is not duplicated.",
    "Make each prompt self-contained: children run in isolated sessions with no access "
    "to this conversation.",
    "The result names the task_id that a later call can reuse to continue the same "
    "subagent session.",
    "State whether the child writes code or does research and how to verify the result.",
    "Project-controlled agent prompts require explicit approval.",
)


def _agent_roster(cwd: Path | None) -> str:
    """Annotated roster of the bundled and user agents for the tool surface.

    Renders one line per agent discovered from the bundled and user layers only,
    so project agents never reach the tool surface. Any discovery failure yields
    an empty string; the caller falls back to the static bundled roster.
    """

    try:
        discovery = discover_agents(cwd or Path.cwd(), "user")
    except Exception:  # noqa: BLE001 - the tool surface must survive discovery issues
        return ""
    lines = []
    for agent in sorted(discovery.agents, key=lambda agent: agent.name):
        annotation = _PROFILE_ANNOTATIONS[agent.profile]
        lines.append(f"- {agent.name}: {one_line(agent.description)} (Tools: {annotation})")
    return "\n".join(lines)


def _task_parameters(roster_text: str) -> dict[str, JSONValue]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["prompt"],
        "properties": {
            "prompt": {
                "type": "string",
                "minLength": 1,
                "description": "The child's task. The prompt is preserved verbatim.",
            },
            "subagent_type": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Optional agent name for the child. Omit subagent_type to select "
                    f"general-purpose. Available agents:\n{roster_text}"
                ),
            },
            "description": {
                "type": "string",
                "description": "Short orchestration label for display. No behavioral effect.",
            },
            "task_id": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Resume a previous child session: pass the task_id from an earlier task "
                    "result to continue the same subagent session instead of starting a "
                    "fresh one. Requires subagent_type."
                ),
            },
            "cwd": {
                "type": "string",
                "description": (
                    "Working directory for a fresh child. Omission uses this session's cwd. "
                    "Ignored on a resumed run."
                ),
            },
            "agentScope": {
                "type": "string",
                "enum": ["user", "project", "both"],
                "default": "user",
            },
            "confirmProjectAgents": {
                "type": "boolean",
                "default": True,
                "description": "Require interactive approval for resolved project agents.",
            },
            "provider": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Optional literal provider override. Omit it to give every child "
                    "this session's provider. When passed, it must be an exact "
                    "configured provider name (from `tau providers`; invalid names "
                    "fail before any child starts, listing the configured ones). A "
                    "default, inherit, or auto placeholder is coerced to omitted with "
                    "a repair note."
                ),
            },
            "model": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Optional literal model override. Omit it to give every child "
                    "this session's model. When passed, it must be an exact model ID "
                    "supported by the selected provider (invalid IDs fail before any "
                    "child starts, listing the provider's configured models). A "
                    "default, inherit, or auto placeholder is coerced to omitted with "
                    "a repair note."
                ),
            },
            "reasoningEffort": {
                "type": "string",
                "enum": ["off", "minimal", "low", "medium", "high", "xhigh"],
                "description": (
                    "Optional literal reasoningEffort override for every child: exactly "
                    "one of `off`, `minimal`, `low`, `medium`, `high`, or `xhigh`. Omit it "
                    "to give every child this session's thinking level. A call-level "
                    "value overrides the config file and agent definition; otherwise "
                    "the level falls back to the config file, then the agent "
                    "definition, then the parent session's thinking level. A default, "
                    "inherit, or auto placeholder is coerced to omitted with a repair note."
                ),
            },
            "timeoutSeconds": {
                "type": "number",
                "exclusiveMinimum": 0,
                "maximum": 10800,
                "default": 3600,
                "description": "Per-child timeout in seconds.",
            },
        },
    }


def _parent_thinking_level(tau: ExtensionAPI) -> str | None:
    """Return the active session thinking level, or None when unavailable.

    Tau 0.3 exposes no public extension property for the session's thinking
    level, so this mirrors the seam documented in ``runner.py``: the bound
    session is reached through the extension runtime view
    (``tau._runtime.session_view``). When any part of that seam is missing or
    the level is not one of the known Tau thinking levels, the parent cannot
    expose its level and unpinned children run at their ambient level.
    """

    runtime = getattr(tau, "_runtime", None)
    if runtime is None:
        return None
    try:
        level = getattr(runtime.session_view, "thinking_level", None)
    except Exception:  # noqa: BLE001 - the seam must never break dispatch
        return None
    if not isinstance(level, str) or level not in THINKING_LEVELS:
        return None
    return level


#: Tau session lifecycle reasons that re-scope the session: totals reset on
#: rebinds, but not at startup or /reload (a fresh setup already starts empty).
_REBIND_REASONS: frozenset[str] = frozenset({"new", "resume", "branch"})


def _reset_tracker_on_rebind(tracker: SubagentUsageTracker, event: object) -> None:
    """Reset session-scoped totals when the session rebinds."""
    if getattr(event, "reason", None) in _REBIND_REASONS:
        tracker.reset()


def setup(tau: ExtensionAPI) -> None:
    """Set up the task tool, session usage tracking, and the sidebar seam."""

    if os.environ.get(RECURSION_GUARD):
        return

    tracker = SubagentUsageTracker()
    install_sidebar_section(tracker)
    runner = TauChildRunner()

    try:
        session_cwd: Path | None = tau.context.cwd
    except Exception:  # noqa: BLE001 - context may be unbound during early setup
        session_cwd = None
    roster_text = _agent_roster(session_cwd) or _BUNDLED_ROSTER

    def on_session_start(event: object, _context: object) -> None:
        _reset_tracker_on_rebind(tracker, event)

    # Explicit handler form: ``ExtensionAPI.on``'s return type is a union that
    # includes the two-argument handler itself, so mypy strict rejects the
    # decorator form; passing the handler directly type-checks cleanly.
    tau.on("session_start", on_session_start)

    async def execute_task(
        tool_call_id: str,
        arguments: Mapping[str, JSONValue],
        signal: ToolCancellationToken | None = None,
        on_update: ToolUpdateCallback | None = None,
    ) -> AgentToolResult:

        def observe(children: Sequence[ChildResult], final: bool) -> None:
            tracker.update(tool_call_id, children, final)

        cwd = tau.context.cwd
        parent_provider = tau.context.provider_name or None
        parent_model = tau.context.model or None
        config = load_subagent_config(cwd)
        dispatcher = TaskDispatcher(
            default_cwd=cwd,
            ui=tau.context.ui,
            runner=runner,
            parent_provider=parent_provider,
            parent_model=parent_model,
            parent_reasoning_effort=_parent_thinking_level(tau),
            config=config,
            usage_observer=observe,
            catalog_fn=lambda: scoped_catalog_snapshot(
                cwd,
                parent_provider=parent_provider,
                parent_model=parent_model,
                config=config,
            ),
        )
        try:
            return await dispatcher.execute(arguments, signal=signal, on_update=on_update)
        finally:
            tracker.discard_pending(tool_call_id)

    tau.register_tool(
        AgentTool(
            name="task",
            label="task",
            description=(
                "Dispatch work to an isolated Tau subagent. Delegate substantive multi-step "
                "work that benefits from an isolated context window, or long-running work "
                "that must not block this session.\n"
                f"{roster_text}\n"
                "Omit subagent_type to select general-purpose.\n"
                "When not to use: Simple reads, searches, commands, and small edits are your "
                "own tool calls, and you never dispatch work you are about to perform "
                "yourself. Never dispatch a task and then do the same work.\n"
                "Usage notes:\n" + "\n".join(f"- {note}" for note in _TASK_USAGE_NOTES)
            ),
            parameters=_task_parameters(roster_text),
            execute_fn=execute_task,
            prompt_snippet="Dispatch substantive work to an isolated Tau subagent.",
            prompt_guidelines=(
                "When using the task tool, delegate only substantive multi-step work "
                "that benefits from an isolated context window, or long-running work "
                "that must not block this session; never delegate simple reads, "
                "searches, commands, or small edits — those are your own tool calls.",
                "Each dispatched subagent replaces your own tool calls for its "
                "delegated task; never dispatch a subagent and then perform the same "
                "work yourself.",
                "Pass exactly one task per call. Several tasks are several task calls "
                "in one message; use separate task-tool calls for conditional sequences "
                "where a later step depends on an earlier result.",
                "Make each delegated task prompt self-contained: children run in "
                "isolated sessions with no access to this conversation, so include "
                "all requirements, file paths, and relevant command output in the "
                "prompt.",
                "The result carries the child's task_id. Pass it as task_id on a later "
                "call, with the same subagent_type, to continue that child session "
                "instead of starting a fresh one.",
                "State whether the child writes code or does research and how to "
                "verify the result.",
                "Pick the agent by task type: `implementation` for implementation "
                "work, `code-review` or `document-review` for reviews, `read-only` "
                "for substantial read-only investigation of named files, and "
                "`general-purpose` for everything else.",
                "Provider, model, and reasoningEffort are optional overrides; omit "
                "all three on normal calls and every child runs on this session's "
                "provider, model, and thinking level. Never send placeholder values "
                "such as `default`, `inherit`, or `auto`: the tool treats them as "
                "omitted with a repair note. When an override is required, pass an "
                "exact configured provider name (see `tau providers`), an exact model "
                "ID supported by that provider, or one of `off`, `minimal`, `low`, "
                "`medium`, `high`, `xhigh`; durable per-agent pins belong in the "
                "superpowers-subagent.toml config file.",
                "Handle BLOCKED and NEEDS_CONTEXT child results explicitly: BLOCKED "
                "means the task could not be completed as dispatched — address the "
                "blocker or change the approach; NEEDS_CONTEXT means required "
                "information was missing — supply it in a new complete task-tool "
                "call.",
            ),
            render_call=render_task_call,
            render_result=render_task_result,
        )
    )
