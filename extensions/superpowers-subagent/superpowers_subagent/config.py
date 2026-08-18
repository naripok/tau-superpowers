"""Subagent dispatch configuration file loading and layering.

The `task` tool reads optional `{CONFIG_FILENAME}` files from two of the
directories Tau reads its other durable configs from:

1. the user Tau home (`~/.tau/`);
2. the nearest ancestor project `.tau/` directory from the session cwd.

Both files MAY define `[defaults]` (applied to every agent that pins nothing)
and `[agents.<name>]` sections (per-agent overrides). Each value is resolved
per key: the project file shadows the user file, so a partial project config
only overrides the keys it sets.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .models import THINKING_LEVELS

CONFIG_FILENAME = "superpowers-subagent.toml"

_VALID_KEYS = frozenset({"provider", "model", "reasoningEffort"})
_VALID_SECTIONS = frozenset({"defaults", "agents"})


@dataclass(frozen=True, slots=True)
class AgentOverrides:
    """Optional provider, model, and reasoning-effort values for one agent."""

    provider: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None


EMPTY_OVERRIDES = AgentOverrides()


@dataclass(frozen=True, slots=True)
class SubagentConfig:
    """Merged and validated subagent dispatch configuration."""

    defaults: AgentOverrides = EMPTY_OVERRIDES
    agents: tuple[tuple[str, AgentOverrides], ...] = ()
    paths: tuple[Path, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def overrides_for(self, name: str) -> AgentOverrides:
        """Return the per-agent overrides for ``name``, or empty overrides."""

        for agent_name, overrides in self.agents:
            if agent_name == name:
                return overrides
        return EMPTY_OVERRIDES


def load_subagent_config(cwd: Path, *, user_dir: Path | None = None) -> SubagentConfig:
    """Load and merge the user then nearest-project dispatch config files.

    Files are loaded user-first with project shadowing per key. Missing files
    are the normal case and add no diagnostics. Unreadable, malformed, or
    invalid content is skipped with a diagnostic so one broken config never
    disables dispatch.
    """

    candidates = _candidate_files(cwd, user_dir or Path.home() / ".tau")

    loaded: list[Path] = []
    diagnostics: list[str] = []
    defaults = EMPTY_OVERRIDES
    agent_sections: dict[str, AgentOverrides] = {}
    for path in candidates:
        raw = _read_toml(path, diagnostics)
        if raw is None:
            continue
        loaded.append(path)
        table_defaults, table_agents = _parse_sections(raw, path, diagnostics)
        defaults = _merge_overrides(defaults, table_defaults)
        for name, overrides in table_agents:
            agent_sections[name] = _merge_overrides(
                agent_sections.get(name, EMPTY_OVERRIDES), overrides
            )
    return SubagentConfig(
        defaults=defaults,
        agents=tuple(sorted(agent_sections.items())),
        paths=tuple(loaded),
        diagnostics=tuple(diagnostics),
    )


def _candidate_files(cwd: Path, user_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    user_file = user_dir / CONFIG_FILENAME
    if user_file.is_file():
        candidates.append(user_file)
    project_file = _nearest_project_config_file(cwd)
    if project_file is not None and project_file.resolve() != user_file.resolve():
        candidates.append(project_file)
    return candidates


def _nearest_project_config_file(cwd: Path) -> Path | None:
    current = cwd.expanduser().resolve()
    while True:
        candidate = current / ".tau" / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def _read_toml(path: Path, diagnostics: list[str]) -> dict[str, object] | None:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        diagnostics.append(f"Could not read subagent config {path}: {exc}")
        return None
    try:
        return tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        diagnostics.append(f"Invalid subagent config {path}: {exc}")
        return None


def _parse_sections(
    raw: dict[str, object],
    path: Path,
    diagnostics: list[str],
) -> tuple[AgentOverrides, list[tuple[str, AgentOverrides]]]:
    for key in sorted(set(raw) - _VALID_SECTIONS):
        diagnostics.append(f"Subagent config {path}: ignoring unknown key {key!r}")

    defaults = EMPTY_OVERRIDES
    if "defaults" in raw:
        defaults_value = raw["defaults"]
        if not isinstance(defaults_value, dict):
            diagnostics.append(f"Subagent config {path}: `defaults` must be a table")
        else:
            defaults = _parse_overrides(defaults_value, path, "defaults", diagnostics)

    agents: list[tuple[str, AgentOverrides]] = []
    if "agents" in raw:
        agents_value = raw["agents"]
        if not isinstance(agents_value, dict):
            diagnostics.append(f"Subagent config {path}: `agents` must be a table")
        else:
            for name, section_value in agents_value.items():
                if not name.strip():
                    diagnostics.append(
                        f"Subagent config {path}: `agents` keys must be non-empty names"
                    )
                    continue
                if not isinstance(section_value, dict):
                    diagnostics.append(f"Subagent config {path}: `agents.{name}` must be a table")
                    continue
                overrides = _parse_overrides(section_value, path, f"agents.{name}", diagnostics)
                agents.append((name.strip(), overrides))
    return defaults, agents


def _parse_overrides(
    table: dict[str, object],
    path: Path,
    section: str,
    diagnostics: list[str],
) -> AgentOverrides:
    for key in sorted(set(table) - _VALID_KEYS):
        diagnostics.append(f"Subagent config {path}: ignoring unknown key {section}.{key}")
    return AgentOverrides(
        provider=_parse_string(table.get("provider"), path, f"{section}.provider", diagnostics),
        model=_parse_string(table.get("model"), path, f"{section}.model", diagnostics),
        reasoning_effort=_parse_thinking_level(
            table.get("reasoningEffort"), path, f"{section}.reasoningEffort", diagnostics
        ),
    )


def _parse_string(
    value: object,
    path: Path,
    key: str,
    diagnostics: list[str],
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        diagnostics.append(f"Subagent config {path}: {key} must be a non-empty string")
        return None
    return value.strip()


def _parse_thinking_level(
    value: object,
    path: Path,
    key: str,
    diagnostics: list[str],
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        diagnostics.append(f"Subagent config {path}: {key} must be a string")
        return None
    normalized = value.strip().lower()
    if normalized not in THINKING_LEVELS:
        allowed = ", ".join(THINKING_LEVELS)
        diagnostics.append(f"Subagent config {path}: {key} must be one of: {allowed}")
        return None
    return normalized


def _merge_overrides(lower: AgentOverrides, upper: AgentOverrides) -> AgentOverrides:
    return AgentOverrides(
        provider=upper.provider if upper.provider is not None else lower.provider,
        model=upper.model if upper.model is not None else lower.model,
        reasoning_effort=(
            upper.reasoning_effort if upper.reasoning_effort is not None else lower.reasoning_effort
        ),
    )
