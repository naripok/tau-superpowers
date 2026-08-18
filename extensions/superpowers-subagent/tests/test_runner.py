from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest
from tau_coding.extensions import ToolCallHookEvent

from superpowers_subagent.models import AgentConfig
from superpowers_subagent.runner import TauChildRunner, compose_child_prompt
from superpowers_subagent.utils import final_output


class CancellationToken:
    def __init__(self) -> None:
        self.cancelled = False

    def is_cancelled(self) -> bool:
        return self.cancelled


def make_agent(tmp_path: Path, *, profile: str = "general-purpose") -> AgentConfig:
    return AgentConfig(
        name="worker",
        description="Worker",
        system_prompt="Original body without trailing newline",
        source="user",
        file_path=tmp_path / "worker.md",
        profile=profile,  # type: ignore[arg-type]
        provider="agent-provider",
        model="agent-model",
    )


def write_fake_tau(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "fake tau"
    path.write_text("#!/usr/bin/python3\n" + source, encoding="utf-8")
    path.chmod(0o755)
    return path


@pytest.mark.asyncio
async def test_runner_collects_jsonl_usage_stderr_updates_and_cleans_temp_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_fake_tau(
        tmp_path,
        r"""
import json, os, pathlib, sys
args = sys.argv[1:]
prompt = pathlib.Path(args[args.index("--append-system-prompt") + 1])
policy = pathlib.Path(args[args.index("-e") + 1]) if "-e" in args else None
record = {
    "args": args,
    "guard": os.environ.get("TAU_SUPERPOWERS_SUBAGENT"),
    "promptPath": str(prompt),
    "prompt": prompt.read_text(),
    "policyPath": str(policy) if policy else None,
    "policy": policy.read_text() if policy else None,
}
pathlib.Path(os.environ["FAKE_TAU_RECORD"]).write_text(json.dumps(record))
print(json.dumps({"type": "message_end", "message": {
    "role": "toolResult", "toolCallId": "call-1", "toolName": "read",
    "content": [{"type": "text", "text": "file"}]
}}))
print("not json")
print(json.dumps({"type": "message_end", "message": {
    "role": "assistant",
    "content": [
        {"type": "text", "text": "analysis\n"},
        {"type": "text", "text": "## Summary\nok\n**Status: DONE**"},
    ],
    "provider": "response-provider", "model": "response-model", "stopReason": "stop",
    "usage": {"input": 3, "output": 4, "cacheRead": 5, "cacheWrite": 6,
              "totalTokens": 9, "cost": {"total": 0.25}}
}}))
print("warning", file=sys.stderr)
""",
    )
    updates = []
    runner = TauChildRunner(executable=str(fake_tau))

    result = await runner.run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path, profile="read-only"),
        task="Do work",
        cwd_override=None,
        provider_override=None,
        model_override="call/model",
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
        on_message=lambda current: updates.append(len(current.messages)),
    )

    assert result.succeeded
    assert result.exit_code == 0
    assert result.status == "DONE"
    assert result.stderr == "warning\n"
    assert result.malformed_json_lines == 1
    assert len(result.messages) == 2
    assert final_output(result.messages) == "analysis\n## Summary\nok\n**Status: DONE**"
    assert result.usage.to_dict() == {
        "input": 3,
        "output": 4,
        "cacheRead": 5,
        "cacheWrite": 6,
        "cost": 0.25,
        "contextTokens": 9,
        "turns": 1,
    }
    assert result.provider == "agent-provider"
    assert result.model == "call/model"
    assert updates == [1, 2]

    record = json.loads(record_path.read_text())
    assert record["guard"] == "1"
    assert record["args"][-1] == "Do work"
    assert "--provider" in record["args"]
    assert record["args"][record["args"].index("--provider") + 1] == "agent-provider"
    assert record["args"][record["args"].index("--model") + 1] == "call/model"
    assert "-e" in record["args"]
    assert "ToolCallHookResult" in record["policy"]
    assert "event.tool_name not in _ALLOWED_TOOLS" in record["policy"]
    assert '"read"' in record["policy"]
    assert '"bash"' not in record["policy"]
    assert record["prompt"].startswith("Original body without trailing newline")
    assert "Do not invoke ambient user\nskills" in record["prompt"]
    assert "Enforced Read-Only Profile" in record["prompt"]
    assert not Path(record["promptPath"]).exists()
    assert not Path(record["policyPath"]).exists()


@pytest.mark.asyncio
async def test_general_purpose_runner_omits_policy_and_default_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_fake_tau(
        tmp_path,
        r"""
import json, os, pathlib, sys
pathlib.Path(os.environ["FAKE_TAU_RECORD"]).write_text(json.dumps(sys.argv[1:]))
print(json.dumps({"type": "message_end", "message": {
    "role": "assistant", "content": [{"type": "text", "text": "done"}]
}}))
""",
    )
    agent = make_agent(tmp_path)
    agent = AgentConfig(
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        source=agent.source,
        file_path=agent.file_path,
        profile=agent.profile,
    )

    result = await TauChildRunner(str(fake_tau)).run(
        default_cwd=tmp_path,
        agent=agent,
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
    )

    argv = json.loads(record_path.read_text())
    assert result.succeeded
    assert "-e" not in argv
    assert "--provider" not in argv
    assert "--model" not in argv


