"""Atomic fresh native jobs; predecessor rows and uncertainty stay immutable."""
from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ...autopilot_contracts import CheckpointEvidence, LaunchPolicy, OperationScope
from ...autopilot_execution_retry import retry_root
from ...codex_exec_contracts import CodexExecAttempt
from ...contract_identity import new_id, utc_now
from ...creative_handoff_contracts import CreativeHandoffRequest
from ...creative_handoff_identity import request_hash
from ...exceptions import InvalidTransitionError
from ...generation_retry_policy import repeatable_failure
from ...provider_budgets import exceeds_budget
from ..codec import stable_hash
from ..schema import (
    ArtReferenceProposalRow,
    AutopilotCheckpointRow,
    AutopilotExecAttemptRow,
    CharacterReferenceProposalRow,
    ImageJobRow,
)
from .autopilot_continuation import project_job_counts
from .autopilot_text_correction import HEADS, _candidate_row
from .creative_execution_pins import freeze_execution_pin
from .creative_terminal import CANDIDATE_ROWS


def assert_execution_retry_lineage(connection, *, run_id, operation_key, evidence):
    lineage = evidence.result.get("executionRetry")
    if not lineage:
        if ":retry:" in operation_key:
            raise ValueError("retry operation has no retained predecessor")
        return operation_key
    parent = connection.execute("SELECT evidence FROM v2_autopilot_checkpoints WHERE run_id=? AND operation_key=?",
                                (run_id, lineage["parentOperationKey"])).fetchone()
    source = connection.execute("SELECT snapshot FROM v2_autopilot_exec_attempts WHERE id=? AND run_id=?",
                                (lineage["predecessorAttemptId"], run_id)).fetchone()
    policy = connection.execute("SELECT policy FROM v2_autopilot_runs WHERE id=?", (run_id,)).fetchone()
    if parent is None or source is None or policy is None:
        raise ValueError("retry predecessor is unavailable")
    prior = CheckpointEvidence.model_validate_json(parent[0])
    attempt = CodexExecAttempt.model_validate_json(source[0])
    historical = CodexExecAttempt.model_validate(lineage["predecessorAttemptSnapshot"])
    immutable = ("attempt_id", "run_id", "project_id", "job_id", "operation_key", "domain", "request_hash", "package_hash", "profile_hash", "plotloom_code_revision", "validation_plan_hash", "reserved_image_outputs")
    if any(getattr(historical, key) != getattr(attempt, key) for key in immutable):
        raise ValueError("execution retry predecessor immutable identity changed")
    previous = prior.result.get("executionRetry", {}).get("ordinal", 0)
    limit = LaunchPolicy.model_validate_json(policy[0]).automatic_retry_limit or 0
    if (not repeatable_failure(historical) or not lineage.get("localExecutionStopped")
            or lineage["ordinal"] != previous + 1
            or lineage.get("automaticRetriesUsed",lineage["ordinal"]) > limit
            or lineage.get("automaticRetriesUsed",lineage["ordinal"]) != prior.result.get("executionRetry",{}).get("automaticRetriesUsed",previous) + (0 if lineage.get("manualCommandId") else 1)
            or lineage["predecessorJobId"] != prior.job_id or prior.executor_attempt_id != attempt.attempt_id
            or retry_root(operation_key) != retry_root(lineage["parentOperationKey"])
            or operation_key != f'{retry_root(operation_key)}:retry:{lineage["ordinal"]}'
            or evidence.owner != prior.owner or evidence.execution_pin != prior.execution_pin):
        raise ValueError("execution retry differs from its finite original authority")
    # A retry can change physical identities only, never the frozen generation input.
    from .autopilot_bindings import CREATIVE_OWNERS, IMAGE_OWNERS
    owner = evidence.owner
    table = CREATIVE_OWNERS[owner] if owner in CREATIVE_OWNERS else IMAGE_OWNERS[owner][0]
    bridge = owner.startswith("bridge-")
    field = "native_request" if bridge else "request"
    identifier = "id" if bridge or owner in IMAGE_OWNERS else "job_id"
    import json
    values = []
    for job in (evidence.job_id, prior.job_id):
        record = connection.execute(f'SELECT {field} FROM "{table}" WHERE {identifier}=?', (job,)).fetchone()
        if record is None:
            raise ValueError("retry frozen input is unavailable")
        values.append(json.loads(record[0]))
    values[0]["jobId"] = values[1]["jobId"]
    if values[0] != values[1]:
        raise ValueError("execution retry changed frozen source or settings")
    assert_execution_retry_lineage(connection, run_id=run_id, operation_key=lineage["parentOperationKey"], evidence=prior)
    return retry_root(operation_key)


