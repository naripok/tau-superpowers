"""Task validation and single-child dispatch."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from tau_agent.messages import AssistantMessage, TextContent
from tau_agent.tools import (
    AgentToolResult,
    ToolCancellationToken,
    ToolUpdateCallback,
)
from tau_agent.types import JSONValue

from .catalog import CatalogSnapshot, provider_model_override_error
from .config import AgentOverrides, SubagentConfig
from .discovery import discover_agents
from .locking import same_id_lock
from .models import (
    THINKING_LEVELS,
    AgentConfig,
    AgentScope,
    ChildResult,
    DiscoveryResult,
    details_dict,
)
from .runner import TauChildRunner
from .utils import (
    effective_provider_model,
    final_output,
    resolve_child_cwd,
)

DEFAULT_TIMEOUT_SECONDS = 3600.0
MAX_TIMEOUT_SECONDS = 10800.0
#: The exact flat field surface; anything else fails closed.
_ALLOWED_FIELDS = frozenset(
    {
        "prompt",
        "subagent_type",
        "description",
        "task_id",
        "cwd",
        "agentScope",
        "confirmProjectAgents",
        "provider",
        "model",
        "reasoningEffort",
        "timeoutSeconds",
    }
)
_RESERVED_OVERRIDE_PLACEHOLDERS: frozenset[str] = frozenset({"default", "inherit", "auto"})

UsageObserver = Callable[[Sequence[ChildResult], bool], None]


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
    """One validated flat task call: exactly one prompt for exactly one child."""

    #: The call's prompt, preserved verbatim; it is the child's task.
    prompt: str
    #: Effective agent name after trimming; omission resolves to general-purpose.
    subagent_type: str
    description: str | None
    #: Trimmed effective id for session lookup, the same-id lock, and repair notes.
    task_id: str | None
    cwd: str | None
    agent_scope: AgentScope
    confirm_project_agents: bool
    provider: str | None
    model: str | None
    reasoning_effort: str | None
    timeout_seconds: float
    #: Repair notes surfaced to the controller, one line per tolerated mistake
    #: (for example placeholders coerced to omitted).
    notices: tuple[str, ...] = ()


class ValidationFailure(ValueError):
    """A user-correctable Task argument error."""


DiscoveryFn = Callable[[Path], DiscoveryResult]
CatalogFn = Callable[[], CatalogSnapshot | None]


class TaskDispatcher:
    """Validate and dispatch one Task call to exactly one child."""

    def __init__(
        self,
        *,
        default_cwd: Path,
        ui: ConfirmationUi,
        runner: TauChildRunner | None = None,
        discovery_fn: DiscoveryFn = discover_agents,
        roster_text: str,
        parent_provider: str | None = None,
        parent_model: str | None = None,
        parent_reasoning_effort: str | None = None,
        config: SubagentConfig | None = None,
        usage_observer: UsageObserver | None = None,
        catalog_fn: CatalogFn | None = None,
    ) -> None:
        self.default_cwd = default_cwd
        self.ui = ui
        self.runner = runner or TauChildRunner()
        self.discovery_fn = discovery_fn
        # The static session-start roster: every teach-back lists these agents,
        # so the teach-back roster cannot drift from the description roster.
        self.roster_text = roster_text
        self.parent_provider = parent_provider
        self.parent_model = parent_model
        self.parent_reasoning_effort = parent_reasoning_effort
        self.config = config
        self.usage_observer = usage_observer
        self.catalog_fn = catalog_fn
        self._config_diagnostics: tuple[str, ...] = ()

    async def execute(
        self,
        arguments: Mapping[str, JSONValue],
        signal: ToolCancellationToken | None = None,
        on_update: ToolUpdateCallback | None = None,
    ) -> AgentToolResult:
        """Execute one validated Task invocation."""

        scope = _scope_for_discovery(arguments)
        discovery = self.discovery_fn(self.default_cwd)
        self._config_diagnostics = self._merged_config_diagnostics(discovery.by_name())
        try:
            request = validate_arguments(arguments)
        except ValidationFailure as exc:
            return self._fail_closed(str(exc), scope=scope, discovery=discovery)

        agents = discovery.by_name()
        agent = agents.get(request.subagent_type)
        if agent is None:
            return self._fail_closed(
                f"unknown agent '{request.subagent_type}'",
                scope=request.agent_scope,
                discovery=discovery,
            )
        catalog_error = self._catalog_override_error(request, agent)
        if catalog_error is not None:
            return self._fail_closed(catalog_error, scope=request.agent_scope, discovery=discovery)
        denial = await self._project_approval(request, agent, discovery)
        if denial is not None:
            return denial
        return await self._run_locked(request, agent, discovery, signal, on_update)

    def _fail_closed(
        self,
        error: str,
        *,
        scope: AgentScope,
        discovery: DiscoveryResult,
    ) -> AgentToolResult:
        """Return the fail-closed contract: teach-back content, empty results,
        no ``planned``, and no child started."""

        return _tool_result(
            _invalid_parameters_content(error, self),
            scope=scope,
            discovery=discovery,
            config=self.config,
            config_diagnostics=self._config_diagnostics,
            results=[],
        )

    def _merged_config_diagnostics(self, agents: dict[str, AgentConfig]) -> tuple[str, ...]:
        """Combine config-file diagnostics with per-call section-name checks.

        A config section whose agent name exists in no bundled, user, or
        project definition is almost always a typo; report it as a diagnostic
        so it cannot silently no-op. All-layer discovery already resolved the
        section names, so no second discovery pass is needed.
        """

        if self.config is None:
            return ()
        unmatched = [name for name, _overrides in self.config.agents if name not in agents]
        extras = tuple(
            f"Subagent config: [agents.{name}] matches no bundled, user, or project "
            "agent definition"
            for name in sorted(unmatched)
        )
        return (*self.config.diagnostics, *extras)

    def _config_layers(
        self, agent_name: str
    ) -> tuple[AgentOverrides | None, AgentOverrides | None]:
        if self.config is None:
            return None, None
        return self.config.overrides_for(agent_name), self.config.defaults

    def _catalog_override_error(self, request: ParsedRequest, agent: AgentConfig) -> str | None:
        """Fail fast on literal overrides the provider catalog cannot honor.

        Without a catalog the check is skipped. The resolution mirrors
        ``_dispatch_child`` exactly, so an accepted pair is the pair the child
        would actually receive.
        """

        if self.catalog_fn is None:
            return None
        snapshot = self.catalog_fn()
        if snapshot is None:
            return None
        config_overrides, config_defaults = self._config_layers(request.subagent_type)
        provider, model = effective_provider_model(
            agent,
            request.provider,
            request.model,
            config_overrides=config_overrides,
            config_defaults=config_defaults,
            parent_provider=self.parent_provider,
            parent_model=self.parent_model,
        )
        return provider_model_override_error(
            provider,
            model,
            parent_provider=self.parent_provider,
            parent_model=self.parent_model,
            snapshot=snapshot,
        )

    async def _project_approval(
        self,
        request: ParsedRequest,
        agent: AgentConfig,
        discovery: DiscoveryResult,
    ) -> AgentToolResult | None:
        """Gate project-controlled agent prompts; None means approved or exempt.

        A headless session fails closed with the directory-naming teach-back. An
        interactive denial cancels the call before any child starts with the
        pre-session failure result: an error envelope with no id attribute and a
        details entry without a ``taskId``.
        """

        if agent.source != "project" or not request.confirm_project_agents:
            return None
        directory = discovery.project_agents_dir
        if not self.ui.has_ui:
            return self._fail_closed(
                "Project agent approval required in headless mode. Inspect "
                f"{directory} and set confirmProjectAgents: false to explicitly approve "
                "these definitions for this task call.",
                scope=request.agent_scope,
                discovery=discovery,
            )
        approved = await self.ui.confirm(
            "Run project-local agents?",
            "Agents: " + agent.name + f"\nSource: {directory}\n\n"
            "Project agents are repository-controlled prompt input.",
        )
        if approved:
            return None
        result = ChildResult(
            agent=request.subagent_type,
            agent_source="project",
            task=request.prompt,
            cwd=str(resolve_child_cwd(self.default_cwd, request.cwd)),
            error_message="Canceled: project-local agents were not approved.",
            status="BLOCKED",
        )
        return _tool_result(
            _call_content(request, result),
            scope=request.agent_scope,
            discovery=discovery,
            config=self.config,
            config_diagnostics=self._config_diagnostics,
            results=[result],
            planned=1,
        )

    async def _run_locked(
        self,
        request: ParsedRequest,
        agent: AgentConfig,
        discovery: DiscoveryResult,
        signal: ToolCancellationToken | None,
        on_update: ToolUpdateCallback | None,
    ) -> AgentToolResult:
        """Run the single child under the same-id lock when the call carries a
        ``task_id``; a lost race fails closed with the conflict teach-back."""

        if request.task_id is None:
            lock: AbstractContextManager[None] = nullcontext()
        else:
            acquired = same_id_lock(request.task_id)
            if acquired is None:
                return self._fail_closed(
                    f"another running task call already holds task_id '{request.task_id}'. "
                    "Wait for that call to finish or use a different task_id.",
                    scope=request.agent_scope,
                    discovery=discovery,
                )
            lock = acquired
        with lock:
            return await self._dispatch_child(request, agent, discovery, signal, on_update)

    async def _dispatch_child(
        self,
        request: ParsedRequest,
        agent: AgentConfig,
        discovery: DiscoveryResult,
        signal: ToolCancellationToken | None,
        on_update: ToolUpdateCallback | None,
    ) -> AgentToolResult:
        """Run the one child and build its envelope result.

        Partial updates stream after each accepted child message and again on
        completion; the envelope appears only on the final result.
        """

        def emit(result: ChildResult) -> None:
            _emit_update(
                on_update,
                _progress_content(result),
                request,
                discovery,
                [result],
                config=self.config,
                config_diagnostics=self._config_diagnostics,
                usage_observer=self.usage_observer,
            )

        config_overrides, config_defaults = self._config_layers(request.subagent_type)
        result = await self.runner.run(
            default_cwd=self.default_cwd,
            agent=agent,
            task=request.prompt,
            cwd_override=request.cwd,
            provider_override=request.provider,
            model_override=request.model,
            reasoning_effort_override=request.reasoning_effort,
            config_overrides=config_overrides,
            config_defaults=config_defaults,
            parent_provider=self.parent_provider,
            parent_model=self.parent_model,
            parent_reasoning_effort=self.parent_reasoning_effort,
            timeout_seconds=request.timeout_seconds,
            signal=signal,
            on_message=emit,
            resume_session_id=request.task_id,
        )
        emit(result)
        if self.usage_observer is not None:
            self.usage_observer([result], True)
        return _tool_result(
            _call_content(request, result),
            scope=request.agent_scope,
            discovery=discovery,
            config=self.config,
            config_diagnostics=self._config_diagnostics,
            results=[result],
            planned=1,
        )


def validate_arguments(arguments: Mapping[str, JSONValue]) -> ParsedRequest:
    """Validate and normalize one flat single-object Task call."""

    if "background" in arguments:
        raise ValidationFailure(
            "background dispatch is not supported in this harness. The result of a task "
            "call arrives when the child finishes; use several task calls in one message "
            "to run children in parallel."
        )
    unknown = sorted(set(arguments) - _ALLOWED_FIELDS)
    if unknown:
        raise ValidationFailure(f"unknown field(s): {', '.join(unknown)}")

    prompt = arguments.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValidationFailure("prompt requires a non-empty string")

    subagent_present = "subagent_type" in arguments
    subagent_type = "general-purpose"
    if subagent_present:
        value = arguments["subagent_type"]
        if not isinstance(value, str) or not value.strip():
            raise ValidationFailure("subagent_type requires a non-empty string when present")
        subagent_type = value.strip()

    description = _optional_string(arguments, "description", nonempty=False)

    task_id: str | None = None
    if "task_id" in arguments:
        value = arguments["task_id"]
        if not isinstance(value, str) or not value.strip():
            raise ValidationFailure("task_id requires a non-empty string when present")
        if not subagent_present:
            raise ValidationFailure(
                "task_id requires subagent_type: pass the agent whose prompt the resumed run uses"
            )
        task_id = value.strip()

    cwd = _optional_string(arguments, "cwd", nonempty=False)

    scope_value = arguments.get("agentScope", "user")
    if scope_value not in {"user", "project", "both"}:
        raise ValidationFailure("agentScope must be `user`, `project`, or `both`")
    scope: AgentScope = cast("AgentScope", scope_value)

    confirm = arguments.get("confirmProjectAgents", True)
    if not isinstance(confirm, bool):
        raise ValidationFailure("confirmProjectAgents must be a boolean")

    notices: list[str] = []
    provider = _optional_literal_override(arguments, "provider", notices)
    model = _optional_literal_override(arguments, "model", notices)
    reasoning_effort = _optional_thinking_level(arguments, "reasoningEffort", notices)
    timeout_value = arguments.get("timeoutSeconds", DEFAULT_TIMEOUT_SECONDS)
    if (
        isinstance(timeout_value, bool)
        or not isinstance(timeout_value, (int, float))
        or not 0 < timeout_value <= MAX_TIMEOUT_SECONDS
    ):
        raise ValidationFailure("timeoutSeconds must be greater than 0 and at most 10800")

    return ParsedRequest(
        prompt=prompt,
        subagent_type=subagent_type,
        description=description,
        task_id=task_id,
        cwd=cwd,
        agent_scope=scope,
        confirm_project_agents=confirm,
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        timeout_seconds=float(timeout_value),
        notices=tuple(notices),
    )


def _optional_string(arguments: Mapping[str, JSONValue], key: str, *, nonempty: bool) -> str | None:
    if key not in arguments:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValidationFailure(f"{key} must be a string")
    if nonempty and not value.strip():
        raise ValidationFailure(f"{key} must be a non-empty string")
    return value


def _optional_literal_override(
    arguments: Mapping[str, JSONValue],
    key: str,
    notices: list[str],
) -> str | None:
    """Return a trimmed literal override, coercing placeholders to omitted.

    Models keep sending ``default``/``inherit``/``auto`` however firmly the
    schema forbids them, and their intent is unambiguous: inherit. Coercing to
    omitted with a repair note keeps the dispatch alive and teaches the fix,
    instead of spending a failed call on it.
    """

    value = _optional_string(arguments, key, nonempty=False)
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValidationFailure(
            f"{key} requires a non-empty string literal override; "
            f"omit {key} for inherited configuration"
        )
    if normalized.lower() in _RESERVED_OVERRIDE_PLACEHOLDERS:
        notices.append(
            f"{key}: {normalized!r} is a placeholder, not a literal value; treated as "
            f"omitted, so {key} inherits configuration. Omit the field next time."
        )
        return None
    return normalized


def _optional_thinking_level(
    arguments: Mapping[str, JSONValue],
    key: str,
    notices: list[str],
) -> str | None:
    if key not in arguments:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValidationFailure(f"{key} must be a string")
    normalized = value.strip().lower()
    if normalized in _RESERVED_OVERRIDE_PLACEHOLDERS:
        notices.append(
            f"{key}: {normalized!r} is a placeholder, not a literal value; treated as "
            f"omitted, so {key} inherits configuration. Omit the field next time."
        )
        return None
    if normalized not in THINKING_LEVELS:
        allowed = ", ".join(THINKING_LEVELS)
        raise ValidationFailure(f"{key} must be one of: {allowed}")
    return normalized


def _scope_for_discovery(arguments: Mapping[str, JSONValue]) -> AgentScope:
    value = arguments.get("agentScope", "user")
    if value in {"user", "project", "both"}:
        return cast("AgentScope", value)
    return "user"


def _tool_result(
    content: str,
    *,
    scope: AgentScope,
    discovery: DiscoveryResult,
    results: list[ChildResult],
    config: SubagentConfig | None = None,
    config_diagnostics: tuple[str, ...] | None = None,
    planned: int | None = None,
) -> AgentToolResult:
    if config_diagnostics is None:
        config_diagnostics = config.diagnostics if config is not None else ()
    return AgentToolResult(
        content=[TextContent(text=content)],
        details=details_dict(
            agent_scope=scope,
            project_agents_dir=discovery.project_agents_dir,
            discovery_diagnostics=discovery.diagnostics,
            config_paths=config.paths if config is not None else (),
            config_diagnostics=config_diagnostics,
            results=results,
            planned=planned,
        ),
    )


def build_envelope(result: ChildResult) -> str:
    """Render the model-facing task envelope for one child result.

    The state is the process outcome only: ``completed`` means the child
    finished and delivered a final assistant message, whatever status marker
    that message carries inside its text. Child status markers stay inside the
    wrapped text. The inner content is the child's own text, verbatim.
    """

    has_final = any(isinstance(message, AssistantMessage) for message in result.messages)
    state = "completed" if result.succeeded and has_final else "error"
    opening = (
        f'<task id="{result.task_id}" state="{state}">'
        if result.task_id is not None
        else f'<task state="{state}">'
    )
    if state == "completed":
        inner = f"<task_result>{final_output(result.messages) or '(no output)'}</task_result>"
    elif has_final:
        inner = f"<task_error>{final_output(result.messages) or '(no output)'}</task_error>"
    elif result.task_id is not None:
        failure = (
            f"Subagent failed (task_id: {result.task_id}): "
            f"{result.error_message or 'unknown error'}"
        )
        inner = f"<task_error>{failure}</task_error>"
    else:
        inner = f"<task_error>{result.error_message}</task_error>"
    return f"{opening}{inner}</task>"


def _result_content(result: ChildResult, notes: tuple[str, ...] = ()) -> str:
    """Render repair notes as ``Note:`` lines ahead of the envelope."""

    envelope = build_envelope(result)
    if not notes:
        return envelope
    rendered = "".join(f"Note: {note}\n" for note in notes)
    return f"{rendered}\n{envelope}"


def _call_content(request: ParsedRequest, result: ChildResult) -> str:
    """Merge the two note sources in the one place that renders call content."""

    return _result_content(result, (*request.notices, *result.notes))


def _is_terminal(result: ChildResult) -> bool:
    return result.exit_code != 1 or result.error_message is not None


def _progress_content(result: ChildResult) -> str:
    """Preserved progress form, fixed to the single child: ``<done>/1 done``."""

    return f"{1 if _is_terminal(result) else 0}/1 done"


def _emit_update(
    callback: ToolUpdateCallback | None,
    content: str,
    request: ParsedRequest,
    discovery: DiscoveryResult,
    results: list[ChildResult],
    *,
    config: SubagentConfig | None = None,
    config_diagnostics: tuple[str, ...] | None = None,
    usage_observer: UsageObserver | None = None,
) -> None:
    """Feed a live usage snapshot, then deliver the update to the frontend."""
    if usage_observer is not None:
        usage_observer(results, False)
    if callback is None:
        return
    callback(
        _tool_result(
            content,
            scope=request.agent_scope,
            discovery=discovery,
            config=config,
            config_diagnostics=config_diagnostics,
            results=results,
            planned=1,
        )
    )


def _teach_back_roster(dispatcher: TaskDispatcher) -> str:
    """The static session-start roster the dispatcher carries.

    Every teach-back lists the same agents as the description roster, so the
    two surfaces cannot name different agent sets.
    """

    return dispatcher.roster_text


def _invalid_parameters_content(error: str, dispatcher: TaskDispatcher) -> str:
    """Teach back the call surface: roster, session inheritance, and an example.

    Without the bundled workflow skills, this failure content is the only
    place a struggling controller learns the full call contract, so it must
    name the valid values, not just reject the call.
    """

    lines = [
        f"Invalid parameters: {error}",
        "",
        f"Available agents: {_teach_back_roster(dispatcher)}",
    ]
    if dispatcher.parent_provider or dispatcher.parent_model:
        lines.append(
            "This session runs on provider "
            f"{dispatcher.parent_provider!r}, model {dispatcher.parent_model!r}: omit "
            "provider, model, and reasoningEffort to give every child exactly this "
            "configuration."
        )
    lines.append(
        "reasoningEffort, when passed, must be one of: " + ", ".join(THINKING_LEVELS) + "."
    )
    lines.append('Example: {"prompt": "Find caching options"}')
    return "\n".join(lines)
