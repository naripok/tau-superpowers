from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from collections.abc import Callable
from pathlib import Path

import pytest
from tau_agent.messages import AssistantMessage
from tau_coding.extensions import ExtensionRuntime, ToolCallHookEvent
from tau_coding.paths import TauPaths
from tau_coding.resources import TauResourcePaths
from tau_coding.session_manager import (
    SUBAGENT_SESSION_ROLE,
    CodingSessionRecord,
    SessionManager,
)

from superpowers_subagent import runner as runner_module
from superpowers_subagent.config import AgentOverrides
from superpowers_subagent.models import AgentConfig, ChildResult, SessionSelection
from superpowers_subagent.runner import (
    _MAX_STDERR_EXCERPT_CODEPOINTS,
    ResumeFailure,
    TauChildRunner,
    _child_exit_error,
    _process_json_line,
    _stderr_excerpt,
    compose_child_prompt,
)
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


def make_store(tmp_path: Path) -> TauPaths:
    """Return a Tau session store redirected under the test directory."""

    return TauPaths(home=tmp_path / "tau-home")


def fresh_session() -> SessionSelection:
    """Return a fresh-run selection carrying a dispatcher-style generated id."""

    return SessionSelection(id=uuid.uuid4().hex)


def create_child_record(
    store: TauPaths,
    cwd: Path,
    *,
    role: str | None = SUBAGENT_SESSION_ROLE,
) -> CodingSessionRecord:
    """Pre-create one child session record, and its creation directory, in the
    redirected store."""

    cwd.mkdir(parents=True, exist_ok=True)
    return SessionManager(store).create_session(
        cwd=cwd,
        model="record-model",
        session_id=uuid.uuid4().hex,
        role=role,
    )


def write_single_record_fake_tau(tmp_path: Path, record_path: Path) -> Path:
    """Fake tau that records one invocation's argv, spawn cwd, prompt, and
    extension contents, then emits one successful assistant turn."""

    return write_fake_tau(
        tmp_path,
        r"""
import json, os, pathlib, sys
args = sys.argv[1:]
prompt = pathlib.Path(args[args.index("--append-system-prompt") + 1])
extension_paths = []
remaining = list(args)
while "-e" in remaining:
    index = remaining.index("-e")
    extension_paths.append(remaining[index + 1])
    del remaining[index : index + 2]
pathlib.Path(os.environ["FAKE_TAU_RECORD"]).write_text(json.dumps({
    "args": args,
    "cwd": os.getcwd(),
    "prompt": prompt.read_text(),
    "extensionPaths": extension_paths,
    "extensions": [pathlib.Path(path).read_text() for path in extension_paths],
}))
print(json.dumps({"type": "message_end", "message": {
    "role": "assistant", "content": [{"type": "text", "text": "done"}]
}}))
""",
    )


_RECORD_INVOCATION = r"""
import json, os, pathlib, sys
args = sys.argv[1:]
with pathlib.Path(os.environ["FAKE_TAU_LOG"]).open("a") as handle:
    handle.write(json.dumps({"args": args, "cwd": os.getcwd()}) + "\n")
"""

_SUCCESS_TURN = r"""
print(json.dumps({"type": "message_end", "message": {
    "role": "assistant", "content": [{"type": "text", "text": "done"}]
}}))
"""


def read_invocations(log_path: Path) -> list[dict]:
    return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]


def _assistant_line(
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read: int = 0,
    cache_write: int = 0,
    total_tokens: int = 0,
    cost_total: float = 0.0,
) -> bytes:
    """Build one raw JSONL ``message_end`` line carrying an assistant message."""
    return json.dumps(
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "work"}],
                "provider": "prov-a",
                "model": "model-a",
                "usage": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "cacheRead": cache_read,
                    "cacheWrite": cache_write,
                    "totalTokens": total_tokens,
                    "cost": {"total": cost_total},
                },
            },
        }
    ).encode("utf-8")


def _collection_result() -> ChildResult:
    """Return a fresh child result for direct ``_process_json_line`` collection."""
    return ChildResult(agent="implementation", agent_source="bundled", task="work", cwd="/tmp")


def _pricer(
    prices: dict[int, float],
) -> tuple[Callable[[AssistantMessage], float | None], list[AssistantMessage]]:
    """Stub the runner's estimator seam, keyed on each message's input count.

    Records every priced message so tests can prove the collection path calls
    the estimator once per message with that message's own usage. A missing key
    models a model without catalog rates and prices to ``None``.
    """
    calls: list[AssistantMessage] = []

    def price(message: AssistantMessage) -> float | None:
        calls.append(message)
        return prices.get(message.usage.input)

    return price, calls


