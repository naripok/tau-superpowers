#!/usr/bin/env python3
"""Scripted evaluation of the model-facing task surface against the ambient provider.

The script runs four scripted controller sessions of
`tau --mode json --no-approve --no-extensions -e extensions/superpowers-subagent "<prompt>"`,
parses the stdout JSON event lines, and records per case: the emitted tool calls with their
complete argument objects, the fail-closed teach-back contents, and the number of launched
children. It writes `report.md` and `raw-events.jsonl` into the output directory. The
evaluation is independent of the unit suite: it exercises the real extension surface with
whatever provider and model the harness configures.

The sessions pass `--no-extensions` so the pinned `-e` path is the only loaded extension:
explicit `-e` paths still load with the flag. Without it, a same-name copy installed under
~/.tau/extensions shadows the `-e` path (Tau's loader dedupes by name and the user dir
precedes `-e` extras) and the sessions measure that copy instead of the repository surface.

The hard measures bind per rejected call: in the unknown-resume and camelcase sessions,
every rejected call's own result must record the fail-closed contract — no launched-child
envelope, an empty `results` array, and the teach-back — so the rejected call itself
launches zero children. A follow-up call the model makes after a teach-back is a
legitimate new dispatch, so the session-level child count and the post-teach-back
behavior are recorded observations, not gates.

Exit codes:
- 0: every session ran and the hard measures hold (see above).
- 1: a hard measure failed, or a session failed to run.
- 3: the ambient harness has no configured provider. The report records the blocked
  state; the gate accepts exit 3 with the blocked report.

The script is stdlib-only and prints no environment values.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

#: The script lives at <repo>/extensions/superpowers-subagent/scripts/, so the
#: repository root is three levels up. The `-e` path and the default output
#: directory resolve against this root regardless of the caller's cwd.
REPO_ROOT = Path(__file__).resolve().parents[3]
EXTENSION_DIR = REPO_ROOT / "extensions" / "superpowers-subagent"
DEFAULT_OUTPUT_DIR = (
    REPO_ROOT / "docs" / "design" / "evidence" / "task-tool-robustness" / "agent-surface-evaluation"
)
REPORT_NAME = "report.md"
RAW_EVENTS_NAME = "raw-events.jsonl"

DEFAULT_TIMEOUT_SECONDS = 600.0
STDERR_TAIL_CHARS = 4_000
MAX_UNPARSED_LINE_CHARS = 2_000

#: The two model-facing tools of the implemented surface.
TASK_SURFACE_TOOLS = frozenset({"task", "task_resume"})
#: The complete `task` call surface; anything else fails closed.
TASK_SURFACE_FIELDS = frozenset({"prompt", "subagent_type", "description", "timeout_seconds"})
#: `task` fields the caller can omit; the key measure counts these on ordinary calls.
TASK_OPTIONAL_FIELDS = frozenset({"subagent_type", "description", "timeout_seconds"})
#: The camelCase remnant the dedicated teach-back names.
CAMELCASE_FIELD = "timeoutSeconds"
#: Substrings every rejected call's teach-back must carry, per failed-resume case.
#: The hard measure binds to the rejected call's own result, so the checks read
#: that call's content only.
TEACH_BACK_CHECKS: dict[str, tuple[tuple[str, str], ...]] = {
    "unknown-resume": (
        ("preserve the rejected task_id `nonexistent`", "nonexistent"),
        ("direct the caller to `task`", "call task with the agent and prompt"),
    ),
    "camelcase": (
        ("name `timeoutSeconds`", CAMELCASE_FIELD),
        ("show `timeout_seconds`", "timeout_seconds"),
    ),
}

#: Envelope marker of a launched child, as built by ``build_envelope``: the state
#: is the process outcome only, ``completed`` or ``error``.
ENVELOPE_PATTERN = re.compile(r'<task(?: id="([^"]*)")? state="(completed|error)">')
#: stderr diagnostic of a harness with no configured provider, before any model call.
NO_PROVIDER_PATTERN = re.compile(r"missing provider api key|run /login", re.IGNORECASE)
#: Session flags for every controller session. ``--no-extensions`` keeps the
#: pinned ``-e`` path the only loaded extension: a same-name copy installed
#: under ~/.tau/extensions otherwise shadows it (first-loaded wins).
SESSION_FLAGS: tuple[str, ...] = ("--mode", "json", "--no-approve", "--no-extensions")
#: The extension's recursion-guard variable. A scripted controller is not a
#: subagent, so the variable is dropped from the session environment: keeping it
#: disables the task tools and makes every case meaningless.
RECURSION_GUARD = "TAU_SUPERPOWERS_SUBAGENT"


@dataclass(frozen=True, slots=True)
class Case:
    """One scripted controller session: a name and the exact controller prompt."""

    name: str
    prompt: str


CASES: tuple[Case, ...] = (
    Case(
        "fresh",
        "Use the task tool to dispatch one general-purpose subagent. Ask it to report the "
        "working directory it runs in. Relay the report, then finish.",
    ),
    Case(
        "resume",
        "Use the task tool to dispatch one general-purpose subagent and ask it to compute "
        "one plus one. Then use the task_resume tool to continue that child session and "
        "ask it to multiply the result by three. Relay both results.",
    ),
    Case(
        "unknown-resume",
        "Use the task_resume tool with task_id set to the exact text nonexistent and the "
        "prompt 'Report status.' Wait for the result and relay it verbatim.",
    ),
    Case(
        "camelcase",
        "Use the task tool to dispatch one general-purpose subagent. Pass timeoutSeconds "
        "with the value 120 as a call argument, exactly that spelling. Relay the result.",
    ),
)


@dataclass(frozen=True, slots=True)
class SessionFacts:
    """Process-level facts of one controller session run."""

    exit_code: int | None
    timed_out: bool
    duration_seconds: float
    stderr_tail: str

    @property
    def failed(self) -> bool:
        """True when the session timed out or exited non-zero."""
        return self.timed_out or self.exit_code != 0


@dataclass(frozen=True, slots=True)
class SurfaceCall:
    """One task-surface call: the emitted arguments and its own result.

    `rejected` marks the implemented fail-closed contract: the result's details
    carry an empty `results` array. A rejected call launches no child and its
    content is the teach-back; envelopes belong to non-rejected dispatches.
    """

    tool: str
    arguments: dict[str, object]
    content: str
    rejected: bool
    #: Launched-child envelope markers in this call's own result content.
    envelopes: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class CaseRecord:
    """Everything the evaluation records about one case."""

    case: str
    prompt: str
    session: SessionFacts
    provider: str | None
    model: str | None
    #: The task-surface calls in emission order, each paired with its own result.
    calls: list[SurfaceCall]
    #: Task-surface toolCall blocks read from assistant messages; cross-evidence
    #: for the harness-observed calls.
    assistant_task_calls: list[dict[str, object]]

    @property
    def rejected_calls(self) -> list[SurfaceCall]:
        """Calls whose own result records the fail-closed contract (empty `results`)."""
        return [call for call in self.calls if call.rejected]

    @property
    def teach_backs(self) -> list[str]:
        """The rejected calls' teach-back contents, in emission order."""
        return [call.content for call in self.rejected_calls]

    @property
    def launched_children(self) -> int:
        """Session-level launched children: envelopes across every call's own result.

        A follow-up call after a teach-back is a legitimate new dispatch, so this
        session-level count is recorded, not gated.
        """
        return sum(len(call.envelopes) for call in self.calls)

    @property
    def follow_up_calls(self) -> list[SurfaceCall]:
        """The calls emitted after the session's last rejected call.

        A follow-up is defined relative to a teach-back, so the list is empty
        when the session recorded no rejected call.
        """
        if not any(call.rejected for call in self.calls):
            return []
        last = max((index for index, call in enumerate(self.calls) if call.rejected), default=-1)
        return self.calls[last + 1 :]


