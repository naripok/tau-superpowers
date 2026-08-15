"""Rendering tests for the Task tool.

These tests pin the portable ``render_call``/``render_result`` contract that
gives the Tau TUI live visibility into running subagents: status icons, the
streamed work (assistant text plus tool calls), task text, errors, and usage
counters. They prove the renderers stay plain-text safe (no unescaped Rich
markup from child content) and that collapsed output stays small while expanded
output exposes the full details payload.
"""

from __future__ import annotations

from tau_agent.messages import TextContent
from tau_agent.tools import AgentToolResult

from superpowers_subagent.rendering import render_task_call, render_task_result


def child_details(
    *,
    output: str = "complete [first] output",
    failed: bool = False,
    task: str = "Do the work",
    status: str | None = None,
    usage: dict[str, object] | None = None,
    model: str | None = None,
    step: int | None = None,
    messages: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if messages is None:
        messages = [
            {"role": "assistant", "content": [{"type": "text", "text": output}]},
        ]
    details: dict[str, object] = {
        "agent": "worker[one]",
        "agentSource": "user",
        "task": task,
        "cwd": "/work",
        "exitCode": 1 if failed else 0,
        "timedOut": False,
        "cancelled": False,
        "messages": messages,
        "usage": usage or {},
        "status": status or ("BLOCKED" if failed else "DONE"),
    }
    if failed:
        details["errorMessage"] = "planned [failure]"
    if model is not None:
        details["model"] = model
    if step is not None:
        details["step"] = step
    return details


def single_result(child: dict[str, object], *, content: str = "(running...)") -> AgentToolResult:
    return AgentToolResult(
        content=[TextContent(text=content)],
        details={"schemaVersion": 1, "mode": "single", "planned": 1, "results": [child]},
    )


# ---------------------------------------------------------------------------
# render_call
# ---------------------------------------------------------------------------


def test_call_renderer_prefers_escaped_one_line_description() -> None:
    rendered = render_task_call(
        {
            "description": "Review [unsafe]\nmarkup",
            "tasks": [{"agent": "a", "task": "x"}],
        }
    )

    # The TUI renders tool invocations as plain text (no Rich markup), so the
    # call line must not contain markup tags.
    assert rendered == "▸ Task · Review \\[unsafe] markup"


def test_call_renderer_describes_each_mode_without_description() -> None:
    assert "single · worker" in render_task_call({"agent": "worker", "task": "x"})
    assert "parallel · 2 children" in render_task_call({"tasks": [{}, {}]})
    assert "chain · 1 step" in render_task_call({"chain": [{}]})


# ---------------------------------------------------------------------------
# Mode headlines and status icons
# ---------------------------------------------------------------------------


def test_parallel_collapsed_shows_counts_and_per_child_previews() -> None:
    result = AgentToolResult(
        content=[TextContent(text="## Summary\nsmall")],
        details={
            "schemaVersion": 1,
            "mode": "parallel",
            "results": [
                child_details(output="complete [first] output"),
                child_details(output="partial second output", failed=True),
            ],
        },
    )

    collapsed = render_task_result(result, expanded=False)

    assert collapsed is not None
    assert "1/2 succeeded" in collapsed
    assert "1 failed" in collapsed
    # Per-child headers plus a short preview of each child's work.
    assert "─── worker\\[one]" in collapsed
    assert "complete \\[first] output" in collapsed
    assert "partial second output" in collapsed
    assert "## Summary" not in collapsed


def test_expanded_parallel_is_details_driven_and_escaped() -> None:
    result = AgentToolResult(
        content=[TextContent(text="## Summary\nsmall")],
        details={
            "schemaVersion": 1,
            "mode": "parallel",
            "results": [
                child_details(output="complete [first] output"),
                child_details(output="partial second output", failed=True),
            ],
        },
    )

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "complete \\[first] output" in expanded
    assert "planned \\[failure]" in expanded
    assert "worker\\[one]" in expanded
    assert "[dim]Task:[/dim] Do the work" in expanded
    # Content is for the parent model; expanded rendering comes from details.
    assert "## Summary" not in expanded


def test_status_icons_map_each_semantic_status() -> None:
    expectations = {
        "DONE": "✓",
        "DONE_WITH_CONCERNS": "⚠",
        "BLOCKED": "✗",
        "NEEDS_CONTEXT": "?",
    }
    for status, icon in expectations.items():
        result = single_result(child_details(status=status))

        collapsed = render_task_result(result, expanded=False)

        assert collapsed is not None
        assert icon in collapsed
        assert f"· {status})" in collapsed


def test_expanded_single_shows_status_hint_for_concern_statuses() -> None:
    result = single_result(child_details(status="BLOCKED"))

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "Status: Cannot complete — check agent report for details" in expanded


def test_running_child_shows_in_flight_marker_not_status_hint() -> None:
    # A partial result mid-run: default exitCode 1, no terminal marker yet.
    running = child_details()
    running["exitCode"] = 1
    running["status"] = "BLOCKED"
    running.pop("errorMessage", None)
    result = single_result(running)

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert "…" in collapsed
    assert "(running)" in collapsed
    assert expanded is not None
    assert "(running)" in expanded
    # The stale default status must not surface a BLOCKED hint while in flight.
    assert "Cannot complete" not in expanded


# ---------------------------------------------------------------------------
# Streamed work: text and tool calls
# ---------------------------------------------------------------------------


def tool_call(name: str, arguments: dict[str, object]) -> dict[str, object]:
    return {"type": "toolCall", "name": name, "arguments": arguments}


def test_tool_calls_and_text_stream_in_message_order() -> None:
    messages: list[dict[str, object]] = [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "inspecting src/[v1]"},
                tool_call("read", {"path": "src/main.py", "offset": 10, "limit": 5}),
            ],
        },
        {
            "role": "assistant",
            "content": [
                tool_call("bash", {"command": "ls -la"}),
                {"type": "text", "text": "found the bug"},
            ],
        },
    ]
    result = single_result(child_details(messages=messages))

    expanded = render_task_result(result, expanded=True)
    collapsed = render_task_result(result, expanded=False)

    assert expanded is not None
    assert "inspecting src/\\[v1]" in expanded
    assert (
        "[dim]→ [/dim][dim]read [/dim][cyan]src/main.py[/cyan][yellow]:10-14[/yellow]" in expanded
    )
    assert "[dim]→ [/dim][dim]$ [/dim]ls -la" in expanded
    assert "found the bug" in expanded
    # Message order is preserved: text before its tool call, then the next turn.
    assert expanded.index("inspecting") < expanded.index("src/main.py")
    assert expanded.index("ls -la") < expanded.index("found the bug")
    # Collapsed shows the same stream, truncated per-item text only.
    assert collapsed is not None
    assert "ls -la" in collapsed


