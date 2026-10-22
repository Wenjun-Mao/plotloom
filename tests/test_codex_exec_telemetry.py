from __future__ import annotations

import hashlib
import json
import struct
import zlib
from base64 import b64encode
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from PIL import Image, ImageFile

from plotloom.codex_exec_telemetry import (
    CodexExecTelemetryError,
    parse_imagegen_tool_source,
    parse_view_image_tool_source,
    read_cli_session,
)
from plotloom.codex_exec_tool_source import validate_inline_image_result

SESSION_ID = UUID("a3f4e0e9-5595-4fbd-a65d-2392f4625eaf")


def _record(event_type: str, payload: dict, *, ordinal: int) -> bytes:
    return json.dumps(
        {"type": event_type, "payload": payload, "ordinal": ordinal},
        separators=(",", ":"),
    ).encode() + b"\n"


def _image_call(call_id: str = "call-1", references: tuple[str, ...] = (), *, ordinal: int = 1) -> bytes:
    references_json = json.dumps(list(references))
    source = (
        'await tools.image_gen__imagegen({prompt: "a quiet blue room", '
        f'referenced_image_paths: {references_json}, transparent_background: false}});'
    )
    return _record(
        "response_item",
        {"type": "custom_tool_call", "name": "exec", "call_id": call_id, "input": source},
        ordinal=ordinal,
    )


def _view_call(path: str, call_id: str = "view-call-1", *, ordinal: int = 1) -> bytes:
    source = f'image((await tools.view_image({{path: {json.dumps(path)}}})).image_url);'
    return _record(
        "response_item",
        {"type": "custom_tool_call", "name": "exec", "call_id": call_id, "input": source},
        ordinal=ordinal,
    )


def _image_view_event(path: str, *, ordinal: int = 2, event_id: str = "view-event-1") -> bytes:
    return _record(
        "event_msg",
        {"item": {"type": "ImageView", "id": event_id, "path": path}},
        ordinal=ordinal,
    )


def _inline_image_output(call_id: str, *, ordinal: int = 3, text: str | None = None) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (3, 2), (20, 30, 40)).save(buffer, format="PNG")
    output = [{"type": "input_text", "text": "viewed image content"}]
    if text is not None:
        output[0]["text"] = text
    output.append({"type": "input_image", "image_url": "data:image/png;base64," + b64encode(buffer.getvalue()).decode()})
    return _record(
        "response_item",
        {"type": "custom_tool_call_output", "call_id": call_id, "output": output},
        ordinal=ordinal,
    )


def _png_header(width: int, height: int) -> bytes:
    def chunk(kind: bytes, value: bytes) -> bytes:
        payload = kind + value
        return len(value).to_bytes(4, "big") + payload + zlib.crc32(payload).to_bytes(4, "big")

    dimensions = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", dimensions)
        + chunk(b"IDAT", zlib.compress(b"\x00"))
        + chunk(b"IEND", b"")
    )


def _jpeg_without_scan_data() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (3, 2), (20, 30, 40)).save(buffer, format="JPEG")
    jpeg = buffer.getvalue()
    scan_marker = jpeg.index(b"\xff\xda")
    scan_header_length = int.from_bytes(jpeg[scan_marker + 2:scan_marker + 4], "big")
    return jpeg[:scan_marker + 2 + scan_header_length]


def _extension(status: str, *, event_id: str = "event-1", result: str = "", ordinal: int = 3) -> bytes:
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
    return _record("event_msg", {"item": item}, ordinal=ordinal)


def _session_bytes(*records: bytes) -> bytes:
    return _record("session_meta", {"id": str(SESSION_ID)}, ordinal=0) + b"".join(records)


def test_parse_imagegen_tool_source_reads_only_literal_builtin_call():
    parsed = parse_imagegen_tool_source(
        'await tools.image_gen__imagegen({prompt: "tools.image_gen__imagegen()", '
        'referenced_image_paths: ["refs/a.png"], transparent_background: true, num_last_images_to_include: 0});'
    )
    assert parsed == {
        "prompt": "tools.image_gen__imagegen()",
        "referenced_image_paths": ["refs/a.png"],
        "transparent_background": True,
        "num_last_images_to_include": 0,
    }


