#!/usr/bin/env python3
"""Deterministic stand-in for child `tau --mode json` integration tests."""

from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import NoReturn


def record(event: str, **values: object) -> None:
    path_value = os.environ.get("FAKE_TAU_LOG")
    if not path_value:
        return
    payload = json.dumps({"event": event, **values}, separators=(",", ":")) + "\n"
    descriptor = os.open(path_value, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, payload.encode())
    finally:
        os.close(descriptor)


def emit(payload: object) -> None:
    print(json.dumps(payload, separators=(",", ":")), flush=True)


def terminate(signum: int, _frame: object) -> NoReturn:
    record("signal", signal=signum)
    raise SystemExit(128 + signum)


def main() -> int:
    arguments = sys.argv[1:]
    task = arguments[-1]
    prompt_path = Path(arguments[arguments.index("--append-system-prompt") + 1])
    policy_path = Path(arguments[arguments.index("-e") + 1]) if "-e" in arguments else None
    record(
        "start",
        task=task,
        argv=arguments,
        cwd=os.getcwd(),
        guard=os.environ.get("TAU_SUPERPOWERS_SUBAGENT"),
        promptPath=str(prompt_path),
        prompt=prompt_path.read_text(encoding="utf-8"),
        policyPath=str(policy_path) if policy_path else None,
        policy=policy_path.read_text(encoding="utf-8") if policy_path else None,
    )

    if task == "no-message":
        emit({"type": "agent_end", "messages": []})
        return 0

    if task == "unknown-provider":
        print("\x1b[31mUnKnOwN PrOvIdEr: made-up-provider\x1b[0m", file=sys.stderr, flush=True)
        return 2

    emit(
        {
            "type": "message_end",
            "message": {
                "role": "toolResult",
                "toolCallId": "fixture-read",
                "toolName": "read",
                "content": [{"type": "text", "text": f"tool output for {task}"}],
            },
        }
    )

    if task == "sleep":
        emit(
            {
                "type": "message_end",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "partial before wait"}],
                },
            }
        )
        signal.signal(signal.SIGTERM, terminate)
        record("waiting", task=task)
        while True:
            time.sleep(0.05)

    print("malformed fixture line", flush=True)
    emit({"type": "message_end", "message": {"role": "invalid"}})
    label = task.splitlines()[0]
    status = "BLOCKED" if task == "fail" else "DONE"
    emit(
        {
            "type": "message_end",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": f"full output for {label}\n"},
                    {
                        "type": "text",
                        "text": f"## Summary\nsummary for {label}\n**Status: {status}**",
                    },
                ],
                "provider": "fixture-provider",
                "model": "fixture-model",
                "stopReason": "stop",
                "usage": {
                    "input": 2,
                    "output": 3,
                    "cacheRead": 0,
                    "cacheWrite": 0,
                    "totalTokens": 5,
                    "cost": {"total": 0.0},
                },
            },
        }
    )
    print(f"stderr for {task}", file=sys.stderr, flush=True)
    return 7 if task == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
