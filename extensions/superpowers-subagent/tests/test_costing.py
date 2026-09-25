"""Guarded estimator seam tests for per-message catalog pricing.

These tests pin the "Catalog-based subagent cost estimation" scenarios at the
seam level: rate resolution through the effective catalog — built-in rates
overlaid by ``~/.tau/catalog.toml`` — exact pricing per token breakdown,
one-hour cache-write pricing split, tier selection by request size, and
degradation to ``None`` when the seam is missing, broken, or has no catalog
entry.
"""

from __future__ import annotations

import sys
from pathlib import Path

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


def _raising_resolver(*_args: object, **_kwargs: object) -> float | None:
    """Catalog resolver stub that always fails."""
    raise RuntimeError("catalog resolution is broken")


def _model_rates(provider: str, model: str) -> dict[str, float]:
    entry = builtin_provider_entry(provider)
    assert entry is not None
    metadata = entry.model_metadata[model]
    assert metadata.cost is not None
    return metadata.cost


def test_missing_seam_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove a missing Tau catalog module degrades to None instead of raising."""
    monkeypatch.setitem(sys.modules, "tau_coding.catalog_loader", None)

    result = estimated_message_cost(_message(input=10, output=2))

    assert result is None


def test_raising_seam_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove a catalog resolution failure degrades to None instead of raising."""
    monkeypatch.setattr("tau_coding.catalog_loader.effective_catalog", _raising_resolver)

    result = estimated_message_cost(_message(input=10, output=2))

    assert result is None


def test_model_without_catalog_rates_returns_none(isolated_home: Path) -> None:
    """Prove a message whose provider and model are absent from the effective
    catalog — built-in plus any overlay — is unpriced: None, not zero."""
    result = estimated_message_cost(_message(provider="prov-a", model="model-a"))

    assert result is None


def test_user_overlay_prices_a_model_missing_from_the_builtin_catalog(
    isolated_home: Path,
) -> None:
    """Prove a message whose provider and model exist only in the user's
    ``~/.tau/catalog.toml`` overlay is priced from the overlay rates — the
    operator's fix for models Tau's built-in catalog omits."""
    overlay = isolated_home / ".tau" / "catalog.toml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text(
        "\n".join(
            [
                "schema_version = 1",
                "",
                "[[providers]]",
                'name = "overlay-provider"',
                'display_name = "Overlay Provider"',
                'kind = "openai-compatible"',
                'base_url = "https://overlay.example/v1"',
                'api_key_env = "OVERLAY_API_KEY"',
                'docs_url = "https://overlay.example/docs"',
                'models = ["overlay-model"]',
                'default_model = "overlay-model"',
                "",
                '[providers.model_metadata."overlay-model"]',
                'input = ["text"]',
                "context_window = 1000000",
                "cost = { input = 2.0, output = 6.0, cacheRead = 0.5, cacheWrite = 1.0,"
                " cacheWrite1h = 4.0 }",
            ]
        ),
        encoding="utf-8",
    )
    message = _message(
        provider="overlay-provider",
        model="overlay-model",
        input=1_000_000,
        output=1_000_000,
        cache_read=1_000_000,
        cache_write=1_000_000,
        cache_write_1h=500_000,
    )

    result = estimated_message_cost(message)

    assert result == pytest.approx(11.0)


def test_overlay_resolution_is_memoized_until_the_overlay_file_changes(
    monkeypatch: pytest.MonkeyPatch, isolated_home: Path
) -> None:
    """Prove the effective catalog resolves once while the overlay file stays
    unchanged and re-resolves after the file changes, so per-message pricing
    avoids re-parsing the overlay on every child message without going stale."""
    from tau_coding import catalog_loader

    overlay = isolated_home / ".tau" / "catalog.toml"
    overlay.parent.mkdir(parents=True)
    real_effective_catalog = catalog_loader.effective_catalog
    calls = 0

    def counting_effective_catalog() -> object:
        nonlocal calls
        calls += 1
        return real_effective_catalog()

    monkeypatch.setattr("tau_coding.catalog_loader.effective_catalog", counting_effective_catalog)

    def write_overlay(input_rate: str) -> None:
        overlay.write_text(
            "\n".join(
                [
                    "schema_version = 1",
                    "",
                    "[[providers]]",
                    'name = "overlay-provider"',
                    'display_name = "Overlay Provider"',
                    'kind = "openai-compatible"',
                    'base_url = "https://overlay.example/v1"',
                    'api_key_env = "OVERLAY_API_KEY"',
                    'docs_url = "https://overlay.example/docs"',
                    'models = ["overlay-model"]',
                    'default_model = "overlay-model"',
                    "",
                    '[providers.model_metadata."overlay-model"]',
                    'input = ["text"]',
                    "context_window = 1000000",
                    f"cost = {{ input = {input_rate}, output = 6.0, cacheRead = 0.5,"
                    " cacheWrite = 1.0, cacheWrite1h = 4.0 }",
                ]
            ),
            encoding="utf-8",
        )

    message = _message(
        provider="overlay-provider",
        model="overlay-model",
        input=1_000_000,
        output=1_000_000,
        cache_read=1_000_000,
        cache_write=1_000_000,
        cache_write_1h=500_000,
    )

    write_overlay("2.0")
    first = estimated_message_cost(message)
    second = estimated_message_cost(message)

    assert first == pytest.approx(11.0)
    assert second == pytest.approx(11.0)
    assert calls == 1

    write_overlay("25.0")
    third = estimated_message_cost(message)

    assert third == pytest.approx(34.0)
    assert calls == 2


def test_real_catalog_prices_a_costed_model(isolated_home: Path) -> None:
    """Prove the real Tau import path prices a message whose model carries
    catalog rates, without any stubbing."""
    entry = builtin_provider_entry("anthropic")
    assert entry is not None
    model = next(name for name in entry.models if entry.model_metadata[name].cost)
    message = _message(provider="anthropic", model=model, input=1_000, output=100)

    result = estimated_message_cost(message)

    assert result is not None
    assert result > 0


def test_real_catalog_prices_one_hour_cache_writes_at_their_rate(
    isolated_home: Path,
) -> None:
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


def test_real_catalog_selects_tier_per_request_size(isolated_home: Path) -> None:
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
