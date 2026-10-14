"""Process lifecycle and exact-evidence tests for the Mac supervisor."""
import json
import os
import signal
import subprocess
import time
from contextlib import closing
from datetime import date, datetime
from pathlib import Path
from threading import Event, Thread
from uuid import uuid4

from codex_exec_supervisor import CodexExecSupervisor
from codex_exec_supervisor_process import CodexExecSupervisorProcessMixin
from codex_exec_supervisor_test_support import _attempt, _prepared_text_job


def test_pre_admission_cancel_is_durable_and_prevents_a_later_spawn(supervisor):
    attempt = _attempt()

    cancelled = supervisor.cancel(attempt)

    assert cancelled.state == "settled"
    assert cancelled.attempt.terminal_result == "not_started"
    assert cancelled.attempt.process_id is None
    assert supervisor.admit(attempt) == cancelled
    assert not supervisor._workers


def test_unrecorded_running_attempt_is_retained_as_unknown(supervisor):
    attempt = _attempt("running")

    cancelled = supervisor.cancel(attempt)

    assert cancelled.state == "outcome_unknown"
    assert cancelled.attempt.process_id == attempt.process_id
    assert supervisor.status(attempt.attempt_id) == cancelled
    assert not supervisor._workers


def test_worker_environment_does_not_inherit_credentials(monkeypatch, supervisor):
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    monkeypatch.setenv("PLOTLOOM_CREATOR_WORKBENCH_TOKEN", "bridge-secret")
    monkeypatch.setenv("PLOTLOOM_DATABASE_PASSWORD", "database-secret")

    environment = supervisor._worker_environment()

    assert not {"OPENAI_API_KEY", "PLOTLOOM_CREATOR_WORKBENCH_TOKEN", "PLOTLOOM_DATABASE_PASSWORD"} & environment.keys()
    assert environment["PYTHONUNBUFFERED"] == "1"


def test_admission_persists_exact_spawn_intent_before_starting_private_worker(supervisor, tmp_path):
    _exchange, _request, _pin, _job_root, attempt, _profile = _prepared_text_job(
        supervisor, tmp_path, fake_cli_source="import sys, time\nsys.stdin.read()\ntime.sleep(30)\n"
    )
    try:
        status = supervisor.admit(attempt)
        assert status.state in {"spawn_intent", "running"}
        assert supervisor._row(attempt.attempt_id)["attempt_json"] == attempt.model_dump_json(by_alias=True)
        assert supervisor._row(attempt.attempt_id)["private_dir"].endswith(str(attempt.attempt_id))
        row = supervisor._row(attempt.attempt_id)
        assert row["worker_pid"] is not None
        assert supervisor._owns_worker(row)
    finally:
        current = supervisor.status(attempt.attempt_id)
        if current.attempt is not None and current.state in {"running", "spawn_intent"}:
            supervisor.cancel(current.attempt)
        worker = supervisor._workers.get(str(attempt.attempt_id))
        if worker is not None:
            worker.wait(timeout=5)


