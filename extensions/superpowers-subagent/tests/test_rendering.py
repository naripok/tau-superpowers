from __future__ import annotations

from tau_agent.messages import TextContent
from tau_agent.tools import AgentToolResult

from superpowers_subagent.rendering import render_task_call, render_task_result


def child_details(*, output: str, failed: bool = False) -> dict[str, object]:
    return {
        "agent": "worker[one]",
        "exitCode": 1 if failed else 0,
        "timedOut": False,
        "cancelled": False,
        "status": "BLOCKED" if failed else "DONE",
        "errorMessage": "planned [failure]" if failed else None,
        "messages": [
            {
                "role": "assistant",
                "content": [{"type": "text", "text": output}],
            }
        ],
    }


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


def test_result_renderer_keeps_collapsed_output_small_and_expands_full_messages() -> None:
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
    expanded = render_task_result(result, expanded=True)

    assert collapsed is not None
    assert "1/2 succeeded" in collapsed
    assert "complete" not in collapsed
    assert expanded is not None
    assert "complete \\[first] output" in expanded
    assert "planned \\[failure]" in expanded
    assert "worker\\[one]" in expanded


def test_result_renderer_falls_back_for_unknown_details_schema() -> None:
    result = AgentToolResult(content="generic", details={"schemaVersion": 2})

    assert render_task_result(result, expanded=False) is None
