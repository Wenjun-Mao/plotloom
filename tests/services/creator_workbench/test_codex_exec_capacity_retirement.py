"""Exact local retirement preserves remote uncertainty and all original evidence."""
import json
from contextlib import closing
from types import SimpleNamespace
from uuid import uuid4

import pytest
from codex_exec_supervisor import CodexExecSupervisor
from codex_exec_supervisor_errors import CodexExecSupervisorError
from codex_exec_supervisor_test_support import _attempt, _insert_attempt_row

from plotloom.codex_exec_capacity_contracts import CapacityRetirementRequest
from plotloom.codex_exec_contracts import CodexExecAttempt, transition_exec_attempt
from tests.services.creator_workbench.test_codex_exec_supervisor_pool import _job


def revoked_unknown(supervisor, monkeypatch):
    original = CodexExecAttempt.model_validate(_attempt().model_dump(mode="python") | {
        "domain": "image", "reserved_image_outputs": 1, "image_budget_state": "reserved",
        "job_id": "ij_" + uuid4().hex[:24]})
    current = transition_exec_attempt(transition_exec_attempt(original, state="running", process_id=900001,
        process_group_id=900001, process_birth_identity="original-cli"), state="outcome_unknown")
    _insert_attempt_row(supervisor, original, current)
    home = supervisor.outputs_root / ("deleted-qa__" + str(original.project_id))
    with closing(supervisor._connect()) as connection:
        connection.execute("UPDATE exec_attempts SET project_home=?,worker_pid=900002,worker_group_id=900002,worker_birth_identity='original-worker' WHERE attempt_id=?",
            (str(home), str(original.attempt_id)))
        connection.execute("INSERT INTO exec_slot VALUES (?, 'image')", (str(original.attempt_id),))
        connection.execute("INSERT INTO exec_queue(attempt_id,enabled) VALUES (?,0)", (str(original.attempt_id),))
        connection.execute("INSERT INTO exec_project_revocations VALUES (?,?,?,?)",
            (str(original.project_id), str(home), "f" * 64, 1))
    monkeypatch.setattr(supervisor, "_prove_group_absent", lambda *_args: True)
    return original, current, CapacityRetirementRequest(project_id=original.project_id, attempt_id=original.attempt_id)


def consent(supervisor, request):
    preview = supervisor.capacity_retirement_preview(request)
    assert preview.eligible
    return request.model_copy(update={"expected_preview_hash": preview.preview_hash, "reason": "Explicit local-only recovery; remote outcome and spending remain UNKNOWN."})


def ledger(supervisor):
    with closing(supervisor._connect()) as connection:
        return tuple(connection.iterdump())


def test_preview_is_read_only_and_atomic_retirement_lost_ack_restart_preserve_unknown(supervisor, monkeypatch):
    original, unknown, request = revoked_unknown(supervisor, monkeypatch)
    before = ledger(supervisor)
    request = consent(supervisor, request)
    assert ledger(supervisor) == before
    retained = dict(supervisor._row(original.attempt_id))
    for method in ("_drain_queue", "_start_worker"):
        monkeypatch.setattr(supervisor, method, lambda *_args: pytest.fail("retirement must never dispatch"))
    result = supervisor.retire_local_capacity(request)
    assert result.already_retired and result.receipt.remote_outcome == "preserved_unknown"
    assert result.local_capacity_state == "retired" and result.image_budget_state == "reserved"
    assert result.reserved_image_outputs == 1 and result.spending_reservations == "preserved"
    assert result.receipt.retained_facts["attempt"] == retained
    assert dict(supervisor._row(original.attempt_id)) == retained
    assert supervisor._load(supervisor._row(original.attempt_id)).attempt == unknown
    assert unknown.image_budget_state == "reserved" and unknown.reserved_image_outputs == 1
    committed = ledger(supervisor)
    assert supervisor.retire_local_capacity(request) == result and ledger(supervisor) == committed
    reopened = CodexExecSupervisor(supervisor.executable, source_root=supervisor.source_root,
        outputs_root=supervisor.outputs_root, private_root=supervisor.private_root)
    assert reopened.retire_local_capacity(request) == result
    assert ledger(supervisor) == committed
    with closing(supervisor._connect()) as connection:
        assert not connection.execute("SELECT * FROM exec_slot").fetchall()
        assert connection.execute("SELECT enabled FROM exec_queue WHERE attempt_id=?", (str(original.attempt_id),)).fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM exec_capacity_retirements").fetchone()[0] == 1


