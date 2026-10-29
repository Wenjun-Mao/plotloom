"""Fresh H3 attempts under the same exact retained production authority."""
from copy import deepcopy

from sqlalchemy import select

from ...contract_identity import utc_now
from ...exceptions import InvalidTransitionError
from ...provider_budgets import exceeds_budget
from ..codec import stable_hash
from ..schema import ProjectVideoDispatchRow, VideoBatchRow, VideoJobRow


def prepare_video_retry(owner, project_id, job_id, *, manual_command_id=None, expected_revision=None):
    owner.assert_video_authority(project_id)
    with owner._access.leases.lifecycle_write() as session:
        prior = session.get(VideoJobRow, job_id)
        if prior is None or prior.project_id != project_id:
            raise InvalidTransitionError("retry predecessor is unavailable")
        basis = (prior.snapshot.get("reviewedDirections") or {}).get("reviewBasis") or {}
        batch = session.get(VideoBatchRow, basis.get("batchId"))
        if batch is None or batch.state not in ({"running","blocked"} if manual_command_id else {"running"}) or batch.project_id != project_id:
            return None
        if manual_command_id:
            known = batch.execution.get("manualRetryCommands", {}).get(str(manual_command_id))
            if known:
                if known["failedJobId"] != job_id:
                    raise InvalidTransitionError("manual retry command changed its failed identity")
                return known["successorJobId"]
            if expected_revision != batch.revision:
                raise InvalidTransitionError("manual retry batch revision changed")
        shot = prior.snapshot["shot"]["id"]
        if shot in batch.execution.get("cancelledTargets",[]):
            return None
        current = batch.execution["jobs"].get(shot)
        if current != job_id:
            return None if manual_command_id else current  # Another controller installed the sole successor.
        policy = prior.snapshot["request"].get("automaticRetryLimit")
        lineage = prior.snapshot.get("executionRetry", {})
        ordinal = lineage.get("ordinal", 0) + 1
        if (policy is None or prior.state not in {"failed", "outcome_unknown"}
                or prior.cancel_requested_at is not None):
            return None
        if not (prior.observed or {}).get("localExecutionStopped"):
            return None
        if any(code in (prior.error or "").lower() for code in
               ("permission", "unauthorized", "authorization", "configuration", "invalid_config", "status_401", "status_403", "credential_unavailable", "profile_unavailable", "local_precondition_failed")):
            return None
        automatic_used = lineage.get("automaticRetriesUsed", lineage.get("ordinal",0)) + (0 if manual_command_id else 1)
        if automatic_used > policy:
            return None
        if not owner._currentness.video_job_current_in_session(session, prior):
            raise InvalidTransitionError("retry source or production authority changed")
        from ...persistence.project.autopilot_closure import material_closure
        if material_closure(session,project_id) != batch.manifest["sourceBinding"]:
            raise InvalidTransitionError("retry complete source authority changed")
        from ...video_batch_basis import assert_direction_basis
        assert_direction_basis(session, prior.snapshot)
        history = deepcopy(batch.execution.get("retryHistory", {}))
        all_ids = set(batch.execution["jobs"].values()) | {identifier for ids in history.values() for identifier in ids}
        rows = session.scalars(select(VideoJobRow).where(VideoJobRow.id.in_(all_ids))).all()
        claims = session.scalars(select(ProjectVideoDispatchRow).where(ProjectVideoDispatchRow.video_job_id.in_(all_ids))).all()
        spent = {claim.video_job_id for claim in claims}
        seconds = sum(row.requested_seconds for row in rows if row.id in spent) + prior.requested_seconds
        caps = batch.manifest["setup"]
        if exceeds_budget(len(spent) + 1, caps["maxJobs"]) or exceeds_budget(seconds, caps["maxRequestedSeconds"]):
            raise InvalidTransitionError("retry exceeds the original finite video allowance")
        now = utc_now()
        identifier = owner._currentness.video_job_id()
        snapshot = deepcopy(prior.snapshot)
        predecessors = [*lineage.get("predecessorJobIds", []), prior.id]
        snapshot["executionRetry"] = {"ordinal":ordinal, "predecessorJobIds":predecessors,
                                      "rootJobId":lineage.get("rootJobId", prior.id), "automaticRetriesUsed":automatic_used, "localExecutionStopped":True,
                                      **({"manualCommandId":str(manual_command_id)} if manual_command_id else {})}
        key = f'{lineage.get("rootJobId", prior.id)}:retry:{ordinal}'
        row = VideoJobRow(id=identifier, project_id=project_id, idempotency_key=key,
            request_hash=stable_hash({"snapshot":snapshot, "idempotencyKey":key}), snapshot=snapshot,
            snapshot_hash=stable_hash(snapshot), requested_seconds=prior.requested_seconds, state="prepared",
            provider_prediction_id=None, output_uri=None, output_hash=None, observed=None, error=None,
            created_at=now, updated_at=now, dispatched_at=None, cancel_requested_at=None)
        session.add(row)
        history[shot] = [*history.get(shot, []), prior.id]
        # Failures describe the current physical target. The predecessor's
        # outcome and charge remain in its immutable job/dispatch history.
        failures = {target: failure for target, failure in batch.execution.get("failures", {}).items() if target != shot}
        batch.execution = batch.execution | {"retryHistory":history, "jobs":batch.execution["jobs"] | {shot:identifier},
            "failures":failures, "error":batch.execution.get("error") if failures else None}
        if manual_command_id:
            commands = batch.execution.get("manualRetryCommands", {}) | {str(manual_command_id):
                {"failedJobId":job_id,"successorJobId":identifier}}
            batch.execution = batch.execution | {"manualRetryCommands":commands}
            batch.state = "running"
        batch.revision += 1
        batch.updated_at = now
        session.flush()
        return identifier
