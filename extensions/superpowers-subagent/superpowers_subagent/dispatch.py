"""Task validation and single/parallel/chain orchestration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from tau_agent.messages import TextContent
from tau_agent.tools import (
    AgentToolResult,
    ToolCancellationToken,
    ToolUpdateCallback,
)
from tau_agent.types import JSONValue

from .discovery import discover_agents
from .models import (
    AgentConfig,
    AgentScope,
    ChildResult,
    DiscoveryResult,
    DispatchMode,
    TaskItem,
    details_dict,
)
from .runner import TauChildRunner
from .utils import final_output, parse_status, resolve_child_cwd, summary_section

MAX_PARALLEL_TASKS = 8
MAX_CONCURRENCY = 4
DEFAULT_TIMEOUT_SECONDS = 3600.0


class ConfirmationUi(Protocol):
    @property
    def has_ui(self) -> bool: ...

    async def confirm(
        self,
        title: str,
        message: str,
        *,
        timeout: float | None = None,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class ParsedRequest:
    mode: DispatchMode
    items: tuple[TaskItem, ...]
    agent_scope: AgentScope
    confirm_project_agents: bool
    provider: str | None
    model: str | None
    timeout_seconds: float


class ValidationFailure(ValueError):
    """A user-correctable Task argument error."""


DiscoveryFn = Callable[[Path, AgentScope], DiscoveryResult]


class TaskDispatcher:
    """Validate and orchestrate one Task call."""

    def __init__(
        self,
        *,
        default_cwd: Path,
        ui: ConfirmationUi,
        runner: TauChildRunner | None = None,
        discovery_fn: DiscoveryFn = discover_agents,
    ) -> None:
        self.default_cwd = default_cwd
        self.ui = ui
        self.runner = runner or TauChildRunner()
        self.discovery_fn = discovery_fn

    async def execute(
        self,
        arguments: Mapping[str, JSONValue],
        signal: ToolCancellationToken | None = None,
        on_update: ToolUpdateCallback | None = None,
    ) -> AgentToolResult:
        """Execute one validated Task invocation."""

        scope = _scope_for_discovery(arguments)
        discovery = self.discovery_fn(self.default_cwd, scope)
        try:
            request = validate_arguments(arguments)
        except ValidationFailure as exc:
            mode = _mode_hint(arguments)
            available = _available_agents(discovery)
            return _tool_result(
                f"Invalid parameters: {exc}\nAvailable agents: {available}",
                mode=mode,
                scope=scope,
                discovery=discovery,
                results=[],
            )

        agents = discovery.by_name()
        project_agents = sorted(
            {
                item.agent
                for item in request.items
                if item.agent in agents and agents[item.agent].source == "project"
            }
        )
        if project_agents and request.confirm_project_agents:
            directory = discovery.project_agents_dir
            if not self.ui.has_ui:
                return _tool_result(
                    "Project agent approval required in headless mode. Inspect "
                    f"{directory} and set confirmProjectAgents: false to explicitly approve "
                    "these definitions for this task call.",
                    mode=request.mode,
                    scope=request.agent_scope,
                    discovery=discovery,
                    results=[],
                )
            approved = await self.ui.confirm(
                "Run project-local agents?",
                "Agents: " + ", ".join(project_agents) + f"\nSource: {directory}\n\n"
                "Project agents are repository-controlled prompt input.",
            )
            if not approved:
                return _tool_result(
                    "Canceled: project-local agents were not approved.",
                    mode=request.mode,
                    scope=request.agent_scope,
                    discovery=discovery,
                    results=[],
                )

        if request.mode == "single":
            results = await self._run_single(request, discovery, agents, signal, on_update)
        elif request.mode == "parallel":
            results = await self._run_parallel(request, discovery, agents, signal, on_update)
        else:
            results = await self._run_chain(request, discovery, agents, signal, on_update)
        return _final_result(request, discovery, results, planned=len(request.items))

    async def _run_single(
        self,
        request: ParsedRequest,
        discovery: DiscoveryResult,
        agents: dict[str, AgentConfig],
        signal: ToolCancellationToken | None,
        on_update: ToolUpdateCallback | None,
    ) -> list[ChildResult]:
        item = request.items[0]

        def update(result: ChildResult) -> None:
            _emit_update(
                on_update,
                _single_content(result, running=True),
                request,
                discovery,
                [result],
            )

        result = await self._run_item(
            item=item,
            agents=agents,
            request=request,
            signal=signal,
            on_message=update,
        )
        _emit_update(
            on_update,
            _single_content(result),
            request,
            discovery,
            [result],
        )
        return [result]

    async def _run_parallel(
        self,
        request: ParsedRequest,
        discovery: DiscoveryResult,
        agents: dict[str, AgentConfig],
        signal: ToolCancellationToken | None,
        on_update: ToolUpdateCallback | None,
    ) -> list[ChildResult]:
        slots: list[ChildResult | None] = [None] * len(request.items)
        next_index = 0
        stop_queued = False

        def current_results() -> list[ChildResult]:
            return [result for result in slots if result is not None]

        def emit() -> None:
            results = current_results()
            complete = sum(_is_terminal_slot(result) for result in results)
            _emit_update(
                on_update,
                f"Parallel: {complete}/{len(slots)} done",
                request,
                discovery,
                results,
            )

        async def worker() -> None:
            nonlocal next_index, stop_queued
            while next_index < len(request.items):
                if stop_queued or _is_cancelled(signal):
                    stop_queued = True
                    return
                index = next_index
                next_index += 1
                item = request.items[index]

                def update(result: ChildResult, *, slot: int = index) -> None:
                    slots[slot] = result
                    emit()

                result = await self._run_item(
                    item=item,
                    agents=agents,
                    request=request,
                    signal=signal,
                    on_message=update,
                )
                slots[index] = result
                if result.cancelled or result.timed_out:
                    stop_queued = True
                emit()

        workers = [
            asyncio.create_task(worker()) for _ in range(min(MAX_CONCURRENCY, len(request.items)))
        ]
        await asyncio.gather(*workers)

        for index, result in enumerate(slots):
            if result is not None:
                continue
            item = request.items[index]
            cancelled = _is_cancelled(signal)
            slots[index] = _not_started_result(
                item,
                agents.get(item.agent),
                self.default_cwd,
                cancelled=cancelled,
                reason=(
                    "Dispatch cancelled before child process started."
                    if cancelled
                    else "Child not started because a parallel timeout stopped queued work."
                ),
            )
        final = cast("list[ChildResult]", slots)
        emit()
        return final

    async def _run_chain(
        self,
        request: ParsedRequest,
        discovery: DiscoveryResult,
        agents: dict[str, AgentConfig],
        signal: ToolCancellationToken | None,
        on_update: ToolUpdateCallback | None,
    ) -> list[ChildResult]:
        results: list[ChildResult] = []
        previous = ""
        for step, original_item in enumerate(request.items, start=1):
            task = original_item.task.replace("{previous}", previous)
            item = TaskItem(
                agent=original_item.agent,
                task=task,
                cwd=original_item.cwd,
            )
            if _is_cancelled(signal):
                results.append(
                    _not_started_result(
                        item,
                        agents.get(item.agent),
                        self.default_cwd,
                        cancelled=True,
                        reason="Dispatch cancelled before child process started.",
                        step=step,
                    )
                )
                break

            def update(result: ChildResult, *, current_step: int = step) -> None:
                _emit_update(
                    on_update,
                    f"Chain: step {current_step}/{len(request.items)} running",
                    request,
                    discovery,
                    [*results, result],
                )

            result = await self._run_item(
                item=item,
                agents=agents,
                request=request,
                signal=signal,
                step=step,
                on_message=update,
            )
            results.append(result)
            _emit_update(
                on_update,
                f"Chain: step {step}/{len(request.items)} complete",
                request,
                discovery,
                results,
            )
            if not result.succeeded:
                break
            previous = final_output(result.messages)
        return results

    async def _run_item(
        self,
        *,
        item: TaskItem,
        agents: dict[str, AgentConfig],
        request: ParsedRequest,
        signal: ToolCancellationToken | None,
        step: int | None = None,
        on_message: Callable[[ChildResult], None] | None = None,
    ) -> ChildResult:
        agent = agents.get(item.agent)
        if agent is None:
            return _unknown_agent_result(
                item,
                self.default_cwd,
                _available_agents_from_map(agents),
                step=step,
            )
        return await self.runner.run(
            default_cwd=self.default_cwd,
            agent=agent,
            task=item.task,
            cwd_override=item.cwd,
            provider_override=request.provider,
            model_override=request.model,
            timeout_seconds=request.timeout_seconds,
            signal=signal,
            step=step,
            on_message=on_message,
        )


def validate_arguments(arguments: Mapping[str, JSONValue]) -> ParsedRequest:
    """Normalize and validate exactly one Task mode."""

    allowed = {
        "description",
        "agent",
        "task",
        "cwd",
        "tasks",
        "chain",
        "agentScope",
        "confirmProjectAgents",
        "provider",
        "model",
        "timeoutSeconds",
    }
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ValidationFailure(f"unknown field(s): {', '.join(unknown)}")

    _optional_string(arguments, "description", nonempty=False)
    scope_value = arguments.get("agentScope", "user")
    if scope_value not in {"user", "project", "both"}:
        raise ValidationFailure("agentScope must be `user`, `project`, or `both`")
    scope: AgentScope = cast("AgentScope", scope_value)

    confirm = arguments.get("confirmProjectAgents", True)
    if not isinstance(confirm, bool):
        raise ValidationFailure("confirmProjectAgents must be a boolean")
    provider = _optional_string(arguments, "provider", nonempty=True)
    model = _optional_string(arguments, "model", nonempty=True)
    timeout_value = arguments.get("timeoutSeconds", DEFAULT_TIMEOUT_SECONDS)
    if (
        isinstance(timeout_value, bool)
        or not isinstance(timeout_value, (int, float))
        or not 0 < timeout_value <= DEFAULT_TIMEOUT_SECONDS
    ):
        raise ValidationFailure("timeoutSeconds must be greater than 0 and at most 3600")
    timeout = float(timeout_value)

    agent = _optional_string(arguments, "agent", nonempty=True)
    task = _optional_string(arguments, "task", nonempty=True)
    cwd = _optional_string(arguments, "cwd", nonempty=False)
    if (agent is None) != (task is None):
        raise ValidationFailure("single mode requires both non-empty agent and task")

    tasks = _optional_items(arguments, "tasks")
    chain = _optional_items(arguments, "chain")
    has_single = agent is not None and task is not None
    has_parallel = bool(tasks)
    has_chain = bool(chain)
    if sum((has_single, has_parallel, has_chain)) != 1:
        raise ValidationFailure(
            "provide exactly one non-empty mode: single (agent + task), parallel "
            "(tasks), or chain (chain)"
        )
    if has_parallel and len(tasks) > MAX_PARALLEL_TASKS:
        raise ValidationFailure(f"parallel mode accepts at most {MAX_PARALLEL_TASKS} tasks")
    if cwd is not None and not has_single:
        raise ValidationFailure("top-level cwd is only valid in single mode")

    mode: DispatchMode
    items: tuple[TaskItem, ...]
    if has_single:
        assert agent is not None and task is not None
        mode = "single"
        items = (TaskItem(agent=agent.strip(), task=task, cwd=cwd),)
    elif has_parallel:
        mode = "parallel"
        items = tasks
    else:
        mode = "chain"
        items = chain
    return ParsedRequest(
        mode=mode,
        items=items,
        agent_scope=scope,
        confirm_project_agents=confirm,
        provider=provider,
        model=model,
        timeout_seconds=timeout,
    )


def _optional_items(arguments: Mapping[str, JSONValue], key: str) -> tuple[TaskItem, ...]:
    if key not in arguments:
        return ()
    value = arguments[key]
    if not isinstance(value, list):
        raise ValidationFailure(f"{key} must be an array")
    items: list[TaskItem] = []
    for index, raw_item in enumerate(value):
        if not isinstance(raw_item, dict):
            raise ValidationFailure(f"{key}[{index}] must be an object")
        unknown = sorted(set(raw_item) - {"agent", "task", "cwd"})
        if unknown:
            raise ValidationFailure(f"{key}[{index}] has unknown field(s): {', '.join(unknown)}")
        agent = raw_item.get("agent")
        task = raw_item.get("task")
        cwd = raw_item.get("cwd")
        if not isinstance(agent, str) or not agent.strip():
            raise ValidationFailure(f"{key}[{index}].agent must be a non-empty string")
        if not isinstance(task, str) or not task.strip():
            raise ValidationFailure(f"{key}[{index}].task must be a non-empty string")
        if cwd is not None and not isinstance(cwd, str):
            raise ValidationFailure(f"{key}[{index}].cwd must be a string")
        items.append(TaskItem(agent=agent.strip(), task=task, cwd=cwd))
    return tuple(items)


def _optional_string(arguments: Mapping[str, JSONValue], key: str, *, nonempty: bool) -> str | None:
    if key not in arguments:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValidationFailure(f"{key} must be a string")
    if nonempty and not value.strip():
        raise ValidationFailure(f"{key} must be a non-empty string")
    return value


def _scope_for_discovery(arguments: Mapping[str, JSONValue]) -> AgentScope:
    value = arguments.get("agentScope", "user")
    if value in {"user", "project", "both"}:
        return cast("AgentScope", value)
    return "user"


def _mode_hint(arguments: Mapping[str, JSONValue]) -> DispatchMode:
    if isinstance(arguments.get("chain"), list) and arguments.get("chain"):
        return "chain"
    if isinstance(arguments.get("tasks"), list) and arguments.get("tasks"):
        return "parallel"
    return "single"


def _tool_result(
    content: str,
    *,
    mode: DispatchMode,
    scope: AgentScope,
    discovery: DiscoveryResult,
    results: list[ChildResult],
    planned: int | None = None,
) -> AgentToolResult:
    return AgentToolResult(
        content=[TextContent(text=content)],
        details=details_dict(
            mode=mode,
            agent_scope=scope,
            project_agents_dir=discovery.project_agents_dir,
            discovery_diagnostics=discovery.diagnostics,
            results=results,
            planned=planned,
        ),
    )


def _final_result(
    request: ParsedRequest,
    discovery: DiscoveryResult,
    results: list[ChildResult],
    *,
    planned: int,
) -> AgentToolResult:
    if request.mode == "single":
        content = _single_content(results[0])
    elif request.mode == "parallel":
        succeeded = sum(result.succeeded for result in results)
        sections = [
            f"[{result.agent}] ({'completed' if result.succeeded else 'failed'})\n\n"
            f"{_summary_or_fallback(result)}"
            for result in results
        ]
        content = f"Parallel: {succeeded}/{len(results)} succeeded\n\n" + "\n\n\n".join(sections)
    else:
        failed = next((result for result in results if not result.succeeded), None)
        if failed is not None:
            content = (
                f"Chain stopped at step {failed.step} ({failed.agent}): "
                f"{failed.error_message or 'child failed; see details'}"
            )
        elif results:
            content = _summary_or_fallback(results[-1])
        else:
            content = "Chain stopped before the first step."
    return _tool_result(
        content,
        mode=request.mode,
        scope=request.agent_scope,
        discovery=discovery,
        results=results,
        planned=planned,
    )


def _single_content(result: ChildResult, *, running: bool = False) -> str:
    output = final_output(result.messages)
    if running:
        return summary_section(output) if output else "(running...)"
    if not result.succeeded:
        return f"Agent {result.agent} failed: {result.error_message or 'see details'}"
    return summary_section(output) or "(no output)"


def _summary_or_fallback(result: ChildResult) -> str:
    return summary_section(final_output(result.messages)) or "(no output)"


def _emit_update(
    callback: ToolUpdateCallback | None,
    content: str,
    request: ParsedRequest,
    discovery: DiscoveryResult,
    results: list[ChildResult],
) -> None:
    if callback is None:
        return
    callback(
        _tool_result(
            content,
            mode=request.mode,
            scope=request.agent_scope,
            discovery=discovery,
            results=results,
            planned=len(request.items),
        )
    )


def _unknown_agent_result(
    item: TaskItem,
    default_cwd: Path,
    available: str,
    *,
    step: int | None,
) -> ChildResult:
    result = ChildResult(
        agent=item.agent,
        agent_source="unknown",
        task=item.task,
        cwd=str(resolve_child_cwd(default_cwd, item.cwd)),
        error_message=f"Unknown agent {item.agent!r}. Available agents: {available}.",
        step=step,
    )
    result.status = parse_status("", failed=True)
    return result


def _not_started_result(
    item: TaskItem,
    agent: AgentConfig | None,
    default_cwd: Path,
    *,
    cancelled: bool,
    reason: str,
    step: int | None = None,
) -> ChildResult:
    result = ChildResult(
        agent=item.agent,
        agent_source=agent.source if agent is not None else "unknown",
        task=item.task,
        cwd=str(resolve_child_cwd(default_cwd, item.cwd)),
        error_message=reason,
        stop_reason="aborted" if cancelled else "error",
        cancelled=cancelled,
        step=step,
    )
    result.status = "BLOCKED"
    return result


def _available_agents(discovery: DiscoveryResult) -> str:
    if not discovery.agents:
        return "none"
    return ", ".join(f"{agent.name} ({agent.source})" for agent in discovery.agents)


def _available_agents_from_map(agents: dict[str, AgentConfig]) -> str:
    if not agents:
        return "none"
    return ", ".join(f"{name} ({agents[name].source})" for name in sorted(agents))


def _is_cancelled(signal: ToolCancellationToken | None) -> bool:
    return signal is not None and signal.is_cancelled()


def _is_terminal_slot(result: ChildResult) -> bool:
    return result.exit_code != 1 or result.error_message is not None
