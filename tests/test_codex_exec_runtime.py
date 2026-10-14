import json
from hashlib import sha256
from uuid import uuid4

import pytest

from plotloom.codex_exec_runtime import (
    CodexExecRuntimeError,
    assert_file_changes_confined,
    read_exec_events,
)


def _write_events(path, terminal="turn.completed", *, suffix=()):
    session_id = str(uuid4())
    records = [
        {"type": "thread.started", "thread_id": session_id},
        {"type": "turn.started"},
        {"type": terminal},
        *suffix,
    ]
    path.write_bytes(b"".join(json.dumps(item).encode() + b"\n" for item in records))
    return session_id


def _write_records(path, records):
    path.write_bytes(b"".join(json.dumps(item).encode() + b"\n" for item in records))


def _record_stream(session_id, *items):
    return [
        {"type": "thread.started", "thread_id": str(session_id)},
        *items,
    ]


def test_exec_stream_binds_one_exact_session_and_terminal(tmp_path):
    path = tmp_path / "events.jsonl"
    session_id = _write_events(path)

    evidence = read_exec_events(path, max_event_bytes=1024, max_total_bytes=4096)

    assert str(evidence.session_id) == session_id
    assert evidence.terminal_event == "turn.completed"
    assert evidence.transcript_size_bytes == path.stat().st_size


def test_exec_stream_retains_a_typed_failed_terminal_for_budget_settlement(tmp_path):
    path = tmp_path / "events.jsonl"
    _write_events(path, terminal="turn.failed")

    evidence = read_exec_events(path, max_event_bytes=1024, max_total_bytes=4096)

    assert evidence.terminal_event == "turn.failed"


def test_exec_stream_rejects_events_after_terminal(tmp_path):
    path = tmp_path / "events.jsonl"
    _write_events(path, suffix=({"type": "turn.started"},))

    with pytest.raises(CodexExecRuntimeError, match="after its terminal event"):
        read_exec_events(path, max_event_bytes=1024, max_total_bytes=4096)


def test_exec_stream_types_bounded_diagnostics_and_matching_file_changes(tmp_path):
    session_id = uuid4()
    delivery = tmp_path / "delivery"
    delivery.mkdir()
    output = delivery / "outline.json"
    diagnostic_message = "Ignoring unsupported setting tools.view_image=false"
    item_id = "fc_01"
    change = {"path": str(output), "kind": "add"}
    records = _record_stream(
        session_id,
        {"type": "item.completed", "item": {"id": "err_01", "type": "error", "message": diagnostic_message}},
        {"type": "turn.started"},
        {"type": "item.started", "item": {"id": item_id, "type": "file_change", "status": "in_progress", "changes": [change]}},
        {"type": "item.completed", "item": {"id": item_id, "type": "file_change", "status": "completed", "changes": [change]}},
        {"type": "turn.completed"},
    )
    path = tmp_path / "events.jsonl"
    _write_records(path, records)

    evidence = read_exec_events(path, max_event_bytes=1024, max_total_bytes=8192)
    assert evidence.diagnostics[0].item_id == "err_01"
    assert evidence.diagnostics[0].message_sha256 == sha256(diagnostic_message.encode()).hexdigest()
    assert evidence.diagnostics[0].message_size_bytes == len(diagnostic_message.encode())
    assert not hasattr(evidence.diagnostics[0], "message")
    assert evidence.file_changes[0].item_id == item_id
    assert evidence.file_changes[0].changes[0].absolute_path == str(output)
    assert evidence.file_changes[0].changes[0].kind == "add"

    assert_file_changes_confined(evidence, delivery)


def test_exec_stream_rejects_duplicate_diagnostic_ids(tmp_path):
    session_id = uuid4()
    error = {"type": "error", "id": "err_01", "message": "configuration warning"}
    records = _record_stream(
        session_id,
        {"type": "item.completed", "item": error},
        {"type": "item.completed", "item": error},
        {"type": "turn.started"},
        {"type": "turn.completed"},
    )
    path = tmp_path / "events.jsonl"
    _write_records(path, records)

    with pytest.raises(CodexExecRuntimeError, match="diagnostic item ID is not unique"):
        read_exec_events(path, max_event_bytes=1024, max_total_bytes=8192)


