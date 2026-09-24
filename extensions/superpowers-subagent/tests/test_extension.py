from __future__ import annotations

import asyncio
import types
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from tau_agent.tools import AgentToolResult

import superpowers_subagent.extension as extension_module
from superpowers_subagent.extension import setup
from superpowers_subagent.models import AgentConfig, DiscoveryResult
from superpowers_subagent.runner import RECURSION_GUARD

#: The five bundled roster lines in sorted-name order with their profile
#: annotations, shared by the layout, fallback, and drift tests.
BUNDLED_ROSTER_LINES = (
    "- code-review: Adversarial read-only code reviewer. Use for code quality review, "
    "spec compliance review, and inspection of named files. (Tools: read, bash)",
    "- document-review: Adversarial read-only document reviewer for the design workflow "
    "gates. Use for proposal review, feature-spec review, pl… (Tools: read, bash)",
    "- general-purpose: General-purpose subagent with full tool access. Use for non-trivial "
    "tasks that requires reading and writing files or ru… (Tools: all)",
    "- implementation: Implementation subagent for writing code, tests, and running "
    "verification. Use for one well-scoped implementation task… (Tools: all)",
    "- read-only: Read-only subagent for multi-file investigation of named files. Cannot "
    "modify files or run commands. Use for non-trivia… (Tools: read)",
)


class FakeContext:
    def __init__(self) -> None:
        self.cwd = Path.cwd()
        self.provider_name = "openai"
        self.model = "gpt-5.6-sol"


class FakeSessionView:
    def __init__(self, thinking_level: str | None = None) -> None:
        self.thinking_level = thinking_level


class FakeRuntime:
    def __init__(self, thinking_level: str | None = None) -> None:
        self.session_view = FakeSessionView(thinking_level)


class FakeTau:
    def __init__(self, *, thinking_level: str | None = None) -> None:
        self.tools: list[Any] = []
        self.context = FakeContext()
        self._runtime = FakeRuntime(thinking_level)
        self.handlers: dict[str, Any] = {}

    def register_tool(self, tool: Any) -> None:
        self.tools.append(tool)

    def on(self, event: str, handler: Any = None) -> Any:
        if handler is None:

            def decorator(decorated: Any) -> Any:
                self.handlers[event] = decorated
                return decorated

            return decorator
        self.handlers[event] = handler
        return handler


def _installed_tool(monkeypatch: Any, tau: FakeTau) -> Any:
    """Set up the extension without the sidebar and return the registered task tool."""
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    setup(tau)  # type: ignore[arg-type]
    assert len(tau.tools) == 1
    return tau.tools[0]


def _pin_discovery_to_user_dir(monkeypatch: Any, user_dir: Path) -> None:
    """Point the extension's discovery at an isolated user agents directory.

    The bundled layer keeps its real definitions, so roster assertions stay
    deterministic even when the running machine has its own user agents.
    """

    from superpowers_subagent import discovery as discovery_module

    def discover(cwd: Path) -> DiscoveryResult:
        return discovery_module.discover_agents(cwd, user_dir=user_dir)

    monkeypatch.setattr(extension_module, "discover_agents", discover)


def _agent_definition(name: str, description: str, profile: str) -> str:
    """Return one agent definition file's content with the given frontmatter."""
    return f"---\nname: {name}\ndescription: {description}\nprofile: {profile}\n---\n\nBody.\n"


