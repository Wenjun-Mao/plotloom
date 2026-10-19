"""QA-specific fences at the existing batch, dispatch and receipt owners."""
from sqlalchemy import select

from .delegated_qa import (
    attribution_for_reviewer,
    binding_attribution,
    direction_attribution,
    project_scope,
    require_qa_write,
    require_scope,
)
from .delegated_qa_contracts import QaAvInspection
from .exceptions import InvalidTransitionError
from .persistence.schema import (
    ApprovalDecisionRow,
    ProjectVideoDispatchRow,
    VideoJobRow,
)


def assert_snapshot(scope, snapshot):
    if not isinstance(snapshot, dict) or any(not isinstance(snapshot.get(key), dict)
            for key in ("shot", "keyframe", "request", "provider")):
        raise InvalidTransitionError("QA frozen video source shape is invalid")
    material = next((item for item in scope.materials if item.shot_id == snapshot["shot"]["id"]), None)
    frame, request, provider = snapshot["keyframe"], snapshot["request"], snapshot["provider"]
    if (material is None or frame["assetId"] != material.asset_id or frame["originalHash"] != material.original_hash
            or request.get("profileId") != scope.profile_id or request.get("audio") is not True
            or request.get("aspectPolicy") != "cover_center_crop" or snapshot.get("endFrame") not in (None, {"revision": 0, "assetId": None})
            or provider.get("adapterId") != "minimax_h3_gateway" or provider.get("costPolicy") != "local_capacity_v1"):
        raise InvalidTransitionError("video request exceeds the exact QA material, profile or provider scope")


def assert_preparation_actor(session, project_id, snapshot):
    """Refuse mismatched review facts before they become an immutable job."""
    material_actor = snapshot["keyframe"]["intent"].get("attribution")
    actor = direction_attribution(snapshot)
    if material_actor is None and actor is None:
        return
    if actor is None or actor != material_actor:
        raise InvalidTransitionError("QA material requires its exact QA batch English endorsement before preparation")
    scope = require_scope(project_id, actor)
    approval = session.get(ApprovalDecisionRow, snapshot["approvalId"])
    if approval is None or binding_attribution(project_id, approval, snapshot["keyframe"]["intent"],
            asset_id=snapshot["keyframe"]["assetId"], shot_id=snapshot["shot"]["id"]) != actor:
        raise InvalidTransitionError("QA preparation attribution differs from material review")
    assert_snapshot(scope, snapshot)


def assert_manifest_actor(store, manifest, attribution):
    actor = attribution.model_dump(mode="json", by_alias=True) if attribution else None
    with store.repository._read() as session:
        for target in manifest["targets"]:
            snapshot = target["snapshot"]
            approval = session.get(ApprovalDecisionRow, snapshot["approvalId"])
            if approval is None or attribution_for_reviewer(store.manifest.project_id, approval.reviewer) != actor:
                raise InvalidTransitionError("English endorsement must state the material review's actual attribution")
        if actor:
            scope = require_qa_write(session, store.manifest.project_id, actor)
            if (manifest["setup"]["profileId"] != scope.profile_id
                    or manifest["setup"]["maxJobs"] > scope.max_submissions
                    or manifest["setup"]["maxRequestedSeconds"] > scope.max_requested_seconds
                    or manifest["scopeShotIds"] != sorted(item.shot_id for item in scope.materials)):
                raise InvalidTransitionError("QA batch exceeds the granted profile, shots or caps")
            for target in manifest["targets"]:
                assert_snapshot(scope, target["snapshot"])
    return actor


def assert_dispatch(session, project_id, job):
    """Cumulative claims include failed and UNKNOWN attempts across all batches."""
    scope = project_scope(project_id)
    if scope is None:
        return
    package = job.snapshot.get("reviewedDirections") or {}
    basis = package.get("reviewBasis") or {}
    actor = basis.get("attribution")
    require_scope(project_id, actor)
    assert_snapshot(scope, job.snapshot)
    approval = session.get(ApprovalDecisionRow, job.snapshot["approvalId"])
    if approval is None or binding_attribution(project_id, approval, job.snapshot["keyframe"]["intent"],
            asset_id=job.snapshot["keyframe"]["assetId"], shot_id=job.snapshot["shot"]["id"]) != actor:
        raise InvalidTransitionError("QA dispatch lacks matching material and English attribution")
    claimed = session.scalars(select(VideoJobRow).join(ProjectVideoDispatchRow,
        ProjectVideoDispatchRow.video_job_id == VideoJobRow.id).where(VideoJobRow.project_id == project_id)).all()
    counted = {item.id: item for item in claimed}
    counted[job.id] = job
    if len(counted) > scope.max_submissions or sum(item.requested_seconds for item in counted.values()) > scope.max_requested_seconds:
        raise InvalidTransitionError("cumulative QA submission or requested-seconds cap exhausted")
    if any(item.id != job.id and item.state in {"dispatching", "submitted", "retrieve_needed", "outcome_unknown"} for item in claimed):
        raise InvalidTransitionError("unsettled QA dispatch blocks another submission")


def assert_receipt_actor(project_id, receipt, english_actor):
    actor = receipt.get("attribution")
    if english_actor is None:
        if actor != {"kind": "unnamed_creator"} or "inspection" in receipt:
            raise InvalidTransitionError("human video confirmation attribution changed")
    else:
        require_scope(project_id, actor)
        if actor != english_actor:
            raise InvalidTransitionError("QA final review attribution differs from English endorsement")
        inspection = QaAvInspection.model_validate(receipt.get("inspection"))
        if inspection.model_dump(mode="json", by_alias=True) != receipt["inspection"]:
            raise InvalidTransitionError("QA final inspection is not canonical")
