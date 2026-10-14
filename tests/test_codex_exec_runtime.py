import json
from uuid import uuid4

import pytest

from plotloom.codex_exec_runtime import CodexExecRuntimeError, read_exec_events


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