def test_tool_call_formatting_covers_bash_read_write_edit_and_generic() -> None:
    messages: list[dict[str, object]] = [
        {
            "role": "assistant",
            "content": [
                tool_call("bash", {"command": "x" * 80, "timeout": 30}),
                tool_call(
                    "write",
                    {"path": "new/notes.md", "content": "line one\nline two\nline three"},
                ),
                tool_call("write", {"path": "tiny.txt", "content": "single"}),
                tool_call("edit", {"path": "existing.py"}),
                tool_call("custom_tool", {"flag": "[raw]", "nested": {"a": 1}}),
            ],
        },
    ]
    result = single_result(child_details(messages=messages))

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    # Long bash commands are previewed and truncated.
    assert "$ " in expanded
    assert "…" in expanded
    assert "x" * 63 not in expanded
    # Write shows the line count only for multi-line content.
    assert "write [/dim][cyan]new/notes.md[/cyan] [dim](3 lines)[/dim]" in expanded
    assert "tiny.txt" in expanded
    assert "(1 lines)" not in expanded
    assert "edit [/dim][cyan]existing.py[/cyan]" in expanded
    # Unknown tools fall back to an escaped JSON argument preview.
    assert "custom_tool" in expanded
    assert "\\[raw]" in expanded


def test_read_range_without_limit_only_shows_start_line() -> None:
    messages: list[dict[str, object]] = [
        {"role": "assistant", "content": [tool_call("read", {"path": "app.py", "offset": 40})]},
    ]
    result = single_result(child_details(messages=messages))

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "app.py[/cyan][yellow]:40[/yellow]" in expanded


def test_read_tool_call_without_range_shows_plain_path() -> None:
    messages: list[dict[str, object]] = [
        {"role": "assistant", "content": [tool_call("read", {"path": "app.py"})]},
    ]
    result = single_result(child_details(messages=messages))

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "read [/dim][cyan]app.py[/cyan]" in expanded
    assert ":" not in expanded.split("app.py", 1)[1]


# ---------------------------------------------------------------------------
# Usage counters
# ---------------------------------------------------------------------------


def test_expanded_single_shows_usage_stats_and_model() -> None:
    usage = {
        "turns": 3,
        "input": 1200,
        "output": 34_000,
        "cacheRead": 120_000,
        "cacheWrite": 500,
        "cost": 0.0123,
        "contextTokens": 50_000,
    }
    result = single_result(
        child_details(usage=usage, model="acme/fast-1"),
    )

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "3 turns" in expanded
    assert "↑1.2k" in expanded
    assert "↓34k" in expanded
    assert "R0.1M" in expanded
    assert "W500" in expanded
    assert "$0.0123" in expanded
    assert "ctx:50k" in expanded
    assert "acme/fast-1" in expanded


