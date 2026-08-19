"""Session-scoped aggregation of delegated subagent token usage and cost."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .models import ChildResult


@dataclass(frozen=True, slots=True)
class SubagentUsageTotals:
    """Cumulative subagent usage for one session, in sidebar display form."""

    runs: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0

    @property
    def has_usage(self) -> bool:
        """Whether any subagent run has reported token usage or cost."""
        return self.runs > 0

    @property
    def prompt_tokens(self) -> int:
        """Prompt input including cached and cache-written tokens.

        Mirrors the session usage section's input figure so the subagents
        section reads consistently next to it.
        """
        return self.input_tokens + self.cached_input_tokens + self.cache_write_tokens


def _add_child(totals: SubagentUsageTotals, child: ChildResult) -> SubagentUsageTotals:
    """Return ``totals`` plus one child's usage; zero-usage children add nothing."""
    usage = child.usage
    consumed = usage.input + usage.output + usage.cache_read + usage.cache_write
    if consumed <= 0 and usage.cost <= 0:
        return totals
    return SubagentUsageTotals(
        runs=totals.runs + 1,
        input_tokens=totals.input_tokens + usage.input,
        cached_input_tokens=totals.cached_input_tokens + usage.cache_read,
        cache_write_tokens=totals.cache_write_tokens + usage.cache_write,
        output_tokens=totals.output_tokens + usage.output,
        cost=totals.cost + usage.cost,
    )


class SubagentUsageTracker:
    """Aggregate child usage across task calls within the active session.

    Live updates replace an in-flight snapshot of the current call's children
    (per-child usage is cumulative, so a snapshot is never additive); a call's
    final result commits once and clears the snapshot. A call that ends without
    committing, such as a hard cancellation, discards its snapshot through
    ``discard_pending``, and a session rebind resets everything.
    """

    def __init__(self) -> None:
        self._committed = SubagentUsageTotals()
        self._active: tuple[ChildResult, ...] = ()

    def update(self, children: Sequence[ChildResult], final: bool) -> None:
        """Replace the in-flight snapshot, or commit the call's children once."""
        if final:
            for child in children:
                self._committed = _add_child(self._committed, child)
            self._active = ()
        else:
            self._active = tuple(children)

    def discard_pending(self) -> None:
        """Drop the in-flight snapshot of a call that ended without committing."""
        self._active = ()

    def reset(self) -> None:
        """Clear all totals for a new, resumed, or branched session."""
        self._committed = SubagentUsageTotals()
        self._active = ()

    @property
    def totals(self) -> SubagentUsageTotals:
        """Committed totals plus the latest in-flight snapshot."""
        totals = self._committed
        for child in self._active:
            totals = _add_child(totals, child)
        return totals
