"""Agent definition parsing and deterministic Tau-path discovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from .models import (
    THINKING_LEVELS,
    AgentConfig,
    AgentProfile,
    AgentScope,
    AgentSource,
    DiscoveryResult,
)

_VALID_PROFILES: frozenset[str] = frozenset({"general-purpose", "read-only"})


class FrontmatterError(ValueError):
    """Raised when an agent definition has malformed frontmatter."""


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse dependency-free scalar YAML frontmatter and return its Markdown body."""

    if not content.startswith(("---\n", "---\r\n", "---\r")):
        raise FrontmatterError("missing opening YAML frontmatter delimiter")
    lines = content.splitlines(keepends=True)
    closing_index: int | None = None
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n") == "---":
            closing_index = index
            break
    if closing_index is None:
        raise FrontmatterError("missing closing YAML frontmatter delimiter")

    metadata: dict[str, str] = {}
    for line_number, raw_line in enumerate(lines[1:closing_index], start=2):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, raw_value = stripped.partition(":")
        key = key.strip()
        if not separator or not key:
            raise FrontmatterError(f"invalid frontmatter line {line_number}")
        if key in metadata:
            raise FrontmatterError(f"duplicate frontmatter key {key!r}")
        metadata[key] = _parse_scalar(raw_value.strip(), line_number)

    return metadata, "".join(lines[closing_index + 1 :])


def _parse_scalar(value: str, line_number: int) -> str:
    if not value:
        return ""
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise FrontmatterError(f"invalid quoted value on line {line_number}") from exc
        if not isinstance(parsed, str):
            raise FrontmatterError(f"non-string value on line {line_number}")
        return parsed
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise FrontmatterError(f"invalid quoted value on line {line_number}")
        return value[1:-1].replace("''", "'")
    if value[0] in "[{&*!|>" or value in {"null", "Null", "NULL", "~"}:
        raise FrontmatterError(f"non-string value on line {line_number}")
    comment = value.find(" #")
    if comment >= 0:
        value = value[:comment].rstrip()
    return value


def find_nearest_project_agents_dir(cwd: Path) -> Path | None:
    """Find the nearest ancestor containing a `.tau/agents` directory."""

    current = cwd.expanduser().resolve()
    while True:
        candidate = current / ".tau" / "agents"
        if candidate.is_dir():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def discover_agents(
    cwd: Path,
    scope: AgentScope,
    *,
    bundled_dir: Path | None = None,
    user_dir: Path | None = None,
) -> DiscoveryResult:
    """Discover bundled, user, and nearest-project agents with fixed precedence."""

    extension_dir = Path(__file__).resolve().parent.parent
    bundled = bundled_dir or extension_dir / "agents"
    user = user_dir or Path.home() / ".tau" / "agents"
    project = find_nearest_project_agents_dir(cwd) if scope != "user" else None

    diagnostics: list[str] = []
    selected: dict[str, AgentConfig] = {}
    layers: list[tuple[Path, AgentSource]] = [(bundled, "bundled")]
    if scope != "project":
        layers.append((user, "user"))
    if project is not None:
        layers.append((project, "project"))

    for directory, source in layers:
        for agent in _load_directory(directory, source, diagnostics):
            selected[agent.name] = agent

    return DiscoveryResult(
        agents=tuple(selected[name] for name in sorted(selected)),
        project_agents_dir=project,
        diagnostics=tuple(diagnostics),
    )


def _load_directory(
    directory: Path,
    source: AgentSource,
    diagnostics: list[str],
) -> list[AgentConfig]:
    if not directory.exists():
        return []
    try:
        entries = sorted(directory.iterdir(), key=lambda path: path.name)
    except OSError as exc:
        diagnostics.append(f"Could not read agent directory {directory}: {exc}")
        return []

    agents: list[AgentConfig] = []
    for path in entries:
        if path.suffix.lower() != ".md" or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            diagnostics.append(f"Skipped agent definition {path}: could not read UTF-8: {exc}")
            continue
        try:
            metadata, body = parse_frontmatter(content)
            agents.append(_agent_from_metadata(metadata, body, source, path))
        except (FrontmatterError, ValueError) as exc:
            diagnostics.append(f"Skipped agent definition {path}: {exc}")
    return agents


def _agent_from_metadata(
    metadata: dict[str, str],
    body: str,
    source: AgentSource,
    path: Path,
) -> AgentConfig:
    name = metadata.get("name", "").strip()
    description = metadata.get("description", "").strip()
    if not name:
        raise ValueError("`name` must be a non-empty string")
    if not description:
        raise ValueError("`description` must be a non-empty string")

    raw_profile = metadata.get("profile", "general-purpose").strip()
    if raw_profile not in _VALID_PROFILES:
        raise ValueError("`profile` must be `general-purpose` or `read-only`")
    profile = cast(AgentProfile, raw_profile)
    provider = _optional_nonempty(metadata, "provider")
    model = _optional_nonempty(metadata, "model")
    reasoning_effort = _optional_thinking_level(metadata, "reasoningEffort")
    return AgentConfig(
        name=name,
        description=description,
        system_prompt=body,
        source=source,
        file_path=path,
        profile=profile,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
    )


def _optional_nonempty(metadata: dict[str, str], key: str) -> str | None:
    if key not in metadata:
        return None
    value = metadata[key].strip()
    if not value:
        raise ValueError(f"`{key}` must be a non-empty string when provided")
    return value


def _optional_thinking_level(metadata: dict[str, str], key: str) -> str | None:
    if key not in metadata:
        return None
    value = metadata[key].strip().lower()
    if value not in THINKING_LEVELS:
        allowed = ", ".join(THINKING_LEVELS)
        raise ValueError(f"`{key}` must be one of: {allowed}")
    return value
