"""Sidebar seam tests for the accumulated subagent usage section.

These tests pin the "Sidebar subagent usage section" and "Unavailable sidebar
display degrades safely" delta requirements: placement directly below usage,
hide and omission rules, and guarded degradation of the display path.

The runtime-integration tests run the extension's real install path in this
same pytest process, so the core sidebar builder may already carry a wrapper
when these tests run; helpers here always resolve the pristine builder.
"""

from __future__ import annotations

import builtins
import io
from pathlib import Path
from typing import Any

import tau_coding.tui.widgets as widgets
from rich.console import Console
from rich.text import Text
from tau_coding.session_stats import SessionStats
from tau_coding.tui.config import TAU_DARK_THEME

from superpowers_subagent.models import ChildResult, UsageStats
from superpowers_subagent.sidebar import _WRAPPER_MARK, _inject_section, install
from superpowers_subagent.usage import SubagentUsageTotals, SubagentUsageTracker


class FakeSession:
    """Minimal SessionSummarySource stand-in for the sidebar content builder."""

    session_title = "Test session"
    session_stats = SessionStats(
        turn_count=3,
        tool_call_count=6,
        input_tokens=12000,
        cached_input_tokens=2000,
        cache_write_tokens=500,
        output_tokens=4000,
        latest_prompt_tokens=12000,
        latest_cached_input_tokens=2000,
        estimated_cost=0.12,
    )
    auto_compact_token_threshold = None
    context_files = ()
    tools = ()
    skills = ()
    prompt_templates = ()
    extension_names = ("superpowers-subagent",)
    cwd = Path("/workspace")
    provider_name = "openai"
    model = "gpt-5.6-sol"
    thinking_level = "high"
    context_window_tokens = 200_000
    has_provider_context_usage = False
    # All remaining attributes needed by the narrow-layout renderer come from
    # the SessionSummarySource protocol; the renderer reads cwd, provider_name,
    # model, thinking level, context usage, and auto-compaction threshold.


def _child(
    *,
    input: int,
    output: int,
    cost: float = 0.0,
    estimated_cost: float = 0.0,
    catalog_priced: bool = False,
) -> ChildResult:
    return ChildResult(
        agent="implementation",
        agent_source="bundled",
        task="work",
        cwd="/workspace",
        exit_code=0,
        usage=UsageStats(
            input=input,
            output=output,
            cost=cost,
            estimated_cost=estimated_cost,
            catalog_priced=catalog_priced,
        ),
    )


def _section_titles(content: Any) -> list[str]:
    """Section headers in render order; the leading title block has none."""
    titles: list[str] = []
    for section in content.summary_sections:
        if not hasattr(section, "renderables") or not section.renderables:
            continue
        header = section.renderables[0].renderable
        if isinstance(header, Text):
            titles.append(header.plain)
    return titles


def _section_body(content: Any, title: str) -> Text:
    """Body text of the sidebar section with the given title.

    The ``summary_sections`` tuple begins with a Padding title block that has
    no ``renderables``, so body lookups must index the filtered
    ``sections``/``titles`` pair rather than raw ``summary_sections`` indices.
    """
    sections = [
        section for section in content.summary_sections if getattr(section, "renderables", None)
    ]
    titles = [section.renderables[0].renderable.plain for section in sections]
    body = sections[titles.index(title)].renderables[1].renderable
    assert isinstance(body, Text)
    return body


def _base_content() -> Any:
    """A pristine sidebar summary built by the real core builder."""
    return _pristine_builder()(FakeSession(), theme=TAU_DARK_THEME)


def _pristine_builder() -> Any:
    """The true core builder, unwrapping a wrapper left by an earlier test."""
    original = widgets._build_sidebar_content
    if getattr(original, _WRAPPER_MARK, False):
        return original.__wrapped__
    return original


def test_injection_places_section_below_usage() -> None:
    """Prove the injected section sits directly below the usage section and
    shows the run count plus accumulated totals in the usage section's style."""
    tracker = SubagentUsageTracker()
    tracker.update("call-1", [_child(input=16000, output=4000, cost=0.05)], final=True)

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    titles = _section_titles(content)
    assert titles.index("subagents") == titles.index("usage") + 1
    body = _section_body(content, "subagents")
    assert "1 run" in body.plain
    assert "16k in" in body.plain
    assert "4k out" in body.plain
    assert "$0.05" in body.plain