def test_stderr_excerpt_removes_complete_csi_sequences_only() -> None:
    stderr = "before\x1b[31mred\x1b[0m\x1b[2Jafter\x1b["

    assert _stderr_excerpt(stderr) == "beforeredafter\x1b["


def test_stderr_excerpt_keeps_final_bounded_unicode_codepoints() -> None:
    assert _MAX_STDERR_EXCERPT_CODEPOINTS == 2_000
    assert _stderr_excerpt("x" + "😀" * 2_000) == "😀" * 2_000


@pytest.mark.parametrize(
    ("stderr", "guidance"),
    [
        (
            "uNkNoWn PrOvIdEr: typo-provider",
            (
                "correct the provider pin in the config file or the agent definition",
                "tau providers",
                "exact provider name",
            ),
        ),
        (
            "mOdEl Is NoT cOnFiGuReD fOr PrOvIdEr: bad-model",
            (
                "correct the model pin in the config file or the agent definition",
                "exact model ID",
                "supported by the provider",
            ),
        ),
    ],
)
def test_child_exit_error_adds_recovery_for_recognized_diagnostics(
    tmp_path: Path, stderr: str, guidance: tuple[str, ...]
) -> None:
    result = ChildResult(
        agent="worker", agent_source="user", task="task", cwd=str(tmp_path), exit_code=9
    )
    result.stderr = stderr

    error = _child_exit_error(result)

    assert "code 9" in error
    assert stderr in error
    assert all(item in error for item in guidance)
    # Recovery directs to the durable pins only: no call-level parameter exists.
    assert "omit" not in error.lower()


def test_child_exit_error_uses_only_bounded_excerpt_for_recovery(tmp_path: Path) -> None:
    result = ChildResult(
        agent="worker", agent_source="user", task="task", cwd=str(tmp_path), exit_code=9
    )
    result.stderr = "Unknown provider: stale" + "x" * 2_001

    error = _child_exit_error(result)

    assert "Unknown provider" not in error
    assert "omit provider" not in error


@pytest.mark.asyncio
async def test_runner_nonzero_exit_includes_csi_free_stderr_excerpt(tmp_path: Path) -> None:
    raw_stderr = "\x1b[31merror\x1b[2J"
    fake_tau = write_fake_tau(
        tmp_path,
        f"""import sys
sys.stderr.write({raw_stderr!r})
raise SystemExit(9)
""",
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
        session=fresh_session(),
    )

    assert result.error_message == "Tau child exited with code 9.\n\nTau stderr:\nerror"
    assert result.stderr == raw_stderr


@pytest.mark.asyncio
async def test_runner_preserves_malformed_csi_text(tmp_path: Path) -> None:
    raw_stderr = "failure\x1b["
    fake_tau = write_fake_tau(
        tmp_path,
        f"""import sys
sys.stderr.write({raw_stderr!r})
raise SystemExit(9)
""",
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
        session=fresh_session(),
    )

    assert result.error_message == f"Tau child exited with code 9.\n\nTau stderr:\n{raw_stderr}"
    assert result.stderr == raw_stderr


@pytest.mark.asyncio
async def test_runner_nonzero_exit_keeps_final_2000_unicode_codepoints(tmp_path: Path) -> None:
    raw_stderr = "\x1b[31mx" + "😀" * 2_000 + "\x1b[2J"
    excerpt = "😀" * 2_000
    fake_tau = write_fake_tau(
        tmp_path,
        f"""import sys
sys.stderr.write({raw_stderr!r})
raise SystemExit(9)
""",
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
        session=fresh_session(),
    )

    assert result.error_message == f"Tau child exited with code 9.\n\nTau stderr:\n{excerpt}"
    assert result.stderr == raw_stderr


