"""Exception-safe Tau provider-catalog access for fail-fast dispatch validation.

The parent session proves its own provider/model pair by running on it, so the
catalog is needed only to reject literal override mistakes before a child
process spawns and dies at provider setup. Any failure to load the catalog
degrades to no validation, exactly like dispatching without this module.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

#: Bound the model lists embedded in teach-back errors so a large catalog
#: cannot flood the controller's context with one validation failure.
_MAX_LISTED_MODELS = 40


class CatalogSnapshot(NamedTuple):
    """Provider names and per-provider model sets from Tau's effective catalog."""

    providers: frozenset[str]
    models_by_provider: dict[str, frozenset[str]]


def catalog_snapshot() -> CatalogSnapshot | None:
    """Return the merged builtin and user catalog, or None when unavailable."""

    try:
        from tau_coding.catalog_loader import effective_catalog

        entries = effective_catalog()
    except Exception:  # noqa: BLE001 - validation must never break dispatch
        return None
    try:
        models = {entry.name: frozenset(entry.models) | {entry.default_model} for entry in entries}
    except Exception:  # noqa: BLE001 - malformed entries degrade to no validation
        return None
    return CatalogSnapshot(providers=frozenset(models), models_by_provider=models)


def _summarize(values: Iterable[str]) -> str:
    ordered = sorted(values)
    listed = ", ".join(ordered[:_MAX_LISTED_MODELS])
    overflow = len(ordered) - _MAX_LISTED_MODELS
    if overflow > 0:
        return f"{listed} … and {overflow} more"
    return listed


def provider_model_override_error(
    provider: str | None,
    model: str | None,
    *,
    parent_provider: str | None,
    parent_model: str | None,
    snapshot: CatalogSnapshot | None,
) -> str | None:
    """Return an actionable error for an override pair the catalog cannot honor.

    Conservative by design: without a snapshot, without a resolved provider, or
    for the parent session's own running pair, the override passes untouched —
    the child would inherit or re-run exactly what the parent session already
    proves works.
    """

    if snapshot is None or provider is None:
        return None
    known_models = snapshot.models_by_provider.get(provider)
    if known_models is None and provider != parent_provider:
        available = _summarize(tuple(snapshot.providers))
        inherited = f" ({parent_provider!r})" if parent_provider else ""
        return (
            f"provider {provider!r} is not a configured Tau provider. Configured "
            f"providers: {available}. Omit provider to inherit the parent session's "
            f"provider{inherited}, or pass one from the list."
        )
    if model is None or known_models is None:
        return None
    if model == parent_model and provider == parent_provider:
        return None
    if model in known_models:
        return None
    available = _summarize(known_models)
    inherit = (
        f" Omit model to inherit the parent session's model ({parent_model!r})."
        if parent_model and provider == parent_provider
        else " Omit model to inherit configuration."
    )
    return (
        f"model {model!r} is not configured for provider {provider!r}. Configured "
        f"models: {available}.{inherit} Or pass one from the list."
    )