def test_injection_counts_in_flight_runs() -> None:
    """Prove totals include the running call's latest snapshot with its runs
    counted, per the in-flight display contract."""
    tracker = SubagentUsageTracker()
    tracker.update("call-1", [_child(input=16000, output=4000)], final=True)
    tracker.update("call-1", [_child(input=10000, output=2000)], final=False)

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    body = _section_body(content, "subagents")
    assert "2 runs" in body.plain
    assert "26k in" in body.plain
    assert "6k out" in body.plain


def test_injection_omits_cost_when_unreported() -> None:
    """Prove the section keeps runs and tokens but no cost value when no child
    reported a cost."""
    tracker = SubagentUsageTracker()
    tracker.update("call-1", [_child(input=16000, output=4000)], final=True)

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    body = _section_body(content, "subagents")
    assert "1 run" in body.plain
    assert "$" not in body.plain


def test_estimate_shows_tilde_without_plus() -> None:
    """Prove a run estimated from catalog rates renders the combined cost with
    the ``~`` prefix and no ``+``, matching the usage section's estimate mark."""
    tracker = SubagentUsageTracker()
    tracker.update(
        "call-1",
        [_child(input=16000, output=4000, estimated_cost=0.03, catalog_priced=True)],
        final=True,
    )

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    assert _section_body(content, "subagents").plain == "1 run · 16k in, 4k out · ~$0.03"


def test_estimate_with_unpriced_runs_shows_tilde_and_plus() -> None:
    """Prove a priced run plus a token-bearing unpriced run renders ``~$X+``:
    the ``~`` marks the estimate and the ``+`` marks the missing amount, so the
    display never understates an incomplete total."""
    tracker = SubagentUsageTracker()
    tracker.update(
        "call-1",
        [
            _child(input=16000, output=4000, estimated_cost=0.03, catalog_priced=True),
            _child(input=1000, output=500),
        ],
        final=True,
    )

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    assert _section_body(content, "subagents").plain == "2 runs · 17k in, 4.5k out · ~$0.03+"


def test_reported_only_with_unpriced_runs_shows_plus_without_tilde() -> None:
    """Prove provider-reported cost with an unpriced run renders ``$X+``: no
    ``~`` because nothing is estimated, ``+`` because the total is incomplete."""
    tracker = SubagentUsageTracker()
    tracker.update(
        "call-1",
        [_child(input=16000, output=4000, cost=0.05), _child(input=1000, output=500)],
        final=True,
    )

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    assert _section_body(content, "subagents").plain == "2 runs · 17k in, 4.5k out · $0.05+"


def test_reported_only_without_unpriced_runs_shows_no_marks() -> None:
    """Prove a fully reported cost with every run priced renders the bare
    amount: neither mark applies."""
    tracker = SubagentUsageTracker()
    tracker.update("call-1", [_child(input=16000, output=4000, cost=0.05)], final=True)

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    assert _section_body(content, "subagents").plain == "1 run · 16k in, 4k out · $0.05"


def test_undeterminable_cost_shows_no_cost_segment() -> None:
    """Prove token-bearing runs with no pricing render the line without a cost
    segment: tokens and run count stay visible, the cost is omitted entirely."""
    tracker = SubagentUsageTracker()
    tracker.update(
        "call-1",
        [_child(input=16000, output=4000), _child(input=1000, output=500)],
        final=True,
    )

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    assert _section_body(content, "subagents").plain == "2 runs · 17k in, 4.5k out"


def test_zero_estimate_priced_run_shows_tilde_with_zero_amount() -> None:
    """Prove the ``~`` keys off catalog provenance, not the amount: a priced
    run with a ``0.0`` estimate renders ``~$0.00``."""
    tracker = SubagentUsageTracker()
    tracker.update(
        "call-1",
        [_child(input=16000, output=4000, catalog_priced=True)],
        final=True,
    )

    content = _inject_section(_base_content(), tracker.totals, TAU_DARK_THEME, widgets)

    assert _section_body(content, "subagents").plain == "1 run · 16k in, 4k out · ~$0.00"


def test_empty_totals_leave_content_unchanged() -> None:
    """Prove no subagents section appears until a run reports usage."""
    base = _base_content()

    content = _inject_section(base, SubagentUsageTotals(), TAU_DARK_THEME, widgets)

    assert content is base
    assert "subagents" not in _section_titles(content)