def creative_retry_origin(connection, *, run_id, evidence):
    import json

    from .autopilot_bindings import CREATIVE_OWNERS
    while evidence.result.get("executionRetry"):
        key = evidence.result["executionRetry"]["parentOperationKey"]
        raw = connection.execute("SELECT evidence FROM v2_autopilot_checkpoints WHERE run_id=? AND operation_key=?",
                                 (run_id,key)).fetchone()
        evidence = CheckpointEvidence.model_validate_json(raw[0])
    bridge = evidence.owner.startswith("bridge-")
    row = connection.execute(f'SELECT {"native_request" if bridge else "request"} FROM "{CREATIVE_OWNERS[evidence.owner]}" WHERE {"id" if bridge else "job_id"}=?',
                             (evidence.job_id,)).fetchone()
    return CreativeHandoffRequest.model_validate(json.loads(row[0]))


def superseded_execution_attempt(session, run_id, attempt_id):
    for row in session.scalars(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == run_id)):
        lineage = row.evidence.get("result", {}).get("executionRetry", {})
        if lineage.get("predecessorAttemptId") == str(attempt_id):
            assert_execution_retry_lineage(session.connection().connection.driver_connection,
                run_id=run_id, operation_key=row.operation_key, evidence=CheckpointEvidence.model_validate(row.evidence))
            return True
    return False


