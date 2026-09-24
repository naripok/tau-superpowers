"""Exception-safe Tau provider-catalog access for scoped dispatch pin validation.

Two jobs, both fail-safe: load the provider catalog, and restrict it to what
the harness can actually run before teach-back errors list options to the
controller. ``catalog_snapshot`` returns the unscoped effective catalog
(builtin + user overlay). ``scoped_catalog_snapshot`` returns only providers
that are configured — a stored credential, the entry's API-key environment
variable, an operator scoped model, a dispatch pin, or the parent session's
running provider — and per provider only the models the harness configures,
never a whole builtin catalog. Any failure degrades to ``None``, which means
"skip validation", exactly like dispatching without this module.

Catalog scope: when the nearest ancestor project defines
``<project>/.tau/catalog.toml``, its overlay replaces the user overlay
(``~/.tau/catalog.toml``); otherwise the user overlay applies. Credentials,
provider settings, and scoped models are harness-global in Tau and stay
user-level at every scope.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from tau_coding.catalog_loader import USER_CATALOG_FILENAME, effective_catalog
from tau_coding.credentials import FileCredentialStore
from tau_coding.paths import TauPaths
from tau_coding.provider_catalog import ProviderCatalogEntry
from tau_coding.provider_config import load_provider_settings

from .config import SubagentConfig
from .discovery import discover_agents
from .models import AgentConfig

#: Bound the model lists embedded in teach-back errors so a large catalog
#: cannot flood the controller's context with one validation failure.
_MAX_LISTED_MODELS = 40


class CatalogSnapshot(NamedTuple):
    """Provider names and per-provider model sets, ready for validation."""

    providers: frozenset[str]
    models_by_provider: dict[str, frozenset[str]]


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """The catalog facts scoping needs, independent of Tau's dataclasses."""

    name: str
    models: frozenset[str]
    default_model: str
    credential_name: str | None
    api_key_env: str | None


@dataclass(frozen=True, slots=True)
class ScopedSources:
    """Plain-data inputs for :func:`build_scoped_snapshot`, injectable in tests."""

    entries: tuple[CatalogEntry, ...]
    builtin_names: frozenset[str]
    credential_names: frozenset[str]
    environ: Mapping[str, str]
    scoped_pairs: tuple[tuple[str, str], ...]
    preference_defaults: Mapping[str, str]
    config: SubagentConfig | None
    agents: tuple[AgentConfig, ...]
    parent_provider: str | None
    parent_model: str | None


def catalog_snapshot() -> CatalogSnapshot | None:
    """Return the unscoped effective catalog, or None when unavailable."""

    try:
        entries = effective_catalog()
    except Exception:  # noqa: BLE001 - validation must never break dispatch
        return None
    try:
        models = {entry.name: frozenset(entry.models) | {entry.default_model} for entry in entries}
    except Exception:  # noqa: BLE001 - malformed entries degrade to no validation
        return None
    return CatalogSnapshot(providers=frozenset(models), models_by_provider=models)


def scoped_catalog_snapshot(
    cwd: Path,
    *,
    parent_provider: str | None = None,
    parent_model: str | None = None,
    config: SubagentConfig | None = None,
    credential_store: FileCredentialStore | None = None,
    environ: Mapping[str, str] | None = None,
    agent_definitions: tuple[AgentConfig, ...] | None = None,
) -> CatalogSnapshot | None:
    """Return only harness-configured providers and their configured models.

    Any failure to read the catalog, credentials, provider settings, or agent
    definitions returns None so dispatch skips validation instead of breaking.
    """

    try:
        entries = _scope_catalog_entries(cwd)
        settings = load_provider_settings()
        store = credential_store or FileCredentialStore()
        agents = agent_definitions if agent_definitions is not None else discover_agents(cwd).agents
        scoped_pairs = tuple((item.provider, item.model) for item in settings.scoped_models)
        preference_defaults = {item.name: item.default_model for item in settings.providers}
        builtin_names = _builtin_provider_names()
    except Exception:  # noqa: BLE001 - scoping must never break dispatch
        return None

    catalog_entries = tuple(
        CatalogEntry(
            name=entry.name,
            models=frozenset(entry.models),
            default_model=entry.default_model,
            credential_name=entry.credential_name,
            api_key_env=entry.api_key_env,
        )
        for entry in entries
    )
    return build_scoped_snapshot(
        entries=catalog_entries,
        builtin_names=builtin_names,
        credential_names=_stored_credential_names(store, catalog_entries),
        environ=os.environ if environ is None else environ,
        scoped_pairs=scoped_pairs,
        preference_defaults=preference_defaults,
        config=config,
        agents=agents,
        parent_provider=parent_provider,
        parent_model=parent_model,
    )


