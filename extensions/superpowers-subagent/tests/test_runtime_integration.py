from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from tau_agent.events import ToolExecutionEndEvent, ToolExecutionUpdateEvent
from tau_agent.messages import AgentMessage, AssistantMessage, ToolCall
from tau_agent.provider_events import AssistantDoneEvent, AssistantStartEvent, ToolCallEndEvent
from tau_agent.session.storage import JsonlSessionStorage
from tau_agent.tools import AgentTool, AgentToolResult
from tau_agent.types import JSONValue
from tau_ai import FakeProvider
from tau_coding.extensions import ExtensionRuntime
from tau_coding.paths import TauPaths
from tau_coding.resources import TauResourcePaths
from tau_coding.session import CodingSession, CodingSessionConfig
from tau_coding.session_manager import SUBAGENT_SESSION_ROLE, SessionManager

from superpowers_subagent.models import AgentConfig
from superpowers_subagent.runner import RECURSION_GUARD, TauChildRunner

EXTENSION_DIR = Path(__file__).resolve().parents[1]
FAKE_TAU_SOURCE = Path(__file__).parent / "fixtures" / "fake_tau.py"


class RecordingSession:
    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd
        self.model = "outer-model"
        self.provider_name = "outer-provider"
        self.session_id = "integration-session"
        self.system_prompt = "integration"
        self.is_running = False
        self.messages: tuple[AgentMessage, ...] = ()

    def queue_steering_message(
        self,
        content: str,
        *,
        custom_type: str | None = None,
        details: dict[str, JSONValue] | None = None,
    ) -> None:
        del content, custom_type, details

    def queue_follow_up_message(
        self,
        content: str,
        *,
        custom_type: str | None = None,
        details: dict[str, JSONValue] | None = None,
    ) -> None:
        del content, custom_type, details

    async def append_custom_entry(self, namespace: str, data: dict[str, JSONValue]) -> None:
        del namespace, data


class InteractiveUi:
    def __init__(self, answer: bool) -> None:
        self.answer = answer
        self.confirmations: list[tuple[str, str]] = []

    @property
    def has_ui(self) -> bool:
        return True

    async def confirm(
        self,
        title: str,
        message: str,
        *,
        timeout: float | None = None,
    ) -> bool:
        del timeout
        self.confirmations.append((title, message))
        return self.answer


class CancellationToken:
    def __init__(self) -> None:
        self.cancelled = False

    def is_cancelled(self) -> bool:
        return self.cancelled


@pytest.fixture
def fake_tau_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    bin_dir = tmp_path / "fixture-bin"
    bin_dir.mkdir()
    executable = bin_dir / "tau"
    shutil.copyfile(FAKE_TAU_SOURCE, executable)
    executable.chmod(0o755)
    log_path = tmp_path / "fake-tau.jsonl"
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_TAU_LOG", str(log_path))
    return executable, log_path


def load_task_tool(
    tmp_path: Path,
    *,
    monkeypatch: pytest.MonkeyPatch,
    ui: InteractiveUi | None = None,
) -> tuple[ExtensionRuntime, AgentTool]:
    # The suite deliberately loads the real extension, so neutralize the
    # recursion guard inherited when the suite itself runs inside a
    # superpowers child (the guard makes setup() register no tools).
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    runtime = ExtensionRuntime(ui=ui) if ui is not None else ExtensionRuntime()
    runtime.load(
        TauResourcePaths(
            root=tmp_path / "tau-home",
            cwd=tmp_path,
            agents_root=tmp_path / "agents-home",
        ),
        extra_paths=(EXTENSION_DIR,),
        include_resource_dirs=False,
    )
    runtime.bind(RecordingSession(tmp_path))
    assert runtime.extension_names == ("superpowers-subagent",)
    assert [tool.name for tool in runtime.extension_tools] == ["task"]
    return runtime, runtime.extension_tools[0]


def child_results(result: AgentToolResult) -> list[dict[str, Any]]:
    assert isinstance(result.details, dict)
    assert result.details["schemaVersion"] == 2
    children = result.details["results"]
    assert isinstance(children, list)
    return children  # type: ignore[return-value]


def read_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


