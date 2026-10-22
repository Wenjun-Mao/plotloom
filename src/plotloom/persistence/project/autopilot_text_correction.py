"""Atomic immutable text correction chains and exact one-attempt creator grants."""
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ...autopilot_contracts import CheckpointEvidence, LaunchPolicy, OperationScope
from ...creative_handoff_contracts import CreativeHandoffRequest
from ...creative_handoff_exchange import request_hash
from ...domain import new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ...text_correction_contracts import (
    CORRECTION_CONTRACT,
    TextCorrection,
    correction_key,
)
from ..schema import (
    ArtHeadRow,
    AutopilotCheckpointRow,
    CastHeadRow,
    SourceOutlineHeadRow,
)
from .creative_execution_pins import freeze_execution_pin
from .creative_terminal import CANDIDATE_ROWS

HEADS = {"outline": SourceOutlineHeadRow, "characters": CastHeadRow, "art": ArtHeadRow}


def correction_job(run_id, rejection, ordinal):
    return "ch_" + uuid5(NAMESPACE_URL,
        f"plotloom:text-correction:{run_id}:{rejection.source_attempt_id}:{ordinal}").hex


def supports_corrections(policy):
    return policy.executor_binding is not None and (
        policy.executor_binding.text_correction_contract == CORRECTION_CONTRACT
        or policy.executor_binding.text_correction_limit == 1)


def assert_correction_lineage(connection, request, *, run_id, operation_key):
    """Validate every immediate parent, ordinal and grant; never infer authority."""
    from ...codex_exec_contracts import CodexExecAttempt
    from .autopilot_bindings import _row
    run = _row(connection, "SELECT policy FROM v2_autopilot_runs WHERE id=?", (run_id,))
    policy = LaunchPolicy.model_validate_json(run["policy"])
    automatic = 0
    current, key = request, operation_key
    while current.text_correction is not None:
        correction = current.text_correction
        rejection = correction.rejection
        if (current.content_validation_contract != "plotloom.typed-content-result.v1"
                or key != correction_key(current.stage, correction.ordinal)
                or rejection.stage != current.stage or str(rejection.run_id) != run_id):
            raise ValueError("correction operation differs from its parent stage/run")
        if (not supports_corrections(policy) or policy.code_revision != rejection.source_revision
                or policy.executor_binding.profile_hash != rejection.profile_hash):
            raise ValueError("correction differs from frozen launch capability")
        if correction.manual_grant is not None:
            if policy.executor_binding.text_correction_contract != CORRECTION_CONTRACT:
                raise ValueError("retained launch cannot acquire explicit extra correction authority")
        else:
            automatic += 1
        source = _row(connection, "SELECT snapshot FROM v2_autopilot_exec_attempts WHERE id=? AND run_id=?",
            (str(rejection.source_attempt_id), run_id))
        attempt = CodexExecAttempt.model_validate_json(source["snapshot"])
        rejection.assert_attempt(attempt)
        parent_key = current.stage if correction.ordinal == 1 else correction_key(current.stage, correction.ordinal - 1)
        if attempt.content_rejection != rejection or attempt.operation_key != parent_key:
            raise ValueError("correction lacks its immediate parent typed rejection")
        checkpoint = _row(connection, "SELECT state,evidence FROM v2_autopilot_checkpoints WHERE run_id=? AND operation_key=?",
            (run_id, parent_key))
        evidence = CheckpointEvidence.model_validate_json(checkpoint["evidence"])
        if (checkpoint["state"] != "failed" or evidence.executor_attempt_id != rejection.source_attempt_id
                or evidence.executor_receipt_hash != attempt.evidence_hash or evidence.job_id != rejection.job_id
                or evidence.execution_pin != policy.execution_pins[current.stage]):
            raise ValueError("correction parent failed checkpoint changed")
        table = CANDIDATE_ROWS[current.stage].__tablename__
        original = _row(connection, f'SELECT request FROM "{table}" WHERE job_id=? AND project_id=?',
            (rejection.job_id, current.project_id))
        parent = CreativeHandoffRequest.model_validate_json(original["request"])
        parent_ordinal = parent.text_correction.ordinal if parent.text_correction else 0
        if parent_ordinal != correction.ordinal - 1 or request_hash(parent) != rejection.request_hash:
            raise ValueError("correction parent ordinal or request changed")
        if current.model_dump(mode="json", by_alias=True, exclude={"job_id", "text_correction"}) != parent.model_dump(
                mode="json", by_alias=True, exclude={"job_id", "text_correction"}):
            raise ValueError("correction changed frozen source/style/upstream authority")
        if current.job_id != correction_job(run_id, rejection, correction.ordinal):
            raise ValueError("correction deterministic identity changed")
        current, key = parent, parent_key
    if key != current.stage:
        raise ValueError("ordinary creative job cannot claim a correction operation")
    if automatic > (policy.text_correction_limit or 0):
        raise ValueError("correction chain exceeds frozen automatic quota")


