"""Tau extension entry point for isolated subagent dispatch."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from tau_agent.tools import (
    AgentTool,
    AgentToolResult,
    ToolCancellationToken,
    ToolExecutor,
    ToolUpdateCallback,
)
from tau_agent.types import JSONValue
from tau_coding.extensions import ExtensionAPI

from .catalog import scoped_catalog_snapshot
from .config import load_subagent_config
from .discovery import discover_agents
from .dispatch import RequestMode, TaskDispatcher
from .models import THINKING_LEVELS, ChildResult
from .rendering import render_resume_call, render_task_call, render_task_result
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

#: Usage notes rendered as bullets at the end of the task tool description.
_TASK_USAGE_NOTES: tuple[str, ...] = (
    "Several tasks are several task calls in one message. Use separate calls for "
    "conditional sequences where a later step depends on an earlier result.",
    "Delegated work is not duplicated.",
    "Make each prompt self-contained: children run in isolated sessions with no access "
    "to this conversation.",
    "The result names the task_id that a later task_resume call can reuse to continue "
    "the same subagent session.",
    "State whether the child writes code or does research and how to verify the result.",
)

#: Prompt guidelines for the task tool: each guideline references the task
#: surface only, and continuation is always named as a task_resume call.
_TASK_PROMPT_GUIDELINES: tuple[str, ...] = (
    "When using the task tool, delegate only substantive multi-step work that benefits "
    "from an isolated context window, or long-running work that must not block this "
    "session; never delegate simple reads, searches, commands, or small edits — those "
    "are your own tool calls.",
    "Each dispatched subagent replaces your own tool calls for its delegated task; "
    "never dispatch a task you are about to perform yourself, and never dispatch a task "
    "and then do the same work.",
    "Pass exactly one task per call. Several tasks are several task calls in one "
    "message, which run children in parallel; use separate task calls for conditional "
    "sequences where a later step depends on an earlier result.",
    "Make each delegated task prompt self-contained: children run in isolated sessions "
    "with no access to this conversation, so include all requirements, file paths, and "
    "relevant command output in the prompt.",
    "The result carries the child's task_id. Pass it to a later task_resume call to "
    "continue that child session; task_resume takes no agent name.",
    "State whether the child writes code or does research and how to verify the result.",
    "Pick the agent by task type: `implementation` for implementation work, "
    "`code-review` or `document-review` for reviews, `read-only` for substantial "
    "read-only investigation of named files, and `general-purpose` for everything else.",
    "Children inherit this session's provider, model, and thinking level unless the "
    "superpowers-subagent.toml config file or the agent definition pins one; no "
    "call-level override exists.",
    "Handle BLOCKED and NEEDS_CONTEXT child results explicitly: BLOCKED means the task "
    "could not be completed as dispatched — address the blocker or change the approach "
    "with a fresh task call; NEEDS_CONTEXT means required information was missing — "
    "supply it in a task_resume call that continues the session.",
)

#: Prompt guidelines for the task_resume tool: each guideline references the
#: task_resume surface only, and the resumed agent is never a call choice.
_RESUME_PROMPT_GUIDELINES: tuple[str, ...] = (
    "Use task_resume only to continue the same subagent's work in that session; the "
    "resumed agent is the one the session started with. For work that needs a "
    "different agent, start a fresh task call instead.",
    "Pass exactly one task per call. Several task_resume calls in one message run "
    "children in parallel, but calls that carry the same task_id conflict: exactly one "
    "runs and the others fail closed.",
    "The prompt is the child's new user turn. Make it self-contained: the child has no "
    "access to this conversation, so restate every requirement, file path, and "
    "relevant command output it needs.",
    "The result carries the same task_id as the resumed session, so a later task_resume "
    "call can continue it again.",
    "timeout_seconds bounds the resumed run; omit it to use the 3600-second default.",
    "Delegate only substantive multi-step work that benefits from an isolated context "
    "window, or long-running work that must not block this session; never delegate "
    "simple reads, searches, commands, or small edits, and never dispatch work you are "
    "about to perform yourself.",
    "Handle BLOCKED and NEEDS_CONTEXT results explicitly: BLOCKED means the task could "
    "not be completed as dispatched — address the blocker or change the approach with a "
    "fresh task call; NEEDS_CONTEXT means required information was missing — supply it "
    "in another task_resume call.",
)


def _agent_roster(cwd: Path | None) -> str:
    """Annotated roster of the bundled, user, and project agents for the tool surface.

    Renders one line per agent discovered at the session cwd from the bundled,
    user, and project layers, so the roster names every agent a task call can
    dispatch. Any discovery failure yields an empty string; the caller falls
    back to the static bundled roster.
    """

    try:
        discovery = discover_agents(cwd or Path.cwd())
    except Exception:  # noqa: BLE001 - the tool surface must survive discovery issues
        return ""
    lines = []
    for agent in sorted(discovery.agents, key=lambda agent: agent.name):
        annotation = _PROFILE_ANNOTATIONS[agent.profile]
        lines.append(f"- {agent.name}: {one_line(agent.description)} (Tools: {annotation})")
    return "\n".join(lines)


_PROMPT_PARAMETER: dict[str, JSONValue] = {
    "type": "string",
    "minLength": 1,
    "description": "The child's task. The prompt is preserved verbatim.",
}

_TIMEOUT_PARAMETER: dict[str, JSONValue] = {
    "type": "number",
    "exclusiveMinimum": 0,
    "maximum": 10800,
    "default": 3600,
    "description": "Per-child timeout in seconds.",
}


def _task_tool_parameters(roster_text: str) -> dict[str, JSONValue]:
    """The task tool's schema: exactly the four-field new-child surface."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["prompt"],
        "properties": {
            "prompt": dict(_PROMPT_PARAMETER),
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
            "timeout_seconds": dict(_TIMEOUT_PARAMETER),
        },
    }


