from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
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
from tau_coding.resources import TauResourcePaths
from tau_coding.session import CodingSession, CodingSessionConfig

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
    ui: InteractiveUi | None = None,
) -> tuple[ExtensionRuntime, AgentTool]:
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
    assert [tool.name for tool in runtime.extension_tools] == ["Task"]
    return runtime, runtime.extension_tools[0]


def child_results(result: AgentToolResult) -> list[dict[str, Any]]:
    assert isinstance(result.details, dict)
    assert result.details["schemaVersion"] == 1
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
    call = ToolCall(id="task-call", name="Task", arguments=arguments)
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
    assert "- Task: Dispatch work to an isolated Tau subagent." in completed.stdout
    assert completed.stderr == ""


@pytest.mark.asyncio
async def test_real_runtime_executes_single_parallel_and_chain_with_ordered_updates(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
) -> None:
    _executable, log_path = fake_tau_environment
    runtime, tool = load_task_tool(tmp_path)
    assert runtime.render_tool_call("Task", {"agent": "general-purpose", "task": "alpha"})

    single_updates: list[AgentToolResult] = []
    single = await tool.execute(
        "single",
        {"agent": "general-purpose", "task": "alpha"},
        on_update=single_updates.append,
    )
    assert single.text == "## Summary\nsummary for alpha\n**Status: DONE**"
    assert "full output" not in single.text
    single_child = child_results(single)[0]
    assert single_child["malformedJsonLines"] == 2
    assert len(single_child["messages"]) == 2
    assert len(single_updates) == 3
    assert all(update.details["schemaVersion"] == 1 for update in single_updates)
    collapsed = runtime.render_tool_result("Task", single, expanded=False)
    expanded = runtime.render_tool_result("Task", single, expanded=True)
    assert collapsed is not None and "1/1 succeeded" in collapsed
    assert expanded is not None and "full output for alpha" in expanded

    parallel_updates: list[AgentToolResult] = []
    parallel = await tool.execute(
        "parallel",
        {
            "tasks": [
                {"agent": "general-purpose", "task": "one"},
                {"agent": "read-only", "task": "two"},
                {"agent": "general-purpose", "task": "three"},
            ]
        },
        on_update=parallel_updates.append,
    )
    assert parallel.text.startswith("Parallel: 3/3 succeeded")
    assert [child["task"] for child in child_results(parallel)] == ["one", "two", "three"]
    assert "full output" not in parallel.text
    assert parallel_updates
    assert [child["task"] for child in child_results(parallel_updates[-1])] == [
        "one",
        "two",
        "three",
    ]

    chain_updates: list[AgentToolResult] = []
    chain = await tool.execute(
        "chain",
        {
            "chain": [
                {"agent": "general-purpose", "task": "first"},
                {"agent": "read-only", "task": "review\n{previous}"},
            ]
        },
        on_update=chain_updates.append,
    )
    assert chain.text == "## Summary\nsummary for review\n**Status: DONE**"
    chain_children = child_results(chain)
    assert [child["step"] for child in chain_children] == [1, 2]
    assert chain_children[1]["task"] == (
        "review\nfull output for first\n## Summary\nsummary for first\n**Status: DONE**"
    )
    assert any(len(child_results(update)) == 2 for update in chain_updates)

    starts = [item for item in read_log(log_path) if item["event"] == "start"]
    assert len(starts) == 6
    read_only = [item for item in starts if item["policyPath"] is not None]
    assert {item["task"].splitlines()[0] for item in read_only} == {"two", "review"}
    assert all(item["guard"] == "1" for item in starts)
    assert all(not Path(item["promptPath"]).exists() for item in starts)
    assert all(not Path(item["policyPath"]).exists() for item in read_only)


