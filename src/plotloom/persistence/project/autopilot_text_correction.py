"""Atomic creation and passive validation of exact corrective creative jobs."""
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ...autopilot_contracts import CheckpointEvidence, LaunchPolicy, OperationScope
from ...creative_handoff_contracts import CreativeHandoffRequest
from ...creative_handoff_exchange import request_hash
from ...domain import utc_now
from ...exceptions import InvalidTransitionError
from ...text_correction_contracts import TextCorrection, correction_key
from ..schema import (
    ArtHeadRow,
    AutopilotCheckpointRow,
    CastHeadRow,
    SourceOutlineHeadRow,
)
from .creative_execution_pins import freeze_execution_pin
from .creative_terminal import CANDIDATE_ROWS

HEADS = {"outline": SourceOutlineHeadRow, "characters": CastHeadRow, "art": ArtHeadRow}


def assert_correction_lineage(connection, request, *, run_id, operation_key):
    """Bind physical suffix to original immutable failure, including passive restore."""
    from ...codex_exec_contracts import CodexExecAttempt
    from .autopilot_bindings import _row
    correction = request.text_correction
    if correction is None:
        if operation_key != request.stage:
            raise ValueError("ordinary creative job cannot claim a correction operation")
        return
    rejection = correction.rejection
    if request.content_validation_contract != "plotloom.typed-content-result.v1":
        raise ValueError("correction requires explicit typed candidate validation authority")
    if operation_key != correction_key(request.stage) or rejection.stage != request.stage or str(rejection.run_id) != run_id:
        raise ValueError("correction operation differs from its original stage/run")
    run = _row(connection, "SELECT policy FROM v2_autopilot_runs WHERE id=?", (run_id,))
    policy = LaunchPolicy.model_validate_json(run["policy"])
    if (policy.text_correction_limit != 1 or policy.executor_binding.text_correction_limit != 1
            or policy.code_revision != rejection.source_revision
            or policy.executor_binding.profile_hash != rejection.profile_hash):
        raise ValueError("correction differs from frozen launch authority")
    source = _row(connection, "SELECT snapshot FROM v2_autopilot_exec_attempts WHERE id=? AND run_id=?", (str(rejection.source_attempt_id), run_id))
    attempt = CodexExecAttempt.model_validate_json(source["snapshot"])
    rejection.assert_attempt(attempt)
    if attempt.content_rejection != rejection or attempt.operation_key != request.stage:
        raise ValueError("correction lacks its exact typed first-attempt rejection")
    checkpoint = _row(connection, "SELECT state,evidence FROM v2_autopilot_checkpoints WHERE run_id=? AND operation_key=?", (run_id, request.stage))
    evidence = CheckpointEvidence.model_validate_json(checkpoint["evidence"])
    if (checkpoint["state"] != "failed" or evidence.executor_attempt_id != rejection.source_attempt_id
            or evidence.executor_receipt_hash != attempt.evidence_hash or evidence.job_id != rejection.job_id):
        raise ValueError("correction original failed checkpoint changed")
    table = CANDIDATE_ROWS[request.stage].__tablename__
    original = _row(connection, f'SELECT request FROM "{table}" WHERE job_id=? AND project_id=?', (rejection.job_id, request.project_id))
    original_request = CreativeHandoffRequest.model_validate_json(original["request"])
    if original_request.text_correction is not None or request_hash(original_request) != rejection.request_hash:
        raise ValueError("correction original request changed")
    if request.model_dump(mode="json", by_alias=True, exclude={"job_id", "text_correction"}) != original_request.model_dump(mode="json", by_alias=True, exclude={"job_id", "text_correction"}):
        raise ValueError("correction changed frozen source/style/upstream request authority")
    expected_job = "ch_" + uuid5(NAMESPACE_URL, f"plotloom:text-correction:{run_id}:{rejection.source_attempt_id}:1").hex
    if request.job_id != expected_job or evidence.execution_pin != policy.execution_pins[request.stage]:
        raise ValueError("correction identity or execution pin changed")


