"""Process-safe file locks for task calls that share a task id and for mapping writes.

``same_id_lock`` keeps two calls that carry the same trimmed ``task_id`` from
both holding the lock, in one process or across the parent processes on the
machine that hosts the session store. That lock coordinates task-tool calls
only: nothing here inspects sessions or processes, and a direct ``tau
--session`` resume by another process is not prevented. ``exclusive_lock``
blocks until it holds an exclusive lock on a caller-provided file; the mapping
write path uses it to serialize read-modify-write cycles.
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


class _HeldLock(AbstractContextManager[None]):
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


def _open_lock_file(path: Path) -> int:
    """Open ``path`` as a lock file, creating it when missing."""
    return os.open(path, _OPEN_FLAGS)


def exclusive_lock(path: Path) -> AbstractContextManager[None]:
    """Acquire an exclusive ``flock`` on ``path``, blocking until it is held.

    The lock file is created when missing. The call blocks until the lock is
    held and releases on context exit; a dead process releases the lock through
    the kernel.
    """
    fd = _open_lock_file(path)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return _HeldLock(fd)


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
    fd = _open_lock_file(directory / name)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return _HeldLock(fd)
