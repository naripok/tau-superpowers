"""Model tests for the additive estimatedCost usage field.

These tests pin the "Additive details field" scenario of the catalog-based
subagent cost estimation requirement: UsageStats serialization gains exactly
one key placed after cost, every existing key and value is unchanged, and the
internal catalog_priced provenance flag never serializes.
"""

from __future__ import annotations

from superpowers_subagent.models import ChildResult, UsageStats


def test_usage_stats_to_dict_adds_estimated_cost() -> None:
    """Prove a populated UsageStats serializes the seven existing keys with
    unchanged values plus estimatedCost placed directly after cost."""
    usage = UsageStats(
        input=100,
        output=50,
        cache_read=20,
        cache_write=10,
        cost=0.25,
        context_tokens=170,
        turns=3,
        estimated_cost=1.5,
    )

    serialized = usage.to_dict()

    assert serialized == {
        "input": 100,
        "output": 50,
        "cacheRead": 20,
        "cacheWrite": 10,
        "cost": 0.25,
        "estimatedCost": 1.5,
        "contextTokens": 170,
        "turns": 3,
    }
    assert list(serialized) == [
        "input",
        "output",
        "cacheRead",
        "cacheWrite",
        "cost",
        "estimatedCost",
        "contextTokens",
        "turns",
    ]


def test_usage_stats_catalog_priced_is_not_serialized() -> None:
    """Prove the internal catalog_priced provenance flag stays out of the
    details dict: estimatedCost is the only new usage content."""
    usage = UsageStats(estimated_cost=0.75, catalog_priced=True)

    serialized = usage.to_dict()

    assert "catalogPriced" not in serialized
    assert "catalog_priced" not in serialized
    assert set(serialized) == {
        "input",
        "output",
        "cacheRead",
        "cacheWrite",
        "cost",
        "estimatedCost",
        "contextTokens",
        "turns",
    }


def test_default_usage_stats_serializes_zero_estimated_cost() -> None:
    """Prove a default UsageStats serializes estimatedCost as 0.0."""
    assert UsageStats().to_dict()["estimatedCost"] == 0.0


def test_child_result_to_dict_carries_estimated_cost() -> None:
    """Prove ChildResult details expose usage.estimatedCost through the
    embedded usage dict."""
    result = ChildResult(
        agent="implementation",
        agent_source="bundled",
        task="work",
        cwd="/workspace",
        usage=UsageStats(input=10, output=5, estimated_cost=0.42),
    )

    details = result.to_dict()

    usage = details["usage"]
    assert isinstance(usage, dict)
    assert usage["estimatedCost"] == 0.42
    assert usage["input"] == 10
    assert usage["output"] == 5
