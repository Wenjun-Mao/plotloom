"""Exact human-reviewed or machine-provisional adaptation source authority."""
from sqlalchemy import select
from ...autopilot_contracts import OperationScope
from ...exceptions import InvalidTransitionError
from ...keyframe_preparation import has_matching_aspect
from ..schema import (AutopilotCheckpointRow, AutopilotDecisionRow, AutopilotRunRow,
    ImageJobRow, ImageJobCandidateRow, ImageJobDeliveryRow, ProductionUnitRow,
    ManagedAssetRow, ReviewedShotBindingRow, VisualIntentRow)
from .autopilot_authority import require_machine_scope


def machine_source(session, access, project_id, shot_id, approval, adaptation):
    authority = require_machine_scope(access, OperationScope.IMAGE)
    run = session.get(AutopilotRunRow, authority.run_id)
    source = adaptation.get("machineProvisionalSource")
    if not isinstance(source, dict) or set(source) != {"decisionId", "assetId", "jobId"}:
        raise InvalidTransitionError("machine adaptation requires an exact provisional source")
    decision = session.get(AutopilotDecisionRow, source["decisionId"])
    checkpoint = session.get(AutopilotCheckpointRow, decision.checkpoint_id) if decision else None
    asset = session.get(ManagedAssetRow, source["assetId"])
    job = session.get(ImageJobRow, source["jobId"])
    unit = session.get(ProductionUnitRow, job.production_unit_id) if job else None
    candidate = session.scalar(select(ImageJobCandidateRow).where(ImageJobCandidateRow.job_id == source["jobId"],
        ImageJobCandidateRow.asset_id == source["assetId"]))
    delivery = session.get(ImageJobDeliveryRow, candidate.delivery_id) if candidate else None
    if (decision is None or checkpoint is None or asset is None or job is None or unit is None or delivery is None
            or any(row.project_id != project_id for row in (decision, checkpoint, asset, job, unit))
            or decision.run_id != run.id or decision.scope != OperationScope.SELECT.value
            or checkpoint.state != "adopted" or checkpoint.evidence["jobId"] != job.id
            or checkpoint.evidence["result"].get("geometryCompatible") is not False
            or checkpoint.evidence["result"].get("assetId") != asset.id
            or {"assetId": asset.id, "originalHash": asset.original_hash} not in decision.decision["selectedAssets"]
            or unit.shot_id != shot_id or unit.storyboard_entity_revision_id != approval.entity_revision_id
            or unit.storyboard_revision != approval.subject_revision or unit.machine_decision_id is None
            or job.request["kind"] != "original" or job.state != "delivered" or delivery.state != "accepted"
            or candidate.output_hash != asset.original_hash):
        raise InvalidTransitionError("machine adaptation source lacks exact current retained original evidence")
    target = adaptation.get("targetProfile")
    expected = {"id": "autopilot-brief-geometry", "width": run.policy["imageWidth"], "height": run.policy["imageHeight"]}
    if target != expected:
        raise InvalidTransitionError("machine adaptation geometry must equal the frozen Brief policy")
    return asset, {"sourceAuthority": {"actor": "machine_provisional", "runId": run.id, "decisionId": decision.id},
        "sourceJobId": job.id, "sourceAssetId": asset.id, "sourceOriginalHash": asset.original_hash,
        "targetProfile": expected}


def prepare_adaptation_source(session, access, admission, currentness, project_id, shot_id, approval, adaptation):
    if approval.machine_decision_id is not None:
        asset, snapshot = machine_source(session, access, project_id, shot_id, approval, adaptation)
        if not currentness.image_job_is_current_in_session(session, session.get(ImageJobRow, snapshot["sourceJobId"])):
            raise InvalidTransitionError("machine adaptation original source dependencies changed")
    else:
        if "machineProvisionalSource" in adaptation:
            raise InvalidTransitionError("human adaptation cannot borrow provisional machine authority")
        binding = session.scalar(select(ReviewedShotBindingRow).where(ReviewedShotBindingRow.project_id == project_id,
            ReviewedShotBindingRow.shot_id == shot_id).order_by(ReviewedShotBindingRow.selection_revision.desc()).limit(1))
        if binding is None or not admission.reviewed_binding_admission_eligible_in_session(session, project_id, binding, approval=approval):
            raise InvalidTransitionError("keyframe adaptation needs the current reviewed selected keyframe")
        asset = session.get(ManagedAssetRow, binding.asset_id)
        intent = session.get(VisualIntentRow, binding.visual_intent_id)
        if (asset is None or asset.project_id != project_id or intent is None or intent.project_id != project_id
                or intent.asset_id != asset.id or intent.revision != binding.visual_intent_revision):
            raise InvalidTransitionError("keyframe adaptation source is unavailable or no longer reviewable")
        snapshot = {"sourceBindingId": binding.id, "sourceSelectionRevision": binding.selection_revision,
            "sourceAssetId": asset.id, "sourceOriginalHash": asset.original_hash,
            "sourceVisualIntentId": intent.id, "sourceVisualIntentRevision": intent.revision,
            "targetProfile": dict(adaptation["targetProfile"])}
    width, height = int(snapshot["targetProfile"]["width"]), int(snapshot["targetProfile"]["height"])
    if has_matching_aspect(asset.width, asset.height, width, height):
        raise InvalidTransitionError("source keyframe already matches the requested adaptation profile")
    snapshot["outputContract"] = {"width": width, "height": height, "mimeTypes": ["image/jpeg", "image/png"]}
    reference = {"assetId": asset.id, "role": "source_keyframe", "required": True, "originalHash": asset.original_hash,
        "mimeType": asset.mime_type, "byteSize": asset.byte_size, "width": asset.width, "height": asset.height}
    return reference, snapshot


def validate_adaptation_outputs(request, outputs):
    from ...image_job_contracts import ImageJobError
    adaptation = request.get("frozenSnapshot", {}).get("keyframeAdaptation")
    if adaptation is None:
        return
    contract = adaptation.get("outputContract")
    if not isinstance(contract, dict):
        raise ImageJobError("delivery_geometry_contract_invalid", "keyframe adaptation lacks its frozen output contract")
    expected = contract.get("width"), contract.get("height")
    if any(item["role"] != "keyframe_adaptation" or (item["width"], item["height"]) != expected for item in outputs):
        raise ImageJobError("delivery_geometry_mismatch", "adaptation requires the frozen role and exact dimensions")
