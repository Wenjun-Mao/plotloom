"""Strict parsing of the qualified Codex CLI and private session event shapes."""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from .codex_exec_tool_source import (
    CodexExecTelemetryError,
    image_view_event_path,
    parse_imagegen_tool_source,
    parse_view_image_tool_source,
    validate_inline_image_result,
)


@dataclass(frozen=True)
class ImageGenCall:
    call_id: str
    prompt: str
    reference_paths: tuple[str, ...]
    transparent_background: bool
    num_last_images_to_include: int | None
    ordinal: int = 0


@dataclass(frozen=True)
class ImageGenEvent:
    call_id: str
    event_id: str
    status: str
    saved_path: str | None
    transparent_background: bool | None
    ordinal: int = 0


@dataclass(frozen=True)
class ReferenceViewEvidence:
    call_id: str
    event_id: str
    path: str
    call_ordinal: int
    event_ordinal: int
    output_ordinal: int
    content_sha256: str
    content_size_bytes: int


@dataclass
class _PendingReferenceView:
    call_id: str
    path: str
    call_ordinal: int
    event_id: str | None = None
    event_ordinal: int | None = None


@dataclass(frozen=True)
class CodexSessionEvidence:
    session_id: UUID
    image_calls: tuple[ImageGenCall, ...]
    image_events: tuple[ImageGenEvent, ...]
    transcript_sha256: str
    transcript_size_bytes: int
    reference_views: tuple[ReferenceViewEvidence, ...] = ()