@pytest.mark.asyncio
async def test_runner_adds_provider_and_model_recovery_from_excerpt(tmp_path: Path) -> None:
    raw_stderr = "uNkNoWn PrOvIdEr: typo-provider\nmOdEl Is NoT cOnFiGuReD fOr PrOvIdEr: bad-model"
    fake_tau = write_fake_tau(
        tmp_path,
        f"""import sys
sys.stderr.write({raw_stderr!r})
raise SystemExit(9)
""",
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
        session=fresh_session(),
    )

    assert result.error_message is not None
    assert raw_stderr in result.error_message
    assert (
        "correct the provider pin in the config file or the agent definition"
        in result.error_message
    )
    assert "exact provider name from `tau providers`" in result.error_message
    assert (
        "correct the model pin in the config file or the agent definition" in result.error_message
    )
    assert "exact model ID supported by the provider" in result.error_message
    assert "omit" not in result.error_message.lower()
    assert result.stderr == raw_stderr


@pytest.mark.asyncio
async def test_runner_preserves_existing_error_message_and_complete_stderr(tmp_path: Path) -> None:
    raw_stderr = (
        "Unknown provider: typo-provider\nModel is not configured for provider: typo-model\n"
    )
    fake_tau = write_fake_tau(
        tmp_path,
        f"""import json, sys
print(json.dumps({{"type": "message_end", "message": {{
    "role": "assistant", "content": [{{"type": "text", "text": "failed"}}],
    "errorMessage": "existing child error"
}}}}))
sys.stderr.write({raw_stderr!r})
raise SystemExit(9)
""",
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
        session=fresh_session(),
    )

    assert result.error_message == "existing child error"
    assert result.stderr == raw_stderr


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
        session=fresh_session(),
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
        "estimatedCost": 0.0,
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


def test_priced_message_accumulates_estimated_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove a priced message adds its estimate to ``estimated_cost``, flags
    ``catalog_priced``, and leaves token accumulation untouched."""
    price, _ = _pricer({3: 0.25})
    monkeypatch.setattr(runner_module, "estimated_message_cost", price)
    result = _collection_result()

    _process_json_line(
        _assistant_line(
            input_tokens=3, output_tokens=4, cache_read=5, cache_write=6, total_tokens=12
        ),
        result,
        None,
    )

    assert result.usage.estimated_cost == 0.25
    assert result.usage.catalog_priced is True
    assert result.usage.input == 3
    assert result.usage.output == 4
    assert result.usage.cache_read == 5
    assert result.usage.cache_write == 6
    assert result.usage.context_tokens == 12
    assert result.usage.turns == 1


def test_each_message_is_priced_with_its_own_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove every accepted message is priced by its own call with its own token
    breakdown, so per-message tier selection and one-hour cache splits stay
    exact instead of collapsing into one aggregated call."""
    price, calls = _pricer({3: 0.25, 7: 0.5})
    monkeypatch.setattr(runner_module, "estimated_message_cost", price)
    result = _collection_result()

    _process_json_line(_assistant_line(input_tokens=3), result, None)
    _process_json_line(_assistant_line(input_tokens=7), result, None)

    assert result.usage.estimated_cost == 0.75
    assert len(calls) == 2
    assert calls[1].usage.input == 7


def test_unpriced_message_with_reported_cost_accumulates_reported_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove a message the catalog cannot price keeps the reported-cost path:
    the provider-reported total accumulates and no estimate or pricing flag
    appears."""
    price, _ = _pricer({})
    monkeypatch.setattr(runner_module, "estimated_message_cost", price)
    result = _collection_result()

    _process_json_line(_assistant_line(input_tokens=3, cost_total=0.3), result, None)

    assert result.usage.cost == 0.3
    assert result.usage.estimated_cost == 0.0
    assert result.usage.catalog_priced is False


def test_unpriced_message_without_reported_cost_adds_no_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove an unpriced message without a provider-reported cost adds nothing
    to either cost field while its tokens still accumulate."""
    price, _ = _pricer({})
    monkeypatch.setattr(runner_module, "estimated_message_cost", price)
    result = _collection_result()

    _process_json_line(_assistant_line(input_tokens=3, output_tokens=4), result, None)

    assert result.usage.cost == 0.0
    assert result.usage.estimated_cost == 0.0
    assert result.usage.catalog_priced is False
    assert result.usage.input == 3
    assert result.usage.output == 4


