"""Task validation and single-child dispatch."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path

from tau_agent.messages import AssistantMessage, TextContent
from tau_agent.tools import (
    AgentToolResult,
    ToolCancellationToken,
    ToolUpdateCallback,
)
from tau_agent.types import JSONValue

from .catalog import CatalogSnapshot, provider_model_pin_error
from .config import AgentOverrides, SubagentConfig
from .discovery import discover_agents
from .locking import same_id_lock
from .mapping import (
    MappingWriteError,
    default_mapping_path,
    read_mapping_entry,
    write_mapping_entry,
)
from .models import (
    AgentConfig,
    ChildResult,
    DiscoveryResult,
    SessionSelection,
    details_dict,
)
from .runner import ResumeFailure, TauChildRunner
from .utils import effective_provider_model, final_output

DEFAULT_TIMEOUT_SECONDS = 3600.0
MAX_TIMEOUT_SECONDS = 10800.0
#: The exact flat field surface; anything else fails closed.
_ALLOWED_FIELDS = frozenset(
    {
        "prompt",
        "subagent_type",
        "description",
        "task_id",
        "timeoutSeconds",
    }
)
#: Teach-back sentence per removed call-level field. Override fields direct the
#: caller to the durable pins; environment and approval fields state the fixed
#: dispatch behavior. The unknown-field teach-back appends the matching
#: sentence for every removed field the call carried.
_REMOVED_FIELD_SENTENCES: dict[str, str] = {
    "provider": (
        "The call-level provider override is removed: pin the provider in the "
        "superpowers-subagent.toml config file ([defaults] or [agents.<name>]) or in "
        "the agent definition's frontmatter."
    ),
    "model": (
        "The call-level model override is removed: pin the model in the "
        "superpowers-subagent.toml config file ([defaults] or [agents.<name>]) or in "
        "the agent definition's frontmatter."
    ),
    "reasoningEffort": (
        "The call-level reasoningEffort override is removed: pin the reasoning effort "
        "in the superpowers-subagent.toml config file ([defaults] or [agents.<name>]) "
        "or in the agent definition's frontmatter."
    ),
    "cwd": (
        "The call-level cwd capability is removed: a fresh child spawns in this "
        "session's working directory, and discovery covers all agent layers."
    ),
    "agentScope": (
        "The call-level agentScope capability is removed: a fresh child spawns in this "
        "session's working directory, and discovery covers all agent layers."
    ),
    "confirmProjectAgents": (
        "The call-level confirmProjectAgents capability is removed: a fresh child "
        "spawns in this session's working directory, and discovery covers all agent "
        "layers."
    ),
}

UsageObserver = Callable[[Sequence[ChildResult], bool], None]


@dataclass(frozen=True, slots=True)
class ParsedRequest:
    """One validated flat task call: exactly one prompt for exactly one child."""

    #: The call's prompt, preserved verbatim; it is the child's task.
    prompt: str
    #: Effective agent name after trimming; omission resolves to general-purpose.
    subagent_type: str
    description: str | None
    #: Trimmed effective id for the session-agent mapping lookup, the session
    #: selection, and the same-id lock.
    task_id: str | None
    timeout_seconds: float


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
        """Execute one validated Task invocation.

        A call carrying ``task_id`` resumes: the session-agent mapping lookup
        runs first and names the agent, so the call's own ``subagent_type``
        selects nothing on a resume.
        """

        discovery = self.discovery_fn(self.default_cwd)
        self._config_diagnostics = self._merged_config_diagnostics(discovery.by_name())
        try:
            request = validate_arguments(arguments)
        except ValidationFailure as exc:
            return self._fail_closed(str(exc), discovery=discovery)

        agents = discovery.by_name()
        if request.task_id is None:
            agent_name = request.subagent_type
            agent = agents.get(agent_name)
            if agent is None:
                return self._fail_closed(
                    f"unknown agent '{request.subagent_type}'",
                    discovery=discovery,
                )
        else:
            mapped_name = read_mapping_entry(request.task_id)
            if mapped_name is None:
                return _resume_fail_closed(
                    request.task_id,
                    f"the session-agent mapping has no entry for task_id '{request.task_id}'",
                    discovery,
                )
            agent_name = mapped_name
            agent = agents.get(mapped_name)
            if agent is None:
                return _resume_fail_closed(
                    request.task_id,
                    f"the mapping entry names agent '{mapped_name}', which no discoverable "
                    "agent provides",
                    discovery,
                )
        catalog_error = self._catalog_pin_error(agent_name, agent)
        if catalog_error is not None:
            return self._fail_closed(catalog_error, discovery=discovery)
        return await self._run_locked(request, agent, agent_name, discovery, signal, on_update)

    def _fail_closed(
        self,
        error: str,
        *,
        discovery: DiscoveryResult,
    ) -> AgentToolResult:
        """Return the fail-closed contract: teach-back content, empty results,
        no ``planned``, and no child started."""

        return _tool_result(
            _invalid_parameters_content(error, self),
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

    def _catalog_pin_error(self, agent_name: str, agent: AgentConfig) -> str | None:
        """Fail fast on a resolved pin pair the provider catalog cannot honor.

        Without a catalog the check is skipped. The resolution mirrors
        ``_dispatch_child`` exactly, so an accepted pair is the pair the child
        receives. On a resume, ``agent_name`` is the mapped name, so the mapped
        agent's config section keys the check.
        """

        if self.catalog_fn is None:
            return None
        snapshot = self.catalog_fn()
        if snapshot is None:
            return None
        config_overrides, config_defaults = self._config_layers(agent_name)
        provider, model = effective_provider_model(
            agent,
            config_overrides=config_overrides,
            config_defaults=config_defaults,
            parent_provider=self.parent_provider,
            parent_model=self.parent_model,
        )
        return provider_model_pin_error(
            provider,
            model,
            parent_provider=self.parent_provider,
            parent_model=self.parent_model,
            snapshot=snapshot,
        )

    async def _run_locked(
        self,
        request: ParsedRequest,
        agent: AgentConfig,
        agent_name: str,
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
                    discovery=discovery,
                )
            lock = acquired
        with lock:
            return await self._dispatch_child(
                request, agent, agent_name, discovery, signal, on_update
            )

    async def _dispatch_child(
        self,
        request: ParsedRequest,
        agent: AgentConfig,
        agent_name: str,
        discovery: DiscoveryResult,
        signal: ToolCancellationToken | None,
        on_update: ToolUpdateCallback | None,
    ) -> AgentToolResult:
        """Run the one child and build its envelope result.

        A fresh run generates the session id and writes its session-agent
        mapping entry before the runner call, so a write failure fails the
        dispatch closed with no child. A resume run pins the requested id and
        surfaces the runner's ``ResumeFailure`` under the fail-closed contract.
        Partial updates stream after each accepted child message and again on
        completion; the envelope appears only on the final result.
        """

        def emit(result: ChildResult) -> None:
            _emit_update(
                on_update,
                _progress_content(result),
                discovery,
                [result],
                config=self.config,
                config_diagnostics=self._config_diagnostics,
                usage_observer=self.usage_observer,
            )

        config_overrides, config_defaults = self._config_layers(agent_name)
        if request.task_id is None:
            fresh_id = uuid.uuid4().hex
            try:
                write_mapping_entry(fresh_id, agent.name)
            except MappingWriteError as exc:
                return _resume_fail_closed(None, str(exc), discovery)
            session = SessionSelection(id=fresh_id)
        else:
            session = SessionSelection(id=request.task_id, resume=True)
        try:
            result = await self.runner.run(
                default_cwd=self.default_cwd,
                agent=agent,
                task=request.prompt,
                config_overrides=config_overrides,
                config_defaults=config_defaults,
                parent_provider=self.parent_provider,
                parent_model=self.parent_model,
                parent_reasoning_effort=self.parent_reasoning_effort,
                timeout_seconds=request.timeout_seconds,
                signal=signal,
                on_message=emit,
                session=session,
            )
        except ResumeFailure as exc:
            return _resume_fail_closed(request.task_id, str(exc), discovery)
        emit(result)
        if self.usage_observer is not None:
            self.usage_observer([result], True)
        return _tool_result(
            build_envelope(result),
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
        raise ValidationFailure(_unknown_field_error(unknown))

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
        timeout_seconds=float(timeout_value),
    )


def _unknown_field_error(unknown: list[str]) -> str:
    """Build the unknown-field error, appending the removed-field sentence for
    every removed field the call carried, so the teach-back states the fix."""

    names = ", ".join(unknown)
    sentences = [
        _REMOVED_FIELD_SENTENCES[name] for name in unknown if name in _REMOVED_FIELD_SENTENCES
    ]
    if not sentences:
        return f"unknown field(s): {names}"
    return f"unknown field(s): {names}. " + " ".join(sentences)


def _optional_string(arguments: Mapping[str, JSONValue], key: str, *, nonempty: bool) -> str | None:
    if key not in arguments:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValidationFailure(f"{key} must be a string")
    if nonempty and not value.strip():
        raise ValidationFailure(f"{key} must be a non-empty string")
    return value


def _tool_result(
    content: str,
    *,
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


def _resume_fail_closed(
    task_id: str | None,
    reason: str,
    discovery: DiscoveryResult,
) -> AgentToolResult:
    """Build the fail-closed result for a resume failure or a failed mapping
    write: teach-back content, no envelope, empty results, and no ``planned``.

    On a resume, ``task_id`` is the requested id: the content preserves it,
    states that no child started, states ``reason``, directs the caller to
    ``task`` for a fresh child, names the call fields that exist on this
    surface, and names the session-agent mapping as the source of the resumed
    agent. On a fresh dispatch whose mapping write failed, ``task_id`` is
    ``None`` and the content omits the id-preservation clause.
    """

    mapping_path = default_mapping_path()
    if task_id is None:
        lines = [
            "Task dispatch failed: the session-agent mapping write failed, so no child started.",
            "",
            f"Reason: {reason}",
            "",
            "No child started and no child session exists. Confirm the mapping file at "
            f"{mapping_path} is writable, then retry the call.",
        ]
    else:
        lines = [
            f"Resume failed for task_id '{task_id}': no child started.",
            "",
            f"Reason: {reason}",
            "",
            f"task_id '{task_id}' is preserved and the session is unchanged. To start a "
            "fresh child instead, call task with the agent and prompt you want.",
            "",
            "A continuation call pairs task_id with subagent_type: the resumed agent comes "
            f"from the session-agent mapping at {mapping_path}, which records each child "
            "session's agent name. Call fields: prompt (required), task_id (required), "
            "timeoutSeconds (optional).",
        ]
    return _tool_result("\n".join(lines), discovery=discovery, results=[])


def _is_terminal(result: ChildResult) -> bool:
    return result.exit_code != 1 or result.error_message is not None


def _progress_content(result: ChildResult) -> str:
    """Preserved progress form, fixed to the single child: ``<done>/1 done``."""

    return f"{1 if _is_terminal(result) else 0}/1 done"


def _emit_update(
    callback: ToolUpdateCallback | None,
    content: str,
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
    """Teach back the call surface: roster, the pin resolution chain, and an
    example.

    Without the bundled workflow skills, this failure content is the only
    place a struggling controller learns the full call contract, so it must
    name the valid values, not just reject the call.
    """

    return "\n".join(
        (
            f"Invalid parameters: {error}",
            "",
            f"Available agents: {_teach_back_roster(dispatcher)}",
            "Children resolve provider, model, and thinking level per field from, highest "
            "first: the config file's [agents.<name>] section, the agent definition's "
            "frontmatter, the config file's [defaults] section, then this session's "
            "provider, model, and thinking level. Durable pins belong in the config file "
            "or an agent definition.",
            'Example: {"prompt": "Find caching options"}',
        )
    )