def read_cli_session(session_path: Path, expected_session_id: UUID, *, max_event_bytes: int, max_total_bytes: int) -> CodexSessionEvidence:
    """Read only the session named by the CLI thread.started event."""
    if max_event_bytes < 1 or max_total_bytes < max_event_bytes:
        raise ValueError("Codex session byte limits must be positive and ordered")
    if session_path.is_symlink():
        raise CodexExecTelemetryError("Codex session evidence must be a regular file")
    descriptor = os.open(session_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    digest = sha256()
    total = 0
    calls: list[ImageGenCall] = []
    pending: list[ImageGenCall] = []
    events: list[ImageGenEvent] = []
    exec_call_ids: set[str] = set()
    event_ids_by_call: dict[str, str] = {}
    reference_views: list[ReferenceViewEvidence] = []
    pending_view: _PendingReferenceView | None = None
    view_event_ids: set[str] = set()
    first = True
    last_ordinal = -1
    try:
        initial = os.fstat(descriptor)
        if not stat.S_ISREG(initial.st_mode):
            raise CodexExecTelemetryError("Codex session evidence must be a regular file")
        with os.fdopen(os.dup(descriptor), "rb", closefd=True) as stream:
            while True:
                raw = stream.readline(max_event_bytes + 1)
                if not raw:
                    break
                total += len(raw)
                if total > max_total_bytes:
                    raise CodexExecTelemetryError("Codex session evidence exceeds the qualified byte limit")
                if len(raw) > max_event_bytes:
                    raise CodexExecTelemetryError("Codex session event exceeds the qualified byte limit")
                digest.update(raw)
                event_bytes = raw[:-1] if raw.endswith(b"\n") else raw
                try:
                    row = json.loads(event_bytes)
                except (json.JSONDecodeError, UnicodeDecodeError) as error:
                    raise CodexExecTelemetryError("Codex session line is not valid JSON") from error
                if not isinstance(row, dict) or not isinstance(row.get("type"), str):
                    raise CodexExecTelemetryError("Codex session line has no typed event")
                if first:
                    first = False
                    metadata = row.get("payload")
                    if (row["type"] != "session_meta" or not isinstance(metadata, dict)
                            or metadata.get("id") != str(expected_session_id)):
                        raise CodexExecTelemetryError("Codex session file does not belong to the exact CLI session")
                ordinal = row.get("ordinal")
                if type(ordinal) is not int or ordinal <= last_ordinal:
                    raise CodexExecTelemetryError("Codex session event order is not monotonic and complete")
                last_ordinal = ordinal
                payload = row.get("payload")
                if row["type"] == "response_item" and isinstance(payload, dict):
                    if payload.get("type") == "custom_tool_call":
                        tool_name = payload.get("name")
                        if tool_name != "exec":
                            raise CodexExecTelemetryError("Codex session contains an unsupported custom tool")
                        source = payload.get("input")
                        call_id = payload.get("call_id")
                        if not isinstance(source, str) or not isinstance(call_id, str) or not call_id:
                            raise CodexExecTelemetryError("Codex tool call lacks its typed source and ID")
                        try:
                            call_id_size = len(call_id.encode("utf-8", "strict"))
                        except UnicodeEncodeError:
                            call_id_size = 161
                        if call_id_size > 160 or call_id in exec_call_ids:
                            raise CodexExecTelemetryError("Codex exec call IDs must be unique and bounded")
                        exec_call_ids.add(call_id)
                        view_path = parse_view_image_tool_source(source)
                        arguments = parse_imagegen_tool_source(source)
                        if view_path is not None:
                            if pending_view is not None or calls:
                                raise CodexExecTelemetryError("reference views must complete before ImageGen and cannot overlap")
                            pending_view = _PendingReferenceView(call_id, view_path, ordinal)
                        elif arguments is not None:
                            if pending_view is not None:
                                raise CodexExecTelemetryError("ImageGen cannot start before its reference view result completes")
                            call = ImageGenCall(
                                call_id=call_id,
                                prompt=arguments["prompt"],
                                reference_paths=tuple(arguments.get("referenced_image_paths", ())),
                                transparent_background=arguments["transparent_background"],
                                num_last_images_to_include=arguments.get("num_last_images_to_include"),
                                ordinal=ordinal,
                            )
                            if any(prior.call_id == call.call_id for prior in calls):
                                raise CodexExecTelemetryError("Codex ImageGen call IDs are not unique")
                            calls.append(call)
                            pending.append(call)
                    elif payload.get("type") == "custom_tool_call_output":
                        output = payload.get("output")
                        if pending_view is not None:
                            if payload.get("call_id") != pending_view.call_id:
                                raise CodexExecTelemetryError("view_image result does not match its exact exec call")
                            if pending_view.event_id is None or pending_view.event_ordinal is None:
                                raise CodexExecTelemetryError("view_image result lacks its exact ImageView event")
                            if not pending_view.call_ordinal < pending_view.event_ordinal < ordinal:
                                raise CodexExecTelemetryError("view_image evidence is not in exact call, event and result order")
                            image = validate_inline_image_result(output, max_bytes=max_event_bytes)
                            reference_views.append(ReferenceViewEvidence(
                                call_id=pending_view.call_id,
                                event_id=pending_view.event_id,
                                path=pending_view.path,
                                call_ordinal=pending_view.call_ordinal,
                                event_ordinal=pending_view.event_ordinal,
                                output_ordinal=ordinal,
                                content_sha256=image.content_sha256,
                                content_size_bytes=image.size_bytes,
                            ))
                            pending_view = None
                        elif isinstance(output, list) and any(
                            isinstance(block, dict) and block.get("type") == "input_image" for block in output
                        ):
                            raise CodexExecTelemetryError("image content is not bound to a successful view_image call")
                if row["type"] == "event_msg" and isinstance(payload, dict) and isinstance(payload.get("item"), dict):
                    item = payload["item"]
                    if item.get("type") == "ImageView":
                        if (
                            pending_view is None or pending_view.event_id is not None
                            or set(item) != {"id", "path", "type"}
                        ):
                            raise CodexExecTelemetryError("ImageView event has no exact pending view_image call")
                        event_id = item.get("id")
                        try:
                            event_id_size = len(event_id.encode("utf-8", "strict")) if isinstance(event_id, str) else 0
                        except UnicodeEncodeError:
                            event_id_size = 161
                        if not isinstance(event_id, str) or not event_id or event_id_size > 160:
                            raise CodexExecTelemetryError("ImageView event lacks its exact bounded ID")
                        if event_id in view_event_ids:
                            raise CodexExecTelemetryError("ImageView event IDs are not unique")
                        event_path = image_view_event_path(item.get("path"))
                        if event_path != pending_view.path:
                            raise CodexExecTelemetryError("ImageView event path differs from its exact source argument")
                        pending_view.event_id = event_id
                        pending_view.event_ordinal = ordinal
                        view_event_ids.add(event_id)
                    elif item.get("type") == "Extension":
                        if pending_view is not None:
                            raise CodexExecTelemetryError("ImageGen event arrived before the reference view result")
                        if item.get("kind") != "image_gen.generation" or not pending:
                            raise CodexExecTelemetryError("Codex extension event has no matching ImageGen tool call")
                        status = item.get("status")
                        if status not in {"in_progress", "completed", "failed"}:
                            raise CodexExecTelemetryError("Codex ImageGen event status is unsupported")
                        call = pending[0]
                        if ordinal <= call.ordinal:
                            raise CodexExecTelemetryError("Codex ImageGen event precedes its exact tool call")
                        event_id = item.get("id")
                        if not isinstance(event_id, str) or not event_id:
                            raise CodexExecTelemetryError("Codex ImageGen event lacks its exact event ID")
                        try:
                            event_id_size = len(event_id.encode("utf-8", "strict"))
                        except UnicodeEncodeError:
                            event_id_size = 161
                        if event_id_size > 160 or event_id in view_event_ids:
                            raise CodexExecTelemetryError("Codex ImageGen event ID is invalid or collides with a view event")
                        prior_event_id = event_ids_by_call.setdefault(call.call_id, event_id)
                        if prior_event_id != event_id:
                            raise CodexExecTelemetryError("Codex ImageGen progress changed its event identity")
                        transparency = item.get("transparentBackground")
                        if status in {"completed", "failed"} and type(transparency) is not bool:
                            raise CodexExecTelemetryError("terminal Codex ImageGen event lacks declared transparency")
                        if transparency is not None and (
                            type(transparency) is not bool or transparency != call.transparent_background
                        ):
                            raise CodexExecTelemetryError("Codex ImageGen event does not match its declared transparency")
                        if status in {"completed", "failed"}:
                            pending.pop(0)
                            saved_path = item.get("savedPath")
                            if status == "completed" and (not isinstance(saved_path, str) or not saved_path):
                                raise CodexExecTelemetryError("completed ImageGen event lacks its declared output path")
                            events.append(ImageGenEvent(
                                call_id=call.call_id,
                                event_id=event_id,
                                status=status,
                                saved_path=saved_path,
                                transparent_background=transparency,
                                ordinal=ordinal,
                            ))
        final = os.fstat(descriptor)
        current = session_path.stat(follow_symlinks=False)
        if (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns) != (
            final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns
        ) or (current.st_dev, current.st_ino) != (initial.st_dev, initial.st_ino) or total != initial.st_size:
            raise CodexExecTelemetryError("Codex session changed during evidence inspection")
        if first:
            raise CodexExecTelemetryError("Codex session evidence is empty")
        if pending_view is not None:
            raise CodexExecTelemetryError("view_image call lacks its exact ImageView event and inline result")
        if pending:
            raise CodexExecTelemetryError("ImageGen call lacks its exact terminal extension event")
        if len({event.event_id for event in events}) != len(events):
            raise CodexExecTelemetryError("Codex ImageGen event IDs are not unique")
        return CodexSessionEvidence(
            expected_session_id, tuple(calls), tuple(events), digest.hexdigest(), total, tuple(reference_views)
        )
    finally:
        os.close(descriptor)
