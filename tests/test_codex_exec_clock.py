"""Benign sleeps are accepted only with complete bound native evidence."""
import json
from uuid import uuid4

import pytest

from plotloom.codex_exec_telemetry import read_cli_session


@pytest.mark.parametrize("defect", [None, "call", "duration", "session", "turn", "result", "missing", "duplicate", "cross_turn", "invalid_arguments", "boolean_duration"])
def test_clock_sleep_has_exact_call_event_and_completed_output(tmp_path, defect):
    session = uuid4()
    rows = [
        {"type":"session_meta","payload":{"id":str(session)}},
        {"type":"turn_context","payload":{"turn_id":"turn"}},
        {"type":"response_item","payload":{"type":"function_call","name":"sleep","namespace":"clock",
            "call_id":"sleep-1","arguments":'{"duration_ms":20}'}},
        {"type":"event_msg","payload":{"type":"item_completed","thread_id":str(session),"turn_id":"turn",
            "item":{"type":"Extension","kind":"clock.sleep","id":"sleep-1","durationMs":20}}},
        {"type":"response_item","payload":{"type":"function_call_output","call_id":"sleep-1",
            "output":"Wall time: 0.020 seconds\nSleep completed."}},
    ]
    if defect == "call": rows[2]["payload"]["name"] = "other"
    if defect == "duration": rows[3]["payload"]["item"]["durationMs"] = 21
    if defect == "session": rows[3]["payload"]["thread_id"] = str(uuid4())
    if defect == "turn": rows[3]["payload"]["turn_id"] = "another"
    if defect == "result": rows[4]["payload"]["output"] = "still running"
    if defect == "missing": rows.pop()
    if defect == "duplicate": rows.insert(4, rows[3].copy())
    if defect == "cross_turn": rows.insert(3, {"type":"turn_context","payload":{"turn_id":"new-turn"}})
    if defect == "invalid_arguments": rows[2]["payload"]["arguments"] = "null"
    if defect == "boolean_duration": rows[3]["payload"]["item"]["durationMs"] = True
    for index,row in enumerate(rows):
        row["ordinal"] = index
    path = tmp_path / "session.jsonl"
    path.write_text("".join(json.dumps(row)+"\n" for row in rows))
    if defect:
        with pytest.raises(ValueError):
            read_cli_session(path, session, max_event_bytes=4096,max_total_bytes=20000)
    else:
        evidence = read_cli_session(path, session, max_event_bytes=4096,max_total_bytes=20000)
        assert not evidence.image_calls and not evidence.image_events
