"""Portable Rich-markup renderers for Task calls and results."""

from __future__ import annotations

from collections.abc import Mapping

from rich.markup import escape
from tau_agent.tools import AgentToolResult
from tau_agent.types import JSONValue


def render_task_call(arguments: Mapping[str, JSONValue]) -> str:
    """Render one concise Task invocation line for Tau frontends."""

    description = arguments.get("description")
    if isinstance(description, str) and description.strip():
        label = _one_line(description)
    else:
        label = _call_label(arguments)
    return f"▸ [bold]Task[/bold] · {escape(label)}"


def render_task_result(result: AgentToolResult, *, expanded: bool) -> str | None:
    """Render Task progress/results, exposing full child output only when expanded."""

    details = result.details
    if not isinstance(details, dict) or details.get("schemaVersion") != 1:
        return None
    mode = details.get("mode")
    raw_results = details.get("results")
    if not isinstance(mode, str) or not isinstance(raw_results, list):
        return None

    children = [child for child in raw_results if isinstance(child, dict)]
    succeeded = sum(_child_succeeded(child) for child in children)
    total = len(children)
    if total == 0:
        headline = "[yellow]•[/yellow] [bold]Task[/bold] · no child results"
    else:
        color = "green" if succeeded == total else "red"
        marker = "✓" if succeeded == total else "✗"
        headline = (
            f"[{color}]{marker}[/{color}] [bold]Task[/bold] · {escape(mode)} · "
            f"{succeeded}/{total} succeeded"
        )
    if not expanded:
        return headline

    sections = [_expanded_child(child, index) for index, child in enumerate(children, start=1)]
    if not sections:
        fallback = result.text.strip()
        return headline if not fallback else f"{headline}\n\n{escape(fallback)}"
    return headline + "\n\n" + "\n\n".join(sections)


def _call_label(arguments: Mapping[str, JSONValue]) -> str:
    tasks = arguments.get("tasks")
    if isinstance(tasks, list):
        return f"parallel · {len(tasks)} children"
    chain = arguments.get("chain")
    if isinstance(chain, list):
        noun = "step" if len(chain) == 1 else "steps"
        return f"chain · {len(chain)} {noun}"
    agent = arguments.get("agent")
    if isinstance(agent, str) and agent.strip():
        return f"single · {agent.strip()}"
    return "dispatch"


def _one_line(value: str, *, limit: int = 120) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1].rstrip() + "…"


def _child_succeeded(child: Mapping[str, object]) -> bool:
    return (
        child.get("exitCode") == 0
        and child.get("timedOut") is not True
        and child.get("cancelled") is not True
        and not child.get("errorMessage")
        and child.get("stopReason") not in {"error", "aborted"}
    )


def _expanded_child(child: Mapping[str, object], index: int) -> str:
    agent = child.get("agent")
    name = agent if isinstance(agent, str) and agent else f"child {index}"
    status = child.get("status")
    status_label = status if isinstance(status, str) and status else "UNKNOWN"
    outcome = "completed" if _child_succeeded(child) else "failed"
    heading = f"[bold]{escape(name)}[/bold] [dim]({escape(outcome)} · {escape(status_label)})[/dim]"
    output = _last_assistant_output(child.get("messages"))
    error = child.get("errorMessage")
    if isinstance(error, str) and error:
        output = f"{output}\n\nError: {error}" if output else error
    if not output:
        output = "(no output)"
    return f"{heading}\n{escape(output)}"


def _last_assistant_output(raw_messages: object) -> str:
    if not isinstance(raw_messages, list):
        return ""
    for message in reversed(raw_messages):
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            return ""
        texts: list[str] = []
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "text":
                continue
            text = block.get("text")
            if isinstance(text, str):
                texts.append(text)
        return "".join(texts)
    return ""