@pytest.mark.asyncio
async def test_runner_passes_parent_provider_and_model_when_agent_is_unpinned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove an unpinned child argv carries the parent session's provider and model."""

    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_fake_tau(
        tmp_path,
        r"""
import json, os, pathlib, sys
pathlib.Path(os.environ["FAKE_TAU_RECORD"]).write_text(json.dumps(sys.argv[1:]))
print(json.dumps({"type": "message_end", "message": {
    "role": "assistant", "content": [{"type": "text", "text": "done"}]
}}))
""",
    )
    agent = make_agent(tmp_path)
    agent = AgentConfig(
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        source=agent.source,
        file_path=agent.file_path,
        profile=agent.profile,
    )

    result = await TauChildRunner(str(fake_tau)).run(
        default_cwd=tmp_path,
        agent=agent,
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        parent_provider="openai",
        parent_model="gpt-5.6-sol",
        timeout_seconds=2,
        signal=None,
    )

    argv = json.loads(record_path.read_text())
    assert result.succeeded
    assert argv[argv.index("--provider") + 1] == "openai"
    assert argv[argv.index("--model") + 1] == "gpt-5.6-sol"


@pytest.mark.asyncio
async def test_runner_writes_thinking_policy_with_effective_level_and_cleans_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_fake_tau(
        tmp_path,
        r"""
import json
import os
import sys
from pathlib import Path
args = sys.argv[1:]
extension_paths = []
while "-e" in args:
    index = args.index("-e")
    extension_paths.append(args[index + 1])
    args = args[:index] + args[index + 2 :]
Path(os.environ["FAKE_TAU_RECORD"]).write_text(json.dumps({
    "paths": extension_paths,
    "contents": [Path(path).read_text() for path in extension_paths],
}))
print(json.dumps({"type": "message_end", "message": {
    "role": "assistant", "content": [{"type": "text", "text": "done"}]
}}))
""",
    )
    agent = make_agent(tmp_path, profile="read-only")

    result = await TauChildRunner(str(fake_tau)).run(
        default_cwd=tmp_path,
        agent=agent,
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override="high",
        timeout_seconds=2,
        signal=None,
    )

    assert result.succeeded
    assert result.reasoning_effort == "high"
    record = json.loads(record_path.read_text())
    assert len(record["paths"]) == 2
    thinking_path = Path(record["paths"][-1])
    assert thinking_path.name == "thinking_policy.py"
    assert "Generated tool policy" in record["contents"][0]
    assert "tool_policy.py" in record["paths"][0]
    assert 'level = "high"' in record["contents"][1]
    assert "set_thinking_level" in record["contents"][1]
    assert not thinking_path.exists()
    assert not Path(record["paths"][0]).exists()


@pytest.mark.asyncio
async def test_runner_omits_thinking_policy_without_effective_level(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_fake_tau(
        tmp_path,
        r"""
import json
import os
import sys
from pathlib import Path
Path(os.environ["FAKE_TAU_RECORD"]).write_text(json.dumps(sys.argv[1:]))
print(json.dumps({"type": "message_end", "message": {
    "role": "assistant", "content": [{"type": "text", "text": "done"}]
}}))
""",
    )
    agent = make_agent(tmp_path)
    agent = AgentConfig(
        name=agent.name,
        description=agent.description,
        system_prompt=agent.system_prompt,
        source=agent.source,
        file_path=agent.file_path,
        profile=agent.profile,
    )

    result = await TauChildRunner(str(fake_tau)).run(
        default_cwd=tmp_path,
        agent=agent,
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
    )

    argv = json.loads(record_path.read_text())
    assert result.reasoning_effort is None
    assert "-e" not in argv
    assert "--provider" not in argv
    assert "--model" not in argv


@pytest.mark.asyncio
async def test_runner_marks_zero_exit_without_assistant_as_protocol_failure(tmp_path: Path) -> None:
    fake_tau = write_fake_tau(
        tmp_path,
        'import json\nprint(json.dumps({"type": "agent_end", "messages": []}))\n',
    )

    result = await TauChildRunner(str(fake_tau)).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
    )

    assert not result.succeeded
    assert result.status == "BLOCKED"
    assert result.error_message == "Tau child exited without a valid assistant message."


@pytest.mark.asyncio
async def test_runner_times_out_and_terminates_child(tmp_path: Path) -> None:
    fake_tau = write_fake_tau(tmp_path, "import time\ntime.sleep(10)\n")

    result = await TauChildRunner(str(fake_tau)).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=0.05,
        signal=None,
    )

    assert result.timed_out
    assert not result.cancelled
    assert result.status == "BLOCKED"
    assert "timed out" in (result.error_message or "")


