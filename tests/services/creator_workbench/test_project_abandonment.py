"""Revocation preserves unknown evidence and serializes exact project writes."""
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest
from codex_exec_supervisor_errors import CodexExecSupervisorError
from codex_exec_supervisor_test_support import _insert_attempt_row, _prepared_text_job

from plotloom.codex_exec_contracts import CodexExecAttempt, transition_exec_attempt
from plotloom.project_abandonment_contracts import AbandonmentPacket


def unknown_project(supervisor, tmp_path):
    _exchange, _request, _pin, job, attempt, _profile = _prepared_text_job(supervisor, tmp_path)
    running = transition_exec_attempt(attempt, state="running", process_id=900001,
        process_group_id=900001, process_birth_identity="retained-original-process")
    unknown = transition_exec_attempt(running, state="outcome_unknown")
    _insert_attempt_row(supervisor, attempt, unknown)
    from plotloom.project_storage.project_home import find_project_home
    home = find_project_home(supervisor.outputs_root, str(attempt.project_id)).path
    with closing(supervisor._connect()) as connection:
        connection.execute("UPDATE exec_attempts SET project_home=?,job_root=?,worker_pid=?,worker_group_id=?,worker_birth_identity=? WHERE attempt_id=?",
            (str(home), str(job), 900002, 900002, "retained-worker", str(attempt.attempt_id)))
        connection.execute("INSERT INTO exec_slot(attempt_id,domain) VALUES (?,?)", (str(attempt.attempt_id), "text"))
    return attempt, unknown, AbandonmentPacket(project_id=str(attempt.project_id), project_home=str(home), attempts=[unknown])


def test_exact_revocation_preserves_unknown_slot_and_survives_reconnect(supervisor, tmp_path, monkeypatch):
    attempt, unknown, packet = unknown_project(supervisor, tmp_path)
    monkeypatch.setattr(supervisor, "_prove_group_absent", lambda *_args: True)
    monkeypatch.setattr(supervisor, "profile", lambda: pytest.fail("old attempt revocation requires no new profile"))
    preview = supervisor.abandonment_preview(packet)
    assert preview.eligible and not preview.revoked
    before = dict(supervisor._row(attempt.attempt_id))
    receipt = supervisor.revoke_project(packet.model_copy(update={"expected_preview_hash": preview.preview_hash}))
    assert receipt.revoked and dict(supervisor._row(attempt.attempt_id)) == before
    assert supervisor.revoke_project(packet.model_copy(update={"expected_preview_hash": preview.preview_hash})) == receipt
    with closing(supervisor._connect()) as connection:
        assert connection.execute("SELECT attempt_id FROM exec_slot").fetchone()[0] == str(attempt.attempt_id)
    monkeypatch.setattr(supervisor, "_namespace_assert_attempt", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(supervisor, "_drain_queue", lambda: pytest.fail("revoked status must not launch unrelated work"))
    assert supervisor.status(attempt.attempt_id).attempt == unknown
    with pytest.raises(CodexExecSupervisorError, match="revoked"):
        supervisor.admit(attempt)
    assert dict(supervisor._row(attempt.attempt_id)) == before


@pytest.mark.parametrize("defect", ["worker", "cli", "validator", "spawn", "foreign", "preview"])
def test_unknown_local_or_foreign_ownership_cannot_revoke(supervisor, tmp_path, monkeypatch, defect):
    attempt, unknown, packet = unknown_project(supervisor, tmp_path)
    monkeypatch.setattr(supervisor, "_prove_group_absent", lambda *_args: defect not in {"worker", "cli", "validator"})
    if defect in {"validator", "spawn"}:
        with closing(supervisor._connect()) as connection:
            connection.execute("INSERT INTO exec_validation_process VALUES (?,?,?,?,?,?,?)",
                (str(attempt.attempt_id), "validate", "spawn_intent" if defect == "spawn" else "running", 900003, 900003, "validator", 1))
    if defect == "foreign":
        packet = packet.model_copy(update={"attempts": [CodexExecAttempt.model_validate(unknown.model_dump(mode="python") | {"run_id": uuid4()})]})
        with pytest.raises(CodexExecSupervisorError, match="identity"):
            supervisor.abandonment_preview(packet)
        return
    preview = supervisor.abandonment_preview(packet)
    with pytest.raises(CodexExecSupervisorError):
        supervisor.revoke_project(packet.model_copy(update={"expected_preview_hash": "0" * 64 if defect == "preview" else preview.preview_hash}))
    with closing(supervisor._connect()) as connection:
        assert not connection.execute("SELECT * FROM exec_project_revocations").fetchall()
        assert connection.execute("SELECT COUNT(*) FROM exec_slot").fetchone()[0] == 1


def test_process_absence_requires_esrch_for_both_group_and_pid(supervisor, monkeypatch):
    def absent(*_args):
        raise ProcessLookupError()
    monkeypatch.setattr("os.killpg", absent)
    monkeypatch.setattr("os.kill", absent)
    assert supervisor._prove_group_absent(900001, 900001, "birth")
    assert not supervisor._prove_group_absent(None, None, None)
    monkeypatch.setattr("os.kill", lambda *_args: None)
    assert not supervisor._prove_group_absent(900001, 900001, "birth")
    def denied(*_args):
        raise PermissionError()
    monkeypatch.setattr("os.killpg", denied)
    assert not supervisor._prove_group_absent(900001, 900001, "birth")


def test_project_admission_fence_does_not_block_other_projects(supervisor, tmp_path, monkeypatch):
    _attempt, _unknown, packet = unknown_project(supervisor, tmp_path)
    monkeypatch.setattr(supervisor, "_prove_group_absent", lambda *_args: True)
    preview = supervisor.abandonment_preview(packet)
    with supervisor._abandonment_fence(packet.project_id):
        with supervisor._abandonment_fence(str(uuid4())):
            pass
        with pytest.raises(CodexExecSupervisorError, match="in progress"):
            supervisor.revoke_project(packet.model_copy(update={"expected_preview_hash": preview.preview_hash}))
    assert not supervisor.abandonment_preview(packet).revoked


def test_manifest_publication_holds_host_write_fence_and_cannot_write_after_revocation(supervisor, tmp_path, monkeypatch):
    import sqlite3
    from types import SimpleNamespace
    attempt, _unknown, packet = unknown_project(supervisor, tmp_path)
    monkeypatch.setattr(supervisor, "_prove_group_absent", lambda *_args: True)
    writes = []
    def publication(_row, _attempt):
        with closing(sqlite3.connect(supervisor.database, timeout=0, isolation_level=None)) as contender, pytest.raises(sqlite3.OperationalError, match="locked"):
            contender.execute("BEGIN IMMEDIATE")
        writes.append(True)
    monkeypatch.setattr(supervisor, "_write_manifest", publication)
    row = dict(supervisor._row(attempt.attempt_id)) | {"manifest_json": "{}"}
    stale_completion = SimpleNamespace(project_id=attempt.project_id, state="completed")
    supervisor._ensure_manifest(row, stale_completion)
    preview = supervisor.abandonment_preview(packet)
    supervisor.revoke_project(packet.model_copy(update={"expected_preview_hash": preview.preview_hash}))
    supervisor._ensure_manifest(row, stale_completion)
    assert writes == [True]
    with pytest.raises(CodexExecSupervisorError, match="revoked"):
        supervisor._copy_image_to_delivery(attempt, Path(row["job_root"]), "late.png", b"late")
    with pytest.raises(CodexExecSupervisorError, match="revoked"):
        supervisor._resolve_job(attempt)
