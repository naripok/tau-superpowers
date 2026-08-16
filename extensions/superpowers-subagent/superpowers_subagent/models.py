"""Portable data models for the Tau subagent extension."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, cast

from tau_agent.messages import AgentMessage
from tau_agent.types import JSONValue

AgentScope = Literal["user", "project", "both"]
AgentSource = Literal["bundled", "user", "project", "unknown"]
AgentProfile = Literal["general-purpose", "read-only"]
DispatchMode = Literal["single", "parallel", "chain"]
SubagentStatus = Literal["DONE", "DONE_WITH_CONCERNS", "BLOCKED", "NEEDS_CONTEXT"]

#: Tau thinking levels, mirrored from Tau's own catalog vocabulary so the
#: extension validates reasoning-effort values without importing Tau internals.
THINKING_LEVELS: tuple[str, ...] = ("off", "minimal", "low", "medium", "high", "xhigh")


@dataclass(frozen=True, slots=True)
class AgentConfig:
    """A validated agent definition."""

    name: str
    description: str
    system_prompt: str
    source: AgentSource
    file_path: Path
    profile: AgentProfile = "general-purpose"
    provider: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Discovered agents and non-fatal diagnostics."""

    agents: tuple[AgentConfig, ...]
    project_agents_dir: Path | None
    diagnostics: tuple[str, ...]

    def by_name(self) -> dict[str, AgentConfig]:
        return {agent.name: agent for agent in self.agents}


@dataclass(frozen=True, slots=True)
class TaskItem:
    """One normalized child invocation."""

    agent: str
    task: str
    cwd: str | None = None


@dataclass(slots=True)
class UsageStats:
    """Usage accumulated from accepted assistant messages."""

    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    cost: float = 0.0
    context_tokens: int = 0
    turns: int = 0

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "input": self.input,
            "output": self.output,
            "cacheRead": self.cache_read,
            "cacheWrite": self.cache_write,
            "cost": self.cost,
            "contextTokens": self.context_tokens,
            "turns": self.turns,
        }


@dataclass(slots=True)
class ChildResult:
    """Complete or partial result from one Tau child."""

    agent: str
    agent_source: AgentSource
    task: str
    cwd: str
    exit_code: int = 1
    messages: list[AgentMessage] = field(default_factory=list)
    stderr: str = ""
    usage: UsageStats = field(default_factory=UsageStats)
    provider: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    stop_reason: str | None = None
    error_message: str | None = None
    status: SubagentStatus = "BLOCKED"
    step: int | None = None
    timed_out: bool = False
    cancelled: bool = False
    malformed_json_lines: int = 0

    @property
    def succeeded(self) -> bool:
        return (
            self.exit_code == 0
            and not self.timed_out
            and not self.cancelled
            and self.stop_reason not in {"error", "aborted"}
            and self.error_message is None
        )

    def to_dict(self) -> dict[str, JSONValue]:
        messages: list[JSONValue] = [
            cast(
                "dict[str, JSONValue]",
                message.model_dump(mode="json", by_alias=True, exclude_none=True),
            )
            for message in self.messages
        ]
        result: dict[str, JSONValue] = {
            "agent": self.agent,
            "agentSource": self.agent_source,
            "task": self.task,
            "cwd": self.cwd,
            "exitCode": self.exit_code,
            "messages": messages,
            "stderr": self.stderr,
            "usage": self.usage.to_dict(),
            "timedOut": self.timed_out,
            "cancelled": self.cancelled,
            "malformedJsonLines": self.malformed_json_lines,
            "status": self.status,
        }
        if self.provider is not None:
            result["provider"] = self.provider
        if self.model is not None:
            result["model"] = self.model
        if self.reasoning_effort is not None:
            result["reasoningEffort"] = self.reasoning_effort
        if self.stop_reason is not None:
            result["stopReason"] = self.stop_reason
        if self.error_message is not None:
            result["errorMessage"] = self.error_message
        if self.step is not None:
            result["step"] = self.step
        return result


def details_dict(
    *,
    mode: DispatchMode,
    agent_scope: AgentScope,
    project_agents_dir: Path | None,
    discovery_diagnostics: tuple[str, ...],
    results: list[ChildResult],
    planned: int | None = None,
) -> dict[str, JSONValue]:
    """Serialize schema-versioned Task details.

    ``planned`` is the number of children the dispatch intends to run. It lets
    partial-result renderers show accurate live counts before every child has
    produced its first message; renderers fall back to ``len(results)`` when
    absent.
    """

    details: dict[str, JSONValue] = {
        "schemaVersion": 1,
        "mode": mode,
        "agentScope": agent_scope,
        "projectAgentsDir": str(project_agents_dir) if project_agents_dir else None,
        "discoveryDiagnostics": list(discovery_diagnostics),
        "results": [result.to_dict() for result in results],
    }
    if planned is not None:
        details["planned"] = planned
    return details
