"""Finite lifetime capacity across real continuation transactions, fake host facts."""
from contextlib import closing
from hashlib import sha256
from uuid import uuid4

from plotloom.autopilot_contracts import ContinueRequest, RunControlRequest
from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.creative_handoff_exchange import canonical_json
from plotloom.text_correction_contracts import TextContentIssue, TextContentRejection
from tests.autopilot_controller_fixtures import candidate, environment


def test_typed_rejection_at_finite_lifetime_job_cap_creates_no_corrective_identity(tmp_path, monkeypatch):
    storage, registry, service, run, calls = environment(tmp_path, monkeypatch, auto_deliver=False, limits={"max_jobs": 9})
    host = registry._codex_exec_test_host
    try:
        assert service.acquire_controller()
        for index in range(9):
            for _ in range(3):
                service.step(run.project_id)
                with closing(storage.projects.open(run.project_id)) as store:
                    attempt = store.repository.autopilot.exec_attempt_for_operation(run.id, "outline")
                if attempt is not None and attempt.state == "running":
                    break
            assert attempt is not None and attempt.state == "running"
            with closing(storage.projects.open(run.project_id)) as store:
                request = host.request(store, attempt)
                raw = canonical_json(candidate(store, request))
                (store.creative_handoff_exchange().root / "jobs" / attempt.job_id / "delivery/outline.json").write_bytes(raw)
            proof = TextContentRejection(source_attempt_id=attempt.attempt_id, run_id=attempt.run_id,
                stage="outline", job_id=attempt.job_id, candidate_hash=sha256(raw).hexdigest(),
                validation_evidence_hash="b" * 64, request_hash=attempt.request_hash,
                package_hash=attempt.package_hash, plan_hash=attempt.validation_plan_hash,
                profile_hash=attempt.profile_hash, source_revision=attempt.plotloom_code_revision,
                issues=(TextContentIssue(code="candidate_content_invalid", field_paths=("$",)),))
            failed = transition_exec_attempt(attempt, state="failed", session_id=uuid4(),
                process_exit_code=0, terminal_result="failure",
                remote_tool_state="not_applicable", evidence_hash="a" * 64, content_rejection=proof)
            host.pending.discard(str(attempt.attempt_id))
            host.statuses[str(attempt.attempt_id)] = CodexExecHostStatus(state="failed", attempt=failed)
            if index < 8:
                # Receipt-only pause/cancel preserves exact closure and prevents
                # the prior run from authorizing a correction before continuation.
                with closing(storage.projects.open(run.project_id)) as store:
                    revision = store.repository.autopilot.current(run.project_id).revision
                service.control(run.project_id, RunControlRequest(expected_revision=revision, action="pause"))
            service.step(run.project_id)
            with closing(storage.projects.open(run.project_id)) as store:
                view = store.repository.autopilot.current(run.project_id)
                assert view.state == ("blocked" if index == 8 else "paused") and view.lifetime_jobs == index + 1
                if index == 8:
                    assert view.policy.max_jobs == 9
                    assert store.repository.autopilot.exec_attempt_for_operation(run.id, "outline:correction:1") is None
                    assert not any(c["operationKey"] == "outline:correction:1" for c in view.checkpoints)
                    retained = store.repository.autopilot.exec_attempt_for_operation(run.id, "outline")
                    assert retained == failed and retained.content_rejection == proof
                    assert any(c["operationKey"] == "outline" and c["state"] == "failed" for c in view.checkpoints)
                    from plotloom.autopilot_text_failures import failure_context
                    details = failure_context(store, registry)
                    assert not details["canRetry"] and "上限" in details["reason"]
                    from plotloom.text_correction_contracts import TextRetryGrant
                    grant = TextRetryGrant(command_id=uuid4(), expected_run_id=run.id, expected_revision=view.revision,
                        failed_attempt_id=failed.attempt_id, rejection_hash=proof.rejection_hash)
                if index == 8:
                    import pytest
                    from plotloom.exceptions import InvalidTransitionError
                    with pytest.raises(InvalidTransitionError, match="capacity"):
                        service.retry_text(run.project_id, grant)
                    with closing(storage.projects.open(run.project_id)) as store:
                        assert store.repository.autopilot.current(run.project_id).lifetime_jobs == 9
                    break
            service.control(run.project_id, RunControlRequest(expected_revision=view.revision, action="cancel"))
            with closing(storage.projects.open(run.project_id)) as store:
                context = store.repository.autopilot.continuation_context(run.project_id)
                assert context["eligible"], context["blockers"]
                continuation = ContinueRequest(expected_brief_revision=1, expected_run_id=context["runId"],
                    expected_run_revision=context["runRevision"], expected_material_closure=context["materialClosure"],
                    render_style="realistic", art_render_style="realistic", max_jobs=9)
            run = service.continue_material(run.project_id, continuation)
        assert len(calls) == len(set(calls)) == host.admissions == 9
    finally:
        service.close()