def test_priced_message_also_accumulates_reported_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove a priced message with a provider-reported cost accumulates both:
    the estimate into ``estimated_cost`` and the report into ``cost``."""
    price, _ = _pricer({3: 0.25})
    monkeypatch.setattr(runner_module, "estimated_message_cost", price)
    result = _collection_result()

    _process_json_line(_assistant_line(input_tokens=3, cost_total=0.3), result, None)

    assert result.usage.estimated_cost == 0.25
    assert result.usage.cost == 0.3


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
        session=fresh_session(),
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
        session=fresh_session(),
    )

    argv = json.loads(record_path.read_text())
    assert result.succeeded
    assert argv[argv.index("--provider") + 1] == "openai"
    assert argv[argv.index("--model") + 1] == "gpt-5.6-sol"


@pytest.mark.asyncio
async def test_runner_inherits_parent_thinking_level_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove an unpinned child whose parent runs at a thinking level receives a
    thinking policy with that level, applying parent inheritance by default."""

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
        parent_reasoning_effort="medium",
        parent_provider="openai",
        parent_model="gpt-5.6-sol",
        timeout_seconds=2,
        signal=None,
        session=fresh_session(),
    )

    assert result.succeeded
    assert result.reasoning_effort == "medium"
    record = json.loads(record_path.read_text())
    assert len(record["paths"]) == 1
    thinking_path = Path(record["paths"][0])
    assert thinking_path.name == "thinking_policy.py"
    assert 'level = "medium"' in record["contents"][0]
    assert not thinking_path.exists()


@pytest.mark.asyncio
async def test_runner_prefers_config_overrides_over_agent_and_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove config-agent reasoning and model shadow the agent pin and the
    parent-session values inside the runner."""

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
    agent = make_agent(tmp_path, profile="read-only")

    result = await TauChildRunner(str(fake_tau)).run(
        default_cwd=tmp_path,
        agent=agent,
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        config_overrides=AgentOverrides(model="config/model", reasoning_effort="high"),
        parent_reasoning_effort="medium",
        parent_provider="parent-provider",
        parent_model="parent-model",
        timeout_seconds=2,
        signal=None,
        session=fresh_session(),
    )

    # make_agent pins provider "agent-provider" and model "agent-model"; the
    # config shadows model and reasoning while provider stays pinned.
    assert result.provider == "agent-provider"
    assert result.model == "config/model"
    assert result.reasoning_effort == "high"
    argv = json.loads(record_path.read_text())
    assert argv[argv.index("--model") + 1] == "config/model"
    assert argv[argv.index("--provider") + 1] == "agent-provider"


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
        session=fresh_session(),
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
        session=fresh_session(),
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
        session=fresh_session(),
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
        session=fresh_session(),
    )

    assert result.timed_out
    assert not result.cancelled
    assert result.status == "BLOCKED"
    assert "timed out" in (result.error_message or "")


@pytest.mark.asyncio
async def test_timed_out_child_keeps_estimated_cost(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a child that emits one priced message and then outlives its timeout
    finalizes with that message's estimate, so a partial child still reports
    catalog costs. Estimation runs in the parent, so the stub applies."""
    price, _ = _pricer({3: 0.5})
    monkeypatch.setattr(runner_module, "estimated_message_cost", price)
    fake_tau = write_fake_tau(
        tmp_path,
        """import json, time
print(json.dumps({"type": "message_end", "message": {
    "role": "assistant", "content": [{"type": "text", "text": "partial"}],
    "usage": {"input": 3, "output": 4, "totalTokens": 7}
}}), flush=True)
time.sleep(10)
""",
    )

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
        session=fresh_session(),
    )

    assert result.timed_out
    assert result.usage.estimated_cost == 0.5
    assert result.usage.catalog_priced is True


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
        session=fresh_session(),
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
            session=fresh_session(),
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
            session=fresh_session(),
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
    # The child contract: the complete final assistant message is relayed
    # verbatim to the controller, so it must be self-contained and end in
    # exactly one status marker; no `## Summary` mandate remains.
    assert "relayed verbatim" in prompt
    assert "last assistant message" in prompt
    for marker in (
        "**Status: DONE**",
        "**Status: DONE_WITH_CONCERNS**",
        "**Status: BLOCKED**",
        "**Status: NEEDS_CONTEXT**",
    ):
        assert marker in prompt
    assert "## Summary" not in prompt
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


class ThinkingRecorderSession:
    """Minimal bound session recording `set_thinking_level` calls."""

    def __init__(self, thinking_level: str | None) -> None:
        self.thinking_level = thinking_level
        self.set_calls: list[str] = []

    async def set_thinking_level(self, level: str) -> str:
        self.set_calls.append(level)
        return level


