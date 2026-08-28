"""Portable Rich-markup renderers for Task calls and results.

``render_task_result`` mirrors the historical pi extension's live visibility:
while children run, Tau re-renders the tool row after every accepted child
message, and this renderer turns the accumulated details into a streaming view
of each child's status, tool calls, and usage. Any child count renders as one
frame: a counts headline plus one self-contained child component per child.
Collapsed output stays compact; expanded output shows each child's full work
stream.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from typing import Literal

from rich.markup import escape
from tau_agent.tools import AgentToolResult
from tau_agent.types import JSONValue

COLLAPSED_CHILD_ITEM_COUNT = 5
_TEXT_PREVIEW_LINES = 3
_TOOL_PREVIEW_LIMIT = 60
_JSON_PREVIEW_LIMIT = 50
_EXPAND_HINT = "[dim](Ctrl+O to expand)[/dim]"
_RUNNING_ICON = "[dim]…[/dim]"

# (kind, payload) display items, in message order, so the live view reads as a
# narrative: what the child said, then which tool it called.
TextItem = tuple[Literal["text"], str]
ToolItem = tuple[Literal["tool"], str, dict[str, JSONValue]]
DisplayItem = TextItem | ToolItem
ChildState = Literal["running", "succeeded", "failed"]

_STATUS_ICONS: dict[str, str] = {
    "DONE": "[green]✓[/green]",
    "DONE_WITH_CONCERNS": "[yellow]⚠[/yellow]",
    "BLOCKED": "[red]✗[/red]",
    "NEEDS_CONTEXT": "[dim]?[/dim]",
}

_STATUS_HINTS: dict[str, str] = {
    "NEEDS_CONTEXT": "Provide missing context and re-dispatch",
    "BLOCKED": "Cannot complete — check agent report for details",
    "DONE_WITH_CONCERNS": "Completed with caveats — review concerns above",
}


def render_task_call(arguments: Mapping[str, JSONValue]) -> str:
    """Render one concise Task invocation line for Tau frontends.

    Tau frontends render tool invocations as plain text (Rich markup is only
    parsed for ``render_result`` output), so this line must not contain tags.
    """

    description = arguments.get("description")
    if isinstance(description, str) and description.strip():
        label = _one_line(description)
    else:
        label = _call_label(arguments)
    return f"▸ Task · {escape(label)}"


def render_task_result(result: AgentToolResult, *, expanded: bool) -> str | None:
    """Render live Task progress and final results from schema-v2 details."""

    details = result.details
    if not isinstance(details, dict) or details.get("schemaVersion") != 2:
        return None
    raw_results = details.get("results")
    if not isinstance(raw_results, list):
        return None

    children = [child for child in raw_results if isinstance(child, dict)]
    if not children:
        return _empty_render(result)

    planned = _planned_count(details, len(children))
    headline = _headline(children, planned)
    if not expanded:
        return _collapsed_frame(headline, children)
    return _expanded_frame(headline, children)


# ---------------------------------------------------------------------------
# Empty and headline rendering
# ---------------------------------------------------------------------------


def _empty_render(result: AgentToolResult) -> str:
    """Render the update/final content when details carry no child results.

    Live updates sometimes precede the first child result, and validation or
    approval failures never produce children; in both cases ``content`` is the
    authoritative text.
    """

    fallback = result.text.strip()
    if fallback:
        return escape(fallback)
    return "[yellow]•[/yellow] [bold]Task[/bold]"


def _planned_count(details: Mapping[str, object], known: int) -> int | None:
    planned = details.get("planned")
    if isinstance(planned, int) and not isinstance(planned, bool) and planned > 0:
        return max(planned, known)
    return None


def _headline(children: Sequence[Mapping[str, object]], planned: int | None) -> str:
    states = [_child_state(child) for child in children]
    total = planned if planned is not None else len(children)
    running = states.count("running")
    succeeded = states.count("succeeded")
    failed = states.count("failed")
    pending = max(total - len(children), 0) if planned is not None else 0

    icon = _RUNNING_ICON if running else ("[red]✗[/red]" if failed else "[green]✓[/green]")
    text = f"{icon} [bold]task[/bold] · {succeeded}/{total} succeeded"
    if failed:
        text += f" · {failed} failed"
    if running:
        text += f" · {running} running"
    if pending:
        text += f" · {pending} pending"
    return text


# ---------------------------------------------------------------------------
# Frame rendering
# ---------------------------------------------------------------------------


def _collapsed_frame(headline: str, children: Sequence[Mapping[str, object]]) -> str:
    lines = [headline]
    any_truncated = False
    for index, child in enumerate(children, start=1):
        body, truncated = _child_component(child, index, expanded=False)
        lines.append(body)
        any_truncated = any_truncated or truncated
    if len(children) > 1:
        total = _aggregate_usage(children)
        if total:
            lines.append(f"[dim]Total: {total}[/dim]")
    if any_truncated:
        lines.append(_EXPAND_HINT)
    return "\n".join(lines)


def _expanded_frame(headline: str, children: Sequence[Mapping[str, object]]) -> str:
    sections = [headline]
    for index, child in enumerate(children, start=1):
        body, _ = _child_component(child, index, expanded=True)
        sections.append(body)
    if len(children) > 1:
        total = _aggregate_usage(children)
        if total:
            sections.append(f"[dim]Total: {total}[/dim]")
    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Child component
# ---------------------------------------------------------------------------


def _child_component(
    child: Mapping[str, object],
    index: int,
    *,
    expanded: bool,
) -> tuple[str, bool]:
    """Render one self-contained child component; ``True`` means the collapsed
    work stream was truncated and the frame should offer the expand hint."""

    state = _child_state(child)
    header = f"[dim]─── {escape(_child_label(child, index))}[/dim] {_status_icon(child, state)}"
    if state == "running":
        header += " [dim](running)[/dim]"
    lines = [header]
    truncated = False
    items = _display_items(child.get("messages"))
    if expanded:
        hint = _status_hint(child.get("status"))
        if hint and state != "running":
            lines.append(f"[dim]Status: {hint}[/dim]")
        error = _error_text(child)
        if error:
            lines.append(f"[red]Error: {escape(error)}[/red]")
        task = child.get("task")
        if isinstance(task, str) and task.strip():
            lines.append(f"[dim]Task:[/dim] {escape(task.strip())}")
        if items:
            body, _ = _render_items(items, None, expanded=True)
            lines.append(body)
        else:
            lines.append("[dim](no output)[/dim]")
    else:
        if items:
            body, truncated = _render_items(items, COLLAPSED_CHILD_ITEM_COUNT, expanded=False)
            lines.append(body)
        else:
            error = _error_text(child)
            if error:
                lines.append(f"[red]{escape(error)}[/red]")
            else:
                lines.append("[dim](no output)[/dim]")
    usage = _usage_line(child.get("usage"), child.get("model"), child.get("reasoningEffort"))
    if usage:
        lines.append(usage)
    return "\n".join(lines), truncated


# ---------------------------------------------------------------------------
# Child helpers
# ---------------------------------------------------------------------------


def _child_state(child: Mapping[str, object]) -> ChildState:
    """Classify a child as running, succeeded, or failed from partial details.

    A child is running while its process has not been reaped: the default
    ``exitCode`` of 1 plus no terminal marker. Final results always carry an
    exit code, an error message, or a terminal stop reason.
    """

    if (
        child.get("exitCode") == 1
        and child.get("timedOut") is not True
        and child.get("cancelled") is not True
        and not _terminal_stop_reason(child)
        and child.get("errorMessage") is None
    ):
        return "running"
    return "succeeded" if _child_succeeded(child) else "failed"


def _child_succeeded(child: Mapping[str, object]) -> bool:
    return (
        child.get("exitCode") == 0
        and child.get("timedOut") is not True
        and child.get("cancelled") is not True
        and not child.get("errorMessage")
        and not _terminal_stop_reason(child)
    )


def _terminal_stop_reason(child: Mapping[str, object]) -> bool:
    reason = child.get("stopReason")
    return reason in {"error", "aborted"} if isinstance(reason, str) else False


def _status_icon(child: Mapping[str, object], state: ChildState) -> str:
    if state == "running":
        return _RUNNING_ICON
    status = child.get("status")
    if isinstance(status, str):
        icon = _STATUS_ICONS.get(status)
        if icon is not None:
            return icon
    return "[green]✓[/green]" if state == "succeeded" else "[red]✗[/red]"


def _status_hint(status: object) -> str:
    if isinstance(status, str):
        return _STATUS_HINTS.get(status, "")
    return ""


def _child_label(child: Mapping[str, object], index: int) -> str:
    return _agent_name(child, index)


def _agent_name(child: Mapping[str, object], index: int) -> str:
    agent = child.get("agent")
    return agent if isinstance(agent, str) and agent else f"child {index}"


def _error_text(child: Mapping[str, object]) -> str:
    error = child.get("errorMessage")
    return error if isinstance(error, str) and error else ""


# ---------------------------------------------------------------------------
# Display items
# ---------------------------------------------------------------------------


def _display_items(raw_messages: object) -> list[DisplayItem]:
    """Extract the child's work stream: assistant text and tool calls in order."""

    if not isinstance(raw_messages, list):
        return []
    items: list[DisplayItem] = []
    for message in raw_messages:
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str) and text:
                    items.append(("text", text))
            elif block.get("type") == "toolCall":
                name = block.get("name")
                arguments = block.get("arguments")
                if isinstance(name, str) and name:
                    args = arguments if isinstance(arguments, dict) else {}
                    items.append(("tool", name, args))
    return items


