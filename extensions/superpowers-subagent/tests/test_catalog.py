from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from superpowers_subagent import catalog as catalog_module
from superpowers_subagent.catalog import (
    CatalogEntry,
    _nearest_project_catalog_dir,
    build_scoped_snapshot,
    scoped_catalog_snapshot,
)
from superpowers_subagent.config import AgentOverrides, SubagentConfig
from superpowers_subagent.models import AgentConfig


def make_entry(
    name: str,
    *,
    models: tuple[str, ...] = ("m-default",),
    default_model: str = "m-default",
    credential_name: str | None = None,
    api_key_env: str | None = None,
) -> CatalogEntry:
    return CatalogEntry(
        name=name,
        models=frozenset(models),
        default_model=default_model,
        credential_name=credential_name,
        api_key_env=api_key_env,
    )


def make_agent(
    name: str,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> AgentConfig:
    return AgentConfig(
        name=name,
        description=f"{name} agent",
        system_prompt="",
        source="bundled",
        file_path=Path(f"{name}.md"),
        provider=provider,
        model=model,
    )


def make_config(
    *,
    defaults: AgentOverrides | None = None,
    agents: dict[str, AgentOverrides] | None = None,
) -> SubagentConfig:
    return SubagentConfig(
        defaults=defaults or AgentOverrides(),
        agents=tuple((name, overrides) for name, overrides in sorted((agents or {}).items())),
    )


def build(
    entries: list[CatalogEntry],
    *,
    builtin_names: frozenset[str] | None = None,
    credential_names: frozenset[str] = frozenset(),
    environ: dict[str, str] | None = None,
    scoped_pairs: list[tuple[str, str]] | None = None,
    preference_defaults: dict[str, str] | None = None,
    config: SubagentConfig | None = None,
    agents: list[AgentConfig] | None = None,
    parent_provider: str | None = None,
    parent_model: str | None = None,
) -> Any:
    return build_scoped_snapshot(
        entries=tuple(entries),
        builtin_names=builtin_names if builtin_names is not None else frozenset(),
        credential_names=credential_names,
        environ=environ or {},
        scoped_pairs=scoped_pairs or [],
        preference_defaults=preference_defaults or {},
        config=config,
        agents=agents or [],
        parent_provider=parent_provider,
        parent_model=parent_model,
    )


def test_unconfigured_builtin_provider_is_excluded() -> None:
    entries = [
        make_entry("openai", credential_name="openai"),
        make_entry("anthropic", credential_name="anthropic"),
    ]

    snapshot = build(
        entries,
        builtin_names=frozenset({"openai", "anthropic"}),
        credential_names=frozenset({"openai"}),
        preference_defaults={"openai": "gpt-5.6-sol"},
    )

    assert snapshot.providers == frozenset({"openai"})
    assert snapshot.models_by_provider["openai"] == frozenset({"gpt-5.6-sol"})


def test_builtin_credential_without_selected_model_is_dropped() -> None:
    """A key alone teaches back nothing: tau catalogs ship defaults no one scoped."""

    entries = [make_entry("openai", credential_name="openai", default_model="gpt-5.5")]

    snapshot = build(
        entries,
        builtin_names=frozenset({"openai"}),
        credential_names=frozenset({"openai"}),
    )

    assert snapshot.providers == frozenset()


def test_env_api_key_configures_provider() -> None:
    entries = [make_entry("anthropic", api_key_env="ANTHROPIC_API_KEY")]

    snapshot = build(
        entries,
        builtin_names=frozenset({"anthropic"}),
        environ={"ANTHROPIC_API_KEY": "sk-x"},
        preference_defaults={"anthropic": "claude-sonnet-4-6"},
    )

    assert snapshot.providers == frozenset({"anthropic"})
    assert snapshot.models_by_provider["anthropic"] == frozenset({"claude-sonnet-4-6"})


def test_scoped_pair_configures_provider_and_model() -> None:
    entries = [make_entry("openrouter", credential_name="openrouter", default_model="other")]

    snapshot = build(
        entries,
        builtin_names=frozenset({"openrouter"}),
        scoped_pairs=[("openrouter", "z-ai/glm-5.3")],
    )

    # The packaged catalog default must not leak into the scoped list.
    assert snapshot.models_by_provider["openrouter"] == frozenset({"z-ai/glm-5.3"})


def test_config_and_agent_pins_add_providers_and_models() -> None:
    entries = [
        make_entry("openrouter", credential_name="openrouter"),
        make_entry(
            "local-gateway",
            models=("qwen3.8-27b", "qwen3.8-8b"),
            default_model="qwen3.8-27b",
        ),
    ]
    config = make_config(defaults=AgentOverrides(provider="openrouter", model="deepseek/x"))
    agents = [make_agent("coder", provider="local-gateway", model="qwen3.8-8b")]

    snapshot = build(
        entries,
        builtin_names=frozenset({"openrouter"}),
        scoped_pairs=[],
        config=config,
        agents=agents,
    )

    # local-gateway is user-catalog-added: its full declared list ships.
    assert snapshot.models_by_provider["local-gateway"] == frozenset({"qwen3.8-27b", "qwen3.8-8b"})
    assert snapshot.models_by_provider["openrouter"] == frozenset({"deepseek/x"})


def test_parent_running_pair_is_always_configured() -> None:
    entries = [make_entry("session-provider", models=("m1", "m2"), default_model="m1")]

    snapshot = build(
        entries,
        builtin_names=frozenset(),
        parent_provider="session-provider",
        parent_model="m1",
    )

    assert snapshot.providers == frozenset({"session-provider"})
    assert snapshot.models_by_provider["session-provider"] == frozenset({"m1", "m2"})


def test_builtin_provider_scopes_to_preference_scoped_and_pins() -> None:
    entries = [make_entry("openai", credential_name="openai", default_model="gpt-5.5")]

    snapshot = build(
        entries,
        builtin_names=frozenset({"openai"}),
        credential_names=frozenset({"openai"}),
        scoped_pairs=[("openai", "gpt-5.5-mini")],
        preference_defaults={"openai": "gpt-5.6-sol"},
    )

    # The packaged default 'gpt-5.5' is not operator configuration: excluded.
    assert snapshot.models_by_provider["openai"] == frozenset({"gpt-5.6-sol", "gpt-5.5-mini"})


def test_pin_referenced_provider_absent_from_catalog_is_excluded() -> None:
    config = make_config(agents={"ghost": AgentOverrides(provider="ghost", model="m")})

    snapshot = build(
        [make_entry("openai", credential_name="openai")],
        builtin_names=frozenset({"openai"}),
        credential_names=frozenset({"openai"}),
        preference_defaults={"openai": "m-default"},
        config=config,
    )

    assert snapshot.providers == frozenset({"openai"})


@dataclass
class FakeStore:
    keys: set[str] = field(default_factory=set)
    oauth: set[str] = field(default_factory=set)

    def get(self, name: str) -> str | None:
        return name if name in self.keys else None

    def get_oauth(self, name: str) -> object | None:
        return name if name in self.oauth else None


def test_scoped_snapshot_uses_project_catalog_over_user(tmp_path: Path, monkeypatch: Any) -> None:
    """A project .tau/catalog.toml replaces the user overlay as the base."""

    user_tau = tmp_path / "user" / ".tau"
    project_tau = tmp_path / "proj" / ".tau"
    project_tau.mkdir(parents=True)
    (project_tau / "catalog.toml").write_text("schema_version = 1\n")
    user_tau.mkdir(parents=True)
    (user_tau / "catalog.toml").write_text("schema_version = 1\n")

    user_entry = make_entry("user-gateway", models=("user-model",))
    project_entry = make_entry("project-gateway", models=("project-model",))

    def fake_effective_catalog(paths: Any = None) -> list[CatalogEntry]:
        return [project_entry] if paths is not None else [user_entry]

    monkeypatch.setattr(catalog_module, "effective_catalog", fake_effective_catalog)

    result = scoped_catalog_snapshot(
        tmp_path / "proj",
        parent_provider="project-gateway",
        agent_definitions=(),
        credential_store=FakeStore(),
    )
    assert result is not None
    assert result.providers == frozenset({"project-gateway"})

    (project_tau / "catalog.toml").unlink()
    result = scoped_catalog_snapshot(
        tmp_path / "proj",
        parent_provider="user-gateway",
        agent_definitions=(),
        credential_store=FakeStore(),
    )
    assert result is not None
    assert result.providers == frozenset({"user-gateway"})


def test_scoped_snapshot_degrades_to_none_on_catalog_failure(
    tmp_path: Path, monkeypatch: Any
) -> None:
    def broken(paths: Any = None) -> list[CatalogEntry]:
        raise ValueError("catalog unreadable")

    monkeypatch.setattr(catalog_module, "effective_catalog", broken)

    assert scoped_catalog_snapshot(tmp_path, agent_definitions=()) is None


def test_nearest_project_catalog_dir_prefers_nearest_and_skips_user_home(
    tmp_path: Path, monkeypatch: Any
) -> None:
    user_tau = tmp_path / "userhome" / ".tau"
    outer = tmp_path / "proj" / ".tau"
    inner = tmp_path / "proj" / "sub" / ".tau"
    for directory in (user_tau, outer, inner):
        directory.mkdir(parents=True)
        (directory / "catalog.toml").write_text("schema_version = 1\n")

    monkeypatch.setattr(
        catalog_module, "TauPaths", lambda: SimpleNamespace(home=tmp_path / "userhome")
    )

    assert _nearest_project_catalog_dir(tmp_path / "proj" / "sub") == inner
    (inner / "catalog.toml").unlink()
    assert _nearest_project_catalog_dir(tmp_path / "proj" / "sub") == outer
    # The user home matches the pattern but is never returned as a project scope.
    (outer / "catalog.toml").unlink()
    assert _nearest_project_catalog_dir(tmp_path / "proj" / "sub") is None


def test_settings_stubs_feed_scoping(tmp_path: Path, monkeypatch: Any) -> None:
    """The settings reader maps scoped pairs and preference defaults into scoping."""

    entries = [make_entry("openai", credential_name="openai", default_model="gpt-5.5")]
    monkeypatch.setattr(catalog_module, "effective_catalog", lambda paths=None: entries)
    monkeypatch.setattr(
        catalog_module,
        "load_provider_settings",
        lambda: SimpleNamespace(
            scoped_models=[
                SimpleNamespace(provider="openai", model="gpt-5.6-sol"),
            ],
            providers=[SimpleNamespace(name="openai", default_model="gpt-5.5-codex")],
        ),
    )
    monkeypatch.setattr(catalog_module, "_builtin_provider_names", lambda: frozenset({"openai"}))

    result = scoped_catalog_snapshot(
        tmp_path,
        agent_definitions=(),
        credential_store=FakeStore(keys={"openai"}),
    )

    assert result is not None
    assert result.models_by_provider["openai"] == frozenset({"gpt-5.6-sol", "gpt-5.5-codex"})
