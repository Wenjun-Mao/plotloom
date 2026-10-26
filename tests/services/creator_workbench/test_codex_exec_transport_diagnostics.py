"""Controlled child/validator contracts; no provider or model execution."""
import json
import time
from contextlib import closing

import pytest
from codex_exec_supervisor_test_support import _prepared_text_job


def fake_recovered_cli(*, valid, exit_code):
    return f'''
import json, os, sys
from datetime import date
from pathlib import Path
from uuid import uuid4
if len(sys.argv)>1 and sys.argv[1]=="sandbox":
    args=sys.argv[sys.argv.index("--")+1:]
    with Path(os.environ["PLOTLOOM_TEST_VALIDATOR_CAPTURE"]).open("a") as record:
        record.write(json.dumps(args)+"\\n")
    if "render" in args:
        print("<!doctype html><html><body>controlled renderer</body></html>")
    else:
        candidate=Path(args[args.index("validate")+1])
        if json.loads(candidate.read_bytes()).get("invalid"):
            print("synthetic invalid candidate",file=sys.stderr)
            raise SystemExit(1)
    raise SystemExit(0)
sys.stdin.read()
(Path.cwd()/"outline.json").write_text(json.dumps({{"source":"synthetic", "invalid":{not valid!r}}}))
session=str(uuid4());day=date.today()
folder=Path(os.environ["CODEX_HOME"])/"sessions"/day.strftime("%Y/%m/%d")
folder.mkdir(parents=True,exist_ok=True)
(folder/f"rollout-synthetic-{{session}}.jsonl").write_text(json.dumps({{"type":"session_meta","payload":{{"id":session}},"ordinal":0}})+"\\n")
for event in [{{"type":"thread.started","thread_id":session}},{{"type":"turn.started"}},
    {{"type":"error","message":"Reconnecting... 2/5 (exceeded retry limit, last status: 429 Too Many Requests)"}},
    {{"type":"turn.completed"}}]:
    print(json.dumps(event),flush=True)
raise SystemExit({exit_code})
'''


@pytest.mark.parametrize("valid,exit_code,expected,validations", [(True,0,"completed",2),(False,0,"failed",1),(True,2,"failed",0)])
def test_recovered_text_requires_normal_exit_and_trusted_content_validation(supervisor, tmp_path, monkeypatch, valid, exit_code, expected, validations):
    capture = tmp_path / "validator-calls.jsonl"
    monkeypatch.setenv("PLOTLOOM_TEST_VALIDATOR_CAPTURE", str(capture))
    _exchange,_request,_pin,_job,attempt,_profile = _prepared_text_job(supervisor,tmp_path,
        fake_cli_source=fake_recovered_cli(valid=valid,exit_code=exit_code))
    status=supervisor.admit(attempt)
    deadline=time.monotonic()+15
    while status.state not in {"completed","failed","settled","outcome_unknown"} and time.monotonic()<deadline:
        time.sleep(0.05)
        status=supervisor.status(attempt.attempt_id)
    assert status.state==expected, status
    assert status.attempt.process_exit_code==exit_code
    calls = [json.loads(line) for line in capture.read_text().splitlines()] if capture.exists() else []
    assert len(calls) == validations
    assert all("validate" in call or "render" in call for call in calls)
    with closing(supervisor._connect()) as connection:
        assert not connection.execute("SELECT * FROM exec_validation_process WHERE attempt_id=?", (str(attempt.attempt_id),)).fetchall()
    if expected=="completed":
        assert status.receipt and status.receipt.text_validation
        assert [step.step_id for step in status.receipt.text_validation.steps]==["validate","render"]
    else:
        assert status.receipt is None and status.attempt.terminal_result=="failure"
        if valid is False:
            diagnostic = supervisor.private_root / "attempts" / str(attempt.attempt_id) / "validation/validate.stderr"
            assert diagnostic.read_text().strip() == "synthetic invalid candidate"