def build_scoped_snapshot(
    *,
    entries: tuple[CatalogEntry, ...],
    builtin_names: frozenset[str],
    credential_names: frozenset[str],
    environ: Mapping[str, str],
    scoped_pairs: Iterable[tuple[str, str]],
    preference_defaults: Mapping[str, str],
    config: SubagentConfig | None,
    agents: Iterable[AgentConfig],
    parent_provider: str | None,
    parent_model: str | None,
) -> CatalogSnapshot:
    """Pure scoping core: plain data in, snapshot out."""

    entry_by_name = {entry.name: entry for entry in entries}
    configured: set[str] = set()
    pinned_models: dict[str, set[str]] = {}

    def note_pair(provider: str | None, model: str | None) -> None:
        """Record a configured provider/model pair from harness configuration."""

        if provider and model:
            configured.add(provider)
            pinned_models.setdefault(provider, set()).add(model)
        elif provider:
            configured.add(provider)

    # Operator-enabled quick-cycling pairs, then dispatch pins from the
    # subagent config file and agent-definition frontmatter.
    for provider, model in scoped_pairs:
        note_pair(provider, model)
    if config is not None:
        note_pair(config.defaults.provider, config.defaults.model)
        for _name, overrides in config.agents:
            note_pair(overrides.provider, overrides.model)
    for agent in agents:
        note_pair(agent.provider, agent.model)
    if parent_provider:
        configured.add(parent_provider)

    for entry in entries:
        if entry.credential_name and entry.credential_name in credential_names:
            configured.add(entry.name)
        elif entry.api_key_env and entry.api_key_env in environ:
            configured.add(entry.name)

    models_by_provider: dict[str, frozenset[str]] = {}
    for name in sorted(configured):
        catalog_entry = entry_by_name.get(name)
        if catalog_entry is None:
            # Referenced by configuration but absent from the catalog: leave
            # it out so validation rejects the pin and lists real providers.
            continue
        if name in builtin_names:
            # Builtin providers list only what the harness selects; the catalog
            # default is Tau's packaged fallback, not operator configuration.
            models: set[str] = set()
        else:
            # User- or project-catalog-added provider: its declared model list
            # is the operator's explicit scope, default included.
            models = {catalog_entry.default_model} | set(catalog_entry.models)
        preference_default = preference_defaults.get(name)
        if preference_default:
            models.add(preference_default)
        if name == parent_provider and parent_model:
            models.add(parent_model)
        models |= pinned_models.get(name, set())
        if not models:
            # Configured but with no model the harness selects: nothing to
            # teach back until the operator scopes one (e.g. via /model).
            continue
        models_by_provider[name] = frozenset(models)
    return CatalogSnapshot(
        providers=frozenset(models_by_provider), models_by_provider=models_by_provider
    )


def _scope_catalog_entries(cwd: Path) -> tuple[ProviderCatalogEntry, ...]:
    """Effective catalog under the project overlay when one exists, else user."""

    project_tau = _nearest_project_catalog_dir(cwd)
    if project_tau is not None:
        return effective_catalog(TauPaths(home=project_tau))
    return effective_catalog()


def _nearest_project_catalog_dir(cwd: Path) -> Path | None:
    """Nearest ancestor ``.tau`` directory with a catalog.toml, minus user home."""

    user_home = TauPaths().home.resolve()
    current = cwd.expanduser().resolve()
    while True:
        candidate = current / ".tau"
        if candidate.is_dir() and (candidate / USER_CATALOG_FILENAME).is_file():
            if candidate.resolve() != user_home:
                return candidate
        if current.parent == current:
            return None
        current = current.parent


def _builtin_provider_names() -> frozenset[str]:
    try:
        from tau_coding.provider_catalog import BUILTIN_PROVIDER_CATALOG

        return frozenset(entry.name for entry in BUILTIN_PROVIDER_CATALOG)
    except Exception:  # noqa: BLE001 - degrade to treating every provider as user-added
        return frozenset()


def _stored_credential_names(
    store: FileCredentialStore, entries: tuple[CatalogEntry, ...]
) -> frozenset[str]:
    """Credential names the store can serve, covering API keys and OAuth."""

    names: set[str] = set()
    for entry in entries:
        if not entry.credential_name:
            continue
        try:
            if store.get(entry.credential_name) is not None:
                names.add(entry.credential_name)
            elif store.get_oauth(entry.credential_name) is not None:
                names.add(entry.credential_name)
        except Exception:  # noqa: BLE001 - one unreadable store must not stop scoping
            continue
    return frozenset(names)


def _summarize(values: Iterable[str]) -> str:
    ordered = sorted(values)
    listed = ", ".join(ordered[:_MAX_LISTED_MODELS])
    overflow = len(ordered) - _MAX_LISTED_MODELS
    if overflow > 0:
        return f"{listed} … and {overflow} more"
    return listed


def provider_model_pin_error(
    provider: str | None,
    model: str | None,
    *,
    parent_provider: str | None,
    parent_model: str | None,
    snapshot: CatalogSnapshot | None,
) -> str | None:
    """Return an actionable error for a pinned pair the catalog cannot honor.

    Conservative by design: without a snapshot, without a resolved provider, or
    for the parent session's own running pair, the pin passes untouched — the
    child inherits or re-runs exactly what the parent session already proves
    works. The failure always directs the caller to the config pin or the agent
    definition, because no call-level parameter exists.
    """

    if snapshot is None or provider is None:
        return None
    known_models = snapshot.models_by_provider.get(provider)
    if known_models is None and provider != parent_provider:
        available = _summarize(snapshot.providers)
        return (
            f"provider {provider!r} is not a configured Tau provider. Configured "
            f"providers: {available}. Correct the provider pin in the config file or "
            "the agent definition, and use an exact provider name from `tau providers`."
        )
    if model is None or known_models is None:
        return None
    if model == parent_model and provider == parent_provider:
        return None
    if model in known_models:
        return None
    available = _summarize(known_models)
    return (
        f"model {model!r} is not configured for provider {provider!r}. Configured "
        f"models: {available}. Correct the model pin in the config file or the agent "
        "definition, or use an exact model ID supported by the provider."
    )