def test_setup_registers_exactly_one_task(monkeypatch: Any) -> None:
    """Prove the task tool registers once with the flat single-object schema:
    exactly the five surviving fields, one required `prompt`, no `tasks`
    property, the 10800-second timeout cap, and unknown fields rejected by
    declaration. The removed cwd, agentScope, confirmProjectAgents, provider,
    model, and reasoningEffort properties advertise nowhere."""

    tau = FakeTau()
    tool = _installed_tool(monkeypatch, tau)

    assert [registered.name for registered in tau.tools] == ["task"]
    assert tool.label == "task"
    assert tool.prompt_snippet == "Dispatch substantive work to an isolated Tau subagent."
    assert tool.execution_mode == "parallel"
    assert tool.render_call is not None
    assert tool.render_result is not None
    parameters = tool.parameters
    assert parameters["type"] == "object"
    assert parameters["additionalProperties"] is False
    assert parameters["required"] == ["prompt"]
    properties = parameters["properties"]
    assert set(properties) == {
        "prompt",
        "subagent_type",
        "description",
        "task_id",
        "timeoutSeconds",
    }
    assert "tasks" not in properties
    for removed in (
        "cwd",
        "agentScope",
        "confirmProjectAgents",
        "provider",
        "model",
        "reasoningEffort",
    ):
        assert removed not in properties
    assert properties["prompt"]["minLength"] == 1
    assert (
        properties["prompt"]["description"] == "The child's task. The prompt is preserved verbatim."
    )
    assert properties["subagent_type"]["minLength"] == 1
    assert properties["description"]["description"] == (
        "Short orchestration label for display. No behavioral effect."
    )
    assert properties["task_id"]["minLength"] == 1
    assert properties["task_id"]["description"] == (
        "Resume a previous child session: pass the task_id from an earlier task result to "
        "continue the same subagent session instead of starting a fresh one. Requires "
        "subagent_type."
    )
    assert properties["timeoutSeconds"] == {
        "type": "number",
        "exclusiveMinimum": 0,
        "maximum": 10800,
        "default": 3600,
        "description": "Per-child timeout in seconds.",
    }


def test_task_description_carries_opencode_layout(monkeypatch: Any, tmp_path: Path) -> None:
    """Prove the description renders the OpenCode layout in order: one-liner, the
    annotated bundled roster, the default rule, when-not-to-use, and usage notes
    for multi-call parallelism, task_id reuse, and verification."""

    _pin_discovery_to_user_dir(monkeypatch, tmp_path / "absent-user-agents")
    description = _installed_tool(monkeypatch, FakeTau()).description

    one_liner = (
        "Dispatch work to an isolated Tau subagent. Delegate substantive multi-step work "
        "that benefits from an isolated context window, or long-running work that must not "
        "block this session."
    )
    default_rule = "Omit subagent_type to select general-purpose."
    when_not_to_use = (
        "When not to use: Simple reads, searches, commands, and small edits are your own "
        "tool calls, and you never dispatch work you are about to perform yourself. Never "
        "dispatch a task and then do the same work."
    )
    usage_notes = (
        "Several tasks are several task calls in one message. Use separate calls for "
        "conditional sequences where a later step depends on an earlier result.",
        "Delegated work is not duplicated.",
        "Make each prompt self-contained: children run in isolated sessions with no access "
        "to this conversation.",
        "The result names the task_id that a later call can reuse to continue the same "
        "subagent session.",
        "State whether the child writes code or does research and how to verify the result.",
        "Project-controlled agent prompts require explicit approval.",
    )
    assert description.startswith(one_liner)
    for line in BUNDLED_ROSTER_LINES:
        assert line in description
    for note in usage_notes:
        assert note in description

    markers = (one_liner, *BUNDLED_ROSTER_LINES, default_rule, when_not_to_use, "Usage notes:")
    positions = [description.find(marker) for marker in markers]
    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_subagent_type_description_carries_discovered_roster(monkeypatch: Any) -> None:
    """Prove the subagent_type description embeds the discovered roster, so the
    parameter alone teaches which agents exist and what each is for."""

    agents = (
        AgentConfig(
            name="alpha",
            description="Alpha investigates named files. " * 8,
            system_prompt="",
            source="bundled",
            file_path=Path("alpha.md"),
        ),
    )
    monkeypatch.setattr(
        extension_module,
        "discover_agents",
        lambda _cwd: DiscoveryResult(agents=agents, diagnostics=()),
    )
    subagent_type = _installed_tool(monkeypatch, FakeTau()).parameters["properties"][
        "subagent_type"
    ]

    assert "Omit subagent_type to select general-purpose." in subagent_type["description"]
    assert "- alpha: Alpha investigates named files." in subagent_type["description"]
    assert "(Tools: all)" in subagent_type["description"]