def test_no_usage_section_prevents_injection() -> None:
    """Prove a summary without a usage section never gains a subagents section."""
    content = widgets._SidebarContent(
        summary_sections=(widgets._sidebar_section("activity", Text("x"), theme=TAU_DARK_THEME),),
        skills=Text(""),
        prompts=Text(""),
        extensions=Text(""),
    )
    tracker = SubagentUsageTracker()
    tracker.update("call-1", [_child(input=100, output=50)], final=True)

    assert _inject_section(content, tracker.totals, TAU_DARK_THEME, widgets) is content


def test_narrow_layout_omits_section() -> None:
    """Prove the narrow-layout session summary never shows the subagents
    section even with the seam installed: it is rendered by core's own
    renderer, which the seam does not touch."""
    tracker = SubagentUsageTracker()
    tracker.update("call-1", [_child(input=100, output=50)], final=True)
    try:
        install(tracker)

        output = io.StringIO()
        Console(file=output, width=100).print(
            widgets.render_compact_session_info(FakeSession(), theme=TAU_DARK_THEME)
        )

        assert "subagents" not in output.getvalue()
    finally:
        widgets._build_sidebar_content = _pristine_builder()


def test_install_wraps_builder_and_injects() -> None:
    """Prove the installed wrapper injects the section into real sidebar
    builds, reading the tracker's current totals on every call rather than
    snapshotting them at install time."""
    tracker = SubagentUsageTracker()
    tracker.update("call-1", [_child(input=16000, output=4000, cost=0.05)], final=True)
    try:
        install(tracker)

        content = widgets._build_sidebar_content(FakeSession(), theme=TAU_DARK_THEME)

        body = _section_body(content, "subagents")
        assert "$0.05" in body.plain

        tracker.update("call-1", [_child(input=16000, output=4000, cost=0.05)], final=True)
        content = widgets._build_sidebar_content(FakeSession(), theme=TAU_DARK_THEME)

        body = _section_body(content, "subagents")
        assert "2 runs" in body.plain
        assert "$0.10" in body.plain
    finally:
        widgets._build_sidebar_content = _pristine_builder()


def test_reinstall_replaces_previous_wrapper() -> None:
    """Prove reinstalling replaces the previous generation's wrapper instead of
    wrapping it again, so the builder never grows a wrapper chain."""
    try:
        install(SubagentUsageTracker())
        first = widgets._build_sidebar_content
        install(SubagentUsageTracker())
        second = widgets._build_sidebar_content

        assert second is not first
        assert second.__wrapped__ is _pristine_builder()
    finally:
        widgets._build_sidebar_content = _pristine_builder()


def test_missing_builder_skips_install() -> None:
    """Prove an unavailable seam leaves the module untouched and never raises."""
    pristine = _pristine_builder()
    try:
        widgets._build_sidebar_content = None  # type: ignore[attr-defined]

        install(SubagentUsageTracker())

        assert widgets._build_sidebar_content is None
    finally:
        widgets._build_sidebar_content = pristine


def test_install_import_failure_degrades_silently(monkeypatch: Any) -> None:
    """Prove a Tau version without the TUI widgets module never breaks install
    (the print-mode branch of degrade-safely)."""
    real_import = builtins.__import__

    def deny_tui(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "tau_coding.tui.widgets":
            raise ImportError("no TUI in this build")
        return real_import(name, *args, **kwargs)

    pristine = _pristine_builder()
    monkeypatch.setattr(builtins, "__import__", deny_tui)
    before = widgets._build_sidebar_content
    install(SubagentUsageTracker())
    assert widgets._build_sidebar_content is before
    widgets._build_sidebar_content = pristine


def test_display_failure_during_rebuild_returns_original(monkeypatch: Any) -> None:
    """Prove a failure while building the section degrades to the normal
    sidebar summary without raising. The failure is injected into the
    extension's own injection step (the only guarded part of the wrapper),
    never into the core builder."""
    import superpowers_subagent.sidebar as sidebar_module

    tracker = SubagentUsageTracker()
    tracker.update("call-1", [_child(input=100, output=50)], final=True)
    try:
        install(tracker)

        def explode(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("boom")

        monkeypatch.setattr(sidebar_module, "_inject_section", explode)
        content = widgets._build_sidebar_content(FakeSession(), theme=TAU_DARK_THEME)
        assert "subagents" not in _section_titles(content)
    finally:
        widgets._build_sidebar_content = _pristine_builder()