async def _run_generated_thinking_policy(
    tmp_path: Path,
    level: str,
    session: ThinkingRecorderSession,
) -> list[str]:
    from superpowers_subagent.runner import _THINKING_EXTENSION

    policy_path = tmp_path / "thinking_policy.py"
    policy_path.write_text(_THINKING_EXTENSION.format(level=level), encoding="utf-8")
    runtime = ExtensionRuntime()
    runtime.load(
        TauResourcePaths(
            root=tmp_path / "tau-home",
            cwd=tmp_path,
            agents_root=tmp_path / "agents-home",
        ),
        extra_paths=(policy_path,),
        include_resource_dirs=False,
    )
    runtime.bind(session)  # type: ignore[arg-type]
    await runtime.emit_session_start("startup")
    assert runtime.extension_names == ("thinking_policy",)
    return session.set_calls


@pytest.mark.asyncio
async def test_generated_thinking_policy_applies_level_at_session_start(
    tmp_path: Path,
) -> None:
    """Prove the generated child extension really runs: loading it into a Tau
    extension runtime and firing `session_start` calls `set_thinking_level`
    with the inherited level before the first turn."""

    calls = await _run_generated_thinking_policy(
        tmp_path, "high", ThinkingRecorderSession(thinking_level="medium")
    )
    assert calls == ["high"]


@pytest.mark.asyncio
async def test_generated_thinking_policy_skips_set_when_level_matches(
    tmp_path: Path,
) -> None:
    """Prove the generated extension no-ops when the child ambient level already
    equals the requested level, so uninherited children add no session work."""

    calls = await _run_generated_thinking_policy(
        tmp_path, "high", ThinkingRecorderSession(thinking_level="high")
    )
    assert calls == []


# --- Pinned child sessions and task_id resume ---


@pytest.mark.asyncio
async def test_runner_pins_every_fresh_child_to_a_new_subagent_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a fresh run pins the dispatcher-supplied session id with the
    subagent role and records that id as the result's task_id."""

    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_single_record_fake_tau(tmp_path, record_path)
    session = fresh_session()

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
        session=session,
    )

    assert result.succeeded
    assert result.task_id == session.id
    assert re.fullmatch(r"[0-9a-f]{32}", result.task_id or "")
    argv = json.loads(record_path.read_text())["args"]
    assert argv[argv.index("--session-id") + 1] == result.task_id
    assert argv[argv.index("--session-role") + 1] == "subagent"
    assert "--session" not in argv
    assert "--cwd" in argv


@pytest.mark.asyncio
async def test_runner_resumes_verified_subagent_session_without_cwd_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a verified resume reconnects with ``--session`` and the recorded
    cwd, drops ``--cwd`` and the fresh-pinning flags, and keeps the fresh-run
    flags, extensions, overrides, and positional task."""

    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_single_record_fake_tau(tmp_path, record_path)
    store = make_store(tmp_path)
    child = create_child_record(store, tmp_path / "recorded-cwd")

    result = await TauChildRunner(str(fake_tau), paths=store).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path, profile="read-only"),
        task="continue the work",
        cwd_override=None,
        provider_override=None,
        model_override="call/model",
        reasoning_effort_override="high",
        timeout_seconds=2,
        signal=None,
        session=SessionSelection(id=child.id, resume=True),
    )

    assert result.succeeded
    assert result.task_id == child.id
    assert result.cwd == str(child.cwd)
    record = json.loads(record_path.read_text())
    argv = record["args"]
    assert argv[argv.index("--session") + 1] == child.id
    assert "--session-id" not in argv
    assert "--session-role" not in argv
    assert "--cwd" not in argv
    assert "--no-extensions" in argv
    assert "--no-approve" in argv
    assert argv[-1] == "continue the work"
    assert argv[argv.index("--model") + 1] == "call/model"
    assert record["cwd"] == str(child.cwd)
    assert len(record["extensionPaths"]) == 2
    assert "Generated tool policy" in record["extensions"][0]
    assert 'level = "high"' in record["extensions"][1]
    assert record["prompt"].startswith("Original body without trailing newline")
    assert "This session continues an earlier delegated task" in record["prompt"]
    assert not any(Path(path).exists() for path in record["extensionPaths"])


@pytest.mark.asyncio
async def test_runner_missing_record_raises_resume_failure_without_starting_a_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a task_id matching no store record raises ResumeFailure before any
    child process starts: no fallback child runs and no invocation is logged."""

    log_path = tmp_path / "invocations.jsonl"
    monkeypatch.setenv("FAKE_TAU_LOG", str(log_path))
    fake_tau = write_fake_tau(tmp_path, _RECORD_INVOCATION + _SUCCESS_TURN)
    store = make_store(tmp_path)

    with pytest.raises(ResumeFailure) as excinfo:
        await TauChildRunner(str(fake_tau), paths=store).run(
            default_cwd=tmp_path,
            agent=make_agent(tmp_path),
            task="task",
            cwd_override=None,
            provider_override=None,
            model_override=None,
            reasoning_effort_override=None,
            timeout_seconds=2,
            signal=None,
            session=SessionSelection(id="missing-id", resume=True),
        )

    assert "missing-id" in str(excinfo.value)
    assert not log_path.exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [None, "user"], ids=["no-role", "other-role"])