class AutopilotTextCorrectionPersistence:
    def automatic_corrections_used(self, run_id, stage):
        if stage not in HEADS:
            return 0
        with self.access.leases.read() as session:
            checkpoints = session.scalars(select(AutopilotCheckpointRow).where(
                AutopilotCheckpointRow.run_id == run_id)).all()
            return sum(1 for c in checkpoints if c.evidence["owner"] == stage
                and (request := CreativeHandoffRequest.model_validate(session.get(CANDIDATE_ROWS[stage], c.evidence["jobId"]).request)).text_correction
                and request.text_correction.manual_grant is None)

    def prepare_text_correction(self, original_request, rejection, prior_candidate_json):
        authority = self.access.authority()
        if authority is None or authority.scope != OperationScope.TEXT:
            raise InvalidTransitionError("text correction requires exact text authority")
        with self.access.leases.lifecycle_write() as session:
            run = self.validate_command(session, authority)
            return self._create_text_correction(session, run, original_request, rejection, prior_candidate_json)

    def grant_text_retry(self, project_id, grant, original_request, rejection, prior_candidate_json):
        """Called inside one manual command; grant and new job commit together."""
        if self.access.authority() is not None:
            raise InvalidTransitionError("only an explicit creator command can grant an extra attempt")
        with self.access.leases.lifecycle_write() as session:
            run = self.row(session, project_id)
            if run is None or run.id != str(grant.expected_run_id):
                raise InvalidTransitionError("text retry run changed")
            # A lost-ACK duplicate is observation, never another grant.
            for checkpoint in session.scalars(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == run.id)):
                if checkpoint.evidence.get("owner") not in HEADS:
                    continue
                candidate = session.get(CANDIDATE_ROWS[checkpoint.evidence["owner"]], checkpoint.evidence["jobId"])
                retained = CreativeHandoffRequest.model_validate(candidate.request)
                correction = retained.text_correction
                if correction and correction.manual_grant and correction.manual_grant.command_id == grant.command_id:
                    if correction.manual_grant != grant:
                        raise InvalidTransitionError("retry command already owns different immutable directions")
                    return retained
            if run.revision != grant.expected_revision:
                raise RevisionConflictError("autopilot", grant.expected_revision, run.revision)
            if run.id in self.recovered_run_ids() or run.state != "blocked":
                raise InvalidTransitionError("only a current blocked native text failure can be retried")
            policy = LaunchPolicy.model_validate(run.policy)
            if policy.executor_binding.text_correction_contract != CORRECTION_CONTRACT:
                raise InvalidTransitionError("frozen launch lacks explicit extra-correction capability")
            from ..codec import stable_hash
            from .autopilot_closure import material_closure
            project = self.access.rows.project(session, project_id)
            self.access.guards.active(project)
            if (run.expected_closure != material_closure(session, project_id)
                    or run.brief_revision != project.revision or run.lifecycle_revision != project.lifecycle_revision
                    or run.brief_hash != stable_hash(project.brief) or run.policy_hash != stable_hash(run.policy)):
                raise InvalidTransitionError("text retry frozen authority or material changed")
            result = self._create_text_correction(session, run, original_request, rejection, prior_candidate_json, grant=grant)
            run.state, run.blocker = "running", None
            run.revision += 1
            run.updated_at = utc_now()
            session.flush()
            run.expected_closure = material_closure(session, project_id)
            return result

    def _create_text_correction(self, session, run, parent, rejection, prior_candidate_json, *, grant=None):
        policy = LaunchPolicy.model_validate(run.policy)
        ordinal = parent.text_correction.ordinal + 1 if parent.text_correction else 1
        key = correction_key(parent.stage, ordinal)
        correction = TextCorrection(ordinal=ordinal, rejection=rejection,
            prior_candidate_json=prior_candidate_json, manual_grant=grant)
        existing = session.scalar(select(AutopilotCheckpointRow).where(
            AutopilotCheckpointRow.run_id == run.id, AutopilotCheckpointRow.operation_key == key))
        if existing is not None:
            retained = CreativeHandoffRequest.model_validate(session.get(CANDIDATE_ROWS[parent.stage], existing.evidence["jobId"]).request)
            if retained.text_correction != correction:
                raise InvalidTransitionError("corrective identity already owns different immutable feedback")
            return retained
        from ...provider_budgets import exceeds_budget
        from .autopilot_continuation import project_job_counts
        if exceeds_budget(project_job_counts(session, run.project_id)[0] + 1, policy.max_jobs):
            raise InvalidTransitionError("text correction exceeds frozen lifetime job capacity")
        request = CreativeHandoffRequest.model_validate(parent.model_dump(mode="python") | {
            "job_id": correction_job(run.id, rejection, ordinal), "text_correction": correction})
        request.assert_secret_free()
        connection = session.connection().connection.driver_connection
        assert_correction_lineage(connection, request, run_id=run.id, operation_key=key)
        row_type = CANDIDATE_ROWS[request.stage]
        original = session.get(row_type, parent.job_id)
        head = session.get(HEADS[request.stage], run.project_id)
        if (original is None or original.status != "prepared" or original.manifest_hash is not None
                or head is None or head.candidate_job_id != parent.job_id
                or original.request != parent.model_dump(mode="json", by_alias=True)):
            raise InvalidTransitionError("rejected candidate is no longer current and unreceived")
        values = {column.key: getattr(original, column.key) for column in row_type.__table__.columns}
        now = utc_now()
        values.update(job_id=request.job_id, request=request.model_dump(mode="json", by_alias=True), created_at=now)
        session.add(row_type(**values))
        freeze_execution_pin(session, request, policy.execution_pins[request.stage])
        head.candidate_job_id, head.updated_at = request.job_id, now
        session.flush()
        evidence = CheckpointEvidence(owner=request.stage, subject_id=request.job_id, job_id=request.job_id,
            request_hash=request_hash(request), execution_pin=policy.execution_pins[request.stage],
            result={"sourceAttemptId": str(rejection.source_attempt_id), "rejectionHash": rejection.rejection_hash,
                "correctionOrdinal": ordinal})
        if grant is None:
            self.checkpoint(key, state="prepared", evidence=evidence)
            self.progress(request.stage)
        else:
            from .autopilot_bindings import assert_checkpoint_binding
            assert_checkpoint_binding(connection, run.project_id, "prepared", evidence, run_id=run.id, operation_key=key)
            session.add(AutopilotCheckpointRow(id=new_id(), run_id=run.id, project_id=run.project_id,
                operation_key=key, revision=1, state="prepared", evidence=evidence.model_dump(mode="json", by_alias=True),
                created_at=now, updated_at=now))
            run.phase = request.stage
        return request


