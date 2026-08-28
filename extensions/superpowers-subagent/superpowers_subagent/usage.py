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
    #: Sum of catalog estimates over contributing runs, from ``UsageStats``.
    estimated_cost: float = 0.0
    #: True when at least one contributing run has a determinable cost: catalog
    #: pricing or a non-zero reported cost.
    has_determinable_cost: bool = False
    #: True when at least one contributing run is estimated from catalog rates,
    #: regardless of the estimated amount.
    has_catalog_estimate: bool = False
    #: Runs that report non-zero token usage and have no determinable cost.
    unpriced_runs: int = 0

    @property
    def has_usage(self) -> bool:
        """Whether any subagent run has token usage or a determinable cost."""
        return self.runs > 0

    @property
    def prompt_tokens(self) -> int:
        """Prompt input including cached and cache-written tokens.

        Mirrors the session usage section's input figure so the subagents
        section reads consistently next to it.
        """
        return self.input_tokens + self.cached_input_tokens + self.cache_write_tokens

    @property
    def total_cost(self) -> float:
        """Reported cost plus the catalog estimate."""
        return self.cost + self.estimated_cost


def _add_child(totals: SubagentUsageTotals, child: ChildResult) -> SubagentUsageTotals:
    """Return ``totals`` plus one child's usage; children without usage or a
    determinable cost add nothing."""
    usage = child.usage
    consumed = usage.input + usage.output + usage.cache_read + usage.cache_write
    if consumed <= 0 and usage.cost <= 0 and not usage.catalog_priced:
        return totals
    determinable = usage.catalog_priced or usage.cost > 0
    return SubagentUsageTotals(
        runs=totals.runs + 1,
        input_tokens=totals.input_tokens + usage.input,
        cached_input_tokens=totals.cached_input_tokens + usage.cache_read,
        cache_write_tokens=totals.cache_write_tokens + usage.cache_write,
        output_tokens=totals.output_tokens + usage.output,
        cost=totals.cost + usage.cost,
        estimated_cost=totals.estimated_cost + usage.estimated_cost,
        has_determinable_cost=totals.has_determinable_cost or determinable,
        has_catalog_estimate=totals.has_catalog_estimate or usage.catalog_priced,
        unpriced_runs=totals.unpriced_runs + (0 if determinable else 1),
    )


class SubagentUsageTracker:
    """Aggregate child usage across task calls within the active session.

    Each in-flight call keeps its own snapshot of the latest child results
    (per-child usage is cumulative, so a snapshot is never additive); tool call
    ids are unique, so concurrent dispatch calls cannot collide. A call's final
    result commits once and drops that call's snapshot, an uncommitted call
    discards its own snapshot through ``discard_pending``, and a session rebind
    resets everything.
    """

    def __init__(self) -> None:
        self._committed = SubagentUsageTotals()
        self._active: dict[str, tuple[ChildResult, ...]] = {}

    def update(self, call_key: str, children: Sequence[ChildResult], final: bool) -> None:
        """Replace a call's in-flight snapshot, or commit its children once."""
        if final:
            for child in children:
                self._committed = _add_child(self._committed, child)
            self._active.pop(call_key, None)
        else:
            self._active[call_key] = tuple(children)

    def discard_pending(self, call_key: str) -> None:
        """Drop one call's in-flight snapshot; committed totals are untouched."""
        self._active.pop(call_key, None)

    def reset(self) -> None:
        """Clear all totals for a new, resumed, or branched session."""
        self._committed = SubagentUsageTotals()
        self._active = {}

    @property
    def totals(self) -> SubagentUsageTotals:
        """Committed totals plus every active call's latest snapshot."""
        totals = self._committed
        for children in self._active.values():
            for child in children:
                totals = _add_child(totals, child)
        return totals
