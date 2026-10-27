"""Prospective text compatibility reaches trusted validators, never image settlement."""
import json
import time
from contextlib import closing
from types import SimpleNamespace

import pytest
from codex_exec_supervisor_test_support import _prepared_text_job

from tests.codex_exec_catalog_fixtures import empty_catalog_pair


def fake_catalog_cli(*, valid, exit_code):
    events = empty_catalog_pair() + empty_catalog_pair("list_mcp_resource_templates", "catalog_2")
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
    elif json.loads(Path(args[args.index("validate")+1]).read_bytes()).get("invalid"):
        print("synthetic invalid candidate",file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(0)
sys.stdin.read()
(Path.cwd()/"outline.json").write_text(json.dumps({{"source":"synthetic","invalid":{not valid!r}}}))
session=str(uuid4());day=date.today()
folder=Path(os.environ["CODEX_HOME"])/"sessions"/day.strftime("%Y/%m/%d")
folder.mkdir(parents=True,exist_ok=True)
(folder/f"rollout-synthetic-{{session}}.jsonl").write_text(json.dumps({{"type":"session_meta","payload":{{"id":session}},"ordinal":0}})+"\\n")
for event in [{{"type":"thread.started","thread_id":session}},{{"type":"turn.started"}},
    *json.loads({json.dumps(json.dumps(events))}),{{"type":"turn.completed"}}]:
    print(json.dumps(event),flush=True)
raise SystemExit({exit_code})
'''


@pytest.mark.parametrize("valid,exit_code,expected,validations", [(True, 0, "completed", 2),
    (False, 0, "failed", 1), (True, 2, "failed", 0)])
def test_text_catalogs_do_not_replace_exit_or_content_validation(supervisor, tmp_path, monkeypatch,
                                                               valid, exit_code, expected, validations):
    capture = tmp_path / "validator-calls.jsonl"
    monkeypatch.setenv("PLOTLOOM_TEST_VALIDATOR_CAPTURE", str(capture))
    _exchange, _request, _pin, job, attempt, _profile = _prepared_text_job(supervisor, tmp_path,
        fake_cli_source=fake_catalog_cli(valid=valid, exit_code=exit_code))
    status = supervisor.admit(attempt)
    deadline = time.monotonic() + 15
    while status.state not in {"completed", "failed", "settled", "outcome_unknown"} and time.monotonic() < deadline:
        time.sleep(0.05)
        status = supervisor.status(attempt.attempt_id)
    assert status.state == expected, status
    assert status.attempt.process_exit_code == exit_code
    calls = [json.loads(line) for line in capture.read_text().splitlines()] if capture.exists() else []
    assert len(calls) == validations
    assert all("validate" in call or "render" in call for call in calls)
    with closing(supervisor._connect()) as connection:
        assert not connection.execute("SELECT * FROM exec_slot").fetchall()
        assert not connection.execute("SELECT * FROM exec_validation_process").fetchall()
    if expected == "completed":
        assert status.receipt and status.receipt.text_validation
        assert [step.step_id for step in status.receipt.text_validation.steps] == ["validate", "render"]
        assert (job / "delivery/completion.json").is_file()
    else:
        assert status.receipt is None and status.attempt.terminal_result == "failure"
        assert not (job / "delivery/completion.json").exists()


@pytest.mark.parametrize("image_calls", [False, True])
def test_domain_inspection_also_vetoes_catalog_metadata_for_images(tmp_path, image_calls):
    from codex_exec_terminal_inspection import inspect_domain_evidence
    from plotloom.codex_exec_runtime import read_exec_events
    path = tmp_path / "events.jsonl"
    rows = [{"type": "thread.started", "thread_id": "00000000-0000-0000-0000-000000000001"},
            {"type": "turn.started"}, *empty_catalog_pair(), {"type": "turn.completed"}]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    stream = read_exec_events(path, max_event_bytes=4096, max_total_bytes=8192, allow_empty_catalog_calls=True)
    session = SimpleNamespace(image_calls=(object(),) if image_calls else (), image_events=(), reference_views=())
    assert not inspect_domain_evidence(SimpleNamespace(domain="image"), path, path, stream, session,
                                       tmp_path, tmp_path)


@pytest.mark.parametrize("field", ["image_calls", "image_events", "reference_views"])
def test_text_catalogs_never_authorize_image_or_reference_contamination(tmp_path, field):
    from codex_exec_terminal_inspection import inspect_domain_evidence
    session = SimpleNamespace(image_calls=(), image_events=(), reference_views=())
    setattr(session, field, (object(),))
    assert not inspect_domain_evidence(SimpleNamespace(domain="text"), tmp_path, tmp_path,
        SimpleNamespace(empty_catalog_calls=(object(),)), session, tmp_path, tmp_path)