def test_roster_annotation_follows_shadowing_user_definition(
    monkeypatch: Any, tmp_path: Path
) -> None:
    """Prove a roster line renders the resolved definition's profile annotation:
    a user definition shadowing a bundled name replaces that line's annotation."""

    user_agents = tmp_path / "user-agents"
    user_agents.mkdir()
    (user_agents / "read-only.md").write_text(
        _agent_definition(
            "read-only", "User read-write investigator for named files.", "general-purpose"
        ),
        encoding="utf-8",
    )
    _pin_discovery_to_user_dir(monkeypatch, user_agents)
    description = _installed_tool(monkeypatch, FakeTau()).description

    assert "- read-only: User read-write investigator for named files. (Tools: all)" in description
    assert (
        "- read-only: Read-only subagent for multi-file investigation of named files."
        not in description
    )
    assert "- general-purpose: General-purpose subagent with full tool access." in description


def test_roster_includes_project_agents(monkeypatch: Any, tmp_path: Path) -> None:
    """Prove the description and the subagent_type description list project-layer
    agents planted at the session cwd: the session-start roster discovers the
    bundled, user, and project layers, so a task call can dispatch a project
    agent by the name the tool surface teaches."""

    project_agents = tmp_path / ".tau" / "agents"
    project_agents.mkdir(parents=True)
    (project_agents / "project-watchdog.md").write_text(
        _agent_definition("project-watchdog", "Project watchdog for repo hygiene.", "review"),
        encoding="utf-8",
    )
    _pin_discovery_to_user_dir(monkeypatch, tmp_path / "absent-user-agents")
    tau = FakeTau()
    tau.context.cwd = tmp_path
    tool = _installed_tool(monkeypatch, tau)

    roster_line = "- project-watchdog: Project watchdog for repo hygiene. (Tools: read, bash)"
    assert roster_line in tool.description
    subagent_type = tool.parameters["properties"]["subagent_type"]["description"]
    assert roster_line in subagent_type
    assert "- general-purpose: General-purpose subagent with full tool access." in tool.description


def test_setup_falls_back_to_bundled_roster_when_discovery_fails(monkeypatch: Any) -> None:
    """Discovery problems degrade to the static annotated bundled roster, never
    to no tool."""

    def broken_discovery(_cwd: Any) -> DiscoveryResult:
        raise RuntimeError("agents unavailable")

    monkeypatch.setattr(extension_module, "discover_agents", broken_discovery)
    tool = _installed_tool(monkeypatch, FakeTau())

    for line in BUNDLED_ROSTER_LINES:
        assert line in tool.description
    subagent_type = tool.parameters["properties"]["subagent_type"]["description"]
    assert BUNDLED_ROSTER_LINES[0] in subagent_type


def test_fallback_roster_matches_bundled_definitions(monkeypatch: Any, tmp_path: Path) -> None:
    """Prove the pinned fallback roster equals the real bundled definitions
    rendered in roster format, so the static text cannot drift from the agents."""

    _pin_discovery_to_user_dir(monkeypatch, tmp_path / "absent-user-agents")

    assert extension_module._agent_roster(tmp_path) == extension_module._BUNDLED_ROSTER


def test_prompt_guidelines_carry_flat_surface_rules(monkeypatch: Any) -> None:
    """Prove the guidelines teach one task per call, task_id reuse, verification,
    and placeholder coercion with a repair note, and never mention the tasks array."""

    guidelines = _installed_tool(monkeypatch, FakeTau()).prompt_guidelines
    joined = "\n".join(guidelines)

    assert "Pass exactly one task per call" in joined
    assert "The result carries the child's task_id" in joined
    assert "State whether the child writes code or does research" in joined
    assert "treats them as omitted with a repair note" in joined
    assert any(
        "isolated context window" in guideline and "long-running" in guideline
        for guideline in guidelines
    )
    assert any("replaces your own tool calls" in guideline for guideline in guidelines)
    assert any("self-contained" in guideline for guideline in guidelines)
    assert any(
        "`implementation`" in guideline and "`code-review`" in guideline for guideline in guidelines
    )
    assert any(
        "BLOCKED means" in guideline and "NEEDS_CONTEXT means" in guideline
        for guideline in guidelines
    )
    assert "`tasks`" not in joined
    assert "tasks array" not in joined