class AutopilotExecutionRetryPersistence:
    def prepare_execution_retry(self, operation_key, expected_attempt, *, manual_command_id=None):
        authority = self.access.authority()
        if (authority is None and manual_command_id is None) or (authority is not None and authority.scope not in {OperationScope.TEXT, OperationScope.INSTALL, OperationScope.IMAGE}):
            raise InvalidTransitionError("execution retry requires current generation authority")
        with self.access.leases.lifecycle_write() as session:
            if authority is None:
                from ...autopilot_contracts import CommandAuthority
                retained = self.row(session,str(expected_attempt.project_id))
                scope = OperationScope.IMAGE if expected_attempt.domain == "image" else OperationScope.INSTALL if expected_attempt.operation_key.startswith("bridge-") else OperationScope.TEXT
                authority = CommandAuthority(str(expected_attempt.run_id),retained.claim,scope)
            run = self.validate_command(session, authority)
            policy = LaunchPolicy.model_validate(run.policy)
            parent = session.scalar(select(AutopilotCheckpointRow).where(
                AutopilotCheckpointRow.run_id == run.id, AutopilotCheckpointRow.operation_key == operation_key))
            prior_attempt = session.get(AutopilotExecAttemptRow, str(expected_attempt.attempt_id))
            if (parent is None or prior_attempt is None or prior_attempt.run_id != run.id
                    or CodexExecAttempt.model_validate(prior_attempt.snapshot) != expected_attempt
                    or not repeatable_failure(expected_attempt)):
                raise InvalidTransitionError("retry predecessor changed")
            evidence = CheckpointEvidence.model_validate(parent.evidence)
            ordinal = evidence.result.get("executionRetry", {}).get("ordinal", 0) + 1
            key = f"{retry_root(operation_key)}:retry:{ordinal}"
            existing = session.scalar(select(AutopilotCheckpointRow).where(
                AutopilotCheckpointRow.run_id == run.id, AutopilotCheckpointRow.operation_key == key))
            if existing is not None:
                return existing.evidence["jobId"]
            automatic_used = evidence.result.get("executionRetry", {}).get("automaticRetriesUsed", ordinal - 1) + (0 if manual_command_id else 1)
            if policy.automatic_retry_limit is None or automatic_used > policy.automatic_retry_limit:
                raise InvalidTransitionError("automatic retry allowance exhausted")
            jobs, images = project_job_counts(session, run.project_id)
            if exceeds_budget(jobs + 1, policy.max_jobs) or (
                    expected_attempt.domain == "image" and exceeds_budget(images + 1, policy.max_images)):
                raise InvalidTransitionError("execution retry exceeds original generation budget")
            prefix = "ch_" if expected_attempt.domain == "text" else evidence.job_id.split("_", 1)[0] + "_"
            job_id = prefix + uuid5(NAMESPACE_URL, f"plotloom:execution-retry:{run.id}:{expected_attempt.attempt_id}:{ordinal}").hex
            now = utc_now()
            if expected_attempt.domain == "text":
                original = _candidate_row(session, evidence.owner, evidence.job_id)
                row_type = CANDIDATE_ROWS[evidence.owner]
                values = {c.key: getattr(original, c.key) for c in row_type.__table__.columns}
                bridge = evidence.owner.startswith("bridge-")
                request = CreativeHandoffRequest.model_validate(original.native_request if bridge else original.request)
                request = request.model_copy(update={"job_id": job_id})
                if bridge:
                    values.update(id=job_id, native_request=request.model_dump(mode="json", by_alias=True),
                        status="queued", created_at=now, updated_at=now, dispatched_at=None, response_evidence=None,
                        response_hash=None, candidate=None, provider_request_id=None, usage=None, error_code=None,
                        error_message=None, result_proposal_revision=None,
                        prompt_trace=original.prompt_trace | {"rendered_hash": request_hash(request)})
                else:
                    field = {"outline":"outline","branches":"outline","characters":"cast","art":"art",
                             "script":"script","storyboard":"storyboard"}[evidence.owner]
                    values.update(job_id=job_id, request=request.model_dump(mode="json", by_alias=True), status="prepared",
                        created_at=now, delivery_id=None, manifest_hash=None, report_html=None, delivered_at=None, **{field:None})
                    head_type = HEADS[evidence.owner]
                    head = session.get(head_type, run.project_id) if head_type else None
                    if head is not None:
                        if head.candidate_job_id != evidence.job_id:
                            raise InvalidTransitionError("retry creative head changed")
                        head.candidate_job_id, head.updated_at = job_id, now
                # Retire only the stopped predecessor's publication authority.
                # Its execution snapshot, actual outcome, bytes and spending
                # remain retained; late evidence cannot become the current head.
                original.status = "failed" if bridge else "cancelled"
                if bridge:
                    original.error_code = "execution.superseded"
                    original.error_message = "A fresh execution retry owns publication; prior execution evidence is retained."
                    original.updated_at = now
                session.add(row_type(**values))
                freeze_execution_pin(session, request, evidence.execution_pin)
                frozen_hash = request_hash(request)
                subject_id = job_id
            else:
                row_type = {"image":ImageJobRow, "character-reference":CharacterReferenceProposalRow,
                            "art-reference":ArtReferenceProposalRow}[evidence.owner]
                original = session.get(row_type, evidence.job_id)
                values = {c.key: getattr(original, c.key) for c in row_type.__table__.columns}
                request = dict(original.request) | {"jobId":job_id}
                frozen_hash = stable_hash(request)
                values.update(id=job_id, request=request, request_hash=frozen_hash, state="prepared",
                    exported_at=None, cancelled_at=None, cancellation_reason=None, created_at=now)
                original.state, original.cancelled_at, original.cancellation_reason = "cancelled", now, "superseded_by_execution_retry"
                session.add(row_type(**values))
                subject_id = evidence.subject_id
            lineage = {"ordinal":ordinal, "parentOperationKey":operation_key, "predecessorJobId":evidence.job_id,
                "predecessorAttemptId":str(expected_attempt.attempt_id), "predecessorAttemptSnapshot":expected_attempt.model_dump(mode="json", by_alias=True), "localExecutionStopped":True,
                "automaticRetriesUsed":automatic_used, **({"manualCommandId":str(manual_command_id)} if manual_command_id else {})}
            result = {k:v for k,v in evidence.result.items() if k not in {"executionRetry","executionRetryExhausted","dispatchAttempted","dispatchOutcomeUnknown"}}
            next_evidence = CheckpointEvidence(owner=evidence.owner, subject_id=subject_id, job_id=job_id,
                request_hash=frozen_hash, execution_pin=evidence.execution_pin, result=result | {"executionRetry":lineage})
            session.flush()
            if manual_command_id:
                from .autopilot_bindings import assert_checkpoint_binding
                assert_checkpoint_binding(session.connection().connection.driver_connection,run.project_id,
                    "prepared",next_evidence,run_id=run.id,operation_key=key)
                session.add(AutopilotCheckpointRow(id=new_id(),run_id=run.id,project_id=run.project_id,
                    operation_key=key,revision=1,state="prepared",evidence=next_evidence.model_dump(mode="json",by_alias=True),
                    created_at=now,updated_at=now))
                from .autopilot_closure import material_closure
                session.flush()
                run.expected_closure=material_closure(session,run.project_id)
                run.revision+=1
                run.updated_at=now
            else:
                self.checkpoint(key, state="prepared", evidence=next_evidence)
            return job_id