def superseded_text_failure(session, run, attempt_row, checkpoint):
    """A rejected ancestor is superseded only by its validated immediate child."""
    if checkpoint.state != "failed" or attempt_row.snapshot.get("contentRejection") is None:
        return False
    stage = checkpoint.evidence["owner"]
    ordinal = checkpoint.evidence["result"].get("correctionOrdinal", 0) + 1
    linked = session.scalar(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == run.id,
        AutopilotCheckpointRow.operation_key == correction_key(stage, ordinal)))
    if linked is None:
        return False
    row = session.get(CANDIDATE_ROWS[stage], linked.evidence["jobId"])
    request = CreativeHandoffRequest.model_validate(row.request)
    assert_correction_lineage(session.connection().connection.driver_connection, request,
        run_id=run.id, operation_key=linked.operation_key)
    return str(request.text_correction.rejection.source_attempt_id) == attempt_row.id


def terminal_content_rejection(connection, project_id, table, job_id):
    """One shared positive proof for publication, lifecycle and rebuild guards."""
    if table not in {CANDIDATE_ROWS[stage].__tablename__ for stage in HEADS}:
        raise ValueError("unsupported typed text publication owner")
    candidate = connection.execute(f'SELECT request FROM "{table}" WHERE project_id=? AND job_id=? AND status=\'prepared\'',
        (project_id, job_id)).fetchone()
    if candidate is None:
        return False
    row = connection.execute(
            "SELECT a.snapshot,c.state,c.evidence,r.policy FROM v2_autopilot_exec_attempts a "
            "JOIN v2_autopilot_checkpoints c ON c.run_id=a.run_id AND c.operation_key=a.operation_key "
            "JOIN v2_autopilot_runs r ON r.id=a.run_id WHERE a.project_id=? AND a.job_id=?", (project_id, job_id)).fetchone()
    if row is None:
        return False
    from ...codex_exec_contracts import CodexExecAttempt
    attempt = CodexExecAttempt.model_validate_json(row[0])
    request = CreativeHandoffRequest.model_validate_json(candidate[0])
    evidence = CheckpointEvidence.model_validate_json(row[2])
    policy = LaunchPolicy.model_validate_json(row[3])
    key = correction_key(request.stage, request.text_correction.ordinal) if request.text_correction else request.stage
    if (request.stage not in HEADS or CANDIDATE_ROWS[request.stage].__tablename__ != table
                or attempt.content_rejection is None or row[1] != "failed" or not supports_corrections(policy)
                or attempt.profile_hash != policy.executor_binding.profile_hash
                or attempt.plotloom_code_revision != policy.code_revision
                or request.content_validation_contract != "plotloom.typed-content-result.v1"
                or attempt.operation_key != key or attempt.content_rejection.stage != request.stage
                or request.job_id != job_id or request.project_id != project_id or attempt.request_hash != request_hash(request)
                or evidence.owner != request.stage or evidence.job_id != job_id
                or evidence.executor_attempt_id != attempt.attempt_id or evidence.executor_receipt_hash != attempt.evidence_hash):
        return False
    assert_correction_lineage(connection, request, run_id=str(attempt.run_id), operation_key=key)
    return True


def has_publishable_candidates(connection, project_id, table):
    if table not in {CANDIDATE_ROWS[stage].__tablename__ for stage in HEADS}:
        raise ValueError("unsupported typed text publication owner")
    return any(not terminal_content_rejection(connection, project_id, table, job_id)
        for job_id, in connection.execute(
            f'SELECT job_id FROM "{table}" WHERE project_id=? AND status=\'prepared\'', (project_id,)))
