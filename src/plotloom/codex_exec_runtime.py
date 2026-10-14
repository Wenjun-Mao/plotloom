"""Small strict readers shared by the Mac Codex Exec supervisor."""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from .codex_exec_contracts import package_manifest_hash
from .codex_exec_files import scan_regular_tree


class CodexExecRuntimeError(ValueError):
    """The installed CLI or a confined execution file is not qualified."""


@dataclass(frozen=True)
class ExecStreamEvidence:
    session_id: UUID
    transcript_sha256: str
    transcript_size_bytes: int
    event_types: tuple[str, ...]
    terminal_event: str


def package_tree_hash(job_root: Path, *, max_total_bytes: int) -> str:
    files = scan_regular_tree(job_root, "package", max_total_bytes=max_total_bytes)
    return package_manifest_hash(files)


def read_exec_events(
    path: Path,
    *,
    max_event_bytes: int,
    max_total_bytes: int,
) -> ExecStreamEvidence:
    """Validate the pinned ``codex exec --json`` terminal event stream."""
    if max_event_bytes < 1 or max_total_bytes < max_event_bytes:
        raise ValueError("Codex event limits must be positive and ordered")
    if path.is_symlink():
        raise CodexExecRuntimeError("Codex CLI event stream must be a regular file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    digest = sha256()
    total = 0
    started = []
    terminal = []
    event_types: list[str] = []
    first = True
    try:
        initial = os.fstat(descriptor)
        if not stat.S_ISREG(initial.st_mode):
            raise CodexExecRuntimeError("Codex CLI event stream must be a regular file")
        with os.fdopen(os.dup(descriptor), "rb", closefd=True) as stream:
            while True:
                raw = stream.readline(max_event_bytes + 1)
                if not raw:
                    break
                total += len(raw)
                if total > max_total_bytes or len(raw) > max_event_bytes:
                    raise CodexExecRuntimeError("Codex CLI event stream exceeds its qualified byte limit")
                digest.update(raw)
                try:
                    record = json.loads(raw[:-1] if raw.endswith(b"\n") else raw)
                except (json.JSONDecodeError, UnicodeDecodeError) as error:
                    raise CodexExecRuntimeError("Codex CLI event stream contains invalid JSON") from error
                if not isinstance(record, dict) or not isinstance(record.get("type"), str):
                    raise CodexExecRuntimeError("Codex CLI event lacks a typed event name")
                event_type = record["type"]
                event_types.append(event_type)
                if terminal:
                    raise CodexExecRuntimeError("Codex CLI event stream contains data after its terminal event")
                if first and event_type != "thread.started":
                    raise CodexExecRuntimeError("Codex CLI stream must begin with thread.started")
                first = False
                if event_type == "thread.started":
                    try:
                        started.append(UUID(record["thread_id"]))
                    except (KeyError, TypeError, ValueError) as error:
                        raise CodexExecRuntimeError("Codex CLI thread.started lacks a UUID session") from error
                elif event_type in {"turn.completed", "turn.failed", "error"}:
                    terminal.append(event_type)
                elif event_type in {"turn.started", "item.started", "item.completed"}:
                    if event_type.startswith("item."):
                        item = record.get("item")
                        if not isinstance(item, dict) or item.get("type") not in {
                            "agent_message", "command_execution", "custom_tool_call", "custom_tool_output",
                        }:
                            raise CodexExecRuntimeError("Codex CLI item event has an unsupported item type")
                else:
                    raise CodexExecRuntimeError("Codex CLI event stream contains an unsupported event")
        final = os.fstat(descriptor)
        current = path.stat(follow_symlinks=False)
        if (
            (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns)
            != (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
            or (current.st_dev, current.st_ino) != (initial.st_dev, initial.st_ino)
            or total != initial.st_size
        ):
            raise CodexExecRuntimeError("Codex CLI event stream changed during inspection")
        if first or len(started) != 1 or len(terminal) != 1:
            raise CodexExecRuntimeError("Codex CLI stream lacks one terminal turn and exact session")
        return ExecStreamEvidence(started[0], digest.hexdigest(), total, tuple(event_types), terminal[0])
    finally:
        os.close(descriptor)


def locate_exact_session(codex_home: Path, session_id: UUID, *, today: date | None = None) -> Path:
    """Find the uniquely named rollout file for one CLI session, never by contents."""
    root = codex_home / "sessions"
    if root.is_symlink() or not root.is_dir():
        raise CodexExecRuntimeError("Codex session root is unavailable or unsafe")
    current = today or date.today()
    matches: list[Path] = []
    for offset in (-1, 0, 1):
        day = current + timedelta(days=offset)
        folder = root / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}"
        if folder.is_symlink() or not folder.is_dir():
            continue
        matches.extend(folder.glob(f"rollout-*-{session_id}.jsonl"))
    safe = [path for path in matches if not path.is_symlink() and path.is_file()]
    if len(safe) != 1:
        raise CodexExecRuntimeError("the exact Codex session file is missing or ambiguous")
    return safe[0]


def read_generated_image(
    path: Path,
    *,
    codex_home: Path,
    session_id: UUID,
    max_bytes: int,
) -> tuple[bytes, str]:
    """Read one regular output beneath the exact session's generated-image directory."""
    expected_root = codex_home / "generated_images" / str(session_id)
    if not path.is_absolute() or path.parent != expected_root or path.name in {"", ".", ".."}:
        raise CodexExecRuntimeError("ImageGen savedPath is outside the exact session output directory")
    for ancestor in (codex_home, codex_home / "generated_images", expected_root):
        if ancestor.is_symlink() or not ancestor.is_dir():
            raise CodexExecRuntimeError("ImageGen output directory is unsafe")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size < 1 or before.st_size > max_bytes:
            raise CodexExecRuntimeError("ImageGen output is not a bounded regular file")
        chunks = []
        remaining = max_bytes + 1
        while remaining:
            block = os.read(descriptor, min(1024 * 1024, remaining))
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        content = b"".join(chunks)
        after = os.fstat(descriptor)
        current = path.stat(follow_symlinks=False)
        if (
            len(content) != before.st_size
            or len(content) > max_bytes
            or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            or (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise CodexExecRuntimeError("ImageGen output changed during inspection")
        return content, sha256(content).hexdigest()
    finally:
        os.close(descriptor)
