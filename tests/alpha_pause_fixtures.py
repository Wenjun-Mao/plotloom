"""Provider-free native qualification pause fixtures over the real SQLite controller."""
from contextlib import closing

from plotloom.alpha_campaign import write_private_json
from plotloom.alpha_pause import QualificationResume, database_identity, publish_pause
from plotloom.alpha_receipts import collect_native_evidence
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.autopilot_text_prefix import AutopilotTextPrefix
from tests.autopilot_controller_fixtures import environment


def sent_pause(tmp_path, monkeypatch, *, stage="outline"):
    storage, registry, original, run, _ = environment(tmp_path, monkeypatch, auto_deliver=False, early_references=True)
    prefix = AutopilotTextPrefix(storage, registry)
    prefix.__enter__()
    host = registry._codex_exec_test_host
    if stage != 'outline':
        host.auto_deliver = True
        admit = registry.codex_exec_admit
        def hold_target(attempt):
            if attempt.operation_key == stage:
                host.auto_deliver = False
            return admit(attempt)
        monkeypatch.setattr(registry, 'codex_exec_admit', hold_target)
    for _ in range(40):
        view = prefix.step(run.project_id)
        if any(status.attempt.operation_key == stage for status in host.statuses.values()):
            break
    assert host.admissions == (1 if stage == 'outline' else 6)
    view = prefix.service.control(run.project_id,
        RunControlRequest(action="pause", expected_revision=view.revision), expected_run_id=run.id)
    evidence = tmp_path / "evidence/story-01-repeat-01"
    evidence.mkdir(parents=True, mode=0o700)
    snapshot = {"commit": view.policy.code_revision, "profileHash": view.policy.executor_binding.profile_hash}
    with closing(storage.projects.open(run.project_id)) as store:
        receipt, bindings = collect_native_evidence(store, view, snapshot=snapshot,
            contract_hash="b" * 64, sample_id=evidence.name, duration_ms=125)
        identity = snapshot | {"contractHash": "b" * 64, "namespaceBinding": "controlled-fixture-not-native-proof", "databases": {
            "project": database_identity(store.database_path), "application": database_identity(storage.application.path)}}
    write_private_json(evidence / "runtime.json", identity)
    path, digest = publish_pause(evidence, receipt=receipt.model_dump(mode="json", by_alias=True),
        bindings=bindings, runtime_identity=identity, elapsed_ms=125)
    request = QualificationResume(project_id=run.project_id, run_id=run.id,
        revision=view.revision, snapshot_hash=digest)
    return storage, registry, original, prefix, host, run, evidence, path, request, identity, snapshot


def complete_original(storage, host):
    attempt = next(iter(host.statuses.values())).attempt
    with closing(storage.projects.open(str(attempt.project_id))) as store:
        host.complete(store, host.request(store, attempt), attempt)
    return attempt