@pytest.mark.parametrize("defect", ["worker", "cli", "validator", "validator_spawn", "missing_worker", "missing_cli", "worker_group", "enabled_queue", "slot", "home", "symlink", "home_permission"])
def test_ambiguous_ownership_or_deleted_home_never_releases_a_slot(supervisor, monkeypatch, defect):
    original, current, request = revoked_unknown(supervisor, monkeypatch)
    with closing(supervisor._connect()) as connection:
        if defect in {"validator", "validator_spawn"}:
            connection.execute("INSERT INTO exec_validation_process VALUES (?,?,?,?,?,?,?)",
                (str(original.attempt_id), "inspect", "spawn_intent" if defect == "validator_spawn" else "running", 900003, 900003, "validator", 1))
        if defect == "missing_worker": connection.execute("UPDATE exec_attempts SET worker_birth_identity=NULL")
        if defect == "worker_group": connection.execute("UPDATE exec_attempts SET worker_group_id=900009")
        if defect == "missing_cli":
            raw = current.model_dump(mode="json", by_alias=True) | {"processId": None, "processGroupId": None, "processBirthIdentity": None}
            connection.execute("UPDATE exec_attempts SET status_json=?", (json.dumps(raw),))
        if defect == "enabled_queue": connection.execute("UPDATE exec_queue SET enabled=1")
        if defect == "slot": connection.execute("UPDATE exec_slot SET domain='text'")
    home = supervisor.outputs_root / ("deleted-qa__" + str(original.project_id))
    if defect == "home": home.mkdir()
    if defect == "symlink": home.symlink_to(supervisor.outputs_root / "missing-target")
    if defect == "home_permission": monkeypatch.setattr(supervisor, "_retired_home_absent", lambda _home: False)
    if defect in {"worker", "cli", "validator"}:
        denied = {"worker": 900002, "cli": 900001, "validator": 900003}[defect]
        monkeypatch.setattr(supervisor, "_prove_group_absent", lambda pid, *_args: pid != denied)
    preview = supervisor.capacity_retirement_preview(request)
    assert not preview.eligible and preview.blockers
    before = ledger(supervisor)
    with pytest.raises(CodexExecSupervisorError):
        supervisor.retire_local_capacity(request.model_copy(update={"expected_preview_hash": preview.preview_hash, "reason": "Do not bypass ambiguity"}))
    assert ledger(supervisor) == before


@pytest.mark.parametrize("change", ["status", "revocation", "project", "no_revocation", "preview", "reason"])
def test_exact_consent_and_all_retained_facts_are_rechecked(supervisor, monkeypatch, change):
    _original, _current, request = revoked_unknown(supervisor, monkeypatch)
    request = consent(supervisor, request)
    with closing(supervisor._connect()) as connection:
        if change == "status": connection.execute("UPDATE exec_attempts SET updated_at=updated_at+1")
        elif change == "revocation": connection.execute("UPDATE exec_project_revocations SET revoked_at=2")
        elif change == "no_revocation": connection.execute("DELETE FROM exec_project_revocations")
    if change == "project": request = request.model_copy(update={"project_id": uuid4()})
    if change == "preview": request = request.model_copy(update={"expected_preview_hash": "0" * 64})
    if change == "reason": request = request.model_copy(update={"reason": ""})
    before = ledger(supervisor)
    with pytest.raises(CodexExecSupervisorError): supervisor.retire_local_capacity(request)
    assert ledger(supervisor) == before


def test_atomic_failure_rolls_back_receipt_and_slot_and_publication_fence_excludes_races(supervisor, monkeypatch):
    _original, _current, request = revoked_unknown(supervisor, monkeypatch)
    request = consent(supervisor, request)
    before = ledger(supervisor)
    with supervisor._abandonment_fence(request.project_id), pytest.raises(CodexExecSupervisorError, match="in progress"):
        supervisor.retire_local_capacity(request)
    def fail_after_insert(*_args): raise RuntimeError("injected slot mutation failure")
    monkeypatch.setattr(supervisor, "_retire_exact_slot_in_transaction", fail_after_insert)
    with pytest.raises(RuntimeError, match="injected"): supervisor.retire_local_capacity(request)
    assert ledger(supervisor) == before


