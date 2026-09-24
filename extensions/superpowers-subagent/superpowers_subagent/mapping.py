"""Durable session-id to agent-name mapping for fresh ``task`` dispatches.

The mapping lives at ``~/.tau/superpowers-subagent-sessions.json``, a sibling
of ``superpowers-subagent.toml``. Each write is a read-modify-write of the
whole file under a dedicated mapping lock and lands through atomic
write-and-rename, so concurrent dispatches cannot lose an entry and a
concurrent reader sees the file whole. A corrupted or unreadable file counts
as a missing entry on read and rebuilds from an empty map on write.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from tau_coding.paths import TauPaths

from .locking import exclusive_lock

MAPPING_FILENAME = "superpowers-subagent-sessions.json"


class MappingWriteError(OSError):
    """Raised when a mapping entry cannot be persisted to the mapping file."""


def default_mapping_path() -> Path:
    """Return the mapping file path under the user's Tau home.

    ``Path.home()`` resolves per call, so tests can redirect ``HOME``.
    """
    return TauPaths().home / MAPPING_FILENAME


def _load_entries(path: Path) -> dict[str, str] | None:
    """Return the parsed mapping, or ``None`` when the file is missing,
    unreadable, or corrupted.

    A corrupted file is one that fails JSON decoding, fails Unicode decoding,
    carries a non-object top level, or carries a non-string value.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(parsed, dict) or not all(isinstance(value, str) for value in parsed.values()):
        return None
    return parsed


def _lock_path(path: Path) -> Path:
    """Return the mapping lock path: the mapping file name plus ``.lock``."""
    return path.with_name(path.name + ".lock")


def _atomic_write(path: Path, entries: dict[str, str]) -> None:
    """Write the whole mapping to a sibling temporary file and rename it over
    ``path``, so a concurrent reader sees the file whole."""
    payload = json.dumps(entries, indent=2, sort_keys=True) + "\n"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def write_mapping_entry(
    session_id: str, agent_name: str, *, mapping_path: Path | None = None
) -> None:
    """Record the agent name for a session id in the mapping file.

    The write is a read-modify-write of the whole file under the mapping lock
    and lands through atomic write-and-rename. A corrupted or unreadable
    existing file rebuilds from an empty map. Raise ``MappingWriteError`` when
    the entry cannot be persisted: the lock file cannot be created or opened,
    the directory cannot be created or written, or the rename fails.
    """
    path = mapping_path if mapping_path is not None else default_mapping_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with exclusive_lock(_lock_path(path)):
            entries = _load_entries(path) or {}
            entries[session_id] = agent_name
            _atomic_write(path, entries)
    except OSError as error:
        raise MappingWriteError(
            f"cannot persist mapping entry for session {session_id!r} at {path}"
        ) from error


def read_mapping_entry(session_id: str, *, mapping_path: Path | None = None) -> str | None:
    """Return the agent name mapped to a session id, or ``None``.

    A missing, unreadable, or corrupted file counts as unmapped, and a read
    creates nothing.
    """
    path = mapping_path if mapping_path is not None else default_mapping_path()
    entries = _load_entries(path)
    if entries is None:
        return None
    return entries.get(session_id)
