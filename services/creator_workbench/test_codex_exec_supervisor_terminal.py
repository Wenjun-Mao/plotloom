"""Process lifecycle and exact-evidence tests for the Mac supervisor."""
import json
import shutil
import time
from pathlib import Path
from uuid import uuid4

from codex_exec_supervisor import CodexExecSupervisor
from codex_exec_supervisor_test_support import _prepared_text_job


def test_fake_cli_process_publishes_exact_terminal_receipt_and_delivery(supervisor, monkeypatch, tmp_path):
    session_id = uuid4()
    monkeypatch.setenv(
        "PLOTLOOM_TEST_CANDIDATE_JSON",
        json.dumps({"source": "The Ferryman", "params": {"episodes": 1}, "episodes": []}),
    )
    monkeypatch.setenv("PLOTLOOM_TEST_SESSION_ID", str(session_id))
    captured_command = tmp_path / "captured-command.json"
    monkeypatch.setenv("PLOTLOOM_TEST_COMMAND_CAPTURE", str(captured_command))
    fake_cli = r'''#!/usr/bin/env python3
import json, os, sys, time
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

if len(sys.argv) > 1 and sys.argv[1] == "sandbox":
    validator_argv = sys.argv[sys.argv.index("--") + 1:]
    if "render" in validator_argv:
        print("<!doctype html><html><body>trusted fake renderer</body></html>")
    raise SystemExit(0)

sys.stdin.read()
Path(os.environ["PLOTLOOM_TEST_COMMAND_CAPTURE"]).write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
time.sleep(1)
delivery = Path.cwd()
(delivery / "outline.json").write_text(os.environ["PLOTLOOM_TEST_CANDIDATE_JSON"], encoding="utf-8")
session_id = UUID(os.environ["PLOTLOOM_TEST_SESSION_ID"])
day = date.today()
session_dir = Path(os.environ["CODEX_HOME"]) / "sessions" / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}"
session_dir.mkdir(parents=True)
timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
(session_dir / f"rollout-{timestamp}-{session_id}.jsonl").write_text(
    json.dumps({"type": "session_meta", "payload": {"id": str(session_id)}, "ordinal": 0}) + "\n",
    encoding="utf-8",
)
for event in (
    {"type": "thread.started", "thread_id": str(session_id)},
    {"type": "turn.started"},
    {"type": "turn.completed"},
):
    print(json.dumps(event), flush=True)
time.sleep(0.2)
'''
    fake_cli = fake_cli.removeprefix("#!/usr/bin/env python3\n")
    exchange, request, execution_pin, job_root, attempt, profile = _prepared_text_job(
        supervisor, tmp_path, fake_cli_source=fake_cli
    )

    status = supervisor.admit(attempt)
    assert status.state in {"spawn_intent", "running"}
    restarted = CodexExecSupervisor(
        supervisor.executable,
        source_root=supervisor.source_root,
        outputs_root=supervisor.outputs_root,
        private_root=supervisor.private_root,
    )
    status = restarted.status(attempt.attempt_id)
    assert status.state in {"spawn_intent", "running"}, status
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status = restarted.status(attempt.attempt_id)
        if status.state in {"completed", "failed", "settled", "outcome_unknown"}:
            break
        time.sleep(0.05)

    assert status.state == "completed", status
    command = json.loads(captured_command.read_text(encoding="utf-8"))
    assert command[0] == "exec"
    assert "--sandbox" not in command
    assert "--ignore-user-config" in command and command[-1] == "-"
    config_values = [command[index + 1] for index, item in enumerate(command[:-1]) if item == "--config"]
    assert 'cli_auth_credentials_store="file"' in config_values
    assert 'default_permissions="plotloom_autopilot_delivery_v5"' in config_values
    filesystem = next(value for value in config_values if value.startswith("permissions.plotloom_autopilot_delivery_v5.filesystem="))
    assert 'web_search="disabled"' in config_values
    assert "tools.view_image=false" not in config_values
    assert any(
        command[index:index + 2] == ["--disable", "view_image"]
        for index, item in enumerate(command[:-1])
        if item == "--disable"
    )
    assert '":root"="deny"' in filesystem
    assert '":minimal"="read"' in filesystem
    assert '":tmpdir"="write"' in filesystem
    assert '":slash_tmp"="deny"' in filesystem
    assert f'{json.dumps(str(supervisor.codex_home))}="deny"' in filesystem
    source_root = supervisor.source_root
    outline_resources = (
        source_root / "third_party" / "shuohao-skills" / "skills" / "novel-outline"
    ).resolve()
    node_runtime_root = Path(shutil.which("node")).resolve().parent.parent
    assert f'{json.dumps(str(outline_resources))}="read"' in filesystem
    assert f'{json.dumps(str(node_runtime_root))}="read"' in filesystem
    assert f'{json.dumps(str(source_root / "src" / "plotloom"))}="read"' not in filesystem
    assert f'{json.dumps(str(source_root / "uv.lock"))}="read"' not in filesystem
    assert f'{json.dumps(str(source_root))}=' not in filesystem
    assert "novel-storyboard" not in filesystem
    assert any(
        command[index:index + 2] == ["--disable", "image_generation"]
        for index, item in enumerate(command[:-1])
        if item == "--disable"
    )
    assert status.receipt is not None
    assert status.receipt.session_id == session_id
    assert (job_root / "delivery" / "completion.json").is_file()
    assert status.receipt.text_validation is not None
    assert tuple(step.step_id for step in status.receipt.text_validation.steps) == ("validate", "render")
    assert (job_root / "delivery" / "report.html").read_text(encoding="utf-8") == (
        "<!doctype html><html><body>trusted fake renderer</body></html>\n"
    )
    delivery = exchange.read_delivery(
        request,
        execution_pin,
        executor_backend="codex_exec",
        executor_attempt=status.attempt,
        executor_profile=profile,
        executor_receipt=status.receipt,
        plotloom_code_revision=attempt.plotloom_code_revision,
    )
    assert delivery is not None
    assert delivery.manifest.codex_session_id == session_id



