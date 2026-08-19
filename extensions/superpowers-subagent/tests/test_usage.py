"""Tracker tests for session-scoped subagent usage aggregation.

These tests pin the "Session-scoped subagent usage aggregation" delta
requirement: snapshot replacement semantics, exactly-once commits, zero-usage
children, partial usage after process failure, rebind resets, and cost
handling.
"""

from __future__ import annotations

from superpowers_subagent.models import ChildResult, UsageStats
from superpowers_subagent.usage import SubagentUsageTotals, SubagentUsageTracker


def _child(
    *,
    input: int = 0,
    output: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    cost: float = 0.0,
    timed_out: bool = False,
) -> ChildResult:
    return ChildResult(
        agent="implementation",
        agent_source="bundled",
        task="work",
        cwd="/workspace",
        exit_code=1 if timed_out else 0,
        timed_out=timed_out,
        usage=UsageStats(
            input=input,
            output=output,
            cache_read=cache_read,
            cache_write=cache_write,
            cost=cost,
        ),
    )


def test_tracker_starts_empty() -> None:
    """Prove a fresh tracker reports no usage and no runs."""
    tracker = SubagentUsageTracker()

    totals = tracker.totals

    assert totals.runs == 0
    assert totals.input_tokens == 0
    assert totals.output_tokens == 0
    assert totals.cached_input_tokens == 0
    assert totals.cache_write_tokens == 0
    assert totals.cost == 0.0
    assert totals.has_usage is False


def test_live_updates_replace_the_snapshot() -> None:
    """Prove live snapshots replace rather than accumulate: a child's usage is
    cumulative over its own messages, so totals must show the latest values
    without double counting."""
    tracker = SubagentUsageTracker()

    tracker.update([_child(input=100, output=50)], final=False)
    tracker.update([_child(input=150, output=80)], final=False)

    totals = tracker.totals
    assert totals.runs == 1
    assert totals.input_tokens == 150
    assert totals.output_tokens == 80


def test_commit_folds_each_call_once() -> None:
    """Prove each call's final result is committed exactly once and calls
    accumulate across the session."""
    tracker = SubagentUsageTracker()

    tracker.update([_child(input=100, output=50, cost=0.01)], final=True)
    tracker.update(
        [_child(input=200, output=100), _child(input=50, output=25)],
        final=True,
    )

    totals = tracker.totals
    assert totals.runs == 3
    assert totals.input_tokens == 350
    assert totals.output_tokens == 175
    assert totals.cost == 0.01


def test_snapshot_cleared_on_commit() -> None:
    """Prove a committed call no longer contributes through the snapshot: the
    snapshot is cleared so the displayed totals cannot double-count it."""
    tracker = SubagentUsageTracker()
    child = _child(input=100, output=50)

    tracker.update([child], final=False)
    tracker.update([child], final=True)

    assert tracker.totals.input_tokens == 100
    assert tracker.totals.runs == 1


def test_discard_pending_drops_snapshot() -> None:
    """Prove a call that ends without committing discards its in-flight
    snapshot, leaving only the committed totals."""
    tracker = SubagentUsageTracker()
    tracker.update([_child(input=100, output=50)], final=True)

    tracker.update([_child(input=500, output=250)], final=False)
    tracker.discard_pending()

    totals = tracker.totals
    assert totals.input_tokens == 100
    assert totals.output_tokens == 50
    assert totals.runs == 1


def test_zero_usage_children_contribute_nothing() -> None:
    """Prove children with no reported usage or cost add no tokens, cost, or
    run count, so never-started children cannot inflate the section."""
    tracker = SubagentUsageTracker()
    empty = _child()

    tracker.update([_child(input=100, output=50), empty], final=True)

    totals = tracker.totals
    assert totals.runs == 1
    assert totals.input_tokens == 100


def test_partial_usage_children_are_included() -> None:
    """Prove a timed-out child keeps its partial usage: tokens were really
    consumed even though the child never completed."""
    tracker = SubagentUsageTracker()

    tracker.update([_child(input=60, output=30, timed_out=True)], final=True)

    assert tracker.totals.input_tokens == 60
    assert tracker.totals.runs == 1


def test_reset_clears_everything() -> None:
    """Prove a session-rebind reset returns the tracker to its initial state,
    committed totals and in-flight snapshot alike."""
    tracker = SubagentUsageTracker()
    tracker.update([_child(input=100, output=50)], final=True)
    tracker.update([_child(input=10, output=5)], final=False)

    tracker.reset()

    assert tracker.totals == SubagentUsageTotals()


def test_prompt_tokens_include_cached_and_written() -> None:
    """Prove the displayed input figure includes cached and cache-written
    tokens, mirroring the session usage section's input definition."""
    tracker = SubagentUsageTracker()

    tracker.update([_child(input=100, cache_read=50, cache_write=10)], final=True)

    assert tracker.totals.prompt_tokens == 160
    assert tracker.totals.input_tokens == 100


def test_cost_reported_only_when_nonzero() -> None:
    """Prove cost accumulates only from children that actually reported it."""
    tracker = SubagentUsageTracker()

    tracker.update(
        [_child(input=100, output=50, cost=0.0), _child(input=200, output=100, cost=0.5)],
        final=True,
    )

    assert tracker.totals.cost == 0.5