def test_fake_cli_process_publishes_exact_terminal_receipt_and_delivery(supervisor, monkeypatch, tmp_path):
    session_id = uuid4()
    monkeypatch.setenv(
        "PLOTLOOM_TEST_CANDIDATE_JSON",
        json.dumps({"source": "The Ferryman", "params": {"episodes": 1}, "episodes": []}),
    )
    monkeypatch.setenv("PLOTLOOM_TEST_SESSION_ID", str(session_id))
    fake_cli = r'''#!/usr/bin/env python3
import json, os, sys, time
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

sys.stdin.read()
time.sleep(1)
delivery = Path.cwd()
(delivery / "outline.json").write_text(os.environ["PLOTLOOM_TEST_CANDIDATE_JSON"], encoding="utf-8")
(delivery / "report.html").write_text("<!doctype html><html><body>fake CLI report</body></html>", encoding="utf-8")
session_id = UUID(os.environ["PLOTLOOM_TEST_SESSION_ID"])
day = date.today()
session_dir = Path(os.environ["CODEX_HOME"]) / "sessions" / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}"
session_dir.mkdir(parents=True)
timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
(session_dir / f"rollout-{timestamp}-{session_id}.jsonl").write_text(
    json.dumps({"type": "session_meta", "payload": {"id": str(session_id)}}) + "\n",
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
    assert status.receipt is not None
    assert status.receipt.session_id == session_id
    assert (job_root / "delivery" / "completion.json").is_file()
    delivery = exchange.read_delivery(
        request,
        execution_pin,
        executor_backend="codex_exec",
        executor_attempt=status.attempt,
        executor_profile=profile,
        executor_receipt=status.receipt,
    )
    assert delivery is not None
    assert delivery.manifest.codex_session_id == session_id


def test_cross_process_cancel_serializes_with_cli_spawn_boundary(supervisor, monkeypatch, tmp_path):
    import codex_exec_supervisor_process as process_module

    _exchange, _request, _pin, job_root, attempt, profile = _prepared_text_job(
        supervisor, tmp_path, fake_cli_source="import sys\nsys.stdin.read()\n"
    )
    monkeypatch.setattr(supervisor, "_start_worker", lambda _attempt_id: None)
    assert supervisor.admit(attempt).state == "spawn_intent"
    private_dir = Path(supervisor._row(attempt.attempt_id)["private_dir"])
    monkeypatch.setattr(supervisor, "_process_identity", lambda pid: (pid, "fixture-birth"))
    assert supervisor._register_worker(attempt.attempt_id)
    package_request = json.loads((job_root / "package" / "request.json").read_text())

    session_id = uuid4()
    process_id = 887766
    popen_entered = Event()
    allow_spawn_commit = Event()
    cancel_entered = Event()
    cancel_result = []
    worker_errors = []

    class FakeStdin:
        def write(self, content):
            return len(content)

        def close(self):
            pass

    class FakeProcess:
        pid = process_id
        stdin = FakeStdin()
        returncode = None

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            if self.returncode is None:
                raise subprocess.TimeoutExpired("fake-codex", timeout)
            return self.returncode

    process = FakeProcess()

    def fake_popen(_command, **kwargs):
        popen_entered.set()
        assert allow_spawn_commit.wait(timeout=5)
        now = datetime.now()
        codex_home = Path(kwargs["env"]["CODEX_HOME"])
        session_dir = codex_home / "sessions" / f"{date.today().year:04d}" / f"{date.today().month:02d}" / f"{date.today().day:02d}"
        session_dir.mkdir(parents=True)
        rollout = session_dir / f"rollout-{now.strftime('%Y-%m-%dT%H-%M-%S')}-{session_id}.jsonl"
        rollout.write_text(
            json.dumps({"type": "session_meta", "payload": {"id": str(session_id)}}) + "\n",
            encoding="utf-8",
        )
        for event in (
            {"type": "thread.started", "thread_id": str(session_id)},
            {"type": "turn.started"},
            {"type": "turn.completed"},
        ):
            kwargs["stdout"].write((json.dumps(event) + "\n").encode())
        kwargs["stdout"].flush()
        return process

    def fake_killpg(group_id, signal_number):
        assert group_id == process_id
        if signal_number == 0:
            if process.returncode is not None:
                raise ProcessLookupError(group_id)
        elif signal_number in {signal.SIGTERM, signal.SIGKILL}:
            process.returncode = -signal_number

    monkeypatch.setattr(process_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(process_module.os, "killpg", fake_killpg)
    bridge = CodexExecSupervisor(
        supervisor.executable,
        source_root=supervisor.source_root,
        outputs_root=supervisor.outputs_root,
        private_root=supervisor.private_root,
    )
    monkeypatch.setattr(bridge, "_process_identity", lambda pid: (pid, "fixture-birth"))

    def run_worker():
        try:
            supervisor._execute(attempt, profile, package_request, job_root, private_dir)
        except BaseException as error:
            worker_errors.append(error)

    def cancel_from_bridge():
        cancel_entered.set()
        cancel_result.append(bridge.cancel(attempt))

    worker_thread = Thread(target=run_worker)
    worker_thread.start()
    assert popen_entered.wait(timeout=5)
    cancel_thread = Thread(target=cancel_from_bridge)
    cancel_thread.start()
    assert cancel_entered.wait(timeout=5)
    time.sleep(0.05)
    assert not cancel_result
    allow_spawn_commit.set()
    worker_thread.join(timeout=5)
    cancel_thread.join(timeout=5)

    assert not worker_thread.is_alive()
    assert not cancel_thread.is_alive()
    assert not worker_errors
    assert cancel_result[0].state in {"cancel_requested", "failed"}
    assert cancel_result[0].attempt.process_id == process_id
    current = supervisor.status(attempt.attempt_id)
    assert current.state == "failed", current
    assert current.attempt.terminal_result == "failure"
    assert current.attempt.process_id == process_id
    assert current.receipt is None


def test_broken_pipe_does_not_trust_output_while_a_descendant_remains(supervisor, monkeypatch, tmp_path):
    session_id = uuid4()
    monkeypatch.setenv(
        "PLOTLOOM_TEST_CANDIDATE_JSON",
        json.dumps({"source": "The Ferryman", "params": {"episodes": 1}, "episodes": []}),
    )
    monkeypatch.setenv("PLOTLOOM_TEST_SESSION_ID", str(session_id))
    fake_cli = r'''import json, os, subprocess, sys, time
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