def test_parallel_aggregates_usage_into_total() -> None:
    usage = {"turns": 2, "input": 1000, "output": 2000, "cost": 0.0004}
    result = AgentToolResult(
        content=[TextContent(text="Parallel: 2/2 succeeded")],
        details={
            "schemaVersion": 1,
            "mode": "parallel",
            "results": [child_details(usage=usage), child_details(usage=usage)],
        },
    )

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert "Total: 4 turns ↑2.0k ↓4.0k $0.0008" in collapsed
    assert expanded is not None
    assert "Total: 4 turns ↑2.0k ↓4.0k $0.0008" in expanded


# ---------------------------------------------------------------------------
# Collapsed size limits and hints
# ---------------------------------------------------------------------------


def test_collapsed_single_truncates_old_items_and_hints_expansion() -> None:
    messages: list[dict[str, object]] = [
        {
            "role": "assistant",
            "content": [
                tool_call("bash", {"command": f"echo step {index}"}) for index in range(12)
            ],
        },
    ]
    result = single_result(child_details(messages=messages))

    collapsed = render_task_result(result, expanded=False)

    assert collapsed is not None
    assert "… 2 earlier items" in collapsed
    assert "(Ctrl+O to expand)" in collapsed
    assert "echo step 11" in collapsed
    assert "echo step 0" not in collapsed


def test_collapsed_single_truncates_long_text_items() -> None:
    messages: list[dict[str, object]] = [
        {"role": "assistant", "content": [{"type": "text", "text": "a\nb\nc\nd\ne"}]},
    ]
    result = single_result(child_details(messages=messages))

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert "a\nb\nc" in collapsed
    assert "c\nd" not in collapsed
    assert "…" in collapsed
    assert expanded is not None
    assert "a\nb\nc\nd\ne" in expanded


def test_collapsed_failed_child_shows_error_when_no_output() -> None:
    result = single_result(child_details(messages=[], failed=True))

    collapsed = render_task_result(result, expanded=False)

    assert collapsed is not None
    assert "planned \\[failure]" in collapsed


# ---------------------------------------------------------------------------
# Live counts across planned children
# ---------------------------------------------------------------------------


def test_parallel_live_headline_counts_running_and_pending_children() -> None:
    running = child_details(output="first child working")
    running["exitCode"] = 1
    running.pop("errorMessage", None)
    result = AgentToolResult(
        content=[TextContent(text="Parallel: 1/4 done")],
        details={
            "schemaVersion": 1,
            "mode": "parallel",
            "planned": 4,
            "results": [running],
        },
    )

    collapsed = render_task_result(result, expanded=False)

    assert collapsed is not None
    assert "0/4 succeeded" in collapsed
    assert "1 running" in collapsed
    assert "3 pending" in collapsed


def test_chain_live_headline_names_current_step() -> None:
    done = child_details(output="step one done", step=1)
    running = child_details(output="step two working", step=2)
    running["exitCode"] = 1
    running.pop("errorMessage", None)
    result = AgentToolResult(
        content=[TextContent(text="Chain: step 2/3 running")],
        details={
            "schemaVersion": 1,
            "mode": "chain",
            "planned": 3,
            "results": [done, running],
        },
    )

    collapsed = render_task_result(result, expanded=False)

    assert collapsed is not None
    assert "1/3 steps" in collapsed
    assert "step 2/3 running" in collapsed


def test_chain_expanded_labels_steps_and_shows_task() -> None:
    result = AgentToolResult(
        content=[TextContent(text="Chain: 2/2 succeeded")],
        details={
            "schemaVersion": 1,
            "mode": "chain",
            "results": [
                child_details(output="first", step=1, task="Step one task"),
                child_details(output="second", step=2, task="Step two task"),
            ],
        },
    )

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "─── Step 1: worker\\[one]" in expanded
    assert "─── Step 2: worker\\[one]" in expanded
    assert "[dim]Task:[/dim] Step one task" in expanded
    assert "[dim]Task:[/dim] Step two task" in expanded


# ---------------------------------------------------------------------------
# Fallbacks and escapes
# ---------------------------------------------------------------------------


def test_result_renderer_falls_back_for_unknown_details_schema() -> None:
    result = AgentToolResult(content="generic", details={"schemaVersion": 2})

    assert render_task_result(result, expanded=False) is None


def test_empty_results_render_the_result_content_text() -> None:
    # Live multi-child updates precede the first child result, and validation
    # or approval errors never produce children: the content text is the
    # authoritative display in those windows.
    result = AgentToolResult(
        content=[TextContent(text="Parallel: 0/3 done")],
        details={"schemaVersion": 1, "mode": "parallel", "planned": 3, "results": []},
    )

    assert render_task_result(result, expanded=False) == "Parallel: 0/3 done"
    assert render_task_result(result, expanded=True) == "Parallel: 0/3 done"