class AutopilotTextCorrectionPersistence:
    def prepare_text_correction(self, original_request, rejection, prior_candidate_json):
        """Copy only an unreceived model-owned candidate; retain its original row."""
        authority = self.access.authority()
        if authority is None or authority.scope != OperationScope.TEXT:
            raise InvalidTransitionError("text correction requires exact text authority")
        with self.access.leases.lifecycle_write() as session:
            run = self.validate_command(session, authority)
            policy = LaunchPolicy.model_validate(run.policy)
            key = correction_key(original_request.stage)
            existing = session.scalar(select(AutopilotCheckpointRow).where(
                AutopilotCheckpointRow.run_id == run.id, AutopilotCheckpointRow.operation_key == key))
            if existing is not None:
                retained = CreativeHandoffRequest.model_validate(session.get(CANDIDATE_ROWS[original_request.stage], existing.evidence["jobId"]).request)
                if retained.text_correction != TextCorrection(rejection=rejection, prior_candidate_json=prior_candidate_json):
                    raise InvalidTransitionError("corrective identity already owns different immutable feedback")
                return retained
            from ...provider_budgets import exceeds_budget
            from .autopilot_continuation import project_job_counts
            if exceeds_budget(project_job_counts(session, run.project_id)[0] + 1, policy.max_jobs):
                raise InvalidTransitionError("text correction exceeds frozen lifetime job capacity")
            correction = TextCorrection(rejection=rejection, prior_candidate_json=prior_candidate_json)
            job_id = "ch_" + uuid5(NAMESPACE_URL, f"plotloom:text-correction:{run.id}:{rejection.source_attempt_id}:1").hex
            request = CreativeHandoffRequest.model_validate(original_request.model_dump(mode="python") | {"job_id": job_id, "text_correction": correction})
            request.assert_secret_free()
            assert_correction_lineage(session.connection().connection.driver_connection, request, run_id=run.id, operation_key=key)
            row_type = CANDIDATE_ROWS[request.stage]
            original = session.get(row_type, original_request.job_id)
            head = session.get(HEADS[request.stage], run.project_id)
            if (original is None or original.status != "prepared" or original.manifest_hash is not None
                    or head is None or head.candidate_job_id != original_request.job_id
                    or original.request != original_request.model_dump(mode="json", by_alias=True)):
                raise InvalidTransitionError("original rejected candidate is no longer current and unreceived")
            values = {column.key: getattr(original, column.key) for column in row_type.__table__.columns}
            now = utc_now()
            values.update(job_id=job_id, request=request.model_dump(mode="json", by_alias=True), created_at=now)
            session.add(row_type(**values))
            freeze_execution_pin(session, request, policy.execution_pins[request.stage])
            head.candidate_job_id, head.updated_at = job_id, now
            session.flush()
            self.checkpoint(key, state="prepared", evidence=CheckpointEvidence(
                owner=request.stage, subject_id=job_id, job_id=job_id,
                request_hash=request_hash(request), execution_pin=policy.execution_pins[request.stage],
                result={"sourceAttemptId": str(rejection.source_attempt_id), "rejectionHash": rejection.rejection_hash, "correctionOrdinal": 1}))
            self.progress(request.stage)
            return request


def superseded_text_failure(session, run, attempt_row, checkpoint):
    """The serial dependency fence ignores only an exactly linked rejected root."""
    if checkpoint.state != "failed":
        return False
    source = attempt_row.snapshot.get("contentRejection")
    if source is None:
        return False
    stage = checkpoint.evidence["owner"]
    linked = session.scalar(select(AutopilotCheckpointRow).where(
        AutopilotCheckpointRow.run_id == run.id,
        AutopilotCheckpointRow.operation_key == correction_key(stage)))
    if linked is None or linked.state == "failed":
        return False
    row = session.get(CANDIDATE_ROWS[stage], linked.evidence["jobId"])
    request = CreativeHandoffRequest.model_validate(row.request)
    assert_correction_lineage(session.connection().connection.driver_connection, request,
        run_id=run.id, operation_key=linked.operation_key)
    return str(request.text_correction.rejection.source_attempt_id) == attempt_row.id


def has_publishable_candidates(connection, project_id, table):
    """A proven completed text rejection cannot retain publication authority.

    Candidate rows remain byte-for-byte retained. Manual, unstarted, UNKNOWN and
    other failures keep their original publication guard until normally settled.
    """
    if table not in {CANDIDATE_ROWS[stage].__tablename__ for stage in HEADS}:
        raise ValueError("unsupported typed text publication owner")
    for job_id, raw_request in connection.execute(
            f'SELECT job_id,request FROM "{table}" WHERE project_id=? AND status=\'prepared\'', (project_id,)):
        row = connection.execute(
            "SELECT a.snapshot,c.state,c.evidence,r.policy FROM v2_autopilot_exec_attempts a "
            "JOIN v2_autopilot_checkpoints c ON c.run_id=a.run_id AND c.operation_key=a.operation_key "
            "JOIN v2_autopilot_runs r ON r.id=a.run_id "
            "WHERE a.project_id=? AND a.job_id=?", (project_id, job_id)).fetchone()
        if row is None:
            return True
        from ...codex_exec_contracts import CodexExecAttempt
        attempt = CodexExecAttempt.model_validate_json(row[0])
        request = CreativeHandoffRequest.model_validate_json(raw_request)
        evidence = CheckpointEvidence.model_validate_json(row[2])
        policy = LaunchPolicy.model_validate_json(row[3])
        if (attempt.content_rejection is None or row[1] != "failed" or policy.text_correction_limit != 1
                or policy.executor_binding is None or policy.executor_binding.text_correction_limit != 1
                or attempt.profile_hash != policy.executor_binding.profile_hash
                or request.content_validation_contract != "plotloom.typed-content-result.v1"
                or attempt.operation_key != (correction_key(request.stage) if request.text_correction else request.stage)
                or attempt.content_rejection.stage != request.stage or request.job_id != job_id
                or request.project_id != project_id or attempt.request_hash != request_hash(request)
                or evidence.owner != request.stage or evidence.job_id != job_id
                or evidence.executor_attempt_id != attempt.attempt_id
                or evidence.executor_receipt_hash != attempt.evidence_hash):
            return True
    return False
