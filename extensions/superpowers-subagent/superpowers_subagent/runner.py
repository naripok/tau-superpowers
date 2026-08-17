"""Asynchronous Tau child process execution and JSONL collection."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import cast

from pydantic import TypeAdapter, ValidationError
from tau_agent.messages import AgentMessage, AssistantMessage, ToolResultMessage
from tau_agent.tools import ToolCancellationToken

from .models import AgentConfig, ChildResult
from .utils import (
    build_tau_argv,
    effective_provider_model,
    effective_reasoning_effort,
    final_output,
    parse_status,
    resolve_child_cwd,
)

RECURSION_GUARD = "TAU_SUPERPOWERS_SUBAGENT"

_SHARED_INSTRUCTIONS = """## Delegated Task Rules

This is an isolated delegated task. Rely only on this prompt and the task input;
you do not have the controller's conversation history. Do not invoke ambient user
skills. That instruction is behavioral guidance, not a security boundary.

## Response Format

End your response with an exact `## Summary` heading and a concise summary covering
what you accomplished or found, files read or modified, tests, errors, and concerns.

End the summary with exactly one supported status marker:

- **Status: DONE**
- **Status: DONE_WITH_CONCERNS**
- **Status: BLOCKED**
- **Status: NEEDS_CONTEXT**
"""

_READ_ONLY_INSTRUCTIONS = """## Enforced Read-Only Profile

Only the `read` tool is permitted. Do not call `bash`, `write`, `edit`, or any other
tool. If named-file reads are insufficient, report `NEEDS_CONTEXT` and request the
missing command output from the controller. A Tau tool-call hook enforces this profile,
but it is not an OS, filesystem, network, credential, model, or provider sandbox.
"""

_REVIEW_INSTRUCTIONS = """## Review Profile Tool Usage

You have Tau's `read` tool and the `bash` tool. Use `bash` strictly for read-only
operations that aid the review: `git diff`, `git log`, `git show`, `git status`,
`grep`/`rg`/`find` searches, and listing or reading files whose exact paths you do
not know. NEVER change the state of the repository or your environment: no git
commands that write (commit, push, checkout, stash, reset, rebase, apply, clean), no
file or directory creation, modification, deletion, or moving, no package installs,
no test or build runs (they write caches and artifacts), and no background or
long-running processes. If completing the review requires a state change, report
exactly what is needed and let the controller perform it. `write`, `edit`, and all
other state-changing Tau tools remain blocked by the tool policy. This policy is a
Tau tool-call hook, not an OS, filesystem, network, credential, model, or provider
sandbox.
"""


_ALLOWED_TOOLS_BY_PROFILE: dict[str, tuple[str, ...]] = {
    "read-only": ("read",),
    "review": ("read", "bash"),
}


def _profile_policy_extension(allowed_tools: tuple[str, ...]) -> str:
    """Generate a tool policy extension permitting exactly ``allowed_tools``."""

    quoted = ", ".join(f'"{tool}"' for tool in sorted(allowed_tools))
    plain = ", ".join(sorted(allowed_tools))
    return f'''"""Generated tool policy for one delegated Tau child."""

from tau_coding.extensions import ExtensionAPI, ToolCallHookEvent, ToolCallHookResult

_ALLOWED_TOOLS: frozenset[str] = frozenset({{{quoted}}})


def setup(tau: ExtensionAPI) -> None:
    @tau.on("tool_call")
    def permit_profile_tools(event: object, _context: object) -> ToolCallHookResult | None:
        if isinstance(event, ToolCallHookEvent) and event.tool_name not in _ALLOWED_TOOLS:
            return ToolCallHookResult(
                block=True,
                reason="subagent profile permits only: {plain}",
            )
        return None
'''


_THINKING_EXTENSION = '''"""Generated reasoning-effort setter for one delegated Tau child.

