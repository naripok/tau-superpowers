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


def _agent_roster(cwd: Path | None) -> str:
    """One-line roster of discovered agents for the always-visible tool surface.

    Makes bundled, user, and project agents discoverable from the tool itself,
    so a controller without the workflow skills still learns which agents
    exist and what each is for. Any discovery failure yields an empty string;
    the caller falls back to the static bundled list.
    """

    try:
        discovery = discover_agents(cwd or Path.cwd(), "both")
    except Exception:  # noqa: BLE001 - the tool surface must survive discovery issues
        return ""
    return "; ".join(f"`{agent.name}`: {one_line(agent.description)}" for agent in discovery.agents)


def _task_item_schema(roster_text: str) -> dict[str, JSONValue]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["agent", "task"],
        "properties": {
            "agent": {
                "type": "string",
                "minLength": 1,
                "description": f"Agent name. Available: {roster_text}.",
            },
            "task": {"type": "string", "minLength": 1},
            "cwd": {"type": "string"},
        },
    }


def _task_parameters(roster_text: str) -> dict[str, JSONValue]:
    return {
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
                "items": _task_item_schema(roster_text),
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
                "description": (
                    "Optional literal provider override. Omit it to give every child "
                    "this session's provider. When passed, it must be an exact "
                    "configured provider name (from `tau providers`; invalid names "
                    "fail before any child starts, listing the configured ones)."
                ),
            },
            "model": {
                "type": "string",
                "minLength": 1,
                "description": (
                    "Optional literal model override. Omit it to give every child "
                    "this session's model. When passed, it must be an exact model ID "
                    "supported by the selected provider (invalid IDs fail before any "
                    "child starts, listing the provider's configured models)."
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
                    "definition, then the parent session's thinking level."
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

    try:
        session_cwd: Path | None = tau.context.cwd
    except Exception:  # noqa: BLE001 - context may be unbound during early setup
        session_cwd = None
    fallback_roster = (
        "`general-purpose` (full tool access), `implementation` (code, tests, and "
        "verification), `code-review` and `document-review` (adversarial read-only "
        "review), `read-only` (enforced read-only investigation)"
    )
    roster_text = _agent_roster(session_cwd) or fallback_roster

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
                "Dispatch substantive work to isolated Tau subagents: multi-step "
                "tasks that benefit from an isolated context window, or long-running "
                "work that must not block this session. Simple reads, searches, "
                "commands, and small edits are your own tool calls, and you never "
                "dispatch work you are about to perform yourself. Every call takes "
                "a tasks array: one item runs a single child, two or more run in "
                "parallel (max eight, four active) preserving input order; use "
                "separate calls for conditional sequences. Available agents (pass "
                f"one as tasks[].agent): {roster_text}. "
                "Project-controlled agent prompts require explicit approval."
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
                "Provider, model, and reasoningEffort are optional overrides; omit "
                "all three on normal calls and every child runs on this session's "
                "provider, model, and thinking level. Never send placeholder values "
                "such as `default`, `inherit`, or `auto`: the tool treats them as "
                "omitted. When an override is required, pass an exact configured "
                "provider name (see `tau providers`), an exact model ID supported by "
                "that provider, or one of `off`, `minimal`, `low`, `medium`, `high`, "
                "`xhigh`; durable per-agent pins belong in the "
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