def _render_items(
    items: list[DisplayItem],
    limit: int | None,
    *,
    expanded: bool,
) -> tuple[str, bool]:
    """Render display items, returning the markup and whether anything was cut."""

    to_show = items if limit is None else items[-limit:]
    skipped = len(items) - len(to_show)
    lines: list[str] = []
    if skipped:
        noun = "item" if skipped == 1 else "items"
        lines.append(f"[dim]… {skipped} earlier {noun}[/dim]")
    for item in to_show:
        match item:
            case ("text", text):
                lines.append(_render_text_item(text, expanded=expanded))
            case ("tool", name, args):
                lines.append(f"[dim]→ [/dim]{_format_tool_call(name, args)}")
    return "\n".join(lines), skipped > 0


def _render_text_item(text: str, *, expanded: bool) -> str:
    if expanded:
        return escape(text)
    lines = text.splitlines()
    preview = "\n".join(lines[:_TEXT_PREVIEW_LINES])
    if len(lines) > _TEXT_PREVIEW_LINES:
        return f"{escape(preview)}\n[dim]…[/dim]"
    return escape(preview)


# ---------------------------------------------------------------------------
# Tool call formatting
# ---------------------------------------------------------------------------


def _format_tool_call(name: str, args: Mapping[str, JSONValue]) -> str:
    if name == "bash":
        command = args.get("command")
        preview = _preview(command if isinstance(command, str) else "…", _TOOL_PREVIEW_LIMIT)
        return f"[dim]$ [/dim]{escape(preview)}"
    if name == "read":
        line = f"[dim]read [/dim]{_path_markup(args)}"
        range_markup = _read_range_markup(args)
        return f"{line}{range_markup}" if range_markup else line
    if name == "write":
        path = _path_markup(args)
        content = args.get("content")
        line_count = len(content.split("\n")) if isinstance(content, str) else 0
        if line_count > 1:
            return f"[dim]write [/dim]{path} [dim]({line_count} lines)[/dim]"
        return f"[dim]write [/dim]{path}"
    if name == "edit":
        return f"[dim]edit [/dim]{_path_markup(args)}"
    preview = _preview(json.dumps(args, ensure_ascii=False, sort_keys=True), _JSON_PREVIEW_LIMIT)
    return f"[cyan]{escape(name)}[/cyan][dim] {escape(preview)}[/dim]"