@pytest.mark.asyncio
async def test_runner_observes_cancellation_before_and_during_spawn(tmp_path: Path) -> None:
    fake_tau = write_fake_tau(tmp_path, "import time\ntime.sleep(10)\n")
    runner = TauChildRunner(str(fake_tau))
    token = CancellationToken()
    token.cancelled = True

    before = await runner.run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=token,
    )
    assert before.cancelled
    assert before.stop_reason == "aborted"

    token.cancelled = False
    running = asyncio.create_task(
        runner.run(
            default_cwd=tmp_path,
            agent=make_agent(tmp_path),
            task="task",
            cwd_override=None,
            provider_override=None,
            model_override=None,
            reasoning_effort_override=None,
            timeout_seconds=2,
            signal=token,
        )
    )
    await asyncio.sleep(0.1)
    token.cancelled = True
    during = await running
    assert during.cancelled
    assert during.status == "BLOCKED"


def _local_process_state(pid: int) -> str:
    """Classify a local pid as 'dead', 'zombie', or 'running' via /proc (Linux)."""
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return "dead"
    # comm may contain spaces or parentheses, so split after the last ')'.
    state = stat.rsplit(")", 1)[1].split()[0]
    return "zombie" if state == "Z" else "running"


@pytest.mark.asyncio
async def test_runner_task_cancellation_terminates_live_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a hard cancellation of the run() task kills the live child process.

    Needed because print-mode SIGINT cancels the dispatcher's task tree
    instead of flipping the cancellation token; without cleanup the child
    would be orphaned (keep running its task and consuming tokens) and its
    prompt files would be deleted mid-startup.
    """
    pid_path = tmp_path / "child.pid"
    monkeypatch.setenv("FAKE_TAU_PID", str(pid_path))
    fake_tau = write_fake_tau(
        tmp_path,
        "import os, pathlib, time\n"
        'pathlib.Path(os.environ["FAKE_TAU_PID"]).write_text(str(os.getpid()))\n'
        "time.sleep(30)\n",
    )
    running = asyncio.create_task(
        TauChildRunner(str(fake_tau)).run(
            default_cwd=tmp_path,
            agent=make_agent(tmp_path),
            task="task",
            cwd_override=None,
            provider_override=None,
            model_override=None,
            reasoning_effort_override=None,
            timeout_seconds=30,
            signal=None,
        )
    )
    deadline = time.monotonic() + 10.0
    while not pid_path.exists():
        if time.monotonic() > deadline:
            pytest.fail("fake tau child never started")
        await asyncio.sleep(0.02)
    child_pid = int(pid_path.read_text())
    await asyncio.sleep(0.1)

    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running

    deadline = time.monotonic() + 5.0
    state = _local_process_state(child_pid)
    while state == "running" and time.monotonic() < deadline:
        await asyncio.sleep(0.05)
        state = _local_process_state(child_pid)
    assert state in {"dead", "zombie"}


def _policy_handler(allowed_tools: tuple[str, ...]):
    from superpowers_subagent.runner import _profile_policy_extension

    handlers = []

    class PolicyTau:
        def on(self, event: str):
            assert event == "tool_call"

            def register(handler):
                handlers.append(handler)
                return handler

            return register

    namespace = {}
    exec(_profile_policy_extension(allowed_tools), namespace)
    namespace["setup"](PolicyTau())
    return handlers[0]


def test_generated_read_only_policy_blocks_every_tool_except_read() -> None:
    handler = _policy_handler(("read",))

    read = handler(ToolCallHookEvent(tool_name="read", arguments={}), object())
    write = handler(ToolCallHookEvent(tool_name="write", arguments={}), object())
    edit = handler(ToolCallHookEvent(tool_name="edit", arguments={}), object())
    bash = handler(ToolCallHookEvent(tool_name="bash", arguments={}), object())
    assert read is None
    assert write.block and "permits only: read" in write.reason
    assert edit.block
    assert bash.block


def test_generated_review_policy_permits_read_and_bash_only() -> None:
    handler = _policy_handler(("read", "bash"))

    read = handler(ToolCallHookEvent(tool_name="read", arguments={}), object())
    bash = handler(ToolCallHookEvent(tool_name="bash", arguments={}), object())
    write = handler(ToolCallHookEvent(tool_name="write", arguments={}), object())
    edit = handler(ToolCallHookEvent(tool_name="edit", arguments={}), object())
    assert read is None
    assert bash is None
    assert write.block and "permits only: bash, read" in write.reason
    assert edit.block


def test_compose_prompt_preserves_agent_body_as_prefix(tmp_path: Path) -> None:
    agent = make_agent(tmp_path)
    prompt = compose_child_prompt(agent)
    assert prompt.startswith(agent.system_prompt)
    assert "## Response Format" in prompt
    assert "Enforced Read-Only Profile" not in prompt
    assert "Review Profile Tool Usage" not in prompt


def test_compose_prompt_injects_profile_specific_tool_instructions(tmp_path: Path) -> None:
    read_only = compose_child_prompt(make_agent(tmp_path, profile="read-only"))
    assert "Enforced Read-Only Profile" in read_only
    assert "Review Profile Tool Usage" not in read_only

    review = compose_child_prompt(make_agent(tmp_path, profile="review"))
    assert "Review Profile Tool Usage" in review
    assert "NEVER change the state of the repository" in review
    assert "Enforced Read-Only Profile" not in review
