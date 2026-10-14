"""Small strict readers shared by the Mac Codex Exec supervisor."""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import UUID

from .codex_exec_contracts import package_manifest_hash
from .codex_exec_files import read_confined_regular_file, scan_regular_tree


class CodexExecRuntimeError(ValueError):
    """The installed CLI or a confined execution file is not qualified."""


@dataclass(frozen=True)
class ExecDiagnostic:
    item_id: str
    message_sha256: str
    message_size_bytes: int


@dataclass(frozen=True)
class ExecFileChangeEntry:
    absolute_path: str
    kind: Literal["add", "update", "delete"]


@dataclass(frozen=True)
class ExecFileChange:
    item_id: str
    changes: tuple[ExecFileChangeEntry, ...]


@dataclass(frozen=True)
class ExecStreamEvidence:
    session_id: UUID
    transcript_sha256: str
    transcript_size_bytes: int
    event_types: tuple[str, ...]
    terminal_event: str
    diagnostics: tuple[ExecDiagnostic, ...]
    file_changes: tuple[ExecFileChange, ...]


MAX_DIAGNOSTICS = 128
MAX_DIAGNOSTIC_MESSAGE_BYTES = 16_384
MAX_FILE_CHANGE_ITEMS = 128
MAX_FILE_CHANGES_PER_ITEM = 256
MAX_EVENT_ITEM_ID_BYTES = 128
MAX_EVENT_RECORDS = 100_000


def package_tree_hash(job_root: Path, *, max_total_bytes: int) -> str:
    files = scan_regular_tree(job_root, "package", max_total_bytes=max_total_bytes)
    return package_manifest_hash(files)


def frozen_package_snapshot(job_root: Path, *, max_total_bytes: int) -> tuple[str, bytes]:
    """Return one package hash and its exact scanned request.json bytes."""
    files = scan_regular_tree(job_root, "package", max_total_bytes=max_total_bytes)
    request_file = next((item for item in files if item.relative_path == "request.json"), None)
    if request_file is None:
        raise CodexExecRuntimeError("frozen package has no request.json")
    request_bytes = read_confined_regular_file(job_root, "package/request.json", max_bytes=max_total_bytes)
    if (len(request_bytes) != request_file.size_bytes
            or sha256(request_bytes).hexdigest() != request_file.sha256):
        raise CodexExecRuntimeError("frozen package request changed after its tree scan")
    return package_manifest_hash(files), request_bytes


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
    diagnostics: list[ExecDiagnostic] = []
    diagnostic_ids: set[str] = set()
    pending_file_changes: dict[str, tuple[ExecFileChangeEntry, ...]] = {}
    file_changes: list[ExecFileChange] = []
    file_change_ids: set[str] = set()
    turn_started = False
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
                if len(event_types) >= MAX_EVENT_RECORDS:
                    raise CodexExecRuntimeError("Codex CLI event count exceeds its qualified limit")
                event_types.append(event_type)
                if terminal:
                    raise CodexExecRuntimeError("Codex CLI event stream contains data after its terminal event")
                if first and event_type != "thread.started":
                    raise CodexExecRuntimeError("Codex CLI stream must begin with thread.started")
                first = False
                if event_type == "thread.started":
                    if len(started) != 0:
                        raise CodexExecRuntimeError("Codex CLI stream contains duplicate session starts")
                    try:
                        started.append(UUID(record["thread_id"]))
                    except (KeyError, TypeError, ValueError) as error:
                        raise CodexExecRuntimeError("Codex CLI thread.started lacks a UUID session") from error
                elif event_type == "turn.started":
                    if turn_started:
                        raise CodexExecRuntimeError("Codex CLI stream contains duplicate turn starts")
                    turn_started = True
                elif event_type in {"turn.completed", "turn.failed", "error"}:
                    terminal.append(event_type)
                elif event_type in {"turn.started", "item.started", "item.completed"}:
                    if event_type.startswith("item."):
                        item = record.get("item")
                        if not isinstance(item, dict) or not isinstance(item.get("type"), str):
                            raise CodexExecRuntimeError("Codex CLI item event has an unsupported item type")
                        item_type = item["type"]
                        if item_type == "error":
                            diagnostic = _read_diagnostic_item(item, event_type)
                            if diagnostic.item_id in diagnostic_ids or diagnostic.item_id in file_change_ids:
                                raise CodexExecRuntimeError("Codex diagnostic item ID is not unique")
                            if len(diagnostics) >= MAX_DIAGNOSTICS:
                                raise CodexExecRuntimeError("Codex CLI diagnostic count exceeds its limit")
                            diagnostic_ids.add(diagnostic.item_id)
                            diagnostics.append(diagnostic)
                        elif item_type == "file_change":
                            if not turn_started:
                                raise CodexExecRuntimeError("Codex file-change item appeared before turn.started")
                            change = _read_file_change_item(item, event_type)
                            if event_type == "item.started":
                                if change.item_id in file_change_ids or change.item_id in diagnostic_ids:
                                    raise CodexExecRuntimeError("Codex file-change item ID is not unique")
                                if len(pending_file_changes) + len(file_changes) >= MAX_FILE_CHANGE_ITEMS:
                                    raise CodexExecRuntimeError("Codex file-change item count exceeds its limit")
                                file_change_ids.add(change.item_id)
                                pending_file_changes[change.item_id] = change.changes
                            else:
                                pending = pending_file_changes.pop(change.item_id, None)
                                if pending is None or pending != change.changes:
                                    raise CodexExecRuntimeError(
                                        "Codex file-change completion does not match its started item"
                                    )
                                file_changes.append(change)
                        elif item_type not in {
                            "agent_message", "command_execution", "custom_tool_call", "custom_tool_output",
                        }:
                            raise CodexExecRuntimeError("Codex CLI item event has an unsupported item type")
                        elif not turn_started:
                            raise CodexExecRuntimeError("Codex CLI turn item appeared before turn.started")
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
        if terminal[0] in {"turn.completed", "turn.failed"} and not turn_started:
            raise CodexExecRuntimeError("Codex CLI turn terminal lacks turn.started")
        if pending_file_changes:
            raise CodexExecRuntimeError("Codex CLI stream ends with an incomplete file-change item")
        return ExecStreamEvidence(
            started[0], digest.hexdigest(), total, tuple(event_types), terminal[0],
            tuple(diagnostics), tuple(file_changes),
        )
    finally:
        os.close(descriptor)


