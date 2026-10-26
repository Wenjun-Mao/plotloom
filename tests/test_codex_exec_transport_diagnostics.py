"""Qualified reconnects are transport evidence, never content or image authority."""
import json
from dataclasses import FrozenInstanceError
from hashlib import sha256
from uuid import uuid4

import pytest
from plotloom.codex_exec_runtime import CodexExecRuntimeError, read_exec_events

RECONNECT = "Reconnecting... 2/5 (exceeded retry limit, last status: 429 Too Many Requests)"


def stream(tmp_path, middle=(), *, started=True, suffix=(), terminal="turn.completed", **limits):
    rows = [{"type": "thread.started", "thread_id": str(uuid4())}]
    if started: rows.append({"type": "turn.started"})
    rows.extend(middle)
    if terminal: rows.append({"type": terminal})
    rows.extend(suffix)
    path = tmp_path / "stdout.jsonl"
    path.write_bytes(b"".join(json.dumps(r).encode() + b"\n" for r in rows))
    return read_exec_events(path, max_event_bytes=limits.get("event", 1024), max_total_bytes=limits.get("total", 100000))


def test_exact_in_turn_reconnect_is_bounded_immutable_hash_only_evidence(tmp_path):
    evidence = stream(tmp_path, [{"type": "error", "message": RECONNECT}])
    assert evidence.terminal_event == "turn.completed" and not evidence.diagnostics
    assert len(evidence.transport_diagnostics) == 1
    diagnostic = evidence.transport_diagnostics[0]
    assert vars(diagnostic) == {"event_ordinal": 2, "message_sha256": sha256(RECONNECT.encode()).hexdigest(),
        "message_size_bytes": len(RECONNECT.encode())}
    assert evidence.transcript_sha256 == sha256((tmp_path / "stdout.jsonl").read_bytes()).hexdigest()
    assert "Too Many Requests" not in repr(diagnostic)
    with pytest.raises(FrozenInstanceError): diagnostic.message_size_bytes = 0


@pytest.mark.parametrize("defect", ["extra-field", "message-type", "unsupported-body", "counter-zero", "counter-six", "other-limit", "before-turn", "missing-terminal", "duplicate-terminal", "after-terminal", "generic-fatal", "byte-bound", "diagnostic-count", "duplicate-turn", "duplicate-session"])
def test_reconnect_exception_keeps_phase_shape_terminal_and_resource_refusals(tmp_path, defect):
    error = {"type": "error", "message": RECONNECT}
    middle, suffix, started, terminal, limits = [error], [], True, "turn.completed", {}
    if defect == "extra-field": error["retryable"] = True
    if defect == "message-type": error["message"] = []
    if defect == "unsupported-body": error["message"] = "Reconnecting... 2/5 (fatal provider failure)"
    if defect == "counter-zero": error["message"] = RECONNECT.replace("2/5", "0/5")
    if defect == "counter-six": error["message"] = RECONNECT.replace("2/5", "6/5")
    if defect == "other-limit": error["message"] = RECONNECT.replace("2/5", "2/6")
    if defect == "before-turn": started = False
    if defect == "missing-terminal": terminal = None
    if defect == "duplicate-terminal": suffix = [{"type": "turn.completed"}]
    if defect == "after-terminal": suffix = [{"type": "item.completed", "item": {"type": "agent_message"}}]
    if defect == "generic-fatal": error["message"] = "Fatal transport failure"
    if defect == "byte-bound": limits = {"event": 80}
    if defect == "diagnostic-count": middle = [error] * 129
    if defect == "duplicate-turn": middle.append({"type": "turn.started"})
    if defect == "duplicate-session": middle.append({"type": "thread.started", "thread_id": str(uuid4())})
    with pytest.raises(CodexExecRuntimeError):
        stream(tmp_path, middle, started=started, suffix=suffix, terminal=terminal, **limits)


def test_generic_error_and_item_error_do_not_become_successful_turns(tmp_path):
    fatal = stream(tmp_path, [{"type": "error", "message": "Fatal transport failure"}], terminal=None)
    assert fatal.terminal_event == "error" and not fatal.transport_diagnostics
    failed = stream(tmp_path, [{"type": "error", "message": RECONNECT}], terminal="turn.failed")
    assert failed.terminal_event == "turn.failed" and failed.transport_diagnostics
    item = stream(tmp_path, [{"type": "error", "message": RECONNECT},
        {"type": "item.completed", "item": {"id": "err_01", "type": "error", "message": "Fatal item error"}}])
    assert item.diagnostics and item.transport_diagnostics
