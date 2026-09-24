from pathlib import Path

import pytest

from superpowers_subagent.discovery import (
    FrontmatterError,
    discover_agents,
    find_nearest_project_agents_dir,
    parse_frontmatter,
)


def write_agent(
    directory: Path,
    filename: str,
    *,
    name: str,
    description: str = "description",
    extra: str = "",
    body: str = "Body\n",
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(
        f"---\nname: {name}\ndescription: {description}\n{extra}---\n{body}",
        encoding="utf-8",
    )
    return path


def test_parse_frontmatter_supports_quoted_scalars_and_preserves_body() -> None:
    metadata, body = parse_frontmatter(
        "---\nname: 'reviewer'\ndescription: \"Review: code\"\nmodel: team/model\n---\n\nBody\n"
    )

    assert metadata == {
        "name": "reviewer",
        "description": "Review: code",
        "model": "team/model",
    }
    assert body == "\nBody\n"

    _, crlf_body = parse_frontmatter(
        "---\r\nname: reviewer\r\ndescription: Review\r\n---\r\nBody\r\n"
    )
    assert crlf_body == "Body\r\n"


@pytest.mark.parametrize(
    "content",
    [
        "name: missing-delimiters\n",
        "---\nname: no-close\n",
        "---\nnot a pair\n---\n",
        "---\nname: one\nname: two\n---\n",
        "---\nname: [not, scalar]\n---\n",
    ],
)
def test_parse_frontmatter_rejects_malformed_documents(content: str) -> None:
    with pytest.raises(FrontmatterError):
        parse_frontmatter(content)


def test_discovery_precedence_and_lexical_order(tmp_path: Path) -> None:
    """Prove discovery without a scope argument always reads the bundled, user,
    and nearest-project layers, applies project > user > bundled collision
    precedence, orders the roster lexically, and skips the project layer when
    no ancestor carries `.tau/agents`."""
    bundled = tmp_path / "extension" / "agents"
    user = tmp_path / "home" / ".tau" / "agents"
    project = tmp_path / "repo" / ".tau" / "agents"
    cwd = tmp_path / "repo" / "nested"
    cwd.mkdir(parents=True)

    write_agent(bundled, "z.md", name="shared", body="bundled")
    write_agent(bundled, "a.md", name="alpha")
    write_agent(bundled, "u.md", name="user-only", body="bundled")
    write_agent(user, "shared.md", name="shared", body="user")
    write_agent(user, "user-only.md", name="user-only", body="user")
    write_agent(project, "shared.md", name="shared", body="project")
    write_agent(project, "project.md", name="project-only")

    result = discover_agents(cwd, bundled_dir=bundled, user_dir=user)
    assert [agent.name for agent in result.agents] == [
        "alpha",
        "project-only",
        "shared",
        "user-only",
    ]
    assert result.by_name()["shared"].source == "project"
    assert result.by_name()["shared"].system_prompt == "project"
    assert result.by_name()["user-only"].source == "user"
    assert result.by_name()["user-only"].system_prompt == "user"

    plain_cwd = tmp_path / "plain"
    plain_cwd.mkdir()
    plain = discover_agents(plain_cwd, bundled_dir=bundled, user_dir=user)
    assert [agent.name for agent in plain.agents] == ["alpha", "shared", "user-only"]
    assert plain.by_name()["shared"].source == "user"


def test_nearest_project_agents_directory_wins(tmp_path: Path) -> None:
    outer = tmp_path / ".tau" / "agents"
    inner = tmp_path / "repo" / ".tau" / "agents"
    cwd = tmp_path / "repo" / "src" / "nested"
    outer.mkdir(parents=True)
    inner.mkdir(parents=True)
    cwd.mkdir(parents=True)

    assert find_nearest_project_agents_dir(cwd) == inner


def test_default_discovery_finds_bundled_agents_without_pinned_config(tmp_path: Path) -> None:
    result = discover_agents(tmp_path, user_dir=tmp_path / "none")

    assert set(result.by_name()) == {
        "general-purpose",
        "read-only",
        "implementation",
        "code-review",
        "document-review",
    }
    assert result.by_name()["general-purpose"].profile == "general-purpose"
    assert result.by_name()["read-only"].profile == "read-only"
    assert result.by_name()["implementation"].profile == "general-purpose"
    assert result.by_name()["code-review"].profile == "review"
    assert result.by_name()["document-review"].profile == "review"
    for agent in result.agents:
        assert agent.provider is None
        assert agent.model is None
        assert agent.reasoning_effort is None


def test_invalid_agent_files_are_skipped_with_diagnostics(tmp_path: Path) -> None:
    """Prove invalid definitions are skipped with diagnostics, the stale
    `reasoningEffort` key instead produces a diagnostic, drops the pin, and
    keeps the remaining metadata, and the renamed `reasoning_effort` key keeps
    resolving while other unknown keys stay ignored without a diagnostic."""
    bundled = tmp_path / "agents"
    bundled.mkdir()
    (bundled / "broken.md").write_text("---\nname: broken\n", encoding="utf-8")
    write_agent(bundled, "profile.md", name="bad-profile", extra="profile: root\n")
    write_agent(bundled, "provider.md", name="bad-provider", extra="provider:\n")
    write_agent(bundled, "effort.md", name="bad-effort", extra="reasoningEffort: turbo\n")
    write_agent(bundled, "effort2.md", name="bad-effort-value", extra="reasoning_effort: turbo\n")
    write_agent(
        bundled,
        "valid.md",
        name="valid",
        extra=(
            "profile: read-only\n"
            "provider: local\n"
            "model: org/model\n"
            "reasoning_effort: XHIGH\n"
            "unknown: ignored\n"
        ),
    )

    result = discover_agents(tmp_path, bundled_dir=bundled, user_dir=tmp_path / "none")

    assert [agent.name for agent in result.agents] == ["bad-effort", "valid"]
    stale = result.by_name()["bad-effort"]
    assert stale.description == "description"
    assert stale.reasoning_effort is None
    valid = result.by_name()["valid"]
    assert valid.profile == "read-only"
    assert valid.provider == "local"
    assert valid.model == "org/model"
    assert valid.reasoning_effort == "xhigh"

    skipped = [d for d in result.diagnostics if d.startswith("Skipped agent definition")]
    assert len(skipped) == 4
    assert "bad-effort-value" not in result.by_name()
    stale_diagnostics = [d for d in result.diagnostics if "reasoningEffort" in d]
    assert len(stale_diagnostics) == 1
    assert str(bundled / "effort.md") in stale_diagnostics[0]
    assert len(result.diagnostics) == 5
