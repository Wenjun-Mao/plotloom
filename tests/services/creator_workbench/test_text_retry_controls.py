"""Unsafe-state and lineage controls use explicit fake-host facts, never providers."""
from contextlib import closing
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from plotloom.autopilot_contracts import (
    ContinueRequest,
    LaunchRequest,
    RunControlRequest,
)
from plotloom.autopilot_text_failures import comparison, failure_context
from plotloom.codex_exec_contracts import CodexExecHostStatus, transition_exec_attempt
from plotloom.creative_handoff_identity import canonical_json
from plotloom.exceptions import InvalidTransitionError
from plotloom.text_correction_contracts import (
    TextContentIssue,
    TextContentRejection,
    TextRetryGrant,
    logical_checkpoint,
)
from tests.autopilot_controller_fixtures import candidate
from tests.autopilot_seed_fixtures import run_facts
from tests.services.creator_workbench.test_text_content_correction import (
    _failed_outline_fixture,
)


def current(storage, run):
    with closing(storage.projects.open(run.project_id)) as store:
        return store.repository.autopilot.current(run.project_id)


def grant_for(storage, registry, run, **changes):
    with closing(storage.projects.open(run.project_id)) as store:
        details = failure_context(store, registry)
    return TextRetryGrant(command_id=uuid4(), expected_run_id=run.id,
        expected_revision=details["runRevision"], failed_attempt_id=details["failedAttemptId"],
        rejection_hash=details["rejectionHash"], **changes)


def fail_latest(storage, registry, service, run):
    """Inject a typed source-result fixture at the current running physical job."""
    host = registry._codex_exec_test_host
    view = current(storage, run)
    checkpoint = logical_checkpoint(view, "outline")
    with closing(storage.projects.open(run.project_id)) as store:
        attempt = store.repository.autopilot.exec_attempt_for_operation(run.id, checkpoint["operationKey"])
        request = host.request(store, attempt)
        raw = canonical_json(candidate(store, request))
        (store.creative_handoff_exchange().root / "jobs" / attempt.job_id / "delivery/outline.json").write_bytes(raw)
    rejection = TextContentRejection(source_attempt_id=attempt.attempt_id, run_id=attempt.run_id,
        stage="outline", job_id=attempt.job_id, candidate_hash=sha256(raw).hexdigest(),
        validation_evidence_hash="b" * 64, request_hash=attempt.request_hash, package_hash=attempt.package_hash,
        plan_hash=attempt.validation_plan_hash, profile_hash=attempt.profile_hash, source_revision=attempt.plotloom_code_revision,
        issues=(TextContentIssue(code="candidate_content_invalid", field_paths=("$",)),))
    failed = transition_exec_attempt(attempt, state="failed", session_id=uuid4(), process_exit_code=0,
        terminal_result="failure", remote_tool_state="not_applicable", evidence_hash="a" * 64, content_rejection=rejection)
    host.pending.discard(str(attempt.attempt_id))
    host.statuses[str(attempt.attempt_id)] = CodexExecHostStatus(state="failed", attempt=failed)
    service.step(run.project_id)
    return current(storage, run)


@pytest.mark.parametrize("value", [True, -1, 1.5, "", None, 9_007_199_254_740_992])
def test_launch_auto_count_rejects_coercion_and_unsafe_integers(value):
    with pytest.raises(ValidationError):
        LaunchRequest(expected_brief_revision=1, text_correction_limit=value)


def test_numeric_latest_checkpoint_and_malformed_identity():
    def checkpoint(ordinal):
        return {"operationKey": f"art:correction:{ordinal}", "evidence": {"result": {"correctionOrdinal": ordinal}}}
    nine, ten = checkpoint(9), checkpoint(10)
    assert logical_checkpoint(SimpleNamespace(checkpoints=[ten, nine]), "art") is ten
    with pytest.raises(ValueError, match="malformed"):
        logical_checkpoint(SimpleNamespace(checkpoints=[checkpoint("broken")]), "art")


def test_generic_feedback_does_not_invent_repeat_certainty():
    generic = SimpleNamespace(display_diagnostics=(), issues=(TextContentIssue(code="candidate_content_invalid", field_paths=("$",)),))
    assert comparison(generic, generic) == "unknown"
    one = SimpleNamespace(display_diagnostics=("params missing",), issues=generic.issues)
    other = SimpleNamespace(display_diagnostics=("summary missing",), issues=generic.issues)
    assert comparison(one, one) == "repeated"
    assert comparison(one, other) == "changed"
    # Both complete results could differ after their retained display boundary.
    truncated = SimpleNamespace(display_diagnostics=("a" * 500,), issues=generic.issues)
    assert comparison(truncated, truncated) == "unknown"
    truncated = SimpleNamespace(display_diagnostics=tuple(str(i) for i in range(16)), issues=generic.issues)
    assert comparison(truncated, truncated) == "unknown"