def test_restored_slot_or_changed_reason_cannot_reuse_retirement_receipt(supervisor, monkeypatch):
    original, _current, request = revoked_unknown(supervisor, monkeypatch)
    request = consent(supervisor, request)
    supervisor.retire_local_capacity(request)
    with pytest.raises(CodexExecSupervisorError, match="reason"):
        supervisor.retire_local_capacity(request.model_copy(update={"reason": "Different operator decision"}))
    with closing(supervisor._connect()) as connection:
        connection.execute("INSERT INTO exec_slot VALUES (?, 'image')", (str(original.attempt_id),))
    before = ledger(supervisor)
    with pytest.raises(CodexExecSupervisorError, match="restored"): supervisor.retire_local_capacity(request)
    assert ledger(supervisor) == before


def test_existing_scheduler_uses_only_retired_local_capacity_and_old_unknown_cannot_resume_or_publish(supervisor, monkeypatch):
    original, unknown, request = revoked_unknown(supervisor, monkeypatch)
    revoked_unknown(supervisor, monkeypatch)
    waiting = _job(supervisor, domain="image")
    launched = []
    monkeypatch.setattr(supervisor, "_start_worker", launched.append)
    assert supervisor._drain_queue() is None
    supervisor.retire_local_capacity(consent(supervisor, request))
    assert not launched
    assert supervisor._drain_queue() == waiting.attempt_id and launched == [waiting.attempt_id]
    with closing(supervisor._connect()) as connection:
        assert supervisor._capacity_counts(connection) == {"text": 0, "image": 2}
    assert supervisor.pool_limits.max_image_processes == 2 and supervisor.pool_limits.max_processes == 4
    with pytest.raises(CodexExecSupervisorError, match="revoked"): supervisor.resume(unknown)
    with pytest.raises(CodexExecSupervisorError, match="revoked"): supervisor.admit(original)
    writes = []
    monkeypatch.setattr(supervisor, "_write_manifest", lambda *_args: writes.append(True))
    supervisor._ensure_manifest(dict(supervisor._row(original.attempt_id)) | {"manifest_json": "{}"},
        SimpleNamespace(project_id=original.project_id, state="completed"))
    assert not writes and supervisor.status(original.attempt_id).attempt == unknown


def test_capacity_readiness_is_read_only_and_distinguishes_retired_remote_unknown(supervisor, monkeypatch):
    _original, _unknown, request = revoked_unknown(supervisor, monkeypatch)
    revoked_unknown(supervisor, monkeypatch)
    before = ledger(supervisor)
    view = supervisor.local_capacity_readiness()
    assert ledger(supervisor) == before
    assert view.held_image == 2 and view.image_lane_blocked and view.operator_action == "exec-capacity-retirement-preview"
    supervisor.retire_local_capacity(consent(supervisor, request))
    view = supervisor.local_capacity_readiness()
    assert view.held_image == 1 and not view.image_lane_blocked and view.retired_unknown_image_holds == 1
    assert view.remote_uncertainty_and_reservations == "preserved"


@pytest.mark.parametrize("case", ["unrevoked_unknown", "mixed", "queued", "running"])
def test_ordinary_busy_or_unknown_or_queued_work_does_not_trigger_historical_lane_blocker(supervisor, monkeypatch, case):
    if case == "mixed": revoked_unknown(supervisor, monkeypatch)
    jobs = [_job(supervisor, domain="image", state="queued" if case == "queued" else "outcome_unknown")]
    if case != "mixed": jobs.append(_job(supervisor, domain="image", state="queued" if case == "queued" else "outcome_unknown"))
    if case == "running":
        with closing(supervisor._connect()) as connection:
            for index, job in enumerate(jobs):
                running = transition_exec_attempt(job, state="running", process_id=900010 + index,
                    process_group_id=900010 + index, process_birth_identity="running-owner")
                connection.execute("UPDATE exec_attempts SET status_json=? WHERE attempt_id=?",
                    (running.model_dump_json(by_alias=True), str(job.attempt_id)))
    before = ledger(supervisor)
    view = supervisor.local_capacity_readiness()
    assert not view.image_lane_blocked and view.operator_action is None and ledger(supervisor) == before


