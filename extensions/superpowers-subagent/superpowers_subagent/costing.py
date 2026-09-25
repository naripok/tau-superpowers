"""Pricing of one child assistant message through Tau's catalog estimator."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from tau_agent.messages import AssistantMessage

if TYPE_CHECKING:
    from tau_coding.provider_catalog import ProviderCatalogEntry

#: Single-slot memo for the effective catalog, keyed on the overlay file's
#: path, mtime, and size. ``effective_catalog()`` re-reads and re-validates the
#: whole merged catalog on every call once an overlay exists, and this module
#: prices every child assistant message, so the entries stay valid until the
#: overlay file changes.
_catalog_memo: tuple[tuple[str, int, int], tuple[ProviderCatalogEntry, ...]] | None = None


def _effective_catalog_entries() -> tuple[ProviderCatalogEntry, ...]:
    """Return the effective catalog, re-resolving only when the overlay changes."""
    global _catalog_memo
    from tau_coding.catalog_loader import USER_CATALOG_FILENAME, effective_catalog
    from tau_coding.paths import TauPaths

    overlay_path = TauPaths().home / USER_CATALOG_FILENAME
    try:
        stat = overlay_path.stat()
    except OSError:
        # No readable overlay: Tau resolves to its cached built-in catalog.
        return effective_catalog()
    key = (str(overlay_path), stat.st_mtime_ns, stat.st_size)
    if _catalog_memo is not None and _catalog_memo[0] == key:
        return _catalog_memo[1]
    entries = effective_catalog()
    _catalog_memo = (key, entries)
    return entries


def estimated_message_cost(message: AssistantMessage) -> float | None:
    """Return the catalog estimate in USD for one accepted child message.

    Tau's catalog loader and cost helpers are imported lazily inside the call so
    the extension loads without them. Rates come from the effective catalog —
    the built-in rates overlaid by ``~/.tau/catalog.toml`` — so an operator can
    price models the built-in catalog omits. Tier selection and the one-hour
    cache-write split follow the same rules as Tau's own estimator. A missing
    seam, an estimator failure, or a model without catalog rates all degrade to
    ``None``; the caller decides what an unpriced message means.
    """
    try:
        from tau_coding import session_usage
        from tau_coding.provider_catalog import model_cost_for_input_tokens

        # Tau exposes no public per-response cost helper; reach the private one
        # through the same guarded getattr pattern the sidebar seam uses.
        response_cost = getattr(session_usage, "_response_cost", None)
        if response_cost is None:
            return None
        entry = next(
            (item for item in _effective_catalog_entries() if item.name == message.provider),
            None,
        )
        metadata = entry.model_metadata.get(message.model) if entry is not None else None
        if metadata is None:
            return None
        prompt_tokens = message.usage.input + message.usage.cache_read + message.usage.cache_write
        rates = model_cost_for_input_tokens(metadata, prompt_tokens)
        if not rates:
            return None
        return cast(
            "float | None",
            response_cost(
                input_tokens=message.usage.input,
                output_tokens=message.usage.output,
                cache_read_tokens=message.usage.cache_read,
                cache_write_tokens=message.usage.cache_write,
                cache_write_1h_tokens=message.usage.cache_write_1h or 0,
                rates=rates,
            ),
        )
    except Exception:
        return None