def test_task_prompt_requires_omitted_or_exact_literal_overrides(monkeypatch: Any) -> None:
    """Prove always-visible guidance prefers omission and teaches exact overrides."""

    guidance = " ".join(_installed_tool(monkeypatch, FakeTau()).prompt_guidelines).lower()
    assert "omit all three on normal calls" in guidance
    assert "this session's provider, model, and thinking level" in guidance
    assert "placeholder values" in guidance
    for placeholder in ("`default`", "`inherit`", "`auto`"):
        assert placeholder in guidance
    assert "treats them as omitted with a repair note" in guidance
    assert "exact configured provider name" in guidance
    assert "tau providers" in guidance
    assert "exact model id supported by that provider" in guidance
    for level in ("`off`", "`minimal`", "`low`", "`medium`", "`high`", "`xhigh`"):
        assert level in guidance
    assert "superpowers-subagent.toml" in guidance


def test_extension_version_stays_0_1_0() -> None:
    """Prove the extension version stays 0.1.0: the surface change rolls out by
    re-install and session restart, not by a version bump."""

    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    assert 'version = "0.1.0"' in pyproject


def test_readme_documents_literal_override_contract() -> None:
    """Prove relevant README sections define literal override relationships."""

    readme = (Path(__file__).parents[3] / "README.md").read_text()
    common_options = (
        readme.split("### Common Options\n", maxsplit=1)[1].split("\n### ", maxsplit=1)[0].lower()
    )
    for field in ("provider", "model", "reasoningEffort"):
        row = next(
            line
            for line in common_options.splitlines()
            if line.startswith(f"| `{field.lower()}` |")
        )
        assert f"optional literal {field.lower()} override" in row
        assert "omit it to inherit configuration" in row

    selection = (
        readme.split("## Provider, Model, and Thinking Effort Selection\n", maxsplit=1)[1]
        .split("\n## ", maxsplit=1)[0]
        .lower()
    )
    for placeholder in ("`default`", "`inherit`", "`auto`"):
        assert placeholder in selection
    assert "placeholders, not values" in selection
    assert "treats them as omitted and reports a repair note" in selection
    assert "fail before any child starts" in selection
    provider_row = next(
        line for line in common_options.splitlines() if line.startswith("| `provider` |")
    )
    assert "exact configured provider name from `tau providers`" in provider_row
    assert "model id supported by the selected provider" in selection


def test_setup_refuses_recursive_registration(monkeypatch: Any) -> None:
    monkeypatch.setenv(RECURSION_GUARD, "1")
    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]

    assert tau.tools == []


@pytest.mark.asyncio
async def test_execute_task_loads_config_per_call(monkeypatch: Any) -> None:
    """Prove each task call rescans the config file so edits apply without a
    Tau reload, mirroring how discovery rescans agent definitions."""

    captured: dict[str, Any] = {}
    loads = []

    class FakeDispatcher:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def execute(
            self,
            arguments: Mapping[str, Any],
            signal: Any = None,
            on_update: Any = None,
        ) -> AgentToolResult:
            del arguments, signal, on_update
            return AgentToolResult(content=[])

    class FakeConfig:
        pass

    def fake_load(cwd: Path) -> FakeConfig:
        loads.append(cwd)
        return FakeConfig()

    monkeypatch.setattr(extension_module, "TaskDispatcher", FakeDispatcher)
    monkeypatch.setattr(extension_module, "load_subagent_config", fake_load)
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]
    for _ in range(2):
        await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
            "call", {"prompt": "work", "subagent_type": "read-only"}, None, None
        )

    assert loads == [Path.cwd(), Path.cwd()]
    assert isinstance(captured["config"], FakeConfig)