async def test_runner_wrong_role_record_raises_resume_failure_without_starting_a_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str | None
) -> None:
    """Prove a record whose role is not the subagent role raises ResumeFailure
    before any child process starts: no fresh child runs."""

    log_path = tmp_path / "invocations.jsonl"
    monkeypatch.setenv("FAKE_TAU_LOG", str(log_path))
    fake_tau = write_fake_tau(tmp_path, _RECORD_INVOCATION + _SUCCESS_TURN)
    store = make_store(tmp_path)
    child = create_child_record(store, tmp_path / "recorded-cwd", role=role)

    with pytest.raises(ResumeFailure) as excinfo:
        await TauChildRunner(str(fake_tau), paths=store).run(
            default_cwd=tmp_path,
            agent=make_agent(tmp_path),
            task="task",
            cwd_override=None,
            provider_override=None,
            model_override=None,
            reasoning_effort_override=None,
            timeout_seconds=2,
            signal=None,
            session=SessionSelection(id=child.id, resume=True),
        )

    assert child.id in str(excinfo.value)
    assert not log_path.exists()


@pytest.mark.asyncio
async def test_runner_resumed_run_uses_the_recorded_cwd_without_a_note(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a resume call with a cwd override still spawns in the session's
    recorded creation cwd, leaves the store record's cwd unchanged, and carries
    no repair note: the note channel is removed from results."""

    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_single_record_fake_tau(tmp_path, record_path)
    store = make_store(tmp_path)
    recorded = tmp_path / "recorded-cwd"
    recorded.mkdir()
    child = create_child_record(store, recorded)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = await TauChildRunner(str(fake_tau), paths=store).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=str(elsewhere),
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
        session=SessionSelection(id=child.id, resume=True),
    )

    assert result.cwd == str(child.cwd)
    assert json.loads(record_path.read_text())["cwd"] == str(child.cwd)
    assert SessionManager(store).get_session(child.id).cwd == child.cwd
    assert not hasattr(result, "notes")


@pytest.mark.asyncio
async def test_runner_unknown_session_diagnostic_raises_resume_failure_without_a_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a resumed child that fails with tau's clean ``Unknown session:``
    diagnostic raises ResumeFailure carrying that diagnostic, and no retry
    child runs: exactly one invocation is logged."""

    log_path = tmp_path / "invocations.jsonl"
    monkeypatch.setenv("FAKE_TAU_LOG", str(log_path))
    fake_tau = write_fake_tau(
        tmp_path,
        _RECORD_INVOCATION
        + r"""if "--session" in args:
    sys.stderr.write("Unknown session: " + args[args.index("--session") + 1] + "\n")
    raise SystemExit(2)
"""
        + _SUCCESS_TURN,
    )
    store = make_store(tmp_path)
    child = create_child_record(store, tmp_path / "recorded-cwd")

    with pytest.raises(ResumeFailure) as excinfo:
        await TauChildRunner(str(fake_tau), paths=store).run(
            default_cwd=tmp_path,
            agent=make_agent(tmp_path),
            task="task",
            cwd_override=None,
            provider_override=None,
            model_override=None,
            reasoning_effort_override=None,
            timeout_seconds=2,
            signal=None,
            session=SessionSelection(id=child.id, resume=True),
        )

    assert "Unknown session:" in str(excinfo.value)
    invocations = read_invocations(log_path)
    assert len(invocations) == 1
    first_args = invocations[0]["args"]
    assert first_args[first_args.index("--session") + 1] == child.id


@pytest.mark.asyncio
async def test_runner_does_not_retry_other_resumed_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a resumed child that fails with an unrecognized diagnostic surfaces
    through the existing error path and starts no second invocation."""

    log_path = tmp_path / "invocations.jsonl"
    monkeypatch.setenv("FAKE_TAU_LOG", str(log_path))
    fake_tau = write_fake_tau(
        tmp_path,
        _RECORD_INVOCATION
        + r"""
print("Provider rejected the request: broken-input", file=sys.stderr)
raise SystemExit(2)
""",
    )
    store = make_store(tmp_path)
    child = create_child_record(store, tmp_path / "recorded-cwd")

    result = await TauChildRunner(str(fake_tau), paths=store).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
        session=SessionSelection(id=child.id, resume=True),
    )

    assert len(read_invocations(log_path)) == 1
    assert not result.succeeded
    assert result.exit_code == 2
    assert result.task_id == child.id


@pytest.mark.asyncio
async def test_runner_resumed_run_uses_the_call_agents_prompt_and_policies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a resume call names the agent whose composed prompt and policy
    extensions the resumed run uses, with no per-session agent owner."""

    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_single_record_fake_tau(tmp_path, record_path)
    store = make_store(tmp_path)
    child = create_child_record(store, tmp_path / "recorded-cwd")
    agent = AgentConfig(
        name="reviewer",
        description="Reviewer",
        system_prompt="Resumed reviewer body",
        source="user",
        file_path=tmp_path / "reviewer.md",
        profile="review",
    )

    result = await TauChildRunner(str(fake_tau), paths=store).run(
        default_cwd=tmp_path,
        agent=agent,
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
        session=SessionSelection(id=child.id, resume=True),
    )

    assert result.succeeded
    assert result.agent == "reviewer"
    assert result.task_id == child.id
    record = json.loads(record_path.read_text())
    assert record["prompt"].startswith("Resumed reviewer body")
    assert "This session continues an earlier delegated task" in record["prompt"]
    assert "Review Profile Tool Usage" in record["prompt"]
    assert len(record["extensionPaths"]) == 1
    assert '"bash"' in record["extensions"][0]


@pytest.mark.asyncio
async def test_runner_resumed_usage_covers_only_the_new_turn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove the resumed run's usage accumulates only the new turn's streamed
    messages, never the prior turns reloaded as context."""

    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_fake_tau(
        tmp_path,
        r"""
import json, sys
print(json.dumps({"type": "message_end", "message": {
    "role": "assistant", "content": [{"type": "text", "text": "new turn"}],
    "usage": {"input": 7, "output": 8, "cacheRead": 0, "cacheWrite": 0,
              "totalTokens": 15, "cost": {"total": 0.5}}
}}))
""",
    )
    store = make_store(tmp_path)
    child = create_child_record(store, tmp_path / "recorded-cwd")

    result = await TauChildRunner(str(fake_tau), paths=store).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
        session=SessionSelection(id=child.id, resume=True),
    )

    assert result.usage.input == 7
    assert result.usage.output == 8
    assert result.usage.cost == 0.5
    assert result.usage.context_tokens == 15
    assert result.usage.turns == 1


@pytest.mark.asyncio
async def test_runner_resumes_a_record_from_another_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prove a store record whose creation cwd belongs to a different project
    still verifies and resumes, because the lookup spans all project indexes."""

    record_path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_TAU_RECORD", str(record_path))
    fake_tau = write_single_record_fake_tau(tmp_path, record_path)
    store = make_store(tmp_path)
    other_project = tmp_path / "other-project"
    other_project.mkdir()
    child = create_child_record(store, other_project)

    result = await TauChildRunner(str(fake_tau), paths=store).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
        session=SessionSelection(id=child.id, resume=True),
    )

    assert result.succeeded
    assert result.task_id == child.id
    assert result.cwd == str(child.cwd)
    argv = json.loads(record_path.read_text())["args"]
    assert argv[argv.index("--session") + 1] == child.id


