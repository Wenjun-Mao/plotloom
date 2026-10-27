"""Only exact, paired empty observations enter prospective text evidence."""
import json
from dataclasses import FrozenInstanceError
from hashlib import sha256
from uuid import uuid4

import pytest

from plotloom.codex_exec_runtime import CodexExecRuntimeError, read_exec_events
from tests.codex_exec_catalog_fixtures import empty_catalog_pair


def read(path, middle, *, text=True, before=(), after=(), terminal=True):
    records = [{"type": "thread.started", "thread_id": str(uuid4())}, *before,
               {"type": "turn.started"}, *middle]
    if terminal:
        records.append({"type": "turn.completed"})
    records.extend(after)
    path.write_bytes(b"".join(json.dumps(r).encode() + b"\n" for r in records))
    return read_exec_events(path, max_event_bytes=50000, max_total_bytes=500000,
                            allow_empty_catalog_calls=text)


def test_exact_empty_pairs_are_immutable_hash_only_text_evidence(tmp_path):
    path = tmp_path / "events.jsonl"
    evidence = read(path, empty_catalog_pair() + empty_catalog_pair("list_mcp_resource_templates", "catalog_2"))
    assert evidence.terminal_event == "turn.completed" and not evidence.diagnostics
    lines = path.read_bytes().splitlines(keepends=True)
    assert evidence.transcript_sha256 == sha256(path.read_bytes()).hexdigest()
    assert len(evidence.empty_catalog_calls) == 2
    for index, call in enumerate(evidence.empty_catalog_calls):
        assert call.started_ordinal == 2 + 2 * index and call.completed_ordinal == 3 + 2 * index
        assert call.started_sha256 == sha256(lines[call.started_ordinal]).hexdigest()
        assert call.completed_sha256 == sha256(lines[call.completed_ordinal]).hexdigest()
        assert call.started_size_bytes == len(lines[call.started_ordinal])
        assert call.completed_size_bytes == len(lines[call.completed_ordinal])
        assert not hasattr(call, "result") and not hasattr(call, "arguments")
        with pytest.raises(FrozenInstanceError):
            call.tool = "other"


def test_clean_stream_has_identical_default_and_text_readback(tmp_path):
    path = tmp_path / "events.jsonl"
    expected = read(path, [])
    actual = read_exec_events(path, max_event_bytes=50000, max_total_bytes=500000)
    assert expected == actual and not actual.empty_catalog_calls


def test_default_reader_refuses_even_exact_empty_catalog(tmp_path):
    with pytest.raises(CodexExecRuntimeError):
        read(tmp_path / "events.jsonl", empty_catalog_pair(), text=False)


