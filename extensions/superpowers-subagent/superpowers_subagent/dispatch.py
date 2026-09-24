"""Task validation and single-child dispatch for the two-tool surface."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

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

#: The calling tool. ``fresh`` dispatches a new child; ``resume`` continues an
#: existing child session and never names an agent.
RequestMode = Literal["fresh", "resume"]

#: The exact per-tool field surfaces; anything else fails closed. Each tool's
#: unknown-field check rejects the other tool's fields automatically.
_TASK_FIELDS = frozenset({"prompt", "subagent_type", "description", "timeout_seconds"})
_RESUME_FIELDS = frozenset({"prompt", "task_id", "timeout_seconds"})

#: The dedicated background reason, shared by both tools. ``execute`` returns
#: the teach-back built from this text directly, so the background rejection
#: carries no roster and no field list.
_BACKGROUND_REASON = (
    "background dispatch is not supported in this harness. The result arrives when the "
    "child finishes; several calls of the same tool in one message run children in parallel."
)

#: The reason for the cross-tool rejection: ``task`` never carries ``task_id``.
_TASK_ID_ON_TASK_REASON = (
    "task_id is not a task parameter. task_resume continues an existing child session: "
    "call it with the task_id from the earlier task result, for example "
    '{"prompt": "Continue the work.", "task_id": "<task_id>"}.'
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
    "timeoutSeconds": (
        "The camelCase timeoutSeconds field is removed: pass timeout_seconds instead."
    ),
}

UsageObserver = Callable[[Sequence[ChildResult], bool], None]


@dataclass(frozen=True, slots=True)
class ParsedRequest:
    """One validated task call: exactly one prompt for exactly one child, on
    the tool the ``mode`` names."""

    #: The calling tool: ``fresh`` dispatches a new child, ``resume`` continues
    #: an existing child session.
    mode: RequestMode
    #: The call's prompt, preserved verbatim; it is the child's task.
    prompt: str
    #: Effective agent name after trimming; omission resolves to general-purpose.
    #: Fresh calls only: a resume never names an agent.
    subagent_type: str
    description: str | None
    #: Trimmed effective id for the session-agent mapping lookup, the session
    #: selection, and the same-id lock. Resume calls only.
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
        *,
        mode: RequestMode,
        signal: ToolCancellationToken | None = None,
        on_update: ToolUpdateCallback | None = None,
    ) -> AgentToolResult:
        """Execute one validated Task invocation on the tool ``mode`` names.

        A ``resume`` call resolves the mapped agent from the session-agent
        mapping and pins the requested session. A ``fresh`` call dispatches a
        new child and writes its mapping entry before the spawn.
        """

        discovery = self.discovery_fn(self.default_cwd)
        self._config_diagnostics = self._merged_config_diagnostics(discovery.by_name())
        if "background" in arguments:
            return self._background_fail_closed(discovery=discovery)
        try:
            request = validate_arguments(arguments, mode)
        except ValidationFailure as exc:
            return self._fail_closed(str(exc), discovery=discovery, mode=mode)

        agents = discovery.by_name()
        if request.mode == "fresh":
            agent_name = request.subagent_type
            agent = agents.get(agent_name)
            if agent is None:
                return self._fail_closed(
                    f"unknown agent '{request.subagent_type}'",
                    discovery=discovery,
                    mode=mode,
                )
        else:
            # Validation guarantees a resume request carries a trimmed id.
            assert request.task_id is not None
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
            return self._fail_closed(catalog_error, discovery=discovery, mode=mode)
        return await self._run_locked(request, agent, agent_name, discovery, signal, on_update)

    def _background_fail_closed(self, *, discovery: DiscoveryResult) -> AgentToolResult:
        """Return the dedicated background teach-back without the composer: the
        background rejection carries no roster and no field list on either tool."""

        return _tool_result(
            f"Invalid parameters: {_BACKGROUND_REASON}",
            discovery=discovery,
            results=[],
        )

    def _fail_closed(
        self,
        error: str,
        *,
        discovery: DiscoveryResult,
        mode: RequestMode,
    ) -> AgentToolResult:
        """Return the fail-closed contract: teach-back content, empty results,
        no ``planned``, and no child started."""

        return _tool_result(
            _invalid_parameters_content(error, self, mode),
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
        """Run the single child under the same-id lock in resume mode only: a
        fresh call never locks. A lost race fails closed with the conflict
        teach-back instead of waiting for the winner."""

        lock: AbstractContextManager[None] = nullcontext()
        if request.mode == "resume":
            # Validation guarantees a resume request carries a trimmed id.
            assert request.task_id is not None
            acquired = same_id_lock(request.task_id)
            if acquired is None:
                return self._fail_closed(
                    f"another running task call already holds task_id '{request.task_id}'. "
                    "Wait for that call to finish or use a different task_id.",
                    discovery=discovery,
                    mode=request.mode,
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
        if request.mode == "fresh":
            fresh_id = uuid.uuid4().hex
            try:
                write_mapping_entry(fresh_id, agent.name)
            except MappingWriteError as exc:
                return _resume_fail_closed(None, str(exc), discovery)
            session = SessionSelection(id=fresh_id)
        else:
            # Validation guarantees a resume request carries a trimmed id.
            assert request.task_id is not None
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


def validate_arguments(arguments: Mapping[str, JSONValue], mode: RequestMode) -> ParsedRequest:
    """Validate and normalize one single-object call on the tool ``mode`` names.

    The checks run in a fixed order: the ``background`` check first, then on
    ``task`` only the cross-tool ``task_id`` rejection, then the unknown-field
    check against that tool's field set, then ``prompt``, then the mode-specific
    fields, then ``timeout_seconds``. The raised ``ValidationFailure`` carries
    the reason text only: the composer appends the mode context.
    """

    if "background" in arguments:
        raise ValidationFailure(_BACKGROUND_REASON)
    if mode == "fresh" and "task_id" in arguments:
        raise ValidationFailure(_TASK_ID_ON_TASK_REASON)
    fields = _TASK_FIELDS if mode == "fresh" else _RESUME_FIELDS
    unknown = sorted(set(arguments) - fields)
    if unknown:
        raise ValidationFailure(_unknown_field_error(unknown))

    prompt = arguments.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValidationFailure("prompt requires a non-empty string")

    subagent_type = "general-purpose"
    description: str | None = None
    task_id: str | None = None
    if mode == "fresh":
        if "subagent_type" in arguments:
            value = arguments["subagent_type"]
            if not isinstance(value, str) or not value.strip():
                raise ValidationFailure("subagent_type requires a non-empty string when present")
            subagent_type = value.strip()
        description = _optional_string(arguments, "description")
    else:
        value = arguments.get("task_id")
        if not isinstance(value, str) or not value.strip():
            raise ValidationFailure("task_id is required and requires a non-empty string")
        task_id = value.strip()

    timeout_value = arguments.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    if (
        isinstance(timeout_value, bool)
        or not isinstance(timeout_value, (int, float))
        or not 0 < timeout_value <= MAX_TIMEOUT_SECONDS
    ):
        raise ValidationFailure("timeout_seconds must be greater than 0 and at most 10800")

    return ParsedRequest(
        mode=mode,
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


def _optional_string(arguments: Mapping[str, JSONValue], key: str) -> str | None:
    if key not in arguments:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValidationFailure(f"{key} must be a string")
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
            f"The resumed agent comes from the session-agent mapping at {mapping_path}, "
            "which records each child session's agent name, so the call carries no agent "
            "name. Call fields: prompt (required), task_id (required), timeout_seconds "
            "(optional).",
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


def _invalid_parameters_content(error: str, dispatcher: TaskDispatcher, mode: RequestMode) -> str:
    """Compose every validation teach-back with its mode context.

    On ``task`` the content carries the static session-start roster, the pin
    resolution chain, and one valid ``task`` example. On ``resume`` it names
    the three ``task_resume`` fields and the session-agent mapping, and lists
    no agents: the resume caller cannot select one, and a roster re-creates
    the removed agent-invention surface.
    """

    lines = [f"Invalid parameters: {error}", ""]
    if mode == "fresh":
        lines.extend(
            (
                f"Available agents: {_teach_back_roster(dispatcher)}",
                "Children resolve provider, model, and thinking level per field from, highest "
                "first: the config file's [agents.<name>] section, the agent definition's "
                "frontmatter, the config file's [defaults] section, then this session's "
                "provider, model, and thinking level. Durable pins belong in the config file "
                "or an agent definition.",
                'Example: {"prompt": "Find caching options"}',
            )
        )
    else:
        lines.extend(
            (
                "Call fields: prompt (required), task_id (required), timeout_seconds (optional).",
                "The resumed agent comes from the session-agent mapping at "
                f"{default_mapping_path()}, which records each child session's agent name.",
            )
        )
    return "\n".join(lines)
