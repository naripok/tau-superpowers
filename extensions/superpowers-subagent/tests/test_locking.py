"""Prove the same-task_id lock behaviors of ``locking.py``.

Each test exercises real ``flock`` semantics: same-process exclusion, release
through the ``with`` exit, distinct-id independence, cross-process exclusion
with a real subprocess, portable file naming for arbitrary task id text, and
the default locks directory under the session store.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from superpowers_subagent.locking import same_id_lock

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

# The holder subprocess imports the real locking module, acquires the lock for
# the id the parent passes, signals through the ready file, and exits once the
# parent removes that file.
_HOLDER_SCRIPT = """\
import sys
import time
from pathlib import Path

from superpowers_subagent.locking import same_id_lock

locks_dir = Path(sys.argv[1])
task_id = sys.argv[2]
ready_path = Path(sys.argv[3])

lock = same_id_lock(task_id, locks_dir=locks_dir)
if lock is None:
    sys.exit(3)
with lock:
    ready_path.touch()
    deadline = time.monotonic() + 60
    while ready_path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
"""


def test_same_id_second_call_returns_none_while_first_holds(tmp_path: Path) -> None:
    """A second call with the same id returns None while the first with block
    still holds the lock, so two same-id calls in one process cannot both run."""
    locks_dir = tmp_path / "locks"
    first = same_id_lock("task-a", locks_dir=locks_dir)
    assert first is not None
    with first:
        second = same_id_lock("task-a", locks_dir=locks_dir)
        assert second is None


def test_same_id_acquires_again_after_release(tmp_path: Path) -> None:
    """A call with the same id acquires again after the with block exits,
    proving the exit unlocks and closes the held file descriptor."""
    locks_dir = tmp_path / "locks"
    first = same_id_lock("task-a", locks_dir=locks_dir)
    assert first is not None
    with first:
        pass
    second = same_id_lock("task-a", locks_dir=locks_dir)
    assert second is not None
    with second:
        pass


def test_distinct_ids_hold_distinct_locks(tmp_path: Path) -> None:
    """Two calls with distinct ids both acquire at once, so exclusion applies
    only to calls that share one id."""
    locks_dir = tmp_path / "locks"
    first = same_id_lock("task-a", locks_dir=locks_dir)
    second = same_id_lock("task-b", locks_dir=locks_dir)
    assert first is not None
    assert second is not None
    with first, second:
        pass


def test_lock_excludes_across_processes(tmp_path: Path) -> None:
    """A subprocess that holds the lock makes the parent's acquire return None,
    and the parent acquires once the subprocess exits, proving the exclusion is
    process-safe and a dead process releases the lock through the kernel."""
    locks_dir = tmp_path / "locks"
    ready = tmp_path / "ready"
    pythonpath = os.pathsep.join([str(PACKAGE_ROOT), os.environ.get("PYTHONPATH", "")])
    holder = subprocess.Popen(
        [sys.executable, "-c", _HOLDER_SCRIPT, str(locks_dir), "shared id", str(ready)],
        env={**os.environ, "PYTHONPATH": pythonpath},
    )
    try:
        deadline = time.monotonic() + 30.0
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists(), "holder subprocess never acquired the lock"
        assert same_id_lock("shared id", locks_dir=locks_dir) is None
        ready.unlink()
        assert holder.wait(timeout=30.0) == 0
    finally:
        holder.kill()
        holder.wait(timeout=30.0)
    acquired = same_id_lock("shared id", locks_dir=locks_dir)
    assert acquired is not None
    with acquired:
        pass


def test_arbitrary_text_maps_to_one_hex_name(tmp_path: Path) -> None:
    """A task id with '/', spaces, and unicode maps to the exact sha256 hex file
    name and acquires, so arbitrary user text creates one portable lock file."""
    locks_dir = tmp_path / "locks"
    task_id = "repo/build 42 — ✓ünïcode"
    lock = same_id_lock(task_id, locks_dir=locks_dir)
    assert lock is not None
    expected = hashlib.sha256(task_id.encode("utf-8")).hexdigest() + ".lock"
    assert [path.name for path in locks_dir.iterdir()] == [expected]
    with lock:
        pass


def test_default_locks_dir_follows_session_store(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without locks_dir the lock lands in the session store's locks directory,
    computed per acquisition, so redirection through HOME isolates dispatchers."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    lock = same_id_lock("task-a")
    assert lock is not None
    expected = hashlib.sha256(b"task-a").hexdigest() + ".lock"
    assert (tmp_path / "home" / ".tau" / "sessions" / "locks" / expected).exists()
    with lock:
        pass
