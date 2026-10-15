"""Synthetic external execution; actual project owner transactions and packages."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from uuid import uuid4

import pytest

from plotloom.autopilot_contracts import OperationScope, RunControlRequest
from plotloom.autopilot_exec_staged import (
    admit_reserved_codex_exec_once,
    observe_existing_codex_exec,
    reserve_prepared_codex_exec,
)
from plotloom.autopilot_text_controller import AutopilotTextController
from plotloom.codex_exec_contracts import CodexExecHostStatus
from plotloom.exceptions import InvalidTransitionError, RevisionConflictError
from tests.autopilot_controller_fixtures import environment

COMMAND = AutopilotTextController.command


@contextmanager
def prepared(tmp_path, monkeypatch):
    storage, registry, service, run, calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        assert service.acquire_controller()
        service.step(run.project_id)
        service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            view = store.repository.autopilot.current(run.project_id)
            checkpoint = next(item for item in view.checkpoints if item["operationKey"] == "outline")
            with COMMAND(store, view, service.claim, OperationScope.EVIDENCE):
                request = store.repository.creative_terminal.run_request(run.project_id, "outline", checkpoint["evidence"]["jobId"])
            paths = store.creative_handoff_exchange().write_package(request,
                checkpoint["evidence"]["executionPin"], executor_backend="codex_exec",
                plotloom_code_revision=view.policy.code_revision)
            kwargs = {"package_path": paths["packagePath"], "command_factory": COMMAND}
            attempt = reserve_prepared_codex_exec(store, registry, view, service.claim,
                checkpoint, domain="text", **kwargs)
            current = store.repository.autopilot.current(run.project_id)
            checkpoint = next(item for item in current.checkpoints if item["operationKey"] == "outline")
            yield storage, registry, service, store, current, checkpoint, attempt, kwargs, calls
    finally:
        service.close()


def test_reserve_only_returns_exact_persisted_uuid_without_spawn(tmp_path, monkeypatch):
    with prepared(tmp_path, monkeypatch) as (_storage, registry, service, store, view, checkpoint, attempt, kwargs, calls):
        retained = store.repository.autopilot.exec_attempt_for_operation(view.id, "outline")
        assert attempt == retained and retained.state == "reserved"
        assert checkpoint["state"] == "prepared"
        assert checkpoint["evidence"]["executorAttemptId"] == str(attempt.attempt_id)
        assert not calls and not registry._codex_exec_test_host.statuses
        assert observe_existing_codex_exec(store, registry, view, service.claim,
            expected_attempt=attempt, command_factory=COMMAND) == (attempt, None)
        with pytest.raises(InvalidTransitionError, match="already"):
            reserve_prepared_codex_exec(store, registry, view, service.claim, checkpoint, domain="text", **kwargs)


def test_competing_strict_consumers_call_host_only_once_and_missing_ack_holds(tmp_path, monkeypatch):
    with prepared(tmp_path, monkeypatch) as (storage, registry, service, _store, view, checkpoint, attempt, kwargs, _calls):
        admitted = []
        def missing(value):
            admitted.append(value.attempt_id)
            return CodexExecHostStatus(state="not_found")
        monkeypatch.setattr(registry, "codex_exec_admit", missing)
        def consume(_index):
            with closing(storage.projects.open(view.project_id)) as store:
                try:
                    return admit_reserved_codex_exec_once(store, registry, view, service.claim, checkpoint,
                        expected_attempt=attempt, expected_run_revision=view.revision, **kwargs)
                except InvalidTransitionError:
                    return "refused"
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(consume, range(2)))
        assert results.count("refused") == 1 and admitted == [attempt.attempt_id]
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
            retained, receipt = observe_existing_codex_exec(store, registry, current, service.claim,
                expected_attempt=attempt, command_factory=COMMAND)
            assert retained.state == "outcome_unknown" and receipt is None
        assert admitted == [attempt.attempt_id]


def test_lost_ack_spends_intent_and_observe_never_resends_or_resumes(tmp_path, monkeypatch):
    with prepared(tmp_path, monkeypatch) as (_storage, registry, service, store, view, checkpoint, attempt, kwargs, _calls):
        admitted = []
        def lost(value):
            admitted.append(value.attempt_id)
            raise OSError("synthetic lost acknowledgment")
        monkeypatch.setattr(registry, "codex_exec_admit", lost)
        monkeypatch.setattr(registry, "codex_exec_resume", lambda _value: pytest.fail("observation resumed"))
        with pytest.raises(OSError, match="acknowledgment"):
            admit_reserved_codex_exec_once(store, registry, view, service.claim, checkpoint,
                expected_attempt=attempt, expected_run_revision=view.revision, **kwargs)
        with pytest.raises(InvalidTransitionError):
            admit_reserved_codex_exec_once(store, registry, view, service.claim, checkpoint,
                expected_attempt=attempt, expected_run_revision=view.revision, **kwargs)
        retained, _receipt = observe_existing_codex_exec(store, registry, view, service.claim,
            expected_attempt=attempt, command_factory=COMMAND)
        assert retained.state == "outcome_unknown" and admitted == [attempt.attempt_id]


def test_strict_spent_snapshot_refuses_with_current_revisions_but_ordinary_intent_is_idempotent(tmp_path, monkeypatch):
    with prepared(tmp_path, monkeypatch) as (_storage, _registry, service, store, view, checkpoint, attempt, _kwargs, calls):
        with COMMAND(store, view, service.claim, OperationScope.TEXT):
            intent = store.repository.autopilot.consume_reserved_exec_attempt_once(attempt,
                expected_run_revision=view.revision, expected_checkpoint_revision=checkpoint["revision"])
        current = store.repository.autopilot.current(view.project_id)
        current_checkpoint = next(item for item in current.checkpoints if item["operationKey"] == "outline")
        with pytest.raises(InvalidTransitionError, match="spent"), COMMAND(store, current, service.claim, OperationScope.TEXT):
            store.repository.autopilot.consume_reserved_exec_attempt_once(attempt,
                expected_run_revision=current.revision, expected_checkpoint_revision=current_checkpoint["revision"])
        with COMMAND(store, current, service.claim, OperationScope.TEXT):
            assert store.repository.autopilot.mark_exec_spawn_intent(intent.attempt_id,
                expected_checkpoint_revision=0) == intent
        assert not calls


@pytest.mark.parametrize("drift", ["identity", "checkpoint", "revision", "pause_resume", "claim", "package"])
def test_strict_admission_rejects_frozen_drift_before_host(tmp_path, monkeypatch, drift):
    with prepared(tmp_path, monkeypatch) as (_storage, registry, service, store, view, checkpoint, attempt, kwargs, calls):
        revision = view.revision
        if drift == "identity":
            attempt = attempt.model_copy(update={"request_hash": "d" * 64})
        elif drift == "checkpoint":
            checkpoint = checkpoint | {"revision": checkpoint["revision"] - 1}
        elif drift == "revision":
            revision -= 1
        elif drift == "pause_resume":
            paused = service.control(view.project_id, RunControlRequest(expected_revision=view.revision, action="pause"))
            service.control(view.project_id, RunControlRequest(expected_revision=paused.revision, action="resume"))
        elif drift == "claim":
            store.repository.autopilot.claim(view.project_id, uuid4().hex)
        else:
            from pathlib import Path
            (Path(kwargs["package_path"]) / "request.json").write_text("{}")
        with pytest.raises((InvalidTransitionError, RevisionConflictError, ValueError)):
            admit_reserved_codex_exec_once(store, registry, view, service.claim, checkpoint,
                expected_attempt=attempt, expected_run_revision=revision, **kwargs)
        assert not calls


@pytest.mark.parametrize("version", ["v4", "v5", "v6", "v7", "v8"])
def test_shared_revision_check_preserves_original_version_condition(tmp_path, monkeypatch, version):
    from types import SimpleNamespace

    from plotloom import autopilot_exec_reservation as owner
    from tests.codex_exec_fixtures import PROFILE
    historical = {
        "v4": ("plotloom_autopilot_delivery_v2", None),
        "v5": ("plotloom_autopilot_delivery_v3", "node_openssl_and_private_zsh_tmp_v1"),
        "v6": ("plotloom_autopilot_delivery_v4", "node_openssl_private_zsh_tmp_and_validator_aliases_v2"),
        "v7": ("plotloom_autopilot_delivery_v5", "node_openssl_private_zsh_tmp_and_checked_python_v3"),
    }
    changes = {"contract_version": "plotloom.codex-exec." + version}
    if version != "v8":
        permission, runtime = historical[version]
        changes |= {"permission_profile": permission, "text_validator_runtime_profile": runtime,
            "max_processes": 1, "max_text_processes": None, "max_image_processes": None, "max_queued_jobs": None}
    profile = PROFILE.model_validate(PROFILE.model_dump(mode="python") | changes)
    view = SimpleNamespace(policy=SimpleNamespace(executor_binding=profile, code_revision=None))
    registry = SimpleNamespace(codex_exec_profile=lambda: profile)
    package = tmp_path / "package"
    package.mkdir()
    monkeypatch.setattr(owner, "frozen_package_snapshot", lambda *_args, **_kwargs: ("a" * 64, b"{}"))
    checkpoint = {"evidence": {"owner": "outline", "subjectId": "fixture", "jobId": "ch_" + "a" * 24, "requestHash": "b" * 64}}
    if version == "v4":
        assert owner.prepared_exec_inputs(registry, view, checkpoint, domain="image", package_path=package)[1] == profile
    else:
        with pytest.raises(InvalidTransitionError, match="source revision"):
            owner.prepared_exec_inputs(registry, view, checkpoint, domain="image", package_path=package)


def test_observe_missing_project_identity_cannot_create_attempt(tmp_path, monkeypatch):
    with prepared(tmp_path, monkeypatch) as (_storage, registry, service, store, view, _checkpoint, attempt, _kwargs, calls):
        with pytest.raises(InvalidTransitionError, match="existing"):
            observe_existing_codex_exec(store, registry, view, service.claim,
                expected_attempt=attempt.model_copy(update={"operation_key": "branches"}), command_factory=COMMAND)
        assert not calls


def test_observe_settles_exact_typed_receipt_without_canonical_adoption(tmp_path, monkeypatch):
    with prepared(tmp_path, monkeypatch) as (_storage, registry, service, store, view, checkpoint, attempt, kwargs, calls):
        admitted, receipt = admit_reserved_codex_exec_once(store, registry, view, service.claim, checkpoint,
            expected_attempt=attempt, expected_run_revision=view.revision, **kwargs)
        assert admitted.state == "running" and receipt is None
        host = registry._codex_exec_test_host
        request = host.request(store, admitted)
        host.complete(store, request, admitted)
        monkeypatch.setattr(registry, "codex_exec_admit", lambda _attempt: pytest.fail("observation admitted"))
        monkeypatch.setattr(registry, "codex_exec_resume", lambda _attempt: pytest.fail("observation resumed"))
        current = store.repository.autopilot.current(view.project_id)
        settled, receipt = observe_existing_codex_exec(store, registry, current, service.claim,
            expected_attempt=attempt, command_factory=COMMAND)
        assert settled.state == "completed" and receipt is not None
        assert receipt.attempt_id == attempt.attempt_id
        latest = store.repository.autopilot.current(view.project_id)
        outline = next(item for item in latest.checkpoints if item["operationKey"] == "outline")
        assert outline["state"] == "sent"
        assert not any(item["operationKey"] == "branches" for item in latest.checkpoints)
        assert calls == [attempt.job_id]