def _path_markup(args: Mapping[str, JSONValue]) -> str:
    raw_path = args.get("path")
    path = raw_path if isinstance(raw_path, str) and raw_path else "…"
    return f"[cyan]{escape(_shorten_path(path))}[/cyan]"


def _read_range_markup(args: Mapping[str, JSONValue]) -> str:
    offset = args.get("offset")
    limit = args.get("limit")
    start = offset if isinstance(offset, int) and not isinstance(offset, bool) else None
    count = limit if isinstance(limit, int) and not isinstance(limit, bool) else None
    if start is None and count is None:
        return ""
    start_line = start if start is not None else 1
    if count is None:
        return f"[yellow]:{start_line}[/yellow]"
    return f"[yellow]:{start_line}-{start_line + count - 1}[/yellow]"


def _shorten_path(path: str) -> str:
    home = os.path.expanduser("~")
    if home and path.startswith(home):
        return f"~{path[len(home) :]}"
    return path


def _preview(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# Usage formatting
# ---------------------------------------------------------------------------


def _usage_line(usage: object, model: object, reasoning_effort: object = None) -> str:
    """Render one child's usage counters; the cost segment shows reported plus
    estimated cost, marked with ``~`` when any estimated cost contributes."""

    if not isinstance(usage, dict):
        return ""
    parts: list[str] = []
    turns = usage.get("turns")
    if isinstance(turns, int) and not isinstance(turns, bool) and turns > 0:
        parts.append(f"{turns} turn{'s' if turns > 1 else ''}")
    for key, prefix in (("input", "↑"), ("output", "↓"), ("cacheRead", "R"), ("cacheWrite", "W")):
        value = _positive_number(usage.get(key))
        if value > 0:
            parts.append(f"{prefix}{_format_tokens(value)}")
    reported = _positive_number(usage.get("cost"))
    estimated = _positive_number(usage.get("estimatedCost"))
    total = reported + estimated
    if total > 0:
        mark = "~" if estimated > 0 else ""
        parts.append(f"{mark}${total:.4f}")
    context = _positive_number(usage.get("contextTokens"))
    if context > 0:
        parts.append(f"ctx:{_format_tokens(context)}")
    if isinstance(model, str) and model and model != "unknown":
        if isinstance(reasoning_effort, str) and reasoning_effort:
            parts.append(escape(f"{model} ({reasoning_effort})"))
        else:
            parts.append(escape(model))
    return " ".join(parts)


def _aggregate_usage(children: Sequence[Mapping[str, object]]) -> str:
    totals = {
        "turns": 0,
        "input": 0.0,
        "output": 0.0,
        "cacheRead": 0.0,
        "cacheWrite": 0.0,
        "cost": 0.0,
        "estimatedCost": 0.0,
    }
    for child in children:
        usage = child.get("usage")
        if not isinstance(usage, dict):
            continue
        totals["turns"] += int(_positive_number(usage.get("turns")))
        for key in ("input", "output", "cacheRead", "cacheWrite", "cost", "estimatedCost"):
            totals[key] += _positive_number(usage.get(key))
    return _usage_line(totals, None)


def _positive_number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    return float(value) if value > 0 else 0.0


def _format_tokens(count: float) -> str:
    if count < 1000:
        return str(int(count))
    if count < 10_000:
        return f"{count / 1000:.1f}k"
    if count < 100_000:
        return f"{round(count / 1000)}k"
    return f"{count / 1_000_000:.1f}M"


# ---------------------------------------------------------------------------
# Call label helpers
# ---------------------------------------------------------------------------


def _call_label(arguments: Mapping[str, JSONValue]) -> str:
    tasks = arguments.get("tasks")
    if isinstance(tasks, list):
        count = len(tasks)
        return "1 child" if count == 1 else f"{count} children"
    return "dispatch"


def _one_line(value: str, *, limit: int = 120) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"