def test_parse_imagegen_tool_source_requires_one_direct_awaited_statement():
    with pytest.raises(CodexExecTelemetryError, match="direct top-level awaited"):
        parse_imagegen_tool_source(
            'if (false) { await tools.image_gen__imagegen({prompt: "dead", '
            'transparent_background: false}); }'
        )

    with pytest.raises(CodexExecTelemetryError, match="direct top-level awaited"):
        parse_imagegen_tool_source(
            'if (false) { await tools.image_gen__imagegen({prompt: "dead", '
            'transparent_background: false}); } '
            'await tools.exec_command({cmd: `run ${await tools.image_gen__imagegen({'
            'prompt: "live", transparent_background: false})}`});'
        )

    with pytest.raises(CodexExecTelemetryError, match="cannot share an exec snippet"):
        parse_imagegen_tool_source(
            'await tools.image_gen__imagegen({prompt: "live", transparent_background: false}); '
            'await tools.exec_command({cmd: "another statement"});'
        )


def test_parse_imagegen_tool_source_ignores_ordinary_javascript_syntax():
    source = "await tools.exec_command({cmd: `printf '%s\\n' > ${outputPath}`});"
    assert parse_imagegen_tool_source(source) is None


def test_parse_view_image_source_requires_exact_image_emission_and_path():
    path = "/tmp/frozen reference.png"
    assert parse_view_image_tool_source(
        f'image((await tools.view_image({{path: {json.dumps(path)}}})).image_url);'
    ) == path
    assert parse_view_image_tool_source("await tools.exec_command({cmd: \"pwd\"});") is None
    for source in (
        f'const result = await tools.view_image({{path: {json.dumps(path)}}}); image(result.image_url);',
        'image((await tools.view_image({path: "relative.png"})).image_url);',
        f'image((await tools.view_image({{path: {json.dumps(path)}}})).image_url); text("extra");',
        f'image((await tools.view_image({{path: {json.dumps(path)}}})).image_url); image((await tools.view_image({{path: {json.dumps(path)}}})).image_url);',
        f'image((await tools.view_image.extra({{path: {json.dumps(path)}}})).image_url);',
    ):
        with pytest.raises(CodexExecTelemetryError):
            parse_view_image_tool_source(source)


def test_inline_reference_image_enforces_the_shared_raster_pixel_limit():
    image_url = "data:image/png;base64," + b64encode(_png_header(5000, 5000)).decode()
    with pytest.raises(CodexExecTelemetryError, match="pixel limit"):
        validate_inline_image_result([{"type": "input_image", "image_url": image_url}], max_bytes=4096)


@pytest.mark.parametrize(
    "mime_type",
    ["image/png", "image/jpeg"],
)
def test_inline_reference_image_rejects_header_with_incomplete_raster(mime_type):
    image_bytes = _png_header(3, 2) if mime_type == "image/png" else _jpeg_without_scan_data()
    image_url = f"data:{mime_type};base64," + b64encode(image_bytes).decode()
    with pytest.raises(CodexExecTelemetryError, match="complete supported raster image"):
        validate_inline_image_result([{"type": "input_image", "image_url": image_url}], max_bytes=4096)


def test_inline_reference_image_refuses_pillow_truncated_image_mode(monkeypatch):
    image_url = "data:image/png;base64," + b64encode(_png_header(3, 2)).decode()
    monkeypatch.setattr(ImageFile, "LOAD_TRUNCATED_IMAGES", True)
    with pytest.raises(CodexExecTelemetryError, match="configured to load truncated"):
        validate_inline_image_result([{"type": "input_image", "image_url": image_url}], max_bytes=4096)