def _read_diagnostic_item(item: dict, event_type: str) -> ExecDiagnostic:
    if event_type != "item.completed" or set(item) != {"id", "type", "message"}:
        raise CodexExecRuntimeError("Codex CLI diagnostic item has an unsupported shape")
    item_id = item.get("id")
    message = item.get("message")
    if not isinstance(item_id, str) or not item_id or _utf8_size(item_id) > MAX_EVENT_ITEM_ID_BYTES:
        raise CodexExecRuntimeError("Codex CLI diagnostic item lacks bounded identity and message")
    if not isinstance(message, str) or not message:
        raise CodexExecRuntimeError("Codex CLI diagnostic item lacks bounded identity and message")
    try:
        message_bytes = message.encode("utf-8", "strict")
    except UnicodeEncodeError as error:
        raise CodexExecRuntimeError("Codex CLI diagnostic message is not valid Unicode") from error
    if len(message_bytes) > MAX_DIAGNOSTIC_MESSAGE_BYTES:
        raise CodexExecRuntimeError("Codex CLI diagnostic message exceeds its byte limit")
    return ExecDiagnostic(item_id, sha256(message_bytes).hexdigest(), len(message_bytes))


def _read_file_change_item(item: dict, event_type: str) -> ExecFileChange:
    if (event_type not in {"item.started", "item.completed"} or item.get("type") != "file_change"
            or set(item) != {"id", "type", "status", "changes"}):
        raise CodexExecRuntimeError("Codex file-change item has an unsupported shape")
    expected_status = "in_progress" if event_type == "item.started" else "completed"
    item_id = item.get("id")
    raw_changes = item.get("changes")
    if (
        not isinstance(item_id, str) or not item_id or _utf8_size(item_id) > MAX_EVENT_ITEM_ID_BYTES
        or item.get("status") != expected_status
        or not isinstance(raw_changes, list) or not raw_changes
        or len(raw_changes) > MAX_FILE_CHANGES_PER_ITEM
    ):
        raise CodexExecRuntimeError("Codex file-change item lacks bounded identity, status or changes")
    changes: list[ExecFileChangeEntry] = []
    seen_paths: set[str] = set()
    for raw in raw_changes:
        if not isinstance(raw, dict) or set(raw) != {"path", "kind"}:
            raise CodexExecRuntimeError("Codex file-change entry has an unsupported shape")
        path, kind = raw.get("path"), raw.get("kind")
        if (
            not isinstance(path, str) or not path or _utf8_size(path) > 4096
            or not Path(path).is_absolute() or "\\" in path or "\x00" in path
            or Path(path).as_posix() != path or ".." in Path(path).parts
            or not isinstance(kind, str) or kind not in {"add", "update", "delete"}
            or path in seen_paths
        ):
            raise CodexExecRuntimeError("Codex file-change entry is not canonical bounded path data")
        seen_paths.add(path)
        changes.append(ExecFileChangeEntry(path, kind))
    return ExecFileChange(item_id, tuple(changes))


def _utf8_size(value: str) -> int:
    try:
        return len(value.encode("utf-8", "strict"))
    except UnicodeEncodeError as error:
        raise CodexExecRuntimeError("Codex CLI event text is not valid Unicode") from error


def assert_file_changes_confined(evidence: ExecStreamEvidence, delivery_root: Path) -> None:
    """Reject any observed built-in file change outside the assigned delivery."""
    try:
        root = delivery_root.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise CodexExecRuntimeError("Codex delivery root is unavailable during file-change review") from error
    if not root.is_dir():
        raise CodexExecRuntimeError("Codex delivery root is not a directory")
    for item in evidence.file_changes:
        for change in item.changes:
            candidate = Path(change.absolute_path)
            if (not candidate.is_absolute() or candidate.as_posix() != change.absolute_path
                    or ".." in candidate.parts or not candidate.is_relative_to(root)):
                raise CodexExecRuntimeError("Codex file-change event is not a canonical delivery path")
            try:
                resolved = candidate.resolve(strict=False)
            except (OSError, RuntimeError, ValueError) as error:
                raise CodexExecRuntimeError("Codex file-change path cannot be safely resolved") from error
            if resolved == root or not resolved.is_relative_to(root):
                raise CodexExecRuntimeError("Codex file-change event escaped the assigned delivery")


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
