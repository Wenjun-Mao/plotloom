from __future__ import annotations

import hashlib
import json
from uuid import UUID

import pytest

from plotloom.codex_exec_telemetry import (
    CodexExecTelemetryError,
    parse_imagegen_tool_source,
    read_cli_session,
)


SESSION_ID = UUID("a3f4e0e9-5595-4fbd-a65d-2392f4625eaf")


def _record(event_type: str, payload: dict, *, ordinal: int) -> bytes:
    return json.dumps(
        {"type": event_type, "payload": payload, "ordinal": ordinal},
        separators=(",", ":"),
    ).encode() + b"\n"


def _image_call(call_id: str = "call-1") -> bytes:
    source = (
        'await tools.image_gen__imagegen({prompt: "a quiet blue room", '
        'images: ["package/reference.png"], transparent_background: false});'
    )
    return _record(
        "response_item",
        {"type": "custom_tool_call", "call_id": call_id, "input": source},
        ordinal=1,
    )


def _extension(status: str, *, event_id: str = "event-1", result: str = "") -> bytes:
    item = {
        "type": "Extension",
        "kind": "image_gen.generation",
        "id": event_id,
        "status": status,
        "transparentBackground": False,
    }
    if status == "completed":
        item["savedPath"] = "/private/generated_images/session/event.png"
        item["result"] = result
    return _record("event_msg", {"item": item}, ordinal=3)


def _session_bytes(*records: bytes) -> bytes:
    return _record("session_meta", {"id": str(SESSION_ID)}, ordinal=0) + b"".join(records)


def test_parse_imagegen_tool_source_reads_only_literal_builtin_call():
    parsed = parse_imagegen_tool_source(
        'await tools.image_gen__imagegen({prompt: "tools.image_gen__imagegen()", '
        'images: ["refs/a.png"], transparent_background: true, num_last_images_to_include: 0});'
    )
    assert parsed == {
        "prompt": "tools.image_gen__imagegen()",
        "images": ["refs/a.png"],
        "transparent_background": True,
        "num_last_images_to_include": 0,
    }


@pytest.mark.parametrize(
    "source",
    [
        'await other.image_gen__imagegen({prompt:"x",transparent_background:false})',
        'tools.image_gen__imagegen({prompt: prompt, transparent_background:false})',
        'tools.image_gen__imagegen({prompt:"x",prompt:"y",transparent_background:false})',
        'tools.image_gen__imagegen({prompt:"x",transparent_background:false,images:[getPath()]})',
        'tools.image_gen__imagegen({prompt:"x",transparent_background:false,external:true})',
    ],
)
def test_parse_imagegen_tool_source_rejects_unbound_or_dynamic_arguments(source: str):
    with pytest.raises(CodexExecTelemetryError):
        parse_imagegen_tool_source(source)


def test_read_cli_session_hashes_each_bounded_record_once_and_correlates_image_event(tmp_path):
    raw = _session_bytes(
        _image_call(),
        _record(
            "event_msg",
            {"item": {"type": "Extension", "kind": "image_gen.generation", "id": "event-1", "status": "in_progress"}},
            ordinal=2,
        ),
        _extension("completed", result="x" * 2_200_000),
    )
    session = tmp_path / "rollout-session.jsonl"
    session.write_bytes(raw)

    evidence = read_cli_session(
        session,
        SESSION_ID,
        max_event_bytes=3_000_000,
        max_total_bytes=4_000_000,
    )

    assert evidence.session_id == SESSION_ID
    assert [call.call_id for call in evidence.image_calls] == ["call-1"]
    assert len(evidence.image_events) == 1
    assert evidence.image_events[0].event_id == "event-1"
    assert evidence.image_events[0].status == "completed"
    assert evidence.transcript_size_bytes == len(raw)
    assert evidence.transcript_sha256 == hashlib.sha256(raw).hexdigest()


def test_read_cli_session_rejects_mismatched_session_and_oversized_record(tmp_path):
    wrong_session = tmp_path / "wrong-session.jsonl"
    wrong_session.write_bytes(_record("session_meta", {"id": "00000000-0000-0000-0000-000000000000"}, ordinal=0))
    with pytest.raises(CodexExecTelemetryError, match="exact CLI session"):
        read_cli_session(wrong_session, SESSION_ID, max_event_bytes=1024, max_total_bytes=4096)

    oversized = tmp_path / "oversized.jsonl"
    oversized.write_bytes(_session_bytes(_record("event_msg", {"payload": "x" * 2048}, ordinal=1)))
    with pytest.raises(CodexExecTelemetryError, match="event exceeds"):
        read_cli_session(oversized, SESSION_ID, max_event_bytes=1024, max_total_bytes=4096)


def test_read_cli_session_rejects_event_identity_or_transparency_mismatch(tmp_path):
    progress = _record(
        "event_msg",
        {"item": {"type": "Extension", "kind": "image_gen.generation", "id": "event-1", "status": "in_progress"}},
        ordinal=2,
    )
    raw = _session_bytes(_image_call(), progress, _extension("completed", event_id="different"))
    session = tmp_path / "event-mismatch.jsonl"
    session.write_bytes(raw)
    with pytest.raises(CodexExecTelemetryError, match="progress changed its event identity"):
        read_cli_session(session, SESSION_ID, max_event_bytes=4096, max_total_bytes=8192)

    item = json.loads(_extension("completed"))
    item["payload"]["item"]["transparentBackground"] = True
    session.write_bytes(_session_bytes(_image_call(), json.dumps(item).encode() + b"\n"))
    with pytest.raises(CodexExecTelemetryError, match="transparency"):
        read_cli_session(session, SESSION_ID, max_event_bytes=4096, max_total_bytes=8192)