def parse_stream(
    case_name: str, stdout: str
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Parse stdout into JSON events and matching raw records.

    Every non-empty line becomes one raw record, so the recorded stream is the
    complete session output; lines that fail to parse are preserved verbatim,
    truncated.
    """

    events: list[dict[str, object]] = []
    raw: list[dict[str, object]] = []
    for seq, line in enumerate(stdout.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            event = json.loads(stripped)
        except json.JSONDecodeError:
            raw.append(
                {"case": case_name, "seq": seq, "unparsed": stripped[:MAX_UNPARSED_LINE_CHARS]}
            )
        else:
            events.append(event)
            raw.append({"case": case_name, "seq": seq, "event": event})
    return events, raw


def session_environment() -> dict[str, str]:
    """The ambient environment without the extension's recursion-guard variable."""

    return {name: value for name, value in os.environ.items() if name != RECURSION_GUARD}


def session_command(prompt: str) -> list[str]:
    """The controller session command for one prompt."""

    return ["tau", *SESSION_FLAGS, "-e", str(EXTENSION_DIR), prompt]


def run_session(
    case: Case, timeout: float
) -> tuple[SessionFacts, list[dict[str, object]], list[dict[str, object]]]:
    """Run one controller session; return its process facts, events, and raw records."""

    command = session_command(case.prompt)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            cwd=REPO_ROOT,
            env=session_environment(),
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        facts = SessionFacts(
            exit_code=None,
            timed_out=True,
            duration_seconds=time.monotonic() - started,
            stderr_tail=stderr[-STDERR_TAIL_CHARS:],
        )
        events, raw = parse_stream(case.name, stdout)
        return facts, events, raw
    except OSError as exc:
        facts = SessionFacts(
            exit_code=127,
            timed_out=False,
            duration_seconds=time.monotonic() - started,
            stderr_tail=f"could not start tau: {exc}"[:STDERR_TAIL_CHARS],
        )
        return facts, [], []
    facts = SessionFacts(
        exit_code=completed.returncode,
        timed_out=False,
        duration_seconds=time.monotonic() - started,
        stderr_tail=completed.stderr[-STDERR_TAIL_CHARS:],
    )
    events, raw = parse_stream(case.name, completed.stdout)
    return facts, events, raw


def _text_of(blocks: object) -> str:
    """Concatenate the text blocks of one content list; other blocks are skipped."""

    if not isinstance(blocks, list):
        return ""
    parts = [
        block["text"]
        for block in blocks
        if isinstance(block, dict)
        and block.get("type") == "text"
        and isinstance(block["text"], str)
    ]
    return "".join(parts)


def _provider_model(events: list[dict[str, object]]) -> tuple[str | None, str | None]:
    """The provider and model of the first assistant response in the stream."""

    for event in events:
        if event.get("type") != "message_end":
            continue
        message = event.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        provider = message.get("provider")
        if provider in (None, "unknown"):
            continue
        model = message.get("model")
        return str(provider), None if model in (None, "unknown") else str(model)
    return None, None


def _assistant_task_calls(events: list[dict[str, object]]) -> list[dict[str, object]]:
    """Task-surface toolCall blocks read from assistant messages."""

    calls = []
    for event in events:
        if event.get("type") != "message_end":
            continue
        message = event.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "toolCall":
                continue
            if block.get("name") not in TASK_SURFACE_TOOLS:
                continue
            arguments = block.get("arguments")
            calls.append(
                {
                    "tool": block.get("name"),
                    "arguments": arguments if isinstance(arguments, dict) else {},
                }
            )
    return calls


def _envelopes_in(content: str) -> list[dict[str, object]]:
    """The launched-child envelope markers in one result content."""

    return [
        {"task_id": match.group(1), "state": match.group(2)}
        for match in ENVELOPE_PATTERN.finditer(content)
    ]


def _pair_calls(events: list[dict[str, object]]) -> list[SurfaceCall]:
    """Pair task-surface start/end events by toolCallId, keeping emission order.

    A start without an end (for example a session cut off mid-call) still yields
    a call, with its result recorded as absent.
    """

    starts: dict[object, dict[str, object]] = {}
    ends: dict[object, dict[str, object]] = {}
    order: list[object] = []
    for event in events:
        event_type = event.get("type")
        if event_type not in ("tool_execution_start", "tool_execution_end"):
            continue
        if event.get("toolName") not in TASK_SURFACE_TOOLS:
            continue
        key = event.get("toolCallId")
        if key not in starts and key not in ends:
            order.append(key)
        if event_type == "tool_execution_start":
            starts[key] = event
        else:
            ends[key] = event
    calls = []
    for key in order:
        start = starts.get(key)
        end = ends.get(key)
        started_event = start if start is not None else {}
        ended_event = end if end is not None else {}
        tool = str(started_event.get("toolName") or ended_event.get("toolName") or "")
        arguments = started_event.get("args")
        result = ended_event.get("result")
        content = _text_of(result.get("content")) if isinstance(result, dict) else ""
        details = result.get("details") if isinstance(result, dict) else None
        calls.append(
            SurfaceCall(
                tool=tool,
                arguments=arguments if isinstance(arguments, dict) else {},
                content=content,
                rejected=isinstance(details, dict) and details.get("results") == [],
                envelopes=_envelopes_in(content),
            )
        )
    return calls


def build_record(case: Case, facts: SessionFacts, events: list[dict[str, object]]) -> CaseRecord:
    """Derive the case record from one session's parsed events."""

    provider, model = _provider_model(events)
    return CaseRecord(
        case=case.name,
        prompt=case.prompt,
        session=facts,
        provider=provider,
        model=model,
        calls=_pair_calls(events),
        assistant_task_calls=_assistant_task_calls(events),
    )


def is_blocked(record: CaseRecord) -> bool:
    """True when the session failed before any model response with a
    missing-provider diagnostic: the ambient harness has no configured provider."""

    return (
        record.provider is None
        and record.session.failed
        and bool(NO_PROVIDER_PATTERN.search(record.session.stderr_tail))
    )


def evaluate(timeout: float) -> tuple[list[CaseRecord], list[dict[str, object]], bool]:
    """Run the cases in order; stop early only on the blocked state.

    Returns the case records, the raw records of every session, and whether the
    ambient harness was detected as having no configured provider.
    """

    records: list[CaseRecord] = []
    raw: list[dict[str, object]] = []
    blocked = False
    for case in CASES:
        facts, events, raw_records = run_session(case, timeout)
        raw.extend(raw_records)
        record = build_record(case, facts, events)
        records.append(record)
        if is_blocked(record):
            blocked = True
            break
    return records, raw, blocked


def fresh_observations(record: CaseRecord) -> dict[str, object]:
    """Tool name, surface-subset, and optional-field facts for the fresh case."""

    task_calls = [call for call in record.calls if call.tool == "task"]
    if not task_calls:
        return {
            "tool": None,
            "argument_keys": [],
            "keys_within_task_surface": None,
            "optional_fields": [],
        }
    first = task_calls[0]
    keys = sorted(first.arguments)
    return {
        "tool": first.tool,
        "argument_keys": keys,
        "keys_within_task_surface": set(keys) <= TASK_SURFACE_FIELDS,
        "optional_fields": sorted(set(keys) & TASK_OPTIONAL_FIELDS),
    }


def _envelope_ids(record: CaseRecord, tool: str) -> list[object]:
    """The launched-child task_ids of every call of one tool, in emission order."""

    return [
        envelope["task_id"]
        for call in record.calls
        if call.tool == tool
        for envelope in call.envelopes
    ]


def resume_observations(record: CaseRecord) -> dict[str, object]:
    """Child counts and task-id passthrough facts for the resume case."""

    fresh_ids = _envelope_ids(record, "task")
    resumed_ids = _envelope_ids(record, "task_resume")
    passed_ids = [
        call.arguments.get("task_id") for call in record.calls if call.tool == "task_resume"
    ]
    passed_id = passed_ids[-1] if passed_ids else None
    return {
        "fresh_children": len(fresh_ids),
        "resumed_children": len(resumed_ids),
        "fresh_envelope_task_id": fresh_ids[0] if fresh_ids else None,
        "task_resume_task_id": passed_id,
        "task_id_passthrough_matches": bool(fresh_ids and passed_id and fresh_ids[0] == passed_id),
    }


def unknown_resume_observations(record: CaseRecord) -> dict[str, bool]:
    """Whether each rejected call's teach-back preserves the id and directs to `task`."""

    content = "\n".join(record.teach_backs)
    return {
        "preserves_nonexistent": "nonexistent" in content,
        "directs_to_task": "call task with the agent and prompt" in content,
    }


def camelcase_observations(record: CaseRecord) -> dict[str, object]:
    """The rejected teach-back facts and the residual camelCase observation.

    The residual rate counts the follow-up calls after the teach-back: how many
    re-emitted the camelCase field and how many carried the corrected spelling.
    """

    content = "\n".join(record.teach_backs)
    return {
        "names_timeoutSeconds": CAMELCASE_FIELD in content,
        "shows_timeout_seconds": "timeout_seconds" in content,
        "emitted_camelcase": sum(1 for call in record.calls if CAMELCASE_FIELD in call.arguments),
        "follow_up_calls": len(record.follow_up_calls),
        "residual_camelcase": sum(
            1 for call in record.follow_up_calls if CAMELCASE_FIELD in call.arguments
        ),
        "corrected_spelling": sum(
            1 for call in record.follow_up_calls if "timeout_seconds" in call.arguments
        ),
    }


def accidental_launches(record: CaseRecord) -> int:
    """Launches attributable to rejected calls: envelopes in a rejected call's own result.

    This is the count the hard measure holds at zero for the failed-resume cases.
    Session-level children include legitimate follow-up dispatches after a
    teach-back and are recorded separately.
    """

    return sum(len(call.envelopes) for call in record.rejected_calls)


def rejected_call_violations(record: CaseRecord) -> list[str]:
    """Violations of the per-rejected-call fail-closed contract for one case.

    The contract binds to the rejected call's own result: it carries no
    launched-child envelope and the case's teach-back content. The empty
    `results` array is the rejection marker itself, so a rejected call that
    satisfies these checks launches zero children. Follow-up calls after a
    teach-back are legitimate new dispatches and are never violations.
    """

    checks = TEACH_BACK_CHECKS.get(record.case)
    if checks is None:
        return []
    violations = []
    for number, call in enumerate(record.rejected_calls, start=1):
        if call.envelopes:
            violations.append(
                f"case {record.case}: rejected call {number} (`{call.tool}`) carries a "
                "launched-child envelope in its own result"
            )
        for label, needle in checks:
            if needle not in call.content:
                violations.append(
                    f"case {record.case}: rejected call {number} (`{call.tool}`) teach-back "
                    f"does not {label}"
                )
    return violations


def classify(records: list[CaseRecord], blocked: bool) -> tuple[int, str]:
    """The script exit code and the one-line outcome the report records.

    The hard measures bind per rejected call: in the failed-resume cases every
    rejected call's own result must record the fail-closed contract. Session
    child counts and post-teach-back behavior are recorded, not gated.
    """

    if blocked:
        return 3, "blocked — the ambient harness has no configured provider"
    if any(record.session.failed for record in records):
        return 1, "failed — at least one session did not run to completion"
    violations = [item for record in records for item in rejected_call_violations(record)]
    if violations:
        return 1, f"failed — the fail-closed contract is unmet: {'; '.join(violations)}"
    return (
        0,
        "passed — every rejected call in the failed-resume cases records the fail-closed "
        "contract: no launched-child envelope, an empty `results` array, and the teach-back",
    )


def _tool_list(calls: list[SurfaceCall]) -> str:
    """A comma-separated tool-name list for an observation line."""

    if not calls:
        return "none"
    return ", ".join(f"`{call.tool}`" for call in calls)


def _rejected_call_proof_line(record: CaseRecord) -> str:
    """The per-rejected-call fail-closed proof line for a failed-resume case."""

    return (
        f"Rejected calls: {len(record.rejected_calls)}. Per-rejected-call proof: every "
        f"rejected call's own result carries an empty `results` array (the rejection marker); "
        f"launched-child envelopes across those rejected results: "
        f"{accidental_launches(record)} — the hard measure holds this at zero."
    )


def _render_call(position: int, call: SurfaceCall, teach_back_number: int | None) -> list[str]:
    """The report lines for one emitted call: its arguments and its own result."""

    arguments = json.dumps(call.arguments, sort_keys=True)
    lines = [f"{position}. `{call.tool}` arguments: `{arguments}`"]
    if call.envelopes:
        launched = ", ".join(
            f"task_id={envelope['task_id']} state={envelope['state']}"
            for envelope in call.envelopes
        )
        own = f"own result: launched {len(call.envelopes)} child(ren) — {launched}"
    else:
        own = "own result: no launched-child envelope"
    if call.rejected:
        own += (
            "; rejected — the result carries an empty `results` array; "
            f"teach-back {teach_back_number} below"
        )
    lines.append(f"   {own}")
    return lines


def _case_observations(record: CaseRecord) -> list[str]:
    """The case-specific recorded observations for one report section."""

    if record.case == "fresh":
        observed = fresh_observations(record)
        optional = ", ".join(f"`{name}`" for name in observed["optional_fields"]) or "none"
        return [
            f"Tool name observed: `{observed['tool']}`; argument keys within the `task` "
            f"surface: {observed['keys_within_task_surface']};",
            f"optional fields carried: {len(observed['optional_fields'])} ({optional}).",
        ]
    if record.case == "resume":
        observed = resume_observations(record)
        return [
            f"Fresh children: {observed['fresh_children']}; resumed children: "
            f"{observed['resumed_children']}.",
            f"Fresh envelope task_id: `{observed['fresh_envelope_task_id']}`; task_resume "
            f"received task_id: `{observed['task_resume_task_id']}`; passthrough matches: "
            f"{observed['task_id_passthrough_matches']}.",
            "A failure to resume is a recorded observation, not a gate.",
        ]
    if record.case == "unknown-resume":
        observed = unknown_resume_observations(record)
        return [
            _rejected_call_proof_line(record),
            f"Teach-back preserves `nonexistent`: {observed['preserves_nonexistent']}; "
            f"directs the caller to `task`: {observed['directs_to_task']}.",
            f"Follow-up observation: {len(record.follow_up_calls)} follow-up call(s) after "
            f"the rejected call ({_tool_list(record.follow_up_calls)}); a follow-up dispatch "
            "is a legitimate new dispatch, recorded not gated.",
        ]
    if record.case == "camelcase":
        observed = camelcase_observations(record)
        return [
            _rejected_call_proof_line(record),
            f"Teach-back names `timeoutSeconds`: {observed['names_timeoutSeconds']}; shows "
            f"`timeout_seconds`: {observed['shows_timeout_seconds']}.",
            f"Residual-rate observation: the model emitted `timeoutSeconds` on "
            f"{observed['emitted_camelcase']} call(s); after the teach-back it made "
            f"{observed['follow_up_calls']} follow-up call(s), "
            f"{observed['residual_camelcase']} re-emitted `timeoutSeconds`, and "
            f"{observed['corrected_spelling']} carried the corrected `timeout_seconds`.",
        ]
    return []


def render_case(index: int, record: CaseRecord) -> list[str]:
    """The report section for one recorded case."""

    session = record.session
    if session.timed_out:
        session_line = f"Session: timed out after {session.duration_seconds:.0f}s"
    else:
        session_line = f"Session: exit code {session.exit_code}, {session.duration_seconds:.1f}s"
    lines = [
        f"## Case {index} — {record.case}",
        "",
        f"Prompt: `{record.prompt}`",
        "",
        session_line,
        "",
        f"Provider/model: {record.provider or '(no model response)'} / "
        f"{record.model or '(unknown)'}",
        "",
        f"Emitted task-surface calls ({len(record.calls)}):",
        "",
    ]
    if record.calls:
        rejected_seen = 0
        for position, call in enumerate(record.calls, start=1):
            number = None
            if call.rejected:
                rejected_seen += 1
                number = rejected_seen
            lines += _render_call(position, call, number)
    else:
        lines.append("none observed")
    lines.append("")
    if record.teach_backs:
        lines.append(f"Fail-closed teach-backs ({len(record.teach_backs)}):")
        for content in record.teach_backs:
            lines += ["", "```", content, "```"]
    else:
        lines.append("Fail-closed teach-backs: none observed")
    lines += [
        "",
        f"Launched children, session-level (recorded, not gated): {record.launched_children}",
    ]
    for position, call in enumerate(record.calls, start=1):
        lines += [
            f"- call {position} (`{call.tool}`): task_id={envelope['task_id']} "
            f"state={envelope['state']}"
            for envelope in call.envelopes
        ]
    lines += ["", *_case_observations(record), ""]
    return lines


def render_key_measures(records: list[CaseRecord], *, exit_code: int, blocked: bool) -> list[str]:
    """The closing section: the two key measures plus the residual camelCase rate."""

    lines = ["## Key measures", ""]
    fresh = next((item for item in records if item.case == "fresh"), None)
    if fresh is None:
        lines.append("- Optional fields on the ordinary fresh call: not measured (blocked).")
    else:
        observed = fresh_observations(fresh)
        keys = ", ".join(f"`{name}`" for name in observed["argument_keys"]) or "none"
        lines.append(
            f"- Optional fields on the ordinary fresh call (case 1 `task`): "
            f"{len(observed['optional_fields'])} (argument keys: {keys})."
        )
    for name in TEACH_BACK_CHECKS:
        record = next((item for item in records if item.case == name), None)
        if record is None:
            lines.append(
                f"- Accidental launches after a failed resume (case `{name}`): "
                "not measured (blocked)."
            )
            continue
        lines.append(
            f"- Accidental launches after a failed resume (case `{name}`): "
            f"{accidental_launches(record)} launched-child envelope(s) across the rejected "
            f"calls' own results; session-level children: {record.launched_children} "
            "(recorded, not gated)."
        )
    camel = next((item for item in records if item.case == "camelcase"), None)
    if camel is not None:
        observed = camelcase_observations(camel)
        lines.append(
            f"- Residual camelCase rate (case `camelcase`): {observed['residual_camelcase']}/"
            f"{observed['follow_up_calls']} follow-up call(s) re-emitted `timeoutSeconds` "
            "after the teach-back."
        )
    lines.append("")
    if blocked:
        lines.append("Hard measures: BLOCKED — the provider the harness configures is missing.")
    elif exit_code == 0:
        lines.append(
            "Hard measures: PASS — every rejected call in the failed-resume cases records the "
            "fail-closed contract: no launched-child envelope, an empty `results` array, and "
            "the teach-back."
        )
    else:
        lines.append("Hard measures: FAIL — see the script exit line above.")
    lines.append("")
    return lines


def render_report(
    records: list[CaseRecord],
    *,
    blocked: bool,
    exit_code: int,
    outcome: str,
    generated_at: str,
) -> str:
    """Assemble report.md from the recorded case records."""

    extension_relative = EXTENSION_DIR.relative_to(REPO_ROOT)
    lines = [
        "# Agent-facing surface evaluation — task-tool-robustness",
        "",
        f"Recorded: {generated_at}",
        "Session command: `tau "
        + " ".join(SESSION_FLAGS)
        + f" -e {extension_relative} "
        + '"<case prompt>"`',
        f"Script exit: {exit_code} — {outcome}",
        "",
        "The sessions pass `--no-extensions` so the pinned `-e` path is the only loaded "
        "extension: explicit `-e` paths still load with the flag, while a same-name copy "
        "installed under `~/.tau/extensions` would otherwise shadow it (Tau's loader dedupes "
        "by name and the user dir precedes `-e` extras). The evaluation therefore exercises "
        "the repository's implemented surface.",
        "",
        "The evaluation runs four scripted controller sessions against the provider and "
        "model the harness configures at evaluation time. Results are reported separately "
        "from the unit-test outcome. The hard measures bind per rejected call: a follow-up "
        "call a model makes after a teach-back is a legitimate new dispatch, so the "
        "session-level child counts are recorded, not gated.",
        "",
    ]
    if blocked:
        blocked_record = records[0] if records else None
        lines += [
            "Blocked: the first session failed before any model call with a "
            "missing-provider diagnostic, so the ambient harness has no configured "
            "provider. The gate accepts this blocked report with exit 3.",
            "",
        ]
        if blocked_record is not None:
            lines += [
                "Observed diagnostic (stderr tail):",
                "",
                "```",
                blocked_record.session.stderr_tail.strip()[-600:],
                "```",
                "",
            ]
    for index, case in enumerate(CASES, start=1):
        record = next((item for item in records if item.case == case.name), None)
        if record is None:
            lines += [
                f"## Case {index} — {case.name}",
                "",
                "Not run: the evaluation stopped on the blocked harness state.",
                "",
            ]
        else:
            lines += render_case(index, record)
    lines += render_key_measures(records, exit_code=exit_code, blocked=blocked)
    return "\n".join(lines)


def serialize_raw(raw: list[dict[str, object]]) -> str:
    """One JSON object per raw record, in session order."""

    return "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in raw)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """The script's two options: the output directory and the per-session timeout."""

    parser = argparse.ArgumentParser(
        description="Scripted agent-facing evaluation of the task tool surface."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for report.md and raw-events.jsonl (default: this proposal's "
        "evidence directory).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-session timeout in seconds (default: 600).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the evaluation, write the report and raw events, and exit with the gate."""

    args = parse_args(argv)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    records, raw, blocked = evaluate(args.timeout)
    exit_code, outcome = classify(records, blocked)
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / RAW_EVENTS_NAME).write_text(serialize_raw(raw), encoding="utf-8")
    report = render_report(
        records, blocked=blocked, exit_code=exit_code, outcome=outcome, generated_at=generated_at
    )
    (output_dir / REPORT_NAME).write_text(report, encoding="utf-8")
    for record in records:
        print(
            f"{record.case}: exit={record.session.exit_code} "
            f"provider={record.provider} launched={record.launched_children}"
        )
    print(f"wrote {output_dir / REPORT_NAME} (script exit {exit_code})")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
