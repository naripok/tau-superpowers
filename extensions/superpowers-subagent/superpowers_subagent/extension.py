"""Tau extension entry point for isolated subagent dispatch."""

from __future__ import annotations

import os
from collections.abc import Mapping

from tau_agent.tools import (
    AgentTool,
    AgentToolResult,
    ToolCancellationToken,
    ToolUpdateCallback,
)
from tau_agent.types import JSONValue
from tau_coding.extensions import ExtensionAPI

from .dispatch import TaskDispatcher
from .rendering import render_task_call, render_task_result
from .runner import RECURSION_GUARD, TauChildRunner

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
            "description": "Agent name for single mode.",
        },
        "task": {
            "type": "string",
            "minLength": 1,
            "description": "Complete delegated prompt for single mode.",
        },
        "cwd": {
            "type": "string",
            "description": "Child working directory for single mode.",
        },
        "tasks": {
            "type": "array",
            "minItems": 1,
            "maxItems": 8,
            "items": _TASK_ITEM_SCHEMA,
            "description": "Independent parallel tasks (at most eight).",
        },
        "chain": {
            "type": "array",
            "minItems": 1,
            "items": _TASK_ITEM_SCHEMA,
            "description": "Sequential tasks; {previous} receives complete prior output.",
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
                "the agent definition's reasoningEffort. Applied as the child's "
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


def setup(tau: ExtensionAPI) -> None:
    """Register the task tool unless this process is a child."""

    if os.environ.get(RECURSION_GUARD):
        return

    runner = TauChildRunner()

    async def execute_task(
        tool_call_id: str,
        arguments: Mapping[str, JSONValue],
        signal: ToolCancellationToken | None = None,
        on_update: ToolUpdateCallback | None = None,
    ) -> AgentToolResult:
        del tool_call_id
        dispatcher = TaskDispatcher(
            default_cwd=tau.context.cwd,
            ui=tau.context.ui,
            runner=runner,
        )
        return await dispatcher.execute(arguments, signal=signal, on_update=on_update)

    tau.register_tool(
        AgentTool(
            name="task",
            label="task",
            description=(
                "Dispatch complete tasks to isolated Tau subagents. Use agent + task for "
                "single mode, tasks for ordered parallel mode (max eight, four active), "
                "or chain for sequential work with {previous}. Bundled agents include "
                "general-purpose, implementation, code-review, and the enforced "
                "read-only profile. Project-controlled "
                "agent prompts require explicit approval."
            ),
            parameters=_TASK_PARAMETERS,
            execute_fn=execute_task,
            prompt_snippet="Dispatch work to an isolated Tau subagent.",
            prompt_guidelines=(
                "Include all required context because subagents cannot see this conversation.",
                "Use implementation for implementation work, code-review for reviews, "
                "and read-only for plain file inspection.",
                "Do not set provider, model, or reasoningEffort unless the user "
                "requests an override or a skill prescribes it.",
                "Handle BLOCKED and NEEDS_CONTEXT reports explicitly.",
            ),
            render_call=render_task_call,
            render_result=render_task_result,
        )
    )