@pytest.mark.asyncio
async def test_execute_task_passes_parent_session_provider_and_model(
    monkeypatch: Any,
) -> None:
    """Prove the task tool binds the parent session's active provider and model to
    dispatch, so unpinned children inherit them unless the call or agent pins them."""

    captured: dict[str, Any] = {}

    class FakeDispatcher:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def execute(
            self,
            arguments: Mapping[str, Any],
            signal: Any = None,
            on_update: Any = None,
        ) -> AgentToolResult:
            del arguments, signal, on_update
            return AgentToolResult(content=[])

    monkeypatch.setattr(extension_module, "TaskDispatcher", FakeDispatcher)
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-1", {"prompt": "work", "subagent_type": "general-purpose"}, None, None
    )

    assert captured["parent_provider"] == "openai"
    assert captured["parent_model"] == "gpt-5.6-sol"
    assert captured["parent_reasoning_effort"] is None
    assert captured["default_cwd"] == Path.cwd()

    tau.context.provider_name = ""
    tau.context.model = ""
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-2", {"prompt": "work", "subagent_type": "general-purpose"}, None, None
    )

    assert captured["parent_provider"] is None
    assert captured["parent_model"] is None


@pytest.mark.asyncio
async def test_execute_task_reads_parent_session_thinking_level(monkeypatch: Any) -> None:
    """Prove the task tool forwards the parent session's active thinking level
    through the extension runtime view so unpinned children inherit it."""

    captured: dict[str, Any] = {}

    class FakeDispatcher:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def execute(
            self,
            arguments: Mapping[str, Any],
            signal: Any = None,
            on_update: Any = None,
        ) -> AgentToolResult:
            del arguments, signal, on_update
            return AgentToolResult(content=[])

    monkeypatch.setattr(extension_module, "TaskDispatcher", FakeDispatcher)
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    monkeypatch.setattr(extension_module, "install_sidebar_section", lambda _tracker: None)
    tau = FakeTau(thinking_level="medium")

    setup(tau)  # type: ignore[arg-type]
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-1", {"prompt": "work", "subagent_type": "read-only"}, None, None
    )

    assert captured["parent_reasoning_effort"] == "medium"

    # A Tau version without the runtime seam yields None instead of crashing.
    del tau._runtime
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call-2", {"prompt": "work", "subagent_type": "read-only"}, None, None
    )
    assert captured["parent_reasoning_effort"] is None


@pytest.mark.asyncio
async def test_execute_task_wires_tracker_as_usage_observer(monkeypatch: Any) -> None:
    """Prove the dispatcher's usage observer feeds the sidebar tracker and the
    registered session_start handler resets it on rebinds but not otherwise."""

    from superpowers_subagent.models import ChildResult, UsageStats

    captured: dict[str, Any] = {}
    installed: dict[str, Any] = {}

    class FakeDispatcher:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def execute(
            self,
            arguments: Mapping[str, Any],
            signal: Any = None,
            on_update: Any = None,
        ) -> AgentToolResult:
            del arguments, signal, on_update
            return AgentToolResult(content=[])

    def fake_install(tracker: Any) -> None:
        installed["tracker"] = tracker

    monkeypatch.setattr(extension_module, "TaskDispatcher", FakeDispatcher)
    monkeypatch.setattr(extension_module, "install_sidebar_section", fake_install)
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    tau = FakeTau()

    setup(tau)  # type: ignore[arg-type]
    tracker = installed["tracker"]
    # The dispatcher is constructed per call, so a call must run before the
    # captured kwargs exist.
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call", {"prompt": "work", "subagent_type": "general-purpose"}, None, None
    )

    assert callable(captured["usage_observer"])
    assert "session_start" in tau.handlers

    tracked = ChildResult(
        agent="a",
        agent_source="bundled",
        task="t",
        cwd="/w",
        exit_code=0,
        usage=UsageStats(input=10, output=5),
    )
    captured["usage_observer"]([tracked], True)
    assert tracker.totals.runs == 1

    handler = tau.handlers["session_start"]
    handler(types.SimpleNamespace(reason="startup"), None)
    assert tracker.totals.runs == 1
    handler(types.SimpleNamespace(reason="reload"), None)
    assert tracker.totals.runs == 1
    handler(types.SimpleNamespace(), None)
    assert tracker.totals.runs == 1
    for reason in ("new", "resume", "branch"):
        handler(types.SimpleNamespace(reason=reason), None)
        assert tracker.totals.runs == 0
        captured["usage_observer"]([tracked], True)
        assert tracker.totals.runs == 1


