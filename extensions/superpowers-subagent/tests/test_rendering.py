"""Rendering tests for the Task tool.

These tests pin the portable ``render_call``/``render_result`` contract that
gives the Tau TUI live visibility into running subagents: status icons, the
streamed work (assistant text plus tool calls), task text, errors, and usage
counters. They prove the renderers stay plain-text safe (no unescaped Rich
markup from child content), that any child count renders as one frame of
self-contained child components, and that collapsed output stays small while
expanded output exposes the full details payload.
"""

from __future__ import annotations

from tau_agent.messages import TextContent
from tau_agent.tools import AgentToolResult

from superpowers_subagent.rendering import render_task_call, render_task_result


def child_details(
    *,
    output: str = "complete [first] output",
    agent: str = "worker[one]",
    failed: bool = False,
    task: str = "Do the work",
    status: str | None = None,
    usage: dict[str, object] | None = None,
    model: str | None = None,
    messages: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if messages is None:
        messages = [
            {"role": "assistant", "content": [{"type": "text", "text": output}]},
        ]
    details: dict[str, object] = {
        "agent": agent,
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
    return details


def task_result(
    children: list[dict[str, object]],
    *,
    content: str = "work in progress",
    planned: int | None = None,
    schema_version: int = 2,
) -> AgentToolResult:
    details: dict[str, object] = {"schemaVersion": schema_version, "results": children}
    if planned is not None:
        details["planned"] = planned
    return AgentToolResult(content=[TextContent(text=content)], details=details)


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


def test_call_renderer_labels_from_task_count() -> None:
    assert render_task_call({"tasks": [{}]}) == "▸ Task · 1 child"
    assert render_task_call({"tasks": [{}, {}, {}]}) == "▸ Task · 3 children"
    assert render_task_call({}) == "▸ Task · dispatch"


# ---------------------------------------------------------------------------
# Frame headline and child components
# ---------------------------------------------------------------------------


def test_frame_renders_single_child_as_one_component() -> None:
    result = task_result([child_details(output="complete [first] output")], content="done")

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert "[bold]task[/bold] · 1/1 succeeded" in collapsed
    assert "─── worker\\[one]" in collapsed
    assert "complete \\[first] output" in collapsed
    # A single child: no aggregate usage line.
    assert "Total:" not in collapsed
    assert expanded is not None
    assert "[bold]task[/bold] · 1/1 succeeded" in expanded
    assert "[dim]Task:[/dim] Do the work" in expanded
    assert "complete \\[first] output" in expanded
    assert "Total:" not in expanded


def test_frame_renders_multiple_children_in_order_with_total() -> None:
    usage = {"turns": 2, "input": 1000, "output": 2000, "cost": 0.0004}
    result = task_result(
        [
            child_details(agent="alpha", output="complete [first] output", usage=usage),
            child_details(agent="beta", output="partial second output", failed=True, usage=usage),
        ],
        content="done",
    )

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert "[bold]task[/bold] · 1/2 succeeded" in collapsed
    assert "1 failed" in collapsed
    assert collapsed.index("─── alpha") < collapsed.index("─── beta")
    assert "Total:" in collapsed
    assert expanded is not None
    assert "[bold]task[/bold] · 1/2 succeeded" in expanded
    assert "Total:" in expanded


def test_live_headline_counts_running_and_pending_children() -> None:
    running = child_details(output="first child working")
    running["exitCode"] = 1
    running.pop("errorMessage", None)
    result = task_result([running], planned=4, content="0/4 done")

    collapsed = render_task_result(result, expanded=False)

    assert collapsed is not None
    assert "[bold]task[/bold] · 0/4 succeeded" in collapsed
    assert "1 running" in collapsed
    assert "3 pending" in collapsed


def test_expanded_component_shows_task_error_hint_and_full_stream() -> None:
    messages: list[dict[str, object]] = [
        {
            "role": "assistant",
            "content": [tool_call("bash", {"command": f"echo step {index}"}) for index in range(7)],
        },
    ]
    result = task_result(
        [child_details(messages=messages, failed=True, status="BLOCKED")],
        content="0/1 succeeded",
    )

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    # The collapsed component truncates the stream to the newest items.
    assert "… 2 earlier items" in collapsed
    assert "echo step 6" in collapsed
    assert "echo step 0" not in collapsed
    assert "(Ctrl+O to expand)" in collapsed
    assert expanded is not None
    assert "Status: Cannot complete — check agent report for details" in expanded
    assert "[red]Error: planned \\[failure][/red]" in expanded
    assert "[dim]Task:[/dim] Do the work" in expanded
    for index in range(7):
        assert f"echo step {index}" in expanded


def test_status_icons_map_each_semantic_status() -> None:
    expectations = {
        "DONE": "✓",
        "DONE_WITH_CONCERNS": "⚠",
        "BLOCKED": "✗",
        "NEEDS_CONTEXT": "?",
    }
    for status, icon in expectations.items():
        result = task_result([child_details(status=status)])

        collapsed = render_task_result(result, expanded=False)

        assert collapsed is not None
        assert icon in collapsed


def test_expanded_component_shows_status_hint_for_concern_statuses() -> None:
    result = task_result([child_details(status="BLOCKED")], content="done")

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "Status: Cannot complete — check agent report for details" in expanded


def test_running_child_shows_in_flight_marker_not_status_hint() -> None:
    # A partial result mid-run: default exitCode 1, no terminal marker yet.
    running = child_details()
    running["exitCode"] = 1
    running["status"] = "BLOCKED"
    running.pop("errorMessage", None)
    result = task_result([running])

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert "…" in collapsed
    assert "(running)" in collapsed
    assert expanded is not None
    assert "(running)" in expanded
    assert "Cannot complete" not in expanded
    # The stale default status must not surface a BLOCKED hint while in flight.
    assert "Status:" not in expanded


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
    result = task_result([child_details(messages=messages)])

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
    result = task_result([child_details(messages=messages)])

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
    result = task_result([child_details(messages=messages)])

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "app.py[/cyan][yellow]:40[/yellow]" in expanded


def test_read_tool_call_without_range_shows_plain_path() -> None:
    messages: list[dict[str, object]] = [
        {"role": "assistant", "content": [tool_call("read", {"path": "app.py"})]},
    ]
    result = task_result([child_details(messages=messages)])

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
    result = task_result([child_details(usage=usage, model="acme/fast-1")], content="done")

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


def test_usage_line_shows_reasoning_effort_next_to_model() -> None:
    usage = {"turns": 1, "input": 10, "output": 20, "cost": 0.0}
    details = child_details(usage=usage, model="acme/fast-1")
    details["reasoningEffort"] = "xhigh"
    result = task_result([details], content="done")

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "acme/fast-1 (xhigh)" in expanded


def test_parallel_aggregates_usage_into_total() -> None:
    usage = {"turns": 2, "input": 1000, "output": 2000, "cost": 0.0004}
    result = task_result(
        [child_details(usage=usage), child_details(usage=usage)],
        content="2/2 succeeded",
    )

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert "Total: 4 turns ↑2.0k ↓4.0k $0.0008" in collapsed
    assert expanded is not None
    assert "Total: 4 turns ↑2.0k ↓4.0k $0.0008" in expanded


def test_usage_line_shows_estimated_cost_with_tilde() -> None:
    # Details from collection carry estimatedCost without a provider-reported
    # cost, so the line must show the estimate marked as such.
    usage = {"turns": 1, "input": 10, "output": 20, "estimatedCost": 0.4231}
    result = task_result([child_details(usage=usage, model="acme/fast-1")], content="done")

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "1 turn ↑10 ↓20 ~$0.4231 acme/fast-1" in expanded


def test_usage_line_shows_reported_cost_without_tilde() -> None:
    # A provider-reported cost alone is exact, so the line must not carry the
    # estimate mark.
    usage = {"turns": 1, "input": 10, "output": 20, "cost": 0.2}
    result = task_result([child_details(usage=usage, model="acme/fast-1")], content="done")

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "1 turn ↑10 ↓20 $0.2000 acme/fast-1" in expanded


def test_usage_line_combines_reported_and_estimated_cost() -> None:
    # The rendered amount must be the sum of both cost kinds when both exist,
    # marked with ~ because an estimated cost contributes.
    usage = {"turns": 1, "input": 10, "output": 20, "cost": 0.2, "estimatedCost": 0.4231}
    result = task_result([child_details(usage=usage, model="acme/fast-1")], content="done")

    expanded = render_task_result(result, expanded=True)

    assert expanded is not None
    assert "1 turn ↑10 ↓20 ~$0.6231 acme/fast-1" in expanded


def test_usage_line_omits_zero_cost() -> None:
    # Zero or missing costs must render no cost segment, matching the old
    # line shape for details produced before estimation existed.
    for usage in (
        {"turns": 1, "input": 10, "output": 20, "cost": 0.0, "estimatedCost": 0.0},
        {"turns": 1, "input": 10, "output": 20},
    ):
        result = task_result([child_details(usage=usage, model="acme/fast-1")], content="done")

        expanded = render_task_result(result, expanded=True)

        assert expanded is not None
        assert "1 turn ↑10 ↓20 acme/fast-1" in expanded
        assert "$" not in expanded


def test_total_line_sums_estimated_cost_with_tilde() -> None:
    # The aggregate line must combine each child's estimated cost and keep the
    # ~ mark, since only estimates contribute.
    result = task_result(
        [
            child_details(
                agent="alpha",
                usage={"turns": 1, "input": 10, "output": 20, "estimatedCost": 0.1},
            ),
            child_details(
                agent="beta",
                usage={"turns": 1, "input": 10, "output": 20, "estimatedCost": 0.3231},
            ),
        ],
        content="done",
    )

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert "Total: 2 turns ↑20 ↓40 ~$0.4231" in collapsed
    assert expanded is not None
    assert "Total: 2 turns ↑20 ↓40 ~$0.4231" in expanded


def test_frame_child_sections_show_estimated_cost() -> None:
    # Both collapsed and expanded frames must show the combined cost per child
    # and on the Total line, so costs are visible while children run.
    usage = {"turns": 1, "input": 10, "output": 20, "cost": 0.1, "estimatedCost": 0.3231}
    result = task_result(
        [child_details(agent="alpha", usage=usage), child_details(agent="beta", usage=usage)],
        content="done",
    )

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert collapsed.count("~$") == 3
    assert "1 turn ↑10 ↓20 ~$0.4231" in collapsed
    assert "Total: 2 turns ↑20 ↓40 ~$0.8462" in collapsed
    assert expanded is not None
    assert expanded.count("~$") == 3
    assert "1 turn ↑10 ↓20 ~$0.4231" in expanded
    assert "Total: 2 turns ↑20 ↓40 ~$0.8462" in expanded


# ---------------------------------------------------------------------------
# Collapsed size limits and hints
# ---------------------------------------------------------------------------


def test_collapsed_truncates_old_items_and_hints_expansion() -> None:
    messages: list[dict[str, object]] = [
        {
            "role": "assistant",
            "content": [
                tool_call("bash", {"command": f"echo step {index}"}) for index in range(12)
            ],
        },
    ]
    result = task_result([child_details(messages=messages)], content="done")

    collapsed = render_task_result(result, expanded=False)

    assert collapsed is not None
    assert "… 7 earlier items" in collapsed
    assert "(Ctrl+O to expand)" in collapsed
    assert "echo step 11" in collapsed
    assert "echo step 0" not in collapsed


def test_collapsed_truncates_long_text_items() -> None:
    messages: list[dict[str, object]] = [
        {"role": "assistant", "content": [{"type": "text", "text": "a\nb\nc\nd\ne"}]},
    ]
    result = task_result([child_details(messages=messages)], content="done")

    collapsed = render_task_result(result, expanded=False)
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert "a\nb\nc" in collapsed
    assert "c\nd" not in collapsed
    assert "…" in collapsed
    assert expanded is not None
    assert "a\nb\nc\nd\ne" in expanded


def test_collapsed_failed_child_shows_error_when_no_output() -> None:
    result = task_result([child_details(messages=[], failed=True)], content="0/1 succeeded")

    collapsed = render_task_result(result, expanded=False)

    assert collapsed is not None
    assert "planned \\[failure]" in collapsed


# ---------------------------------------------------------------------------
# Fallbacks and escapes
# ---------------------------------------------------------------------------


def test_result_renderer_ignores_details_with_old_schema_version() -> None:
    result = AgentToolResult(
        content="generic",
        details={"schemaVersion": 1, "mode": "parallel", "results": [child_details()]},
    )

    assert render_task_result(result, expanded=False) is None
    assert render_task_result(result, expanded=True) is None


def test_result_renderer_ignores_details_without_results_list() -> None:
    result = AgentToolResult(content="generic", details={"schemaVersion": 2})

    assert render_task_result(result, expanded=False) is None


def test_empty_results_render_the_result_content_text() -> None:
    # Live updates precede the first child result, and validation or approval
    # errors never produce children: the content text is the authoritative
    # display in those windows.
    result = task_result([], content="0/3 done", planned=3)

    assert render_task_result(result, expanded=False) == "0/3 done"
    assert render_task_result(result, expanded=True) == "0/3 done"


def test_empty_results_with_empty_content_fall_back_to_task_bullet() -> None:
    result = task_result([], content="")

    assert render_task_result(result, expanded=False) == "[yellow]•[/yellow] [bold]Task[/bold]"
    assert render_task_result(result, expanded=True) == "[yellow]•[/yellow] [bold]Task[/bold]"