def test_capacity_readiness_uses_actual_persisted_limits_not_two(supervisor, monkeypatch):
    revoked_unknown(supervisor, monkeypatch)
    limits = supervisor.pool_limits.model_copy(update={"max_image_processes": 1})
    with closing(supervisor._connect()) as connection:
        connection.execute("UPDATE exec_pool_configuration SET limits_json=?", (limits.model_dump_json(by_alias=True),))
    reopened = CodexExecSupervisor(supervisor.executable, source_root=supervisor.source_root,
        outputs_root=supervisor.outputs_root, private_root=supervisor.private_root)
    view = reopened.local_capacity_readiness()
    assert view.limits.max_image_processes == 1 and view.image_lane_blocked


@pytest.mark.parametrize("historical_blocked", [True, False])
def test_fresh_auto_material_preflight_blocks_only_nonprogressing_history_before_any_text_dispatch(
    supervisor, tmp_path, monkeypatch, historical_blocked,
):
    from plotloom.autopilot_contracts import LaunchRequest
    from plotloom.codex_exec_contracts import CodexExecReadiness
    from plotloom.exceptions import InvalidTransitionError
    from plotloom.project_storage import ProjectFolderStorage
    from tests.autopilot_controller_fixtures import default_brief, runtime
    if historical_blocked:
        revoked_unknown(supervisor, monkeypatch)
        revoked_unknown(supervisor, monkeypatch)
    else:
        _job(supervisor, domain="image", state="outcome_unknown")
        _job(supervisor, domain="image", state="outcome_unknown")
    storage = ProjectFolderStorage(outputs_root=tmp_path / "fresh-outputs", application_data_root=tmp_path / "application")
    with closing(storage.projects.create(default_brief())) as store: project = store.manifest.project_id
    registry, service, host = runtime(storage, monkeypatch, auto_deliver=False)
    monkeypatch.setattr(registry, "codex_exec_readiness", lambda: CodexExecReadiness(state="ready", local_capacity=supervisor.local_capacity_readiness()))
    request = LaunchRequest(expected_brief_revision=1, render_style="realistic", art_render_style="realistic")
    try:
        if historical_blocked:
            with pytest.raises(InvalidTransitionError, match="不会先发送文字"):
                service.launch(project, request)
            with closing(storage.projects.open(project)) as store:
                assert store.repository.autopilot.current(project) is None
        else:
            assert service.launch(project, request).state == "running"
        assert not host.calls
    finally:
        service.close()


def test_positive_validator_absence_is_recorded_without_deleting_its_original_evidence(supervisor, monkeypatch):
    original, _unknown, request = revoked_unknown(supervisor, monkeypatch)
    with closing(supervisor._connect()) as connection:
        connection.execute("INSERT INTO exec_validation_process VALUES (?, 'inspect', 'running', 900003,900003,'validator',1)", (str(original.attempt_id),))
        before = tuple(connection.execute("SELECT * FROM exec_validation_process").fetchone())
    result = supervisor.retire_local_capacity(consent(supervisor, request))
    assert any(proof["role"] == "validator" and proof["pidAndWholeGroupAbsent"] for proof in result.receipt.absence_proofs)
    with closing(supervisor._connect()) as connection:
        assert tuple(connection.execute("SELECT * FROM exec_validation_process").fetchone()) == before


def test_process_absence_is_rechecked_at_mutation_not_just_preview(supervisor, monkeypatch):
    _original, _unknown, request = revoked_unknown(supervisor, monkeypatch)
    request = consent(supervisor, request)
    calls = []
    def changes_before_mutation(*_args):
        calls.append(True)
        return len(calls) <= 2
    monkeypatch.setattr(supervisor, "_prove_group_absent", changes_before_mutation)
    before = ledger(supervisor)
    with pytest.raises(CodexExecSupervisorError, match="positively absent"):
        supervisor.retire_local_capacity(request)
    assert ledger(supervisor) == before and len(calls) == 4