def test_reset_tracker_on_rebind_reasons() -> None:
    """Prove totals reset only for new, resumed, or branched sessions, not at
    startup or reload, so the accumulation stays scoped to the active session."""

    from superpowers_subagent.extension import _reset_tracker_on_rebind
    from superpowers_subagent.models import ChildResult, UsageStats
    from superpowers_subagent.usage import SubagentUsageTracker

    tracker = SubagentUsageTracker()
    tracker.update(
        "call-1",
        [
            ChildResult(
                agent="a",
                agent_source="bundled",
                task="t",
                cwd="/w",
                exit_code=0,
                usage=UsageStats(input=10, output=5),
            )
        ],
        True,
    )

    _reset_tracker_on_rebind(tracker, types.SimpleNamespace(reason="startup"))
    assert tracker.totals.runs == 1
    _reset_tracker_on_rebind(tracker, types.SimpleNamespace(reason="reload"))
    assert tracker.totals.runs == 1
    _reset_tracker_on_rebind(tracker, types.SimpleNamespace(reason="resume"))
    assert tracker.totals.runs == 0


@pytest.mark.asyncio
async def test_execute_task_discards_pending_on_hard_cancellation(monkeypatch: Any) -> None:
    """Prove a hard cancellation of the dispatch propagates and drops the
    in-flight snapshot, so stale partial usage cannot stay displayed."""

    from superpowers_subagent.models import ChildResult, UsageStats

    captured: dict[str, Any] = {}
    installed: dict[str, Any] = {}
    calls = 0

    class FakeDispatcher:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

        async def execute(
            self,
            arguments: Mapping[str, Any],
            signal: Any = None,
            on_update: Any = None,
        ) -> AgentToolResult:
            del arguments, signal, on_update
            nonlocal calls
            calls += 1
            if calls > 1:
                raise asyncio.CancelledError()
            return AgentToolResult(content=[])

    def fake_install(tracker: Any) -> None:
        installed["tracker"] = tracker

    monkeypatch.setattr(extension_module, "TaskDispatcher", FakeDispatcher)
    monkeypatch.setattr(extension_module, "install_sidebar_section", fake_install)
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    tau = FakeTau()
    setup(tau)  # type: ignore[arg-type]
    tracker = installed["tracker"]
    # The dispatcher is built per call, so one benign call under the same tool
    # call id binds and captures the observer that later feeds the pending
    # snapshot; its hard-cancelled twin must be the same call so the finally
    # drops exactly that call's snapshot.
    await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
        "call", {"prompt": "work", "subagent_type": "read-only"}, None, None
    )
    captured["usage_observer"](
        [
            ChildResult(
                agent="a",
                agent_source="bundled",
                task="t",
                cwd="/w",
                exit_code=0,
                usage=UsageStats(input=10, output=5),
            )
        ],
        False,
    )
    assert tracker.totals.runs == 1

    with pytest.raises(asyncio.CancelledError):
        await tau.tools[0].execute_fn(  # type: ignore[attr-defined]
            "call", {"prompt": "work", "subagent_type": "read-only"}, None, None
        )

    assert tracker.totals.runs == 0
