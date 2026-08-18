"""Tests for subagent dispatch configuration file loading and layering.

The config module reads `superpowers-subagent.toml` from the user Tau home
and the nearest ancestor project `.tau` directory, the same directories Tau
reads its other durable config files from, and merges them with project
precedence per key.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from superpowers_subagent.config import (
    CONFIG_FILENAME,
    EMPTY_OVERRIDES,
    AgentOverrides,
    load_subagent_config,
)


def test_load_without_config_files_returns_empty_config(tmp_path: Path) -> None:
    """Prove absence of any config file yields empty defaults and no diagnostics."""

    config = load_subagent_config(tmp_path, user_dir=tmp_path / ".tau")

    assert config.defaults == EMPTY_OVERRIDES
    assert config.agents == ()
    assert config.paths == ()
    assert config.diagnostics == ()


def test_load_user_config_parses_defaults_and_agents(tmp_path: Path) -> None:
    """Prove a user config file contributes defaults and per-agent overrides."""

    user_dir = tmp_path / ".tau"
    user_dir.mkdir()
    (user_dir / CONFIG_FILENAME).write_text(
        "[defaults]\n"
        'provider = "openai"\n'
        'model = "gpt-5.6-sol"\n'
        "\n"
        "[agents.worker]\n"
        'reasoningEffort = " XHIGH "\n',
        encoding="utf-8",
    )

    config = load_subagent_config(tmp_path, user_dir=user_dir)

    assert config.defaults == AgentOverrides(provider="openai", model="gpt-5.6-sol")
    assert config.overrides_for("worker") == AgentOverrides(reasoning_effort="xhigh")
    assert config.overrides_for("missing") == EMPTY_OVERRIDES
    assert config.paths == (user_dir / CONFIG_FILENAME,)
    assert config.diagnostics == ()


def test_project_config_overrides_user_config_per_key(tmp_path: Path) -> None:
    """Prove the nearest project config shadows the user config per key."""

    user_dir = tmp_path / ".tau"
    user_dir.mkdir()
    (user_dir / CONFIG_FILENAME).write_text(
        '[defaults]\nmodel = "user-model"\n\n[agents.worker]\nreasoningEffort = "medium"\n',
        encoding="utf-8",
    )
    project_dir = tmp_path / "proj" / ".tau"
    project_dir.mkdir(parents=True)
    (project_dir / CONFIG_FILENAME).write_text(
        "[defaults]\n"
        'provider = "project-provider"\n'
        'model = "project-model"\n'
        "\n"
        "[agents.worker]\n"
        'model = "project-worker-model"\n',
        encoding="utf-8",
    )

    config = load_subagent_config(
        tmp_path / "proj" / "nested",
        user_dir=user_dir,
    )

    assert config.defaults == AgentOverrides(provider="project-provider", model="project-model")
    # reasoningEffort comes from the user file, model from the project file.
    assert config.overrides_for("worker") == AgentOverrides(
        model="project-worker-model", reasoning_effort="medium"
    )
    assert config.paths == (user_dir / CONFIG_FILENAME, project_dir / CONFIG_FILENAME)
    assert config.diagnostics == ()


def test_nearest_project_config_wins_over_farther_ancestors(tmp_path: Path) -> None:
    """Prove config discovery walks only the nearest ancestor with a file."""

    user_dir = tmp_path / ".tau"
    user_dir.mkdir()
    (user_dir / CONFIG_FILENAME).write_text(
        '[defaults]\nmodel = "user-model"\n',
        encoding="utf-8",
    )
    outer_dir = tmp_path / "outer" / ".tau"
    outer_dir.mkdir(parents=True)
    (outer_dir / CONFIG_FILENAME).write_text(
        '[defaults]\nmodel = "outer-model"\n',
        encoding="utf-8",
    )
    inner_dir = tmp_path / "outer" / "inner" / ".tau"
    inner_dir.mkdir(parents=True)
    (inner_dir / CONFIG_FILENAME).write_text(
        '[defaults]\nmodel = "inner-model"\n',
        encoding="utf-8",
    )

    config = load_subagent_config(
        tmp_path / "outer" / "inner" / "deep",
        user_dir=user_dir,
    )

    assert config.defaults.model == "inner-model"
    assert config.paths[-1] == inner_dir / CONFIG_FILENAME


def test_invalid_files_are_skipped_with_diagnostics(tmp_path: Path) -> None:
    """Prove malformed TOML and wrong-typed tables produce diagnostics without
    blocking valid files, so one broken config never disables dispatch."""

    user_dir = tmp_path / ".tau"
    user_dir.mkdir()
    (user_dir / CONFIG_FILENAME).write_text("not [ valid toml\n", encoding="utf-8")
    project_dir = tmp_path / "proj" / ".tau"
    project_dir.mkdir(parents=True)
    (project_dir / CONFIG_FILENAME).write_text(
        '[defaults]\nmodel = "valid-model"\n',
        encoding="utf-8",
    )

    config = load_subagent_config(tmp_path / "proj", user_dir=user_dir)

    assert config.defaults.model == "valid-model"
    assert config.paths == (project_dir / CONFIG_FILENAME,)
    assert len(config.diagnostics) == 1
    assert "Invalid subagent config" in config.diagnostics[0]


def test_unknown_keys_and_invalid_values_are_dropped_with_diagnostics(
    tmp_path: Path,
) -> None:
    """Prove unknown keys and invalid values are ignored with actionable
    diagnostics rather than silently accepted, mirroring agent discovery."""

    user_dir = tmp_path / ".tau"
    user_dir.mkdir()
    (user_dir / CONFIG_FILENAME).write_text(
        "unknownTop = true\n"
        "\n"
        'agents = "not-a-table"\n'
        "\n"
        "[defaults]\n"
        'model = ""\n'
        'reasoningEffort = "max"\n'
        "provider = 5\n"
        'typoed = "value"\n',
        encoding="utf-8",
    )

    config = load_subagent_config(tmp_path, user_dir=user_dir)

    assert config.defaults == EMPTY_OVERRIDES
    assert config.agents == ()
    messages = config.diagnostics
    assert any("unknown key 'unknownTop'" in message for message in messages)
    assert any("defaults.model" in message for message in messages)
    assert any("defaults.reasoningEffort" in message for message in messages)
    assert any("defaults.provider" in message for message in messages)
    assert any("defaults.typoed" in message for message in messages)
    assert any("`agents` must be a table" in message for message in messages)


def test_invalid_agent_sections_are_dropped_with_diagnostics(tmp_path: Path) -> None:
    """Prove a non-table agent section and an invalid agent key are dropped."""

    user_dir = tmp_path / ".tau"
    user_dir.mkdir()
    (user_dir / CONFIG_FILENAME).write_text(
        '[agents.broken]\nmodel = 3\n\n[agents.readline]\nmodel = "x"\n',
        encoding="utf-8",
    )

    config = load_subagent_config(tmp_path, user_dir=user_dir)

    assert config.overrides_for("broken") == EMPTY_OVERRIDES
    assert config.overrides_for("readline") == AgentOverrides(model="x")
    assert any("agents.broken.model" in message for message in config.diagnostics)


def test_same_file_as_user_and_project_layer_loads_once(tmp_path: Path) -> None:
    """Prove a config file that is both the user file and the nearest project
    file (for example a session cwd under the user home) loads exactly once."""

    home = tmp_path / "home"
    user_dir = home / ".tau"
    user_dir.mkdir(parents=True)
    (user_dir / CONFIG_FILENAME).write_text(
        '[defaults]\nmodel = "once"\n',
        encoding="utf-8",
    )

    config = load_subagent_config(home, user_dir=user_dir)

    assert config.paths == (user_dir / CONFIG_FILENAME,)
    assert config.defaults.model == "once"
    assert config.diagnostics == ()


def test_unreadable_config_file_is_skipped_with_diagnostic(tmp_path: Path) -> None:
    """Prove an unreadable config file is skipped with a diagnostic rather than
    aborting dispatch, matching the malformed-TOML path."""

    user_dir = tmp_path / ".tau"
    user_dir.mkdir()
    path = user_dir / CONFIG_FILENAME
    path.write_text('[defaults]\nmodel = "x"\n', encoding="utf-8")
    path.chmod(0o000)
    try:
        config = load_subagent_config(tmp_path, user_dir=user_dir)
    finally:
        path.chmod(0o644)

    assert config.paths == ()
    assert config.defaults == EMPTY_OVERRIDES
    assert any("Could not read subagent config" in message for message in config.diagnostics)


def test_shipped_example_config_is_valid_and_encodes_current_defaults(
    tmp_path: Path,
) -> None:
    """Prove the shipped example config parses cleanly and pins the bundled
    implementation and review agents to their current defaults, so copying it
    into a dotfiles-managed `~/.tau` keeps dispatch behavior unchanged."""

    example = Path(__file__).resolve().parents[1] / "superpowers-subagent.example.toml"
    assert example.is_file()
    user_dir = tmp_path / ".tau"
    user_dir.mkdir()
    shutil.copy(example, user_dir / CONFIG_FILENAME)

    config = load_subagent_config(tmp_path, user_dir=user_dir)

    assert config.diagnostics == ()
    assert config.defaults == EMPTY_OVERRIDES
    assert config.agents == (
        (
            "code-review",
            AgentOverrides(
                provider="openrouter",
                model="deepseek/deepseek-v4-flash-0731",
                reasoning_effort="xhigh",
            ),
        ),
        (
            "document-review",
            AgentOverrides(
                provider="openrouter",
                model="deepseek/deepseek-v4-flash-0731",
                reasoning_effort="xhigh",
            ),
        ),
        (
            "implementation",
            AgentOverrides(
                provider="openrouter",
                model="deepseek/deepseek-v4-flash-0731",
                reasoning_effort="high",
            ),
        ),
    )