async def wait_for_log_event(path: Path, event: str, *, timeout: float = 2) -> None:
    async with asyncio.timeout(timeout):
        # An external process owns the append-only log, so polling is the synchronization seam.
        while not any(item.get("event") == event for item in read_log(path)):  # noqa: ASYNC110
            await asyncio.sleep(0.01)


async def collect_session_events(stream: AsyncIterator[Any]) -> list[Any]:
    return [event async for event in stream]


def tool_call_stream(arguments: dict[str, JSONValue]) -> list[object]:
    call = ToolCall(id="task-call", name="task", arguments=arguments)
    message = AssistantMessage(content=[call], model="fake")
    return [
        AssistantStartEvent(partial=AssistantMessage(model="fake")),
        ToolCallEndEvent(content_index=0, tool_call=call, partial=message),
        AssistantDoneEvent(reason="toolUse", message=message),
    ]


def final_stream() -> list[object]:
    message = AssistantMessage(content="controller done", model="fake", stop_reason="stop")
    return [
        AssistantStartEvent(partial=AssistantMessage(model="fake")),
        AssistantDoneEvent(reason="stop", message=message),
    ]


def test_real_tau_cli_loads_directory_extension_and_registers_task(tmp_path: Path) -> None:
    tau = shutil.which("tau")
    assert tau is not None
    home = tmp_path / "home"
    home.mkdir()
    environment = os.environ.copy()
    environment.update(
        {
            "HOME": str(home),
            "OPENAI_API_KEY": "unused-in-command-mode",
            "TAU_NO_UPDATE_CHECK": "1",
        }
    )
    # Same recursion-guard neutralization as load_task_tool; the spawned tau
    # must actually register the task tool.
    environment.pop(RECURSION_GUARD, None)

    completed = subprocess.run(
        [
            tau,
            "--mode",
            "json",
            "--no-extensions",
            "--no-approve",
            "-e",
            str(EXTENSION_DIR),
            "/system",
        ],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "- task: Dispatch substantive work to an isolated Tau subagent." in completed.stdout
    assert completed.stderr == ""


@pytest.mark.asyncio
async def test_real_runtime_executes_single_and_parallel_with_ordered_updates(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _executable, log_path = fake_tau_environment
    runtime, tool = load_task_tool(tmp_path, monkeypatch=monkeypatch)
    runtime.render_tool_call("task", {"prompt": "alpha", "subagent_type": "general-purpose"})

    single_updates: list[AgentToolResult] = []
    single = await tool.execute(
        "single",
        {"prompt": "alpha", "subagent_type": "general-purpose"},
        on_update=single_updates.append,
    )
    # The envelope relays the child's complete final assistant message verbatim:
    # both text blocks, no tool-call output, no extraction.
    assert single.text.startswith('<task id="')
    assert 'state="completed"' in single.text
    assert single.text.endswith("</task>")
    assert (
        "<task_result>full output for alpha\n## Summary\nsummary for alpha\n**Status: DONE**"
        "</task_result>" in single.text
    )
    assert "tool output" not in single.text
    single_child = child_results(single)[0]
    assert single_child["malformedJsonLines"] == 2
    assert len(single_child["messages"]) == 2
    # Updates: one per accepted child message plus the completion emit; the
    # envelope appears only on the final result.
    assert len(single_updates) == 3
    assert all(update.details["schemaVersion"] == 2 for update in single_updates)
    assert [update.text for update in single_updates] == ["0/1 done", "0/1 done", "1/1 done"]
    collapsed = runtime.render_tool_result("task", single, expanded=False)
    expanded = runtime.render_tool_result("task", single, expanded=True)
    # The frame shows one self-contained child component: header, streamed
    # work, delegated task, usage.
    assert collapsed is not None and "─── general-purpose" in collapsed
    assert "[bold]task[/bold] · 1/1 succeeded" in collapsed
    assert "full output for alpha" in collapsed
    assert expanded is not None and "full output for alpha" in expanded
    assert "[dim]Task:[/dim] alpha" in expanded

    concurrent_updates: list[list[AgentToolResult]] = [[], [], []]
    concurrent_calls = (
        ("one", "general-purpose"),
        ("two", "read-only"),
        ("three", "general-purpose"),
    )
    # Several task calls in one assistant message run concurrently through
    # Tau's parallel tool scheduling; the tool sets no cap on the count.
    concurrent = await asyncio.gather(
        *[
            tool.execute(
                f"parallel-{index}",
                {"prompt": prompt, "subagent_type": agent},
                on_update=concurrent_updates[index].append,
            )
            for index, (prompt, agent) in enumerate(concurrent_calls)
        ]
    )
    for index, result in enumerate(concurrent):
        prompt = concurrent_calls[index][0]
        assert f"full output for {prompt}" in result.text
        assert result.text.startswith('<task id="')
        assert "tool output" not in result.text
        assert [update.text for update in concurrent_updates[index]] == [
            "0/1 done",
            "0/1 done",
            "1/1 done",
        ]

    starts = [item for item in read_log(log_path) if item["event"] == "start"]
    assert len(starts) == 4
    # Every fresh child is pinned to a new subagent-role session and keeps the
    # fresh-run cwd flag.
    assert all(item["sessionRole"] == "subagent" for item in starts)
    assert all(re.fullmatch(r"[0-9a-f]{32}", item["sessionId"]) for item in starts)
    assert all("--cwd" in item["argv"] and "--session" not in item["argv"] for item in starts)
    assert single_child["taskId"] == starts[0]["sessionId"]
    read_only = [item for item in starts if item["policyPath"] is not None]
    assert {item["task"].splitlines()[0] for item in read_only} == {"two"}
    assert all(item["guard"] == "1" for item in starts)
    assert all(not Path(item["promptPath"]).exists() for item in starts)
    assert all(not Path(item["policyPath"]).exists() for item in read_only)


@pytest.mark.asyncio
async def test_coding_session_propagates_task_partial_updates_and_final_message_content(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del fake_tau_environment
    # Same recursion-guard neutralization as load_task_tool: the session must
    # actually register the task tool from the explicit extension path.
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    provider = FakeProvider(
        [
            tool_call_stream({"prompt": "session-child", "subagent_type": "general-purpose"}),
            final_stream(),
        ]
    )
    session = await CodingSession.load(
        CodingSessionConfig(
            provider=provider,
            model="fake",
            provider_name="fake",
            storage=JsonlSessionStorage(tmp_path / "session.jsonl"),
            cwd=tmp_path,
            resource_paths=TauResourcePaths(
                root=tmp_path / "tau-home",
                agents_root=tmp_path / "agents-home",
            ),
            extension_paths=(EXTENSION_DIR,),
            extensions_enabled=False,
            trust_override="decline",
        )
    )
    try:
        assert "task" in {tool.name for tool in session.tools}
        events = await collect_session_events(session.prompt("delegate"))
    finally:
        await session.aclose()

    updates = [event for event in events if isinstance(event, ToolExecutionUpdateEvent)]
    ended = next(event for event in events if isinstance(event, ToolExecutionEndEvent))
    assert len(updates) == 3
    assert all(update.partial_result.details["schemaVersion"] == 2 for update in updates)
    assert ended.tool_name == "task"
    # The controller sees the envelope wrapping the child's complete final message.
    assert ended.result.text.startswith('<task id="')
    assert (
        "<task_result>full output for session-child\n## Summary\n"
        "summary for session-child\n**Status: DONE**</task_result>" in ended.result.text
    )
    assert "tool output" not in ended.result.text
    assert "full output for session-child" in json.dumps(ended.result.details)
    controller_tool_result = provider.calls[1][2][-1]
    assert controller_tool_result.role == "toolResult"
    assert "full output for session-child" in controller_tool_result.text
    assert "tool output" not in controller_tool_result.text


@pytest.mark.asyncio
async def test_runtime_exposes_actionable_unknown_provider_failure_and_retains_stderr(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del fake_tau_environment
    _runtime, tool = load_task_tool(tmp_path, monkeypatch=monkeypatch)

    result = await tool.execute(
        "unknown-provider",
        {"prompt": "unknown-provider", "subagent_type": "general-purpose"},
    )

    child = child_results(result)[0]
    assert "Subagent failed (task_id: " in result.text
    assert "UnKnOwN PrOvIdEr: made-up-provider" in result.text
    assert "omit provider, model, and reasoningEffort" in result.text
    assert "tau providers" in result.text
    assert child["stderr"] == "\x1b[31mUnKnOwN PrOvIdEr: made-up-provider\x1b[0m\n"


@pytest.mark.asyncio
async def test_runtime_retains_partial_data_for_nonzero_and_protocol_failures(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    del fake_tau_environment
    _runtime, tool = load_task_tool(tmp_path, monkeypatch=monkeypatch)

    failed = await tool.execute("failed", {"prompt": "fail", "subagent_type": "general-purpose"})
    failed_child = child_results(failed)[0]
    # The child delivered a final assistant message, so task_error wraps it.
    assert failed.text.startswith('<task id="')
    assert 'state="error"' in failed.text
    assert "<task_error>full output for fail" in failed.text
    assert failed_child["exitCode"] == 7
    assert failed_child["status"] == "BLOCKED"
    assert len(failed_child["messages"]) == 2
    assert failed_child["malformedJsonLines"] == 2
    assert "stderr for fail" in failed_child["stderr"]

    protocol = await tool.execute(
        "protocol", {"prompt": "no-message", "subagent_type": "general-purpose"}
    )
    protocol_child = child_results(protocol)[0]
    assert "Subagent failed (task_id: " in protocol.text
    assert "without a valid assistant message" in protocol_child["errorMessage"]
    assert protocol_child["status"] == "BLOCKED"


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True], ids=["timeout", "cancellation"])
async def test_runtime_terminates_child_on_timeout_or_cancellation_and_retains_partial_messages(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
    cancel: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _executable, log_path = fake_tau_environment
    _runtime, tool = load_task_tool(tmp_path, monkeypatch=monkeypatch)
    token = CancellationToken()
    arguments: dict[str, JSONValue] = {
        "prompt": "sleep",
        "subagent_type": "general-purpose",
        "timeoutSeconds": 2 if cancel else 0.1,
    }

    execution = asyncio.create_task(tool.execute("stop", arguments, signal=token))
    await wait_for_log_event(log_path, "waiting")
    if cancel:
        token.cancelled = True
    result = await execution

    child = child_results(result)[0]
    assert result.text.startswith('<task id="')
    assert 'state="error"' in result.text
    assert "partial before wait" in result.text
    assert child["cancelled"] is cancel
    assert child["timedOut"] is (not cancel)
    assert child["status"] == "BLOCKED"
    assert child["messages"][-1]["content"][0]["text"] == "partial before wait"
    signal_events = [item for item in read_log(log_path) if item["event"] == "signal"]
    assert signal_events[-1]["signal"] == 15


@pytest.mark.asyncio
async def test_project_agent_approval_uses_headless_fail_closed_and_public_ui_confirmation(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _executable, log_path = fake_tau_environment
    project_agents = tmp_path / ".tau" / "agents"
    project_agents.mkdir(parents=True)
    (project_agents / "project-worker.md").write_text(
        "---\nname: project-worker\ndescription: Project worker\n---\nProject instructions.\n",
        encoding="utf-8",
    )
    arguments: dict[str, JSONValue] = {
        "prompt": "approved",
        "subagent_type": "project-worker",
        "agentScope": "project",
    }

    _headless_runtime, headless_tool = load_task_tool(tmp_path, monkeypatch=monkeypatch)
    headless = await headless_tool.execute("headless", arguments)
    assert "approval required in headless mode" in headless.text
    assert headless.details["results"] == []
    assert read_log(log_path) == []

    denied_ui = InteractiveUi(answer=False)
    _denied_runtime, denied_tool = load_task_tool(tmp_path, monkeypatch=monkeypatch, ui=denied_ui)
    denied = await denied_tool.execute("denied", arguments)
    # The denial is a pre-session failure: an error envelope with no id
    # attribute and a details entry without a taskId.
    assert '<task state="error">' in denied.text
    assert "Canceled: project-local agents were not approved." in denied.text
    assert "project-worker" in denied_ui.confirmations[0][1]
    assert "taskId" not in child_results(denied)[0]
    assert read_log(log_path) == []

    approved_ui = InteractiveUi(answer=True)
    _approved_runtime, approved_tool = load_task_tool(
        tmp_path, monkeypatch=monkeypatch, ui=approved_ui
    )
    approved = await approved_tool.execute("approved", arguments)
    assert approved.text.startswith('<task id="')
    assert 'state="completed"' in approved.text
    assert child_results(approved)[0]["agentSource"] == "project"
    assert len([item for item in read_log(log_path) if item["event"] == "start"]) == 1


class ThinkingRecordingSession(RecordingSession):
    """Recording session that also exposes a parent thinking level."""

    def __init__(self, cwd: Path) -> None:
        super().__init__(cwd)
        self.thinking_level = "medium"


@pytest.mark.asyncio
async def test_real_runtime_inherits_parent_thinking_level_and_config_overrides(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove through the real extension runtime that an unpinned child inherits
    the parent session's thinking level by default, and that a per-agent config
    section overrides lower layers, end to end into the child argv and back."""

    _executable, log_path = fake_tau_environment
    monkeypatch.delenv(RECURSION_GUARD, raising=False)
    runtime = ExtensionRuntime()
    runtime.load(
        TauResourcePaths(
            root=tmp_path / "tau-home",
            cwd=tmp_path,
            agents_root=tmp_path / "agents-home",
        ),
        extra_paths=(EXTENSION_DIR,),
        include_resource_dirs=False,
    )
    runtime.bind(ThinkingRecordingSession(tmp_path))
    tool = runtime.extension_tools[0]

    inherited = await tool.execute(
        "inherited", {"prompt": "inherit-thinking", "subagent_type": "general-purpose"}
    )
    child = child_results(inherited)[0]
    assert child["reasoningEffort"] == "medium"
    starts = [item for item in read_log(log_path) if item["event"] == "start"]
    assert len(starts) == 1
    start = starts[0]
    assert start["policyPath"] is not None
    assert Path(start["policyPath"]).name == "thinking_policy.py"
    assert 'level = "medium"' in start["policy"]

    config_home = tmp_path / "config-home"
    config_user_dir = config_home / ".tau"
    config_user_dir.mkdir(parents=True)
    config_path = config_user_dir / "superpowers-subagent.toml"
    config_path.write_text(
        '[agents.general-purpose]\nmodel = "cfg/model"\nreasoning_effort = "high"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: config_home))

    pinned = await tool.execute(
        "pinned", {"prompt": "config-pinned", "subagent_type": "general-purpose"}
    )
    pinned_child = child_results(pinned)[0]
    assert pinned_child["model"] == "cfg/model"
    assert pinned_child["reasoningEffort"] == "high"
    assert pinned.details["configPaths"] == [str(config_path)]
    pinned_start = [
        item
        for item in read_log(log_path)
        if item["event"] == "start" and item["task"] == "config-pinned"
    ][0]
    argv = pinned_start["argv"]
    assert argv[argv.index("--model") + 1] == "cfg/model"
    assert 'level = "high"' in pinned_start["policy"]

    # Agents the config never mentions stay unconfigured: the read-only agent
    # falls through to parent model and thinking level.
    config_path.write_text("", encoding="utf-8")
    unpinned = await tool.execute(
        "unpinned", {"prompt": "unpinned-work", "subagent_type": "read-only"}
    )
    unpinned_child = child_results(unpinned)[0]
    assert unpinned_child["model"] == "outer-model"
    assert unpinned_child["reasoningEffort"] == "medium"


def resume_agent(tmp_path: Path) -> AgentConfig:
    """A read-only agent distinct from the fresh call's agent, so a resume test
    can prove the resumed run regenerates the call agent's prompt and policy."""

    return AgentConfig(
        name="resume-worker",
        description="Resume worker",
        system_prompt="Resumed integration body",
        source="user",
        file_path=tmp_path / "resume-worker.md",
        profile="read-only",
    )


def create_store_record(session_id: str, cwd: Path) -> None:
    """Pre-create one subagent-role record in the default (HOME-redirected)
    session store, so a resume call's verification finds it."""

    SessionManager(TauPaths()).create_session(
        cwd=cwd,
        model="fixture-model",
        session_id=session_id,
        role=SUBAGENT_SESSION_ROLE,
    )


async def run_resumed(
    tmp_path: Path,
    *,
    agent: AgentConfig,
    task: str,
    resume_session_id: str,
    timeout_seconds: float = 2,
) -> Any:
    """Drive one resumed child through the extension-constructed runner against
    the redirected store. The dispatch wiring (tool.execute → lock → runner)
    is covered by the dispatch tests with a fake runner."""

    return await TauChildRunner().run(
        default_cwd=tmp_path,
        agent=agent,
        task=task,
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=timeout_seconds,
        signal=None,
        resume_session_id=resume_session_id,
    )


@pytest.mark.asyncio
async def test_runtime_pins_a_session_and_resumes_it(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove the full extension path pins every fresh child to a persisted
    session id, and that the same id resumes through the real session store in
    the recorded cwd with the call agent's regenerated settings."""

    _executable, log_path = fake_tau_environment
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    _runtime, tool = load_task_tool(tmp_path, monkeypatch=monkeypatch)

    pinned = await tool.execute(
        "pinned", {"prompt": "pinned work", "subagent_type": "general-purpose"}
    )
    pinned_child = child_results(pinned)[0]
    starts = [item for item in read_log(log_path) if item["event"] == "start"]
    assert len(starts) == 1
    pinned_start = starts[0]
    task_id = pinned_child["taskId"]
    assert pinned_start["sessionId"] == task_id
    assert pinned_start["sessionRole"] == "subagent"
    assert pinned_start["argv"][pinned_start["argv"].index("--session-id") + 1] == task_id
    assert "--session" not in pinned_start["argv"]
    assert "This is an isolated delegated task" in pinned_start["prompt"]

    recorded_cwd = tmp_path / "recorded-cwd"
    recorded_cwd.mkdir()
    create_store_record(task_id, recorded_cwd)

    result = await run_resumed(
        tmp_path,
        agent=resume_agent(tmp_path),
        task="continue the pinned work",
        resume_session_id=task_id,
    )

    assert result.succeeded
    assert result.task_id == task_id
    assert result.cwd == str(recorded_cwd.resolve())
    assert result.notes == ()
    assert result.usage.turns == 1
    assert result.usage.input == 2
    assert result.usage.output == 3
    starts = [item for item in read_log(log_path) if item["event"] == "start"]
    assert len(starts) == 2
    resumed_start = starts[1]
    argv = resumed_start["argv"]
    assert argv[argv.index("--session") + 1] == task_id
    assert "--session-id" not in argv
    assert "--session-role" not in argv
    assert "--cwd" not in argv
    assert "--no-extensions" in argv
    assert "--no-approve" in argv
    assert resumed_start["resumeSession"] == task_id
    assert resumed_start["cwd"] == str(recorded_cwd.resolve())
    assert resumed_start["prompt"].startswith("Resumed integration body")
    assert "This session continues an earlier delegated task" in resumed_start["prompt"]
    assert "Enforced Read-Only Profile" in resumed_start["prompt"]
    assert resumed_start["policyPath"] is not None
    assert not Path(resumed_start["promptPath"]).exists()
    assert not Path(resumed_start["policyPath"]).exists()
    assert SessionManager(TauPaths()).get_session(task_id).cwd == recorded_cwd.resolve()


@pytest.mark.asyncio
async def test_runtime_resumed_unknown_session_falls_back_to_a_fresh_child(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove a verified resume whose child reports tau's clean ``Unknown
    session:`` failure retries once as a fresh child running the call's prompt."""

    _executable, log_path = fake_tau_environment
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    _runtime, _tool = load_task_tool(tmp_path, monkeypatch=monkeypatch)

    orphan_id = uuid.uuid4().hex
    create_store_record(orphan_id, tmp_path)

    result = await run_resumed(
        tmp_path,
        agent=resume_agent(tmp_path),
        task="unknown-session",
        resume_session_id=orphan_id,
    )

    starts = [item for item in read_log(log_path) if item["event"] == "start"]
    assert len(starts) == 2
    assert starts[0]["resumeSession"] == orphan_id
    retry_argv = starts[1]["argv"]
    fresh_id = retry_argv[retry_argv.index("--session-id") + 1]
    assert re.fullmatch(r"[0-9a-f]{32}", fresh_id)
    assert fresh_id != orphan_id
    assert "--session" not in retry_argv
    assert "--cwd" in retry_argv
    assert starts[1]["task"] == "unknown-session"
    assert result.succeeded
    assert result.task_id == fresh_id
    assert result.cwd == str(tmp_path.resolve())
    assert result.notes == (f"task_id {orphan_id} matched no session, so a fresh child started.",)