def test_cli_error_diagnostic_cannot_publish_a_success_receipt(supervisor, monkeypatch, tmp_path):
    session_id = uuid4()
    monkeypatch.setenv("PLOTLOOM_TEST_SESSION_ID", str(session_id))
    fake_cli = r'''import json, os, sys
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

sys.stdin.read()
session_id = UUID(os.environ["PLOTLOOM_TEST_SESSION_ID"])
day = date.today()
session_dir = Path(os.environ["CODEX_HOME"]) / "sessions" / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}"
session_dir.mkdir(parents=True)
timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
(session_dir / f"rollout-{timestamp}-{session_id}.jsonl").write_text(
    json.dumps({"type": "session_meta", "payload": {"id": str(session_id)}, "ordinal": 0}) + "\n",
    encoding="utf-8",
)
for event in (
    {"type": "thread.started", "thread_id": str(session_id)},
    {"type": "item.completed", "item": {"id": "err_01", "type": "error", "message": "Ignoring unsupported configuration setting"}},
    {"type": "turn.started"},
    {"type": "turn.completed"},
):
    print(json.dumps(event), flush=True)
'''
    _exchange, _request, _pin, _job_root, attempt, _profile = _prepared_text_job(
        supervisor, tmp_path, fake_cli_source=fake_cli
    )

    status = supervisor.admit(attempt)
    assert status.state in {"spawn_intent", "running"}
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status = supervisor.status(attempt.attempt_id)
        if status.state in {"completed", "failed", "settled", "outcome_unknown"}:
            break
        time.sleep(0.05)

    assert status.state == "failed", status
    assert status.receipt is None
    assert status.attempt.terminal_result == "failure"
    assert status.attempt.process_exit_code == 0
    assert status.attempt.session_id == session_id