Tau 0.3 has no CLI flag or public extension hook for the startup thinking
level, so the child session's own `set_thinking_level` API is invoked at
`session_start`; it validates the level against the provider/model catalog and
rebuilds the runtime provider before the first turn. The session handle is
reached through the extension runtime's bound-session view (``tau._runtime``),
which is the only reachable handle; if any part of that seam is missing or the
level is unsupported, a diagnostic is printed to stderr and the child proceeds
with its ambient level.
"""

from __future__ import annotations

import sys


def setup(tau: object) -> None:
    @tau.on("session_start")  # type: ignore[attr-defined]
    async def apply_reasoning_effort(_event: object, _context: object) -> None:
        level = "{level}"
        try:
            runtime = getattr(tau, "_runtime", None)
            session = getattr(runtime, "session_view", None) if runtime is not None else None
            if session is None:
                raise RuntimeError("session not reachable through this Tau version")
            set_level = getattr(session, "set_thinking_level", None)
            if set_level is None:
                raise RuntimeError("Tau session has no set_thinking_level API")
            if getattr(session, "thinking_level", None) != level:
                await set_level(level)
        except Exception as exc:  # noqa: BLE001 - diagnostics must never crash the child
            print(
                f"[superpowers-subagent] could not apply reasoning effort {level}: {{exc}}",
                file=sys.stderr,
                flush=True,
            )
'''

_MESSAGE_ADAPTER: TypeAdapter[AgentMessage] = TypeAdapter(AgentMessage)
ChildUpdate = Callable[[ChildResult], None]


class TauChildRunner:
    """Run one agent in an isolated Tau subprocess."""

    def __init__(self, executable: str = "tau") -> None:
        self.executable = executable

    async def run(
        self,
        *,
        default_cwd: Path,
        agent: AgentConfig,
        task: str,
        cwd_override: str | None,
        provider_override: str | None,
        model_override: str | None,
        reasoning_effort_override: str | None,
        parent_provider: str | None = None,
        parent_model: str | None = None,
        timeout_seconds: float,
        signal: ToolCancellationToken | None,
        step: int | None = None,
        on_message: ChildUpdate | None = None,
    ) -> ChildResult:
        """Launch and collect one child, retaining partial state on every exit path."""

        cwd = resolve_child_cwd(default_cwd, cwd_override)
        provider, model = effective_provider_model(
            agent,
            provider_override,
            model_override,
            parent_provider=parent_provider,
            parent_model=parent_model,
        )
        reasoning_effort = effective_reasoning_effort(agent, reasoning_effort_override)
        result = ChildResult(
            agent=agent.name,
            agent_source=agent.source,
            task=task,
            cwd=str(cwd),
            provider=provider,
            model=model,
            reasoning_effort=reasoning_effort,
            step=step,
        )
        if _is_cancelled(signal):
            result.cancelled = True
            result.stop_reason = "aborted"
            result.error_message = "Dispatch cancelled before child process started."
            return result

        prompt = compose_child_prompt(agent)
        with tempfile.TemporaryDirectory(prefix="tau-subagent-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            prompt_path = temp_dir / "prompt.md"
            prompt_path.write_text(prompt, encoding="utf-8")
            prompt_path.chmod(0o600)
            policy_path: Path | None = None
            if agent.profile in _ALLOWED_TOOLS_BY_PROFILE:
                policy_path = temp_dir / "tool_policy.py"
                policy_path.write_text(
                    _profile_policy_extension(_ALLOWED_TOOLS_BY_PROFILE[agent.profile]),
                    encoding="utf-8",
                )
                policy_path.chmod(0o600)
            thinking_policy_path: Path | None = None
            if reasoning_effort is not None:
                thinking_policy_path = temp_dir / "thinking_policy.py"
                thinking_policy_path.write_text(
                    _THINKING_EXTENSION.format(level=reasoning_effort),
                    encoding="utf-8",
                )
                thinking_policy_path.chmod(0o600)

            argv = build_tau_argv(
                executable=self.executable,
                cwd=cwd,
                prompt_path=prompt_path,
                task=task,
                provider=provider,
                model=model,
                policy_path=policy_path,
                thinking_policy_path=thinking_policy_path,
            )
            environment = os.environ.copy()
            environment[RECURSION_GUARD] = "1"
            try:
                process = await asyncio.create_subprocess_exec(
                    *argv,
                    cwd=str(cwd),
                    env=environment,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    limit=10 * 1024 * 1024,
                )
            except (OSError, ValueError) as exc:
                result.error_message = f"Could not start Tau child: {exc}"
                return result

            assert process.stdout is not None
            assert process.stderr is not None
            stdout_task = asyncio.create_task(_collect_stdout(process.stdout, result, on_message))
            stderr_task = asyncio.create_task(process.stderr.read())
            wait_task = asyncio.create_task(process.wait())
            cancellation_task: asyncio.Task[None] | None = None
            if signal is not None:
                cancellation_task = asyncio.create_task(_wait_for_cancellation(signal))

            controls: set[asyncio.Task[object]] = {cast("asyncio.Task[object]", wait_task)}
            if cancellation_task is not None:
                controls.add(cast("asyncio.Task[object]", cancellation_task))
            done, _ = await asyncio.wait(
                controls,
                timeout=timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if wait_task not in done:
                if cancellation_task is not None and cancellation_task in done:
                    result.cancelled = True
                    result.stop_reason = "aborted"
                    result.error_message = "Tau child was cancelled."
                else:
                    result.timed_out = True
                    result.stop_reason = "error"
                    result.error_message = f"Tau child timed out after {timeout_seconds:g} seconds."
                await _terminate_process(process, wait_task)
            if cancellation_task is not None:
                cancellation_task.cancel()
                await asyncio.gather(cancellation_task, return_exceptions=True)

            await asyncio.gather(stdout_task, return_exceptions=False)
            stderr_bytes = await stderr_task
            result.stderr = stderr_bytes.decode("utf-8", errors="replace")
            result.exit_code = process.returncode if process.returncode is not None else 1

        has_assistant = any(isinstance(message, AssistantMessage) for message in result.messages)
        if (
            result.exit_code == 0
            and not has_assistant
            and not result.cancelled
            and not result.timed_out
        ):
            result.stop_reason = "error"
            result.error_message = "Tau child exited without a valid assistant message."
        elif result.exit_code != 0 and result.error_message is None:
            result.error_message = f"Tau child exited with code {result.exit_code}."
        result.status = parse_status(final_output(result.messages), failed=not result.succeeded)
        return result


def compose_child_prompt(agent: AgentConfig) -> str:
    """Preserve the agent body, then append fixed isolation/profile instructions."""

    sections = [_SHARED_INSTRUCTIONS]
    if agent.profile == "review":
        sections.insert(0, _REVIEW_INSTRUCTIONS)
    elif agent.profile == "read-only":
        sections.insert(0, _READ_ONLY_INSTRUCTIONS)
    suffix = "\n\n".join(section.rstrip() for section in sections) + "\n"
    if not agent.system_prompt:
        return suffix
    separator = (
        ""
        if agent.system_prompt.endswith("\n\n")
        else ("\n" if agent.system_prompt.endswith("\n") else "\n\n")
    )
    return f"{agent.system_prompt}{separator}{suffix}"


async def _collect_stdout(
    stream: asyncio.StreamReader,
    result: ChildResult,
    on_message: ChildUpdate | None,
) -> None:
    buffer = b""
    while chunk := await stream.read(64 * 1024):
        buffer += chunk
        lines = buffer.split(b"\n")
        buffer = lines.pop()
        for line in lines:
            _process_json_line(line, result, on_message)
    if buffer:
        _process_json_line(buffer, result, on_message)


def _process_json_line(
    raw_line: bytes,
    result: ChildResult,
    on_message: ChildUpdate | None,
) -> None:
    if not raw_line.strip():
        return
    try:
        event = json.loads(raw_line.decode("utf-8"))
    except UnicodeDecodeError, json.JSONDecodeError:
        result.malformed_json_lines += 1
        return
    if not isinstance(event, dict) or event.get("type") != "message_end":
        return
    try:
        message = _MESSAGE_ADAPTER.validate_python(event.get("message"))
    except ValidationError:
        result.malformed_json_lines += 1
        return
    result.messages.append(message)
    if isinstance(message, AssistantMessage):
        result.usage.turns += 1
        result.usage.input += message.usage.input
        result.usage.output += message.usage.output
        result.usage.cache_read += message.usage.cache_read
        result.usage.cache_write += message.usage.cache_write
        result.usage.cost += message.usage.cost.total
        result.usage.context_tokens = message.usage.total_tokens
        if result.provider is None:
            result.provider = message.provider
        if result.model is None:
            result.model = message.model
        result.stop_reason = message.stop_reason
        result.error_message = message.error_message
    if on_message is not None and isinstance(message, (AssistantMessage, ToolResultMessage)):
        on_message(result)


async def _wait_for_cancellation(signal: ToolCancellationToken) -> None:
    # Tau's public cancellation protocol only exposes a synchronous polling method.
    while not signal.is_cancelled():  # noqa: ASYNC110
        await asyncio.sleep(0.05)


async def _terminate_process(
    process: asyncio.subprocess.Process,
    wait_task: asyncio.Task[int],
) -> None:
    if process.returncode is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        return
    done, _ = await asyncio.wait({wait_task}, timeout=5.0)
    if wait_task in done:
        return
    try:
        process.kill()
    except ProcessLookupError:
        return
    await process.wait()


def _is_cancelled(signal: ToolCancellationToken | None) -> bool:
    return signal is not None and signal.is_cancelled()