@pytest.mark.parametrize(
    "source",
    [
        'await other.image_gen__imagegen({prompt:"x",transparent_background:false})',
        'tools.image_gen__imagegen({prompt: prompt, transparent_background:false})',
        'tools.image_gen__imagegen({prompt:"x",prompt:"y",transparent_background:false})',
        'tools.image_gen__imagegen({prompt:"x",transparent_background:false,images:[getPath()]})',
        'tools.image_gen__imagegen({prompt:"x",transparent_background:false,images:["refs/a.png"]})',
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


def test_read_cli_session_binds_ordered_reference_view_to_inline_image_and_imagegen(tmp_path):
    reference_path = str(tmp_path / "package" / "references" / "reference one.png")
    raw = _session_bytes(
        _view_call(reference_path, ordinal=1),
        _image_view_event(Path(reference_path).as_uri(), ordinal=2),
        _inline_image_output("view-call-1", ordinal=3),
        _image_call(references=(reference_path,), ordinal=4),
        _extension("in_progress", event_id="image-event", ordinal=5),
        _extension("completed", event_id="image-event", ordinal=6),
    )
    session = tmp_path / "view-session.jsonl"
    session.write_bytes(raw)

    evidence = read_cli_session(
        session, SESSION_ID, max_event_bytes=4096, max_total_bytes=16_384,
    )

    assert evidence.image_calls[0].reference_paths == (reference_path,)
    assert evidence.image_calls[0].ordinal == 4
    assert len(evidence.reference_views) == 1
    view = evidence.reference_views[0]
    assert (view.path, view.call_ordinal, view.event_ordinal, view.output_ordinal) == (
        reference_path, 1, 2, 3,
    )
    assert len(view.content_sha256) == 64 and view.content_size_bytes > 0


def test_read_cli_session_rejects_missing_mismatched_or_late_reference_view_evidence(tmp_path):
    reference_path = str(tmp_path / "package" / "references" / "reference.png")
    cases = (
        (
            _view_call(reference_path, ordinal=1),
            _inline_image_output("view-call-1", ordinal=3),
        ),
        (
            _view_call(reference_path, ordinal=1),
            _image_view_event(Path(reference_path + ".other").as_uri(), ordinal=2),
            _inline_image_output("view-call-1", ordinal=3),
        ),
        (
            _view_call(reference_path, ordinal=1),
            _image_view_event(Path(reference_path).as_uri(), ordinal=2),
            _inline_image_output("another-call", ordinal=3),
        ),
        (
            _view_call(reference_path, ordinal=1),
            _image_view_event(Path(reference_path).as_uri(), ordinal=2),
            _inline_image_output("view-call-1", ordinal=3),
            _view_call(reference_path, ordinal=4),
        ),
    )
    for index, records in enumerate(cases):
        path = tmp_path / f"invalid-view-{index}.jsonl"
        path.write_bytes(_session_bytes(*records))
        with pytest.raises(CodexExecTelemetryError):
            read_cli_session(path, SESSION_ID, max_event_bytes=4096, max_total_bytes=16_384)

    late = tmp_path / "late-view.jsonl"
    late.write_bytes(_session_bytes(
        _image_call(references=(reference_path,), ordinal=1),
        _extension("completed", ordinal=2),
        _view_call(reference_path, ordinal=3),
    ))
    with pytest.raises(CodexExecTelemetryError, match="before ImageGen"):
        read_cli_session(late, SESSION_ID, max_event_bytes=4096, max_total_bytes=16_384)


def test_read_cli_session_skips_non_image_exec_input_with_normal_javascript(tmp_path):
    raw = _session_bytes(
        _record(
            "response_item",
            {
                "type": "custom_tool_call",
                "name": "exec",
                "call_id": "call-text-1",
                "input": "await tools.exec_command({cmd: `printf '%s\\n' > ${outputPath}`});",
            },
            ordinal=1,
        ),
    )
    session_path = tmp_path / "text-session.jsonl"
    session_path.write_bytes(raw)

    evidence = read_cli_session(
        session_path,
        SESSION_ID,
        max_event_bytes=4096,
        max_total_bytes=8192,
    )

    assert evidence.image_calls == ()
    assert evidence.image_events == ()


def test_read_cli_session_rejects_unrecognized_custom_tool_name(tmp_path):
    raw = _session_bytes(
        _record(
            "response_item",
            {"type": "custom_tool_call", "name": "other", "call_id": "call-1", "input": "{}"},
            ordinal=1,
        ),
    )
    session_path = tmp_path / "unexpected-tool.jsonl"
    session_path.write_bytes(raw)

    with pytest.raises(CodexExecTelemetryError, match="unsupported custom tool"):
        read_cli_session(session_path, SESSION_ID, max_event_bytes=4096, max_total_bytes=8192)


def test_read_cli_session_rejects_imagegen_hidden_in_template_interpolation(tmp_path):
    raw = _session_bytes(
        _record(
            "response_item",
            {
                "type": "custom_tool_call",
                "name": "exec",
                "call_id": "call-template-image",
                "input": (
                    'await tools.exec_command({cmd: `run ${await tools.image_gen__imagegen('
                    '{prompt: "hidden", transparent_background: false})}`});'
                ),
            },
            ordinal=1,
        ),
        _extension("completed"),
    )
    session_path = tmp_path / "template-image-session.jsonl"
    session_path.write_bytes(raw)

    with pytest.raises(CodexExecTelemetryError, match="no matching ImageGen"):
        read_cli_session(session_path, SESSION_ID, max_event_bytes=4096, max_total_bytes=8192)


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