@pytest.mark.parametrize("defect", [
    "envelope-extra", "item-extra", "missing-field", "foreign-server", "mutating-tool", "unknown-tool",
    "tool-type", "arguments", "argument-type", "start-result", "error", "error-false", "result-extra",
    "structured-content", "reference", "nonempty", "empty-content", "multiple-content", "block-extra",
    "wrong-key", "wrong-json", "wrong-text-type", "start-status", "end-status", "mismatched-id",
    "mismatched-tool", "duplicate-start", "duplicate-complete", "reused-id", "missing-start",
    "missing-complete", "missing-terminal", "before-turn", "after-terminal", "duplicate-terminal",
    "duplicate-turn", "duplicate-session", "foreign-id-before", "foreign-id-after", "id-type",
    "id-empty", "id-bytes", "id-surrogate", "call-count", "completion-arguments", "completion-server",
])
def test_catalog_exception_remains_closed_world(tmp_path, defect):
    pair = empty_catalog_pair()
    first, last = pair[0]["item"], pair[1]["item"]
    before, after, terminal = [], [], True
    if defect == "envelope-extra": pair[0]["extra"] = None
    elif defect == "item-extra": first["extra"] = None
    elif defect == "missing-field": del first["error"]
    elif defect == "foreign-server": first["server"] = "external"
    elif defect == "mutating-tool": first["tool"] = "write_resource"
    elif defect == "unknown-tool": first["tool"] = "read_resource"
    elif defect == "tool-type": first["tool"] = []
    elif defect == "arguments": first["arguments"] = {"uri": "resource://private"}
    elif defect == "argument-type": first["arguments"] = []
    elif defect == "start-result": first["result"] = last["result"]
    elif defect in {"error", "error-false"}: last["error"] = {} if defect == "error" else False
    elif defect == "result-extra": last["result"]["extra"] = None
    elif defect == "structured-content": last["result"]["structured_content"] = {}
    elif defect == "reference": last["result"]["content"] = [{"type": "resource_link", "uri": "resource://private"}]
    elif defect == "nonempty": last["result"]["content"][0]["text"] = '{"resources":[{}]}'
    elif defect == "empty-content": last["result"]["content"] = []
    elif defect == "multiple-content": last["result"]["content"] *= 2
    elif defect == "block-extra": last["result"]["content"][0]["annotations"] = {}
    elif defect == "wrong-key": last["result"]["content"][0]["text"] = '{"resourceTemplates":[]}'
    elif defect == "wrong-json": last["result"]["content"][0]["text"] = '{"resources":[],"resources":[]}'
    elif defect == "wrong-text-type": last["result"]["content"][0]["text"] = {"resources": []}
    elif defect == "start-status": first["status"] = "completed"
    elif defect == "end-status": last["status"] = "failed"
    elif defect == "mismatched-id": last["id"] = "another"
    elif defect == "mismatched-tool": last["tool"] = "list_mcp_resource_templates"
    elif defect == "duplicate-start": pair.insert(1, pair[0])
    elif defect == "duplicate-complete": pair.append(pair[1])
    elif defect == "reused-id": pair += empty_catalog_pair()
    elif defect == "missing-start": pair.pop(0)
    elif defect == "missing-complete": pair.pop()
    elif defect == "missing-terminal": terminal = False
    elif defect == "before-turn": before, pair = pair, []
    elif defect == "after-terminal": after, pair = pair, []
    elif defect == "duplicate-terminal": after = [{"type": "turn.completed"}]
    elif defect == "duplicate-turn": pair.insert(0, {"type": "turn.started"})
    elif defect == "duplicate-session": pair.insert(0, {"type": "thread.started", "thread_id": str(uuid4())})
    elif defect == "foreign-id-before": pair.insert(0, {"type": "item.completed", "item": {"id": first["id"], "type": "agent_message"}})
    elif defect == "foreign-id-after": pair.append({"type": "item.completed", "item": {"id": first["id"], "type": "agent_message"}})
    elif defect == "id-type": first["id"] = None
    elif defect == "id-empty": first["id"] = ""
    elif defect == "id-bytes": first["id"] = "文" * 43
    elif defect == "id-surrogate": first["id"] = "\ud800"
    elif defect == "call-count": pair = sum((empty_catalog_pair(item_id=str(i)) for i in range(129)), [])
    elif defect == "completion-arguments": last["arguments"] = {"uri": "resource://private"}
    elif defect == "completion-server": last["server"] = "external"
    with pytest.raises(CodexExecRuntimeError):
        read(tmp_path / "events.jsonl", pair, before=before, after=after, terminal=terminal)


@pytest.mark.parametrize("defect", ["duplicate-field", "record-bytes", "truncation", "partial-record"])
def test_catalog_raw_record_and_file_guards(tmp_path, defect):
    path = tmp_path / "events.jsonl"
    read(path, empty_catalog_pair())
    raw = path.read_bytes()
    if defect == "duplicate-field": raw = raw.replace(b'"server": "codex"', b'"server":"codex","server":"codex"')
    elif defect == "record-bytes": raw = raw.replace(b'"server": "codex"', b'"server":' + b' ' * 16384 + b'"codex"')
    elif defect == "truncation": raw = raw[:raw.rfind(b'{"type": "turn.completed"}')]
    else: raw = raw[:-3]
    path.write_bytes(raw)
    with pytest.raises(CodexExecRuntimeError):
        read_exec_events(path, max_event_bytes=50000, max_total_bytes=500000, allow_empty_catalog_calls=True)


def test_empty_catalog_does_not_convert_fatal_or_item_errors_into_success(tmp_path):
    path = tmp_path / "events.jsonl"
    fatal = read(path, empty_catalog_pair() + [{"type": "error", "message": "fatal"}], terminal=False)
    assert fatal.terminal_event == "error" and fatal.empty_catalog_calls
    item = read(path, empty_catalog_pair() + [
        {"type": "item.completed", "item": {"id": "err", "type": "error", "message": "fatal"}}])
    assert item.diagnostics and item.empty_catalog_calls