def _resume_tool_parameters() -> dict[str, JSONValue]:
    """The task_resume tool's schema: exactly the three-field continuation
    surface, with no agent name anywhere."""

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["prompt", "task_id"],
        "properties": {
            "prompt": dict(_PROMPT_PARAMETER),
            "task_id": {
                "type": "string",
                "minLength": 1,
                "description": "The child session id from an earlier task result to continue.",
            },
            "timeout_seconds": dict(_TIMEOUT_PARAMETER),
        },
    }


def _task_description(roster_text: str) -> str:
    """The task tool's description, in contract order: threshold one-liner,
    minimal example, inheritance default, fixed environment, roster, default
    rule, when-not-to-use, usage notes, and the task_resume pointer."""

    return "\n".join(
        (
            "Dispatch work to an isolated Tau subagent. Delegate substantive multi-step "
            "work that benefits from an isolated context window, or long-running work "
            "that must not block this session.",
            'Minimal call: {"prompt": "Find caching options"}',
            "An unpinned child resolves to this session's provider, model, and thinking "
            "level; durable pins live in the superpowers-subagent.toml config file or in "
            "an agent definition.",
            "The child spawns in this session's working directory, and agent discovery "
            "covers all layers: bundled, user, and project definitions.",
            roster_text,
            "Omit subagent_type to select general-purpose.",
            "When not to use: Simple reads, searches, commands, and small edits are your "
            "own tool calls, and you never dispatch work you are about to perform "
            "yourself. Never dispatch a task and then do the same work.",
            "Usage notes:\n" + "\n".join(f"- {note}" for note in _TASK_USAGE_NOTES),
            "To continue an existing child session, call task_resume with its task_id.",
        )
    )


_RESUME_DESCRIPTION = "\n".join(
    (
        "Continue an existing child session with task_resume. Resume only that session's "
        "own work; start a fresh task call for different work.",
        'Example: {"prompt": "Now re-check the authz paths.", "task_id": "<id from the '
        'earlier result>", "timeout_seconds": 7200}',
        "The resumed agent comes from the session-agent mapping at "
        "~/.tau/superpowers-subagent-sessions.json, which records each child session's "
        "agent name, so the call carries no agent name.",
    )
)


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
    """Set up the two task tools, session usage tracking, and the sidebar seam."""

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

    def build_executor(mode: RequestMode) -> ToolExecutor:
        async def execute(
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
                runner=runner,
                roster_text=roster_text,
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
                return await dispatcher.execute(
                    arguments, mode=mode, signal=signal, on_update=on_update
                )
            finally:
                tracker.discard_pending(tool_call_id)

        return execute

    tau.register_tool(
        AgentTool(
            name="task",
            label="task",
            description=_task_description(roster_text),
            parameters=_task_tool_parameters(roster_text),
            execute_fn=build_executor("fresh"),
            prompt_snippet="Dispatch substantive work to an isolated Tau subagent.",
            prompt_guidelines=_TASK_PROMPT_GUIDELINES,
            render_call=render_task_call,
            render_result=render_task_result,
        )
    )
    tau.register_tool(
        AgentTool(
            name="task_resume",
            label="task_resume",
            description=_RESUME_DESCRIPTION,
            parameters=_resume_tool_parameters(),
            execute_fn=build_executor("resume"),
            prompt_snippet="Continue an existing child session with a task_resume call.",
            prompt_guidelines=_RESUME_PROMPT_GUIDELINES,
            render_call=render_resume_call,
            render_result=render_task_result,
        )
    )