@pytest.mark.parametrize("kind", ["unknown", "runtime", "refusal"])
def test_no_manual_retry_for_noncontent_outcome(tmp_path, monkeypatch, kind):
    storage, registry, service, run, calls = _failed_outline_fixture(tmp_path, monkeypatch, kind=kind, limits={"text_correction_limit": 0})
    try:
        service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            context = failure_context(store, registry)
            from plotloom.persistence.project.production_rebuild_quiescence import (
                assert_production_quiescent,
            )
            with store.repository._read() as session, pytest.raises(InvalidTransitionError):
                assert_production_quiescent(store.repository._project_access, session, run.project_id)
        assert not context["canRetry"] and not context["terminalContentFailure"]
        grant = TextRetryGrant(command_id=uuid4(), expected_run_id=run.id, expected_revision=current(storage, run).revision,
            failed_attempt_id=uuid4(), rejection_hash="a" * 64)
        with pytest.raises(InvalidTransitionError):
            service.retry_text(run.project_id, grant)
        assert len(calls) == 1
    finally:
        service.close()


def test_duplicate_after_manual_edit_never_rebases_or_creates_work(tmp_path, monkeypatch):
    storage, registry, service, run, calls = _failed_outline_fixture(tmp_path, monkeypatch, limits={"text_correction_limit": 0})
    try:
        service.step(run.project_id)
        grant = grant_for(storage, registry, run)
        service.retry_text(run.project_id, grant)
        with closing(storage.projects.open(run.project_id)) as store:
            # A supported ordinary manual control withdraws this run; duplicate
            # acknowledgement must not turn it back into automatic authority.
            revision = store.repository.autopilot.current(run.project_id).revision
        service.control(run.project_id, RunControlRequest(expected_revision=revision, action="takeover"))
        with closing(storage.projects.open(run.project_id)) as store:
            project = store.project()
            store.update_brief(project.brief.model_copy(update={"title": project.brief.title + " · manual edit"}), expected_revision=project.revision)
            from plotloom.persistence.project.autopilot_closure import material_closure
            with store.repository._read() as session:
                row = store.repository.autopilot.row(session, run.project_id)
                frozen_closure = row.expected_closure
                assert frozen_closure != material_closure(session, run.project_id)
        before = current(storage, run)
        with pytest.raises(InvalidTransitionError):
            service.retry_text(run.project_id, grant)
        after = current(storage, run)
        assert run_facts(after) == run_facts(before) and after.state == "taken_over"
        with pytest.raises(InvalidTransitionError):
            service.retry_text(run.project_id, grant.model_copy(update={"command_id": uuid4()}))
        with closing(storage.projects.open(run.project_id)) as store, store.repository._read() as session:
            assert store.repository.autopilot.row(session, run.project_id).expected_closure == frozen_closure
        assert len(calls) == 1 and after.lifetime_jobs == 2
    finally:
        service.close()


def test_multi_manual_chain_numeric_resolution_restart_and_inherited_adopted_leaf(tmp_path, monkeypatch):
    storage, registry, service, run, _calls = _failed_outline_fixture(tmp_path, monkeypatch, limits={"text_correction_limit": 0})
    try:
        service.step(run.project_id)
        for ordinal in range(1, 11):
            grant = grant_for(storage, registry, run)
            view = service.retry_text(run.project_id, grant)
            assert logical_checkpoint(view, "outline")["operationKey"] == f"outline:correction:{ordinal}"
            service.step(run.project_id)
            service.step(run.project_id)
            if ordinal < 10:
                assert fail_latest(storage, registry, service, run).state == "blocked"
        host = registry._codex_exec_test_host
        host.auto_deliver = True
        for _ in range(4):
            service.step(run.project_id)
            if logical_checkpoint(current(storage, run), "outline")["state"] == "adopted":
                break
        view = current(storage, run)
        assert logical_checkpoint(view, "outline")["state"] == "adopted", view.blocker
        assert len([c for c in view.checkpoints if c["evidence"]["owner"] == "outline"]) == 11
        with closing(storage.projects.open(run.project_id)) as store:
            assert store.repository.autopilot.automatic_corrections_used(run.id, "outline") == 0
        service.control(run.project_id, RunControlRequest(expected_revision=view.revision, action="cancel"))
        with closing(storage.projects.open(run.project_id)) as store:
            context = store.repository.autopilot.continuation_context(run.project_id)
        assert context["eligible"], context
        successor = service.continue_material(run.project_id, ContinueRequest(expected_brief_revision=1,
            expected_run_id=context["runId"], expected_run_revision=context["runRevision"],
            expected_material_closure=context["materialClosure"], render_style="realistic", art_render_style="realistic", text_correction_limit=0))
        assert logical_checkpoint(successor, "outline")["operationKey"] == "outline:correction:10"
        with closing(storage.projects.open(run.project_id)) as store:
            history = failure_context(store, registry, stage="outline")
            assert history["resolved"] and not history["canRetry"] and len(history["history"]) == 11
        service.close()
        from plotloom.autopilot_service import AutopilotService
        service = AutopilotService(storage, registry)
        assert service.acquire_controller()
        service.step(run.project_id)
        assert logical_checkpoint(current(storage, successor), "outline")["operationKey"] == "outline:correction:10"
    finally:
        service.close()


