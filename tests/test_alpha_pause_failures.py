"""Paused host facts reach only existing correction/blocking policy after durable ack."""
from contextlib import closing
from hashlib import sha256
from uuid import uuid4

import pytest

from plotloom.alpha_pause import resume_paused_sample
from plotloom.alpha_receipts import collect_native_evidence
from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.creative_handoff_identity import canonical_json
from plotloom.text_correction_contracts import TextContentIssue, TextContentRejection, logical_checkpoint
from tests.alpha_pause_fixtures import sent_pause
from tests.autopilot_controller_fixtures import candidate


def fail_original(storage, host, *, kind):
    attempt = next(iter(host.statuses.values())).attempt
    with closing(storage.projects.open(str(attempt.project_id))) as store:
        request = host.request(store, attempt)
        raw = canonical_json(candidate(store, request))
        job = store.creative_handoff_exchange().root / "jobs" / attempt.job_id
        (job / "delivery/outline.json").write_bytes(raw)
    changes = dict(state="failed", session_id=uuid4(), process_exit_code=0,
        terminal_result="failure", remote_tool_state="not_applicable", evidence_hash="a" * 64)
    if kind == "content":
        changes["content_rejection"] = TextContentRejection(source_attempt_id=attempt.attempt_id,
            run_id=attempt.run_id, stage="outline", job_id=attempt.job_id,
            candidate_hash=sha256(raw).hexdigest(), validation_evidence_hash="b" * 64,
            request_hash=attempt.request_hash, package_hash=attempt.package_hash,
            plan_hash=attempt.validation_plan_hash, profile_hash=attempt.profile_hash,
            source_revision=attempt.plotloom_code_revision,
            issues=(TextContentIssue(code="candidate_content_invalid", field_paths=("$",)),))
    elif kind == "noncontent":
        changes["process_exit_code"] = 1
    else:
        changes = {"state": "outcome_unknown"}
    failed = transition_exec_attempt(attempt, **changes)
    host.pending.discard(str(attempt.attempt_id))
    host.statuses[str(attempt.attempt_id)] = CodexExecHostStatus(state=failed.state, attempt=failed)
    return failed


@pytest.mark.parametrize("kind", ["content", "noncontent", "unknown"])
def test_paused_host_failure_keeps_production_correction_policy_and_original_identity(tmp_path, monkeypatch, kind):
    storage, _, original, prefix, host, run, evidence, pause, request, identity, snapshot = sent_pause(tmp_path, monkeypatch)
    try:
        original_bytes = {p.name: p.read_bytes() for p in pause.iterdir()}
        failed = fail_original(storage, host, kind=kind)
        if kind == "unknown":
            with pytest.raises(ValueError, match="UNKNOWN"):
                resume_paused_sample(prefix, run.project_id, evidence, request, identity)
            assert not (evidence / "resumptions" / str(request.revision) / "ack.json").exists()
            assert host.admissions == 1
            return
        resume_paused_sample(prefix, run.project_id, evidence, request, identity)
        assert (evidence / "resumptions" / str(request.revision) / "ack.json").is_file()
        assert host.admissions == 1
        host.auto_deliver = True
        for _ in range(12):
            view = prefix.step(run.project_id)
            current = logical_checkpoint(view, "outline")
            if view.state == "blocked" or current and current["state"] == "adopted": break
        with closing(storage.projects.open(run.project_id)) as store:
            original_attempt, _ = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id, "outline")
            assert original_attempt == failed
            corrected, _ = store.repository.autopilot.exec_attempt_evidence_for_operation(run.id, "outline:correction:1")
            if kind == "content":
                assert view.state == "running" and current["state"] == "adopted"
                assert host.admissions == 2 and corrected is not None
                assert corrected.attempt_id != failed.attempt_id and corrected.job_id != failed.job_id
                assert original_attempt.content_rejection is not None
                receipt, _ = collect_native_evidence(store, view, snapshot=snapshot,
                    contract_hash="b" * 64, sample_id=evidence.name, duration_ms=200)
                outline = receipt.operations[0]
                assert outline.attempt_count == 2 and outline.accepted and not outline.first_pass
                # No third attempt or manual retry is authorized by resume.
                assert not any(c["operationKey"] == "outline:correction:2" for c in view.checkpoints)
            else:
                assert view.state == "blocked" and host.admissions == 1 and corrected is None
                assert original_attempt.content_rejection is None
        assert {p.name: p.read_bytes() for p in pause.iterdir()} == original_bytes
        assert not host.image_calls
    finally:
        prefix.__exit__()
        original.close()
