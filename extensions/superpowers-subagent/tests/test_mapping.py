"""Prove the session-agent mapping behaviors of ``mapping.py``.

Each test exercises the real mapping file on disk: round-trip persistence in
the canonical whole-file JSON, read-modify-write preservation, serialization
of concurrent writes through the dedicated mapping lock, corrupted-file
rebuild on write and missing-entry read, the fail-closed error when the
mapping directory is unwritable, reads that create nothing, and the default
path under the redirected home.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from superpowers_subagent.locking import exclusive_lock
from superpowers_subagent.mapping import (
    MappingWriteError,
    default_mapping_path,
    read_mapping_entry,
    write_mapping_entry,
)


def canonical_json(entries: dict[str, str]) -> str:
    """Return the mapping file's canonical serialization for ``entries``."""
    return json.dumps(entries, indent=2, sort_keys=True) + "\n"


def test_written_entry_reads_back_as_agent_name(tmp_path: Path) -> None:
    """A written entry reads back as the agent name, and the file holds exactly
    the canonical whole-file JSON, so every reader sees one object whose keys
    are session ids and whose values are agent-name strings."""
    path = tmp_path / "map.json"
    write_mapping_entry("s1", "code-review", mapping_path=path)
    assert read_mapping_entry("s1", mapping_path=path) == "code-review"
    assert path.read_text(encoding="utf-8") == canonical_json({"s1": "code-review"})


def test_second_write_preserves_first_entry(tmp_path: Path) -> None:
    """A second write preserves the first entry: the write is a read-modify-write
    of the whole file, not an overwrite."""
    path = tmp_path / "map.json"
    write_mapping_entry("s1", "code-review", mapping_path=path)
    write_mapping_entry("s2", "read-only", mapping_path=path)
    assert read_mapping_entry("s1", mapping_path=path) == "code-review"
    assert read_mapping_entry("s2", mapping_path=path) == "read-only"


def test_write_blocks_while_mapping_lock_is_held(tmp_path: Path) -> None:
    """A write waits while another holder keeps the ``<mapping_path>.lock`` lock
    file, proving each read-modify-write cycle runs under the dedicated
    process-safe mapping lock."""
    path = tmp_path / "map.json"
    write_mapping_entry("s0", "first", mapping_path=path)
    done = threading.Event()
    failures: list[Exception] = []

    def write() -> None:
        try:
            write_mapping_entry("s1", "second", mapping_path=path)
        except Exception as error:  # collected so the assertion names the failure
            failures.append(error)
        done.set()

    with exclusive_lock(path.with_name(path.name + ".lock")):
        thread = threading.Thread(target=write, daemon=True)
        thread.start()
        assert not done.wait(timeout=0.2), "write did not block on the held mapping lock"
    assert done.wait(timeout=30.0)
    thread.join(timeout=30.0)
    assert failures == []
    assert read_mapping_entry("s0", mapping_path=path) == "first"
    assert read_mapping_entry("s1", mapping_path=path) == "second"


def test_concurrent_writes_keep_both_entries(tmp_path: Path) -> None:
    """Two threads writing concurrently keep both entries, because the blocking
    mapping lock serializes each read-modify-write cycle; a lock-free write
    loses one entry when both threads read before either write lands."""
    path = tmp_path / "map.json"
    start = threading.Barrier(2, timeout=30.0)
    failures: list[Exception] = []

    def write(session_id: str, agent_name: str) -> None:
        try:
            start.wait()
            write_mapping_entry(session_id, agent_name, mapping_path=path)
        except Exception as error:  # collected so the assertion names the failure
            failures.append(error)

    threads = [
        threading.Thread(target=write, args=args, daemon=True)
        for args in (("s1", "code-review"), ("s2", "read-only"))
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30.0)
    assert failures == []
    assert read_mapping_entry("s1", mapping_path=path) == "code-review"
    assert read_mapping_entry("s2", mapping_path=path) == "read-only"


def test_corrupted_file_rebuilds_from_empty_map_on_write(tmp_path: Path) -> None:
    """A corrupted mapping file rebuilds from an empty map plus the new entry:
    the write treats corruption as a missing file instead of a write failure,
    and every pre-existing id reads as unmapped afterwards."""
    path = tmp_path / "map.json"
    path.write_bytes(b'{"s0": "ghost"')
    write_mapping_entry("s1", "code-review", mapping_path=path)
    assert path.read_text(encoding="utf-8") == canonical_json({"s1": "code-review"})
    assert read_mapping_entry("s1", mapping_path=path) == "code-review"
    assert read_mapping_entry("s0", mapping_path=path) is None


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b'{"s1": "code-review"', id="truncated-json"),
        pytest.param(b"\xff\xfe{s1}", id="invalid-utf8"),
        pytest.param(b'["s1"]', id="non-object-top-level"),
        pytest.param(b'{"s1": 5}', id="non-string-value"),
    ],
)
def test_corrupted_file_reads_as_missing_entry(tmp_path: Path, content: bytes) -> None:
    """A file that fails JSON decoding, fails Unicode decoding, carries a
    non-object top level, or carries a non-string value reads as unmapped, so a
    corrupted file never yields a usable agent name."""
    path = tmp_path / "map.json"
    path.write_bytes(content)
    assert read_mapping_entry("s1", mapping_path=path) is None


def test_unwritable_mapping_directory_raises_mapping_write_error(
    tmp_path: Path,
) -> None:
    """When the mapping directory cannot be written, the write raises
    ``MappingWriteError`` and starts no rewrite: the previous file stays whole
    and no lock or temporary file appears beside it."""
    directory = tmp_path / "ro"
    directory.mkdir()
    path = directory / "map.json"
    path.write_text('{"s0": "first"}\n', encoding="utf-8")
    directory.chmod(0o500)
    try:
        with pytest.raises(MappingWriteError):
            write_mapping_entry("s1", "second", mapping_path=path)
    finally:
        directory.chmod(0o700)
    assert path.read_text(encoding="utf-8") == '{"s0": "first"}\n'
    assert [entry.name for entry in directory.iterdir()] == ["map.json"]


def test_missing_file_reads_as_none_without_creating(tmp_path: Path) -> None:
    """A read on a missing file returns None and creates nothing, so lookups
    never leave state behind."""
    path = tmp_path / "map.json"
    assert read_mapping_entry("s1", mapping_path=path) is None
    assert list(tmp_path.iterdir()) == []


def test_default_mapping_path_follows_redirected_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``default_mapping_path`` resolves the home per call, so a redirected HOME
    moves the mapping file to ``<home>/.tau/superpowers-subagent-sessions.json``."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    assert default_mapping_path() == (
        tmp_path / "home" / ".tau" / "superpowers-subagent-sessions.json"
    )
