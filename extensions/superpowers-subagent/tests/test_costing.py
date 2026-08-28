"""Guarded estimator seam tests for per-message catalog pricing.

These tests pin the "Catalog-based subagent cost estimation" scenarios at the
seam level: argument forwarding to Tau's estimator, one-hour cache-write
pricing split, tier selection by request size, and degradation to ``None``
when the seam is missing, broken, or has no catalog entry.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from tau_agent.messages import AssistantMessage, Usage
from tau_coding.provider_catalog import builtin_provider_entry

from superpowers_subagent.costing import estimated_message_cost


def _message(
    *,
    provider: str = "prov-a",
    model: str = "model-a",
    input: int = 0,
    output: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    cache_write_1h: int | None = None,
) -> AssistantMessage:
    return AssistantMessage(
        provider=provider,
        model=model,
        usage=Usage(
            input=input,
            output=output,
            cache_read=cache_read,
            cache_write=cache_write,
            cache_write_1h=cache_write_1h,
        ),
    )


@dataclass(frozen=True)
class _EstimatorCall:
    """One recorded estimator invocation with its forwarded arguments."""

    provider: str
    model: str
    fresh: int
    cached: int
    cache_write: int
    cache_write_1h: int
    output: int


def _stub_estimator(
    result: float | None,
) -> tuple[Callable[..., float | None], list[_EstimatorCall]]:
    """Return a keyword-strict estimator stub that records calls and returns
    ``result``; the strict signature proves the wrapper forwards by keyword."""
    calls: list[_EstimatorCall] = []

    def record(
        provider: str,
        model: str,
        *,
        fresh: int,
        cached: int,
        cache_write: int,
        cache_write_1h: int,
        output: int,
    ) -> float | None:
        calls.append(
            _EstimatorCall(
                provider=provider,
                model=model,
                fresh=fresh,
                cached=cached,
                cache_write=cache_write,
                cache_write_1h=cache_write_1h,
                output=output,
            )
        )
        return result

    return record, calls


def _raising_estimator(*_args: object, **_kwargs: object) -> float | None:
    """Estimator stub that always fails."""
    raise RuntimeError("estimator is broken")


def _model_rates(provider: str, model: str) -> dict[str, float]:
    entry = builtin_provider_entry(provider)
    assert entry is not None
    metadata = entry.model_metadata[model]
    assert metadata.cost is not None
    return metadata.cost


def test_passthrough_returns_estimator_value_and_forwards_message_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove the seam returns the estimator's value and forwards the message's
    provider, model, and all five token counts by keyword."""
    message = _message(input=100, output=10, cache_read=5, cache_write=3, cache_write_1h=1234)
    stub, calls = _stub_estimator(0.5)
    monkeypatch.setattr("tau_coding.session_usage.estimated_request_cost", stub)

    result = estimated_message_cost(message)

    assert result == 0.5
    assert calls == [
        _EstimatorCall(
            provider="prov-a",
            model="model-a",
            fresh=100,
            cached=5,
            cache_write=3,
            cache_write_1h=1234,
            output=10,
        )
    ]


def test_none_cache_write_1h_forwards_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove a missing one-hour write count reaches the estimator as zero —
    the estimator's non-optional argument — rather than None."""
    message = _message(input=10, output=2, cache_write_1h=None)
    stub, calls = _stub_estimator(0.25)
    monkeypatch.setattr("tau_coding.session_usage.estimated_request_cost", stub)

    result = estimated_message_cost(message)

    assert result == 0.25
    assert calls == [
        _EstimatorCall(
            provider="prov-a",
            model="model-a",
            fresh=10,
            cached=0,
            cache_write=0,
            cache_write_1h=0,
            output=2,
        )
    ]


def test_missing_seam_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove a missing Tau usage module degrades to None instead of raising."""
    monkeypatch.setitem(sys.modules, "tau_coding.session_usage", None)

    result = estimated_message_cost(_message(input=10, output=2))

    assert result is None


def test_raising_seam_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove an estimator failure degrades to None instead of raising."""
    monkeypatch.setattr("tau_coding.session_usage.estimated_request_cost", _raising_estimator)

    result = estimated_message_cost(_message(input=10, output=2))

    assert result is None


def test_estimator_none_passes_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove the estimator's own None — no catalog entry for the model —
    reaches the caller unchanged as an unpriced message."""
    stub, calls = _stub_estimator(None)
    monkeypatch.setattr("tau_coding.session_usage.estimated_request_cost", stub)

    result = estimated_message_cost(_message(provider="prov-a", model="model-a"))

    assert result is None
    assert len(calls) == 1


def test_real_catalog_prices_a_costed_model() -> None:
    """Prove the real Tau import path prices a message whose model carries
    catalog rates, without any stubbing."""
    entry = builtin_provider_entry("anthropic")
    assert entry is not None
    model = next(name for name in entry.models if entry.model_metadata[name].cost)
    message = _message(provider="anthropic", model=model, input=1_000, output=100)

    result = estimated_message_cost(message)

    assert result is not None
    assert result > 0


def test_real_catalog_prices_one_hour_cache_writes_at_their_rate() -> None:
    """Prove one-hour writes price at the catalog's 1-hour rate and the rest of
    the write count at the 5-minute rate, while a message without a one-hour
    count prices every written token at the 5-minute rate."""
    rates = _model_rates("anthropic", "claude-fable-5")
    write_count = 1_000_000
    one_hour = 500_000
    with_one_hour = _message(
        provider="anthropic",
        model="claude-fable-5",
        cache_write=write_count,
        cache_write_1h=one_hour,
    )
    without_one_hour = _message(
        provider="anthropic",
        model="claude-fable-5",
        cache_write=write_count,
        cache_write_1h=None,
    )

    priced_with = estimated_message_cost(with_one_hour)
    priced_without = estimated_message_cost(without_one_hour)

    expected_with = (
        (write_count - one_hour) * rates["cacheWrite"] + one_hour * rates["cacheWrite1h"]
    ) / 1_000_000
    expected_without = write_count * rates["cacheWrite"] / 1_000_000
    assert priced_with == pytest.approx(expected_with)
    assert priced_without == pytest.approx(expected_without)


def test_real_catalog_selects_tier_per_request_size() -> None:
    """Prove tier selection follows the request size: input sized at the tier
    threshold prices at the lower-tier rate and one token more prices at the
    higher-tier rate."""
    entry = builtin_provider_entry("minimax")
    assert entry is not None
    model, metadata = next(
        (name, meta) for name, meta in entry.model_metadata.items() if meta.cost_tiers
    )
    lower, higher = metadata.cost_tiers[0], metadata.cost_tiers[1]
    threshold = lower.max_input_tokens
    assert threshold is not None

    priced_at = estimated_message_cost(_message(provider="minimax", model=model, input=threshold))
    priced_above = estimated_message_cost(
        _message(provider="minimax", model=model, input=threshold + 1)
    )

    assert priced_at == pytest.approx(threshold * lower.cost["input"] / 1_000_000)
    assert priced_above == pytest.approx((threshold + 1) * higher.cost["input"] / 1_000_000)
