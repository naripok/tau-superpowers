"""Tau extension entry point for isolated subagent dispatch."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence

from tau_agent.tools import (
    AgentTool,
    AgentToolResult,
    ToolCancellationToken,
    ToolUpdateCallback,
)
from tau_agent.types import JSONValue
from tau_coding.extensions import ExtensionAPI

from .config import load_subagent_config
from .dispatch import TaskDispatcher
from .models import THINKING_LEVELS, ChildResult
from .rendering import render_task_call, render_task_result
from .runner import RECURSION_GUARD, TauChildRunner
from .sidebar import install as install_sidebar_section
from .usage import SubagentUsageTracker

_TASK_ITEM_SCHEMA: dict[str, JSONValue] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["agent", "task"],
    "properties": {
        "agent": {"type": "string", "minLength": 1},
        "task": {"type": "string", "minLength": 1},
        "cwd": {"type": "string"},
    },
}

_TASK_PARAMETERS: dict[str, JSONValue] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tasks"],
    "properties": {
        "description": {
            "type": "string",
            "description": "Short orchestration description for display.",
        },
        "tasks": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": _TASK_ITEM_SCHEMA,
            "description": (
                "Delegated tasks, one child per item; each item runs as an "
                "isolated child. One item runs a single child, two or more "
                "run in parallel (max eight, four active)."
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
            "description": "Opaque Tau provider override.",
        },
        "model": {
            "type": "string",
            "minLength": 1,
            "description": "Opaque Tau model override; never split on slash.",
        },
        "reasoningEffort": {
            "type": "string",
            "enum": ["off", "minimal", "low", "medium", "high", "xhigh"],
            "description": (
                "Thinking level for every child; a call-level value overrides "
                "the config file and the agent definition. Otherwise the level "
                "falls back to the config file, then the agent definition, then "
                "the parent session's thinking level. Applied as the child's "
                "Tau thinking level at session start; an unsupported level is "
                "reported on the child's stderr."
            ),
        },
        "timeoutSeconds": {
            "type": "number",
            "exclusiveMinimum": 0,
            "maximum": 3600,
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

        dispatcher = TaskDispatcher(
            default_cwd=tau.context.cwd,
            ui=tau.context.ui,
            runner=runner,
            parent_provider=tau.context.provider_name or None,
            parent_model=tau.context.model or None,
            parent_reasoning_effort=_parent_thinking_level(tau),
            config=load_subagent_config(tau.context.cwd),
            usage_observer=observe,
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
                "Dispatch substantive work to isolated Tau subagents: multi-step "
                "tasks that benefit from an isolated context window, or long-running "
                "work that must not block this session. Simple reads, searches, "
                "commands, and small edits are your own tool calls, and you never "
                "dispatch work you are about to perform yourself. Every call takes "
                "a tasks array: one item runs a single child, two or more run in "
                "parallel (max eight, four active) preserving input order; use "
                "separate calls for conditional sequences. Bundled agents include "
                "general-purpose, implementation, code-review and document-review "
                "(read plus read-only bash), and the enforced read-only profile. "
                "Project-controlled agent prompts require explicit approval."
            ),
            parameters=_TASK_PARAMETERS,
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
                "Always pass the `tasks` array, even for a single child: one item "
                "runs one child, several items run in parallel; use separate "
                "task-tool calls for conditional sequences where a later step "
                "depends on an earlier result.",
                "Make each delegated task prompt self-contained: children run in "
                "isolated sessions with no access to this conversation, so include "
                "all requirements, file paths, and relevant command output in the "
                "prompt.",
                "Pick the agent by task type: `implementation` for implementation "
                "work, `code-review` or `document-review` for reviews, `read-only` "
                "for substantial read-only investigation of named files, and "
                "`general-purpose` for everything else.",
                "Do not pass provider, model, or reasoningEffort in task-tool calls "
                "unless the user requests an override or a skill prescribes it; "
                "children inherit the parent session's provider, model, and "
                "thinking effort by default, and durable per-agent pins belong in "
                "the superpowers-subagent.toml config file.",
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
