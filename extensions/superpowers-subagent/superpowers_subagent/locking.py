"""Process-safe, non-blocking exclusion for task calls that share a task id.

Two calls that carry the same trimmed ``task_id`` cannot both hold the lock,
in one process or across the parent processes on the machine that hosts the
session store. The lock coordinates task-tool calls only: nothing here
inspects sessions or processes, and a direct ``tau --session`` resume by
another process is not prevented.
"""

from __future__ import annotations

import fcntl
import hashlib
import os
from contextlib import AbstractContextManager
from pathlib import Path
from types import TracebackType

from tau_coding.paths import TauPaths

# O_CLOEXEC keeps the descriptor out of spawned child processes, so a held lock
# dies with this process instead of living on inside a child.
_OPEN_FLAGS = os.O_RDWR | os.O_CREAT | os.O_CLOEXEC


class _HeldSameIdLock(AbstractContextManager[None]):
    """Hold the acquired lock descriptor until the ``with`` block exits."""

    def __init__(self, fd: int) -> None:
        self._fd = fd

    def __enter__(self) -> None:
        return None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        finally:
            os.close(self._fd)


def same_id_lock(
    task_id: str, *, locks_dir: Path | None = None
) -> AbstractContextManager[None] | None:
    """Acquire the same-id lock for ``task_id`` without blocking.

    ``task_id`` is the trimmed effective id. Return a context manager that
    holds the lock until its ``with`` block exits, or ``None`` when another
    call already holds the lock for the same id. The acquire never blocks, so
    async code calls this directly. A dead process releases the lock through
    the kernel.
    """
    directory = locks_dir if locks_dir is not None else TauPaths().sessions_dir / "locks"
    directory.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(task_id.encode("utf-8")).hexdigest() + ".lock"
    fd = os.open(directory / name, _OPEN_FLAGS)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return _HeldSameIdLock(fd)
