"""Guarded sidebar integration showing accumulated subagent usage.

Tau 0.3 exposes no public extension point for sidebar content: the sidebar
summary is built by core from session stats. This module therefore wraps the
TUI's internal sidebar content builder (``tau_coding.tui.widgets``), the one
function through which every sidebar summary is constructed, and splices a
``subagents`` section below the ``usage`` section. Every seam step is guarded:
when an expected part is missing or a build fails, the original summary is
returned unchanged. Aggregation and dispatch never depend on this module.
"""

from __future__ import annotations

import dataclasses
import functools
from typing import Any

from .usage import SubagentUsageTotals, SubagentUsageTracker

_SECTION_TITLE = "subagents"
_USAGE_TITLE = "usage"
_WRAPPER_MARK = "_superpowers_subagent_wrapper"


def install(tracker: SubagentUsageTracker) -> None:
    """Wrap the TUI sidebar content builder to include the tracker's section.

    Reinstalling replaces a wrapper from a previous load generation instead of
    wrapping it again, so the builder never grows a wrapper chain. When the
    seam is missing, nothing is changed.
    """
    try:
        import tau_coding.tui.widgets as widgets
    except Exception:
        return
    original = getattr(widgets, "_build_sidebar_content", None)
    if not callable(original):
        return
    if getattr(original, _WRAPPER_MARK, False):
        original = getattr(original, "__wrapped__", original)
    try:
        widgets._build_sidebar_content = _make_wrapper(original, tracker, widgets)
    except Exception:
        return


def _make_wrapper(
    original: Any,
    tracker: SubagentUsageTracker,
    widgets: Any,
) -> Any:
    """Build the guarded wrapper bound to one tracker and widgets module."""
    default_theme = widgets.TAU_DARK_THEME

    @functools.wraps(original)
    def wrapped(session: object, *args: Any, **kwargs: Any) -> Any:
        content = original(session, *args, **kwargs)
        theme = kwargs.get("theme", default_theme)
        try:
            return _inject_section(content, tracker.totals, theme, widgets)
        except Exception:
            return content

    setattr(wrapped, _WRAPPER_MARK, True)
    return wrapped


def _inject_section(
    content: Any,
    totals: SubagentUsageTotals,
    theme: Any,
    widgets: Any,
) -> Any:
    """Return the sidebar content with the subagents section, or input unchanged."""
    if not totals.has_usage:
        return content
    sections = content.summary_sections
    index = _usage_section_index(sections)
    if index is None:
        return content
    section = widgets._sidebar_section(
        _SECTION_TITLE,
        _section_body(totals, theme, widgets),
        theme=theme,
    )
    return dataclasses.replace(
        content,
        summary_sections=(*sections[: index + 1], section, *sections[index + 1 :]),
    )


def _usage_section_index(sections: Any) -> int | None:
    """Index of the sidebar's usage section, found by its header text."""
    for index, section in enumerate(sections):
        try:
            header = section.renderables[0].renderable
        except Exception:
            continue
        if getattr(header, "plain", None) == _USAGE_TITLE:
            return index
    return None


def _section_body(totals: SubagentUsageTotals, theme: Any, widgets: Any) -> Any:
    """Build the section text in the usage section's own style."""
    label = "1 run" if totals.runs == 1 else f"{totals.runs} runs"
    body = widgets.Text(style=theme.completion_description)
    body.append(f"{label} · ")
    body.append(f"{widgets._compact_usage_count(totals.prompt_tokens)} in, ")
    body.append(f"{widgets._compact_usage_count(totals.output_tokens)} out")
    if totals.cost > 0:
        body.append(" · ")
        # Provider-reported value: no estimation tilde, matching the per-child widget.
        body.append(widgets._format_cost(totals.cost))
    return body
