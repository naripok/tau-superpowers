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
    "properties": {
        "description": {
            "type": "string",
            "description": "Short orchestration description for display.",
        },
        "agent": {
            "type": "string",
            "minLength": 1,
            "description": (
                "Agent name for single mode; requires task and never combines with tasks or chain."
            ),
        },
        "task": {
            "type": "string",
            "minLength": 1,
            "description": (
                "Complete delegated prompt for single mode; requires agent and "
                "never combines with tasks or chain."
            ),
        },
        "cwd": {
            "type": "string",
            "description": (
                "Child working directory for single mode; parallel and chain "
                "items carry their own cwd."
            ),
        },
        "tasks": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": _TASK_ITEM_SCHEMA,
            "description": (
                "Independent parallel tasks (at most eight); never combine "
                "with agent + task or chain."
            ),
        },
        "chain": {
            "type": "array",
            "minItems": 1,
            "items": _TASK_ITEM_SCHEMA,
            "description": (
                "Sequential tasks; {previous} receives complete prior output. "
                "Never combine with agent + task or tasks."
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
                "Dispatch complete tasks to isolated Tau subagents. Pass exactly one "
                "mode per call: agent + task for single mode, tasks for ordered "
                "parallel mode (max eight, four active), or chain for sequential work "
                "with {previous}. The mode fields are mutually exclusive: never pass "
                "agent + task together with tasks or chain; use separate calls for "
                "additional or conditional work. Bundled agents include "
                "general-purpose, implementation, code-review and document-review "
                "(read plus read-only bash), and the enforced read-only profile. "
                "Project-controlled agent prompts require explicit approval."
            ),
            parameters=_TASK_PARAMETERS,
            execute_fn=execute_task,
            prompt_snippet="Dispatch work to an isolated Tau subagent.",
            prompt_guidelines=(
                "Include all required context because subagents cannot see this conversation.",
                "Pass exactly one dispatch mode per call: agent + task, or tasks, or "
                "chain. Mode fields never combine; use separate calls for conditional "
                "sequences.",
                "Use implementation for implementation work, code-review for reviews, "
                "and read-only for plain file inspection.",
                "Do not set provider, model, or reasoningEffort unless the user "
                "requests an override or a skill prescribes it; subagents inherit "
                "the parent session's model and thinking effort by default and can "
                "be pinned per agent in a superpowers-subagent.toml config file.",
                "Handle BLOCKED and NEEDS_CONTEXT reports explicitly.",
            ),
            render_call=render_task_call,
            render_result=render_task_result,
        )
    )