@pytest.mark.asyncio
async def test_coding_session_propagates_task_partial_updates_and_small_result_context(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
) -> None:
    del fake_tau_environment
    provider = FakeProvider(
        [
            tool_call_stream({"agent": "general-purpose", "task": "session-child"}),
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
        assert "Task" in {tool.name for tool in session.tools}
        events = await collect_session_events(session.prompt("delegate"))
    finally:
        await session.aclose()

    updates = [event for event in events if isinstance(event, ToolExecutionUpdateEvent)]
    ended = next(event for event in events if isinstance(event, ToolExecutionEndEvent))
    assert len(updates) == 3
    assert all(update.partial_result.details["schemaVersion"] == 1 for update in updates)
    assert ended.tool_name == "Task"
    assert ended.result.text == "## Summary\nsummary for session-child\n**Status: DONE**"
    assert "full output" not in ended.result.text
    assert "full output for session-child" in json.dumps(ended.result.details)
    controller_tool_result = provider.calls[1][2][-1]
    assert controller_tool_result.role == "toolResult"
    assert "full output" not in controller_tool_result.text


@pytest.mark.asyncio
async def test_runtime_retains_partial_data_for_nonzero_and_protocol_failures(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
) -> None:
    del fake_tau_environment
    _runtime, tool = load_task_tool(tmp_path)

    failed = await tool.execute("failed", {"agent": "general-purpose", "task": "fail"})
    failed_child = child_results(failed)[0]
    assert "failed" in failed.text
    assert failed_child["exitCode"] == 7
    assert failed_child["status"] == "BLOCKED"
    assert len(failed_child["messages"]) == 2
    assert failed_child["malformedJsonLines"] == 2
    assert "stderr for fail" in failed_child["stderr"]

    protocol = await tool.execute("protocol", {"agent": "general-purpose", "task": "no-message"})
    protocol_child = child_results(protocol)[0]
    assert "without a valid assistant message" in protocol_child["errorMessage"]
    assert protocol_child["status"] == "BLOCKED"


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True], ids=["timeout", "cancellation"])
async def test_runtime_terminates_child_on_timeout_or_cancellation_and_retains_partial_messages(
    tmp_path: Path,
    fake_tau_environment: tuple[Path, Path],
    cancel: bool,
) -> None:
    _executable, log_path = fake_tau_environment
    _runtime, tool = load_task_tool(tmp_path)
    token = CancellationToken()
    arguments: dict[str, JSONValue] = {
        "agent": "general-purpose",
        "task": "sleep",
        "timeoutSeconds": 2 if cancel else 0.1,
    }

    execution = asyncio.create_task(tool.execute("stop", arguments, signal=token))
    await wait_for_log_event(log_path, "waiting")
    if cancel:
        token.cancelled = True
    result = await execution

    child = child_results(result)[0]
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
) -> None:
    _executable, log_path = fake_tau_environment
    project_agents = tmp_path / ".tau" / "agents"
    project_agents.mkdir(parents=True)
    (project_agents / "project-worker.md").write_text(
        "---\nname: project-worker\ndescription: Project worker\n---\nProject instructions.\n",
        encoding="utf-8",
    )
    arguments: dict[str, JSONValue] = {
        "agent": "project-worker",
        "task": "approved",
        "agentScope": "project",
    }

    _headless_runtime, headless_tool = load_task_tool(tmp_path)
    headless = await headless_tool.execute("headless", arguments)
    assert "approval required in headless mode" in headless.text
    assert read_log(log_path) == []

    denied_ui = InteractiveUi(answer=False)
    _denied_runtime, denied_tool = load_task_tool(tmp_path, ui=denied_ui)
    denied = await denied_tool.execute("denied", arguments)
    assert denied.text.startswith("Canceled")
    assert "project-worker" in denied_ui.confirmations[0][1]
    assert read_log(log_path) == []

    approved_ui = InteractiveUi(answer=True)
    _approved_runtime, approved_tool = load_task_tool(tmp_path, ui=approved_ui)
    approved = await approved_tool.execute("approved", arguments)
    assert approved.text.startswith("## Summary")
    assert child_results(approved)[0]["agentSource"] == "project"
    assert len([item for item in read_log(log_path) if item["event"] == "start"]) == 1
