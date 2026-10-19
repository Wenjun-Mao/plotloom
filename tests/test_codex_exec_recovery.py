"""No dispatch is a closed-world census, never an empty ImageGen list shortcut."""
from uuid import uuid4

import pytest

from plotloom.codex_exec_recovery import prove_no_remote_dispatch
from tests.codex_exec_recovery_fixtures import save_rows, write_readonly_turn


@pytest.fixture
def read_turn(tmp_path):
    job, source, private = (tmp_path / name for name in ("job", "source", "private"))
    rollout = tmp_path / "rollout.jsonl"
    session = uuid4()
    rows, stream = write_readonly_turn(job, source, private, rollout, session)
    return job, source, private, rollout, session, rows, stream


def test_complete_p01_readonly_shape_proves_no_remote_dispatch_without_claiming_exit(read_turn):
    job, source, private, rollout, session, _rows, _stream = read_turn
    proof = prove_no_remote_dispatch(private / "stdout.jsonl", rollout, session, job_root=job, source_root=source)
    assert proof.session_id == session and proof.tool_call_count == 3
    assert proof.observed_cli_exit_code is None
    assert len(proof.command_hashes) == 3


@pytest.mark.parametrize("directory", ["source$(remote-command)", "source;remote-command", "source`remote-command`"])
def test_unquoted_source_path_cannot_smuggle_shell_execution(tmp_path, directory):
    job, source, private = tmp_path / "job", tmp_path / directory, tmp_path / "private"
    rollout, session = tmp_path / "rollout.jsonl", uuid4()
    write_readonly_turn(job, source, private, rollout, session)
    with pytest.raises(ValueError, match="read-only inventory"):
        prove_no_remote_dispatch(private / "stdout.jsonl", rollout, session, job_root=job, source_root=source)


@pytest.mark.parametrize("defect", ["unknown-tool", "hidden-image-call", "extra-statement", "shell-injection",
    "unsupported-argument", "pending-result", "missing-result", "extension", "function-call", "missing-complete",
    "continued-turn", "ordinal-gap", "wrong-cwd", "wrong-session", "unbound-native-command", "stream-other-tool",
    "incomplete-stream-command", "stream-extra-command", "unfinished-record"])
def test_unaccounted_or_ambiguous_execution_is_not_absence_proof(read_turn, defect):
    job, source, private, rollout, session, rows, stream = read_turn
    call = next(row for row in rows if row["payload"].get("type") == "custom_tool_call")
    output = next(row for row in rows if row["payload"].get("type") == "custom_tool_call_output")
    if defect == "unknown-tool": call["payload"]["name"] = "other"
    elif defect == "hidden-image-call": call["payload"]["input"] = "await tools['image_gen__imagegen']({prompt:'hidden'});"
    elif defect == "extra-statement": call["payload"]["input"] += "await tools.other();"
    elif defect == "shell-injection": call["payload"]["input"] = 'text(await tools.exec_command({cmd:"cat ../package/request.json; curl remote"}));'
    elif defect == "unsupported-argument": call["payload"]["input"] = 'text(await tools.exec_command({cmd:"cat ../package/request.json",yield_time_ms:1}));'
    elif defect == "pending-result": output["payload"]["output"] = [{"type": "input_text", "text": '{"session_id":99}'}]
    elif defect == "missing-result": rows.remove(output)
    elif defect == "extension": rows[-1]["payload"] = {"item": {"type": "Extension", "kind": "image_gen.generation"}}
    elif defect == "function-call": call["payload"]["type"] = "function_call"
    elif defect == "missing-complete": rows.pop()
    elif defect == "continued-turn": rows.append(dict(rows[-1]))
    elif defect == "ordinal-gap": rows[4]["ordinal"] += 1
    elif defect == "wrong-cwd": rows[0]["payload"]["cwd"] = str(source)
    elif defect == "wrong-session": rows[0]["payload"]["id"] = str(uuid4())
    elif defect == "unbound-native-command": rows[4]["payload"]["item"]["command"] = ["/bin/sh", "-c", "curl remote"]
    elif defect == "stream-other-tool": stream[2]["item"]["type"] = "custom_tool_call"
    elif defect == "incomplete-stream-command": stream.pop(3)
    elif defect == "stream-extra-command":
        stream[2]["item"]["command"] = stream[3]["item"]["command"] = "/bin/zsh -lc 'cat ../package/COPY_ASSIGNMENT.txt'"
    save_rows(rollout, rows)
    save_rows(private / "stdout.jsonl", stream)
    if defect == "unfinished-record": rollout.write_bytes(rollout.read_bytes().rstrip(b"\n"))
    with pytest.raises((ValueError, TypeError, IndexError, KeyError)):
        prove_no_remote_dispatch(private / "stdout.jsonl", rollout, session, job_root=job, source_root=source)