def test_terminal_rejection_does_not_hide_a_prepared_manual_neighbor(tmp_path, monkeypatch):
    storage, _registry, service, run, _calls = _failed_outline_fixture(tmp_path, monkeypatch, limits={"text_correction_limit": 0})
    try:
        service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            from plotloom.outline_preparation import outline_request
            from plotloom.persistence.project.production_rebuild_quiescence import (
                assert_production_quiescent,
            )
            from plotloom.persistence.project.repository_codecs import (
                project_is_busy_in_session,
            )
            with store.repository._read() as session:
                assert not project_is_busy_in_session(session, run.project_id)
            store.prepare_outline_candidate(outline_request(store, job_id="ch_" + uuid4().hex))
            with store.repository._read() as session:
                assert project_is_busy_in_session(session, run.project_id)
                with pytest.raises(InvalidTransitionError, match="active project work"):
                    assert_production_quiescent(store.repository._project_access, session, run.project_id)
    finally:
        service.close()


@pytest.mark.parametrize("corruption", ["gapped", "wrong-parent", "cyclic"])
def test_lineage_and_publication_proof_fail_closed_on_forged_parent(tmp_path, monkeypatch, corruption):
    storage, registry, service, run, _calls = _failed_outline_fixture(tmp_path, monkeypatch, limits={"text_correction_limit": 0})
    try:
        service.step(run.project_id)
        service.retry_text(run.project_id, grant_for(storage, registry, run))
        service.step(run.project_id); service.step(run.project_id)
        fail_latest(storage, registry, service, run)
        from plotloom.creative_handoff_contracts import CreativeHandoffRequest
        from plotloom.persistence.project.autopilot_text_correction import (
            assert_correction_lineage,
            terminal_content_rejection,
        )
        from plotloom.persistence.project.creative_terminal import CANDIDATE_ROWS
        with closing(storage.projects.open(run.project_id)) as store:
            view = store.repository.autopilot.current(run.project_id)
            checkpoint = logical_checkpoint(view, "outline")
            with store.repository._write() as session:
                row = session.get(CANDIDATE_ROWS["outline"], checkpoint["evidence"]["jobId"])
                request = CreativeHandoffRequest.model_validate(row.request)
                connection = session.connection().connection.driver_connection
                assert terminal_content_rejection(connection, run.project_id, row.__tablename__, row.job_id)
                correction = request.text_correction
                if corruption == "gapped":
                    broken = correction.model_copy(update={"ordinal": 2})
                else:
                    attempt_id = uuid4() if corruption == "wrong-parent" else checkpoint["evidence"]["executorAttemptId"]
                    from uuid import UUID
                    rejection = correction.rejection.model_copy(update={"source_attempt_id": UUID(str(attempt_id))})
                    grant = correction.manual_grant.model_copy(update={"failed_attempt_id": rejection.source_attempt_id,
                        "rejection_hash": rejection.rejection_hash})
                    broken = correction.model_copy(update={"rejection": rejection, "manual_grant": grant})
                forged = request.model_copy(update={"text_correction": broken})
                with pytest.raises(ValueError):
                    assert_correction_lineage(connection, forged, run_id=run.id, operation_key=checkpoint["operationKey"])
                row.request = forged.model_dump(mode="json", by_alias=True)
                session.flush()
                assert not terminal_content_rejection(connection, run.project_id, row.__tablename__, row.job_id)
    finally:
        service.close()