os.close(0)
subprocess.Popen(["/bin/sleep", "30"])
delivery = Path.cwd()
(delivery / "outline.json").write_text(os.environ["PLOTLOOM_TEST_CANDIDATE_JSON"], encoding="utf-8")
(delivery / "report.html").write_text("<!doctype html><html><body>fake CLI report</body></html>", encoding="utf-8")
session_id = UUID(os.environ["PLOTLOOM_TEST_SESSION_ID"])
day = date.today()
session_dir = Path(os.environ["CODEX_HOME"]) / "sessions" / f"{day.year:04d}" / f"{day.month:02d}" / f"{day.day:02d}"
session_dir.mkdir(parents=True)
timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
(session_dir / f"rollout-{timestamp}-{session_id}.jsonl").write_text(
    json.dumps({"type": "session_meta", "payload": {"id": str(session_id)}}) + "\n",
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
    _exchange, _request, _execution_pin, job_root, attempt, _profile = _prepared_text_job(
        supervisor, tmp_path, fake_cli_source=fake_cli
    )

    group_id = None
    try:
        status = supervisor.admit(attempt)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            status = supervisor.status(attempt.attempt_id)
            if status.attempt is not None:
                group_id = status.attempt.process_group_id
            if status.state in {"completed", "failed", "settled", "outcome_unknown"}:
                break
            time.sleep(0.05)

        assert status.state == "outcome_unknown", status
        assert status.receipt is None
        assert not (job_root / "delivery" / "completion.json").exists()
        assert supervisor._row(attempt.attempt_id)["attempt_id"] == str(attempt.attempt_id)
        with closing(supervisor._connect()) as connection:
            assert connection.execute(
                "SELECT attempt_id FROM exec_slot WHERE slot_id=1"
            ).fetchone()[0] == str(attempt.attempt_id)
    finally:
        if group_id is not None:
            try:
                os.killpg(group_id, signal.SIGTERM)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + 2
        while (group_id and CodexExecSupervisorProcessMixin._process_group_exists(group_id)
               and time.monotonic() < deadline):
            time.sleep(0.05)


def test_broken_pipe_wait_obeys_runtime_watchdog_and_retains_unknown(supervisor, monkeypatch, tmp_path):
    import codex_exec_supervisor_process as process_module

    _exchange, _request, _pin, job_root, attempt, profile = _prepared_text_job(
        supervisor, tmp_path, fake_cli_source="import sys\nsys.stdin.read()\n"
    )
    monkeypatch.setattr(supervisor, "_start_worker", lambda _attempt_id: None)
    monkeypatch.setattr(supervisor, "_process_identity", lambda pid: (pid, "fixture-worker" if pid == os.getpid() else "fixture-birth"))
    status = supervisor.admit(attempt)
    assert supervisor._register_worker(attempt.attempt_id)
    package_request = json.loads((job_root / "package" / "request.json").read_text())
    private_dir = Path(supervisor._row(attempt.attempt_id)["private_dir"])
    profile = profile.model_copy(update={"max_runtime_seconds": 0})

    class BrokenPipeStdin:
        def write(self, _payload):
            raise BrokenPipeError

        def close(self):
            pass

    class StillRunningProcess:
        pid = 43212
        stdin = BrokenPipeStdin()
        returncode = None

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            if self.returncode is None:
                raise subprocess.TimeoutExpired("fake-codex", timeout)
            return self.returncode

    process = StillRunningProcess()
    signals = []

    def fake_killpg(group_id, signal_number):
        assert group_id == process.pid
        signals.append(signal_number)
        if signal_number == signal.SIGKILL:
            process.returncode = -signal_number
        elif signal_number == 0 and process.returncode is not None:
            raise ProcessLookupError(group_id)

    monotonic = [0.0]

    def advance_clock():
        monotonic[0] += 4.0
        return monotonic[0]

    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *_args, **_kwargs: process)
    monkeypatch.setattr(process_module.os, "killpg", fake_killpg)
    monkeypatch.setattr(process_module.time, "monotonic", advance_clock)
    monkeypatch.setattr(process_module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(supervisor, "_wait_for_process_group_exit", lambda _group_id: True)

    supervisor._execute(attempt, profile, package_request, job_root, private_dir)

    current = supervisor.status(attempt.attempt_id)
    assert status.state == "spawn_intent"
    assert current.state == "outcome_unknown"
    assert signal.SIGTERM in signals
    assert signal.SIGKILL in signals
    assert current.receipt is None
    assert not (job_root / "delivery" / "completion.json").exists()


def test_exited_leader_does_not_hide_a_live_process_group_descendant():
    process = subprocess.Popen(
        ["/bin/sh", "-c", "sleep 30 >/dev/null 2>&1 &"],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    group_id = process.pid
    try:
        process.wait(timeout=2)
        assert CodexExecSupervisorProcessMixin._process_group_exists(group_id)
    finally:
        try:
            os.killpg(group_id, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + 2
        while CodexExecSupervisorProcessMixin._process_group_exists(group_id) and time.monotonic() < deadline:
            time.sleep(0.05)