@pytest.mark.parametrize(("event_type", "item"), (
    ("item.completed", {"id": "err_01", "type": "error", "message": "warning", "code": "unknown"}),
    ("item.started", {"id": "err_01", "type": "error", "message": "warning"}),
))
def test_exec_stream_rejects_unqualified_diagnostic_shapes(tmp_path, event_type, item):
    session_id = uuid4()
    records = _record_stream(
        session_id,
        {"type": event_type, "item": item},
        {"type": "turn.started"},
        {"type": "turn.completed"},
    )
    path = tmp_path / "events.jsonl"
    _write_records(path, records)

    with pytest.raises(CodexExecRuntimeError, match="diagnostic item"):
        read_exec_events(path, max_event_bytes=1024, max_total_bytes=8192)


@pytest.mark.parametrize("kind", ([], "rename", None))
def test_exec_stream_rejects_unsupported_or_untyped_file_change_kinds(tmp_path, kind):
    session_id = uuid4()
    change = {"path": str(tmp_path / "delivery" / "outline.json"), "kind": kind}
    item = {"id": "fc_01", "type": "file_change", "status": "in_progress", "changes": [change]}
    records = _record_stream(
        session_id,
        {"type": "turn.started"},
        {"type": "item.started", "item": item},
        {"type": "turn.completed"},
    )
    path = tmp_path / "events.jsonl"
    _write_records(path, records)

    with pytest.raises(CodexExecRuntimeError, match="file-change entry"):
        read_exec_events(path, max_event_bytes=1024, max_total_bytes=8192)


@pytest.mark.parametrize("target", ("outside", "symlink", "traversal"))
def test_exec_file_changes_reject_escape_paths(tmp_path, target):
    session_id = uuid4()
    delivery = tmp_path / "delivery"
    delivery.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    if target == "outside":
        changed_path = outside
    elif target == "symlink":
        link = delivery / "link"
        link.symlink_to(outside)
        changed_path = link
    else:
        changed_path = delivery / ".." / "outside.txt"
    change = {"id": "fc_01", "type": "file_change", "status": "in_progress",
              "changes": [{"path": str(changed_path), "kind": "update"}]}
    completed = {**change, "status": "completed"}
    records = _record_stream(
        session_id,
        {"type": "turn.started"},
        {"type": "item.started", "item": change},
        {"type": "item.completed", "item": completed},
        {"type": "turn.completed"},
    )
    path = tmp_path / "events.jsonl"
    _write_records(path, records)
    if target == "traversal":
        with pytest.raises(CodexExecRuntimeError, match="canonical bounded path"):
            read_exec_events(path, max_event_bytes=1024, max_total_bytes=8192)
        return
    evidence = read_exec_events(path, max_event_bytes=1024, max_total_bytes=8192)

    with pytest.raises(CodexExecRuntimeError, match="delivery"):
        assert_file_changes_confined(evidence, delivery)


def test_exec_stream_rejects_file_change_completion_drift(tmp_path):
    session_id = uuid4()
    started = {
        "id": "fc_01", "type": "file_change", "status": "in_progress",
        "changes": [{"path": str(tmp_path / "delivery" / "one.json"), "kind": "add"}],
    }
    completed = {
        **started,
        "status": "completed",
        "changes": [{"path": str(tmp_path / "delivery" / "two.json"), "kind": "add"}],
    }
    records = _record_stream(
        session_id,
        {"type": "turn.started"},
        {"type": "item.started", "item": started},
        {"type": "item.completed", "item": completed},
        {"type": "turn.completed"},
    )
    path = tmp_path / "events.jsonl"
    _write_records(path, records)

    with pytest.raises(CodexExecRuntimeError, match="does not match its started item"):
        read_exec_events(path, max_event_bytes=1024, max_total_bytes=8192)