@pytest.mark.asyncio
async def test_runner_resumed_run_times_out_with_the_resumed_task_id(
    tmp_path: Path,
) -> None:
    store = make_store(tmp_path)
    child = create_child_record(store, tmp_path / "recorded-cwd")
    fake_tau = write_fake_tau(tmp_path, "import time\ntime.sleep(10)\n")

    result = await TauChildRunner(str(fake_tau), paths=store).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=0.05,
        signal=None,
        session=SessionSelection(id=child.id, resume=True),
    )

    assert result.timed_out
    assert result.task_id == child.id


@pytest.mark.asyncio
async def test_runner_fresh_pre_session_failures_leave_task_id_unset(
    tmp_path: Path,
) -> None:
    """Prove cancellation before spawn and a spawn OSError are pre-session
    failures: no Tau session exists, so task_id stays unset."""

    token = CancellationToken()
    token.cancelled = True
    cancelled = await TauChildRunner(str(tmp_path / "unused")).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=token,
        session=fresh_session(),
    )
    assert cancelled.cancelled
    assert cancelled.task_id is None

    missing = await TauChildRunner(str(tmp_path / "missing-tau")).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
        session=fresh_session(),
    )
    assert missing.error_message is not None
    assert missing.error_message.startswith("Could not start Tau child")
    assert missing.task_id is None


@pytest.mark.asyncio
async def test_runner_resumed_pre_spawn_failures_keep_the_verified_task_id(
    tmp_path: Path,
) -> None:
    """Prove the resume path classifies pre-spawn failures differently: the
    session was just verified to exist, so task_id keeps the verified id."""

    store = make_store(tmp_path)
    child = create_child_record(store, tmp_path / "recorded-cwd")
    token = CancellationToken()
    token.cancelled = True
    cancelled = await TauChildRunner(str(tmp_path / "unused"), paths=store).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=token,
        session=SessionSelection(id=child.id, resume=True),
    )
    assert cancelled.cancelled
    assert cancelled.task_id == child.id

    missing = await TauChildRunner(str(tmp_path / "missing-tau"), paths=store).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
        session=SessionSelection(id=child.id, resume=True),
    )
    assert missing.error_message is not None
    assert missing.error_message.startswith("Could not start Tau child")
    assert missing.task_id == child.id
    assert missing.stderr == ""


@pytest.mark.asyncio
async def test_runner_post_spawn_failures_keep_the_generated_task_id(
    tmp_path: Path,
) -> None:
    """Prove every failure after the child process spawned keeps the
    dispatcher-generated session id, so the attempt stays resumable."""

    failing = write_fake_tau(
        tmp_path,
        'import sys\nsys.stderr.write("boom\\n")\nraise SystemExit(9)\n',
    )
    failed_session = fresh_session()
    failed = await TauChildRunner(str(failing)).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=2,
        signal=None,
        session=failed_session,
    )
    assert not failed.succeeded
    assert failed.task_id == failed_session.id

    sleeping = write_fake_tau(tmp_path, "import time\ntime.sleep(10)\n")
    timed_out_session = fresh_session()
    timed_out = await TauChildRunner(str(sleeping)).run(
        default_cwd=tmp_path,
        agent=make_agent(tmp_path),
        task="task",
        cwd_override=None,
        provider_override=None,
        model_override=None,
        reasoning_effort_override=None,
        timeout_seconds=0.05,
        signal=None,
        session=timed_out_session,
    )
    assert timed_out.timed_out
    assert timed_out.task_id == timed_out_session.id


def test_compose_prompt_resume_variant_replaces_only_the_isolation_sentence(
    tmp_path: Path,
) -> None:
    """Prove the resume variant swaps the isolation paragraph for the pinned
    continuation sentence and keeps every other section unchanged."""

    resume_sentence = (
        "This session continues an earlier delegated task: the session's own prior "
        "turns are your earlier work on this task. Rely on them, this prompt, and the "
        "task input; you do not have the controller's conversation history. Do not "
        "invoke ambient user skills. That instruction is behavioral guidance, not a "
        "security boundary."
    )
    agent = make_agent(tmp_path, profile="read-only")

    resumed = compose_child_prompt(agent, resumed=True)
    fresh = compose_child_prompt(agent, resumed=False)

    assert resume_sentence in resumed
    assert "This is an isolated delegated task" not in resumed
    assert "## Response Format" in resumed
    assert "Enforced Read-Only Profile" in resumed
    assert resumed.startswith("Original body without trailing newline")
    for marker in (
        "**Status: DONE**",
        "**Status: DONE_WITH_CONCERNS**",
        "**Status: BLOCKED**",
        "**Status: NEEDS_CONTEXT**",
    ):
        assert marker in resumed
    assert fresh == compose_child_prompt(agent)
    assert "This is an isolated delegated task" in fresh
    assert "This session continues an earlier delegated task" not in fresh
