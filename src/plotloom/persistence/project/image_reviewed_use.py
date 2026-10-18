"""Binding-aware image use and frozen reviewed-frame evidence."""
import json
from hashlib import sha256
from pathlib import Path

from ...cross_shot_image_contracts import CrossShotTargetUse, ReviewedFrameSource
from ...exceptions import InvalidTransitionError
from ..codec import stable_hash
from ..schema import (
    ImageJobRow,
    ManagedAssetRow,
    ReviewedShotBindingRow,
    VisualIntentRow,
)
from .image_source_lineage import _row, resolve_image_source


def connection_for(session):
    return session.connection().connection.driver_connection


def _assert_source_bytes(connection, asset, *, asset_home=None):
    from ...project_storage.artifacts import ProjectArtifactStore, _OwnedArtifactStore
    from ...project_storage.format import ProjectStorageError
    database = next((row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"), None)
    if database is None or not 0 < asset["byte_size"] <= 64 * 1024 * 1024:
        raise ValueError("reviewed source lacks bounded project-owned bytes")
    try:
        store = ProjectArtifactStore(_OwnedArtifactStore(asset_home or Path(database).parent, create=False), writable=False)
        content = store.get(asset["original_uri"])
    except (OSError, ValueError, ProjectStorageError) as error:
        raise ValueError("reviewed source bytes are unavailable") from error
    if len(content) != asset["byte_size"] or sha256(content).hexdigest() != asset["original_hash"]:
        raise ValueError("reviewed source bytes changed")


def _origin(connection, source):
    if source is None:
        return None, None, None
    job = _row(connection, "SELECT * FROM v2_image_jobs WHERE id=?", (source.job_id,))
    candidate = _row(connection, "SELECT * FROM v2_image_job_candidates WHERE id=?", (source.candidate_id,))
    delivery = _row(connection, "SELECT * FROM v2_image_job_deliveries WHERE id=?", (candidate["delivery_id"],))
    request, manifest = json.loads(job["request"]), json.loads(delivery["manifest"])
    if (stable_hash(request) != job["request_hash"] or candidate["job_id"] != job["id"]
            or delivery["job_id"] != job["id"] or delivery["state"] != "accepted"
            or stable_hash(manifest) != delivery["manifest_hash"]):
        raise ValueError("reviewed source native origin evidence changed")
    return request.get("frozenSnapshot", {}).get("shot", {}).get("id"), job["request_hash"], delivery["manifest_hash"]


def _binding_identity(binding):
    return {key: binding[key] for key in (
        "id", "project_id", "asset_id", "shot_id", "scene_id", "visual_intent_id",
        "visual_intent_revision", "approval_id", "storyboard_entity_revision_id",
        "storyboard_revision", "selection_revision", "compatibility_note",
    )}


def resolve_reviewed_use(connection, project_id, asset_id, shot_id, intent, *, asset_home=None, ancestors=frozenset(), continuation=True):
    """Historical proof; source selection position is deliberately not authority."""
    use = intent.get("targetUse")
    if use is None:
        return resolve_image_source(connection, project_id, asset_id, shot_id=shot_id, asset_home=asset_home, continuation=continuation)
    parsed = CrossShotTargetUse.model_validate(use)
    if intent.get("role") != "shot_keyframe" or parsed.target_shot_id != shot_id:
        raise ValueError("target use does not name this shot keyframe")
    context = parsed.target_context
    approval = _row(connection, "SELECT * FROM v2_approval_decisions WHERE id=?", (context.approval_id,))
    if (approval["project_id"] != project_id or approval["decision"] != "approve"
            or approval["entity_revision_id"] != context.storyboard_entity_revision_id
            or approval["subject_revision"] != context.storyboard_revision):
        raise ValueError("target use approval context changed")
    frozen = parsed.source
    if frozen.binding_id in ancestors or frozen.source_shot_id == shot_id:
        raise ValueError("cross-shot use is cyclic or self-referential")
    source = validate_reviewed_source(connection, project_id, frozen, asset_home=asset_home,
        ancestors=ancestors | {frozen.binding_id}, continuation=continuation)
    if frozen.asset_id != asset_id:
        raise ValueError("target use cannot change source pixels")
    return source


def validate_reviewed_source(connection, project_id, frozen, *, asset_home=None, ancestors=frozenset(), continuation=True):
    frozen = ReviewedFrameSource.model_validate(frozen)
    binding = _row(connection, "SELECT * FROM v2_reviewed_shot_bindings WHERE id=?", (frozen.binding_id,))
    intent = _row(connection, "SELECT * FROM v2_visual_intents WHERE id=?", (binding["visual_intent_id"],))
    asset = _row(connection, "SELECT * FROM v2_managed_assets WHERE id=?", (binding["asset_id"],))
    payload = json.loads(intent["intent"])
    if (any(row["project_id"] != project_id for row in (binding, intent, asset))
            or stable_hash(_binding_identity(binding)) != frozen.binding_hash
            or intent["id"] != frozen.visual_intent_id or intent["revision"] != frozen.visual_intent_revision
            or intent["asset_id"] != asset["id"] or stable_hash(payload) != frozen.intent_hash
            or asset["id"] != frozen.asset_id or asset["original_hash"] != frozen.original_hash
            or binding["shot_id"] != frozen.source_shot_id):
        raise ValueError("reviewed source identity, intent or bytes changed")
    _assert_source_bytes(connection, asset, asset_home=asset_home)
    source = resolve_reviewed_use(connection, project_id, asset["id"], binding["shot_id"], payload,
        asset_home=asset_home, ancestors=ancestors, continuation=continuation)
    origin_shot, request_hash, delivery_hash = _origin(connection, source)
    if (frozen.origin_job_id != (source.job_id if source else None)
            or frozen.origin_candidate_id != (source.candidate_id if source else None)
            or frozen.origin_shot_id != origin_shot or frozen.origin_request_hash != request_hash
            or frozen.origin_delivery_hash != delivery_hash):
        raise ValueError("reviewed source origin changed")
    return source


def use_in_session(session, binding, *, currentness=None):
    intent = session.get(VisualIntentRow, binding.visual_intent_id)
    if intent is None or intent.project_id != binding.project_id or intent.asset_id != binding.asset_id or intent.revision != binding.visual_intent_revision:
        raise InvalidTransitionError("reviewed use lacks its exact visual intent")
    try:
        source = resolve_reviewed_use(connection_for(session), binding.project_id, binding.asset_id, binding.shot_id, intent.intent)
        if currentness is not None:
            require_use_current(session, binding.project_id, intent.intent, currentness)
            if source:
                job = session.get(ImageJobRow, source.job_id)
                eligible = currentness.image_source_is_current_in_session if intent.intent.get("targetUse") else currentness.image_job_is_current_in_session
                if job is None or job.state != "delivered" or not eligible(session, job):
                    raise ValueError("generated source is no longer currently applicable")
        return source
    except (ValueError, TypeError, KeyError) as error:
        raise InvalidTransitionError(str(error)) from error


def require_use_current(session, project_id, intent, currentness):
    use = intent.get("targetUse")
    if use is None:
        return
    parsed = CrossShotTargetUse.model_validate(use)
    context = parsed.target_context
    approval = currentness._admission.approval_is_active_in_session(session, context.approval_id)
    if (approval.project_id != project_id or approval.entity_revision_id != context.storyboard_entity_revision_id
            or approval.subject_revision != context.storyboard_revision
            or stable_hash(currentness.presentations.current(session, project_id, parsed.target_shot_id)) != context.presentation_hash):
        raise ValueError("target image use context is no longer current")
    frozen = parsed.source
    binding = session.get(ReviewedShotBindingRow, frozen.binding_id)
    if binding is None or not currentness._admission.reviewed_binding_context_current_in_session(session, project_id, binding):
        raise ValueError("source review context is no longer current")
    source_intent = session.get(VisualIntentRow, binding.visual_intent_id)
    require_use_current(session, project_id, source_intent.intent, currentness)


def freeze_target_context(session, project_id, target_shot_id, source_binding_id, admission, currentness):
    from ...cross_shot_image_contracts import TargetUseContext
    binding = session.get(ReviewedShotBindingRow, source_binding_id)
    approval = admission.approval_is_active_in_session(session, binding.approval_id)
    return TargetUseContext(approval_id=approval.id, storyboard_entity_revision_id=approval.entity_revision_id,
        storyboard_revision=approval.subject_revision,
        presentation_hash=stable_hash(currentness.presentations.current(session, project_id, target_shot_id)))


def retain_target_use(session, project_id, asset_id, target_shot_id, intent_id, source_binding_id, admission, currentness):
    retained = session.get(VisualIntentRow, intent_id)
    if retained is None or retained.project_id != project_id or retained.asset_id != asset_id:
        raise ValueError("retained visual intent does not belong to this target asset")
    use = CrossShotTargetUse.model_validate(retained.intent.get("targetUse"))
    latest = admission.latest_visual_intent_for_role_in_session(session, project_id, asset_id, "shot_keyframe", target_shot_id)
    if (use.target_shot_id != target_shot_id or use.source.binding_id != source_binding_id
            or latest is None or latest.id != retained.id):
        raise ValueError("retained visual intent must be the current exact target/source choice")
    source = resolve_reviewed_use(connection_for(session), project_id, asset_id, target_shot_id, retained.intent)
    require_use_current(session, project_id, retained.intent, currentness)
    if source:
        job = session.get(ImageJobRow, source.job_id)
        if job is None or job.state != "delivered" or not currentness.image_source_is_current_in_session(session, job):
            raise ValueError("retained target use source is no longer applicable")
    return use.model_dump(mode="json", by_alias=True)


def freeze_reviewed_source(session, project_id, binding_id, target_shot_id, admission, currentness):
    binding = session.get(ReviewedShotBindingRow, binding_id)
    if (binding is None or binding.project_id != project_id or binding.shot_id == target_shot_id
            or not admission.reviewed_binding_admission_eligible_in_session(session, project_id, binding)):
        raise InvalidTransitionError("cross-shot use requires another shot's current reviewed frame in this project")
    source = use_in_session(session, binding, currentness=currentness)
    intent = session.get(VisualIntentRow, binding.visual_intent_id)
    asset = session.get(ManagedAssetRow, binding.asset_id)
    connection = connection_for(session)
    raw = _row(connection, "SELECT * FROM v2_reviewed_shot_bindings WHERE id=?", (binding.id,))
    _assert_source_bytes(connection, _row(connection, "SELECT * FROM v2_managed_assets WHERE id=?", (asset.id,)))
    origin_shot, request_hash, delivery_hash = _origin(connection, source)
    frozen = ReviewedFrameSource(binding_id=binding.id, binding_hash=stable_hash(_binding_identity(raw)),
        visual_intent_id=intent.id, visual_intent_revision=intent.revision, intent_hash=stable_hash(intent.intent),
        asset_id=asset.id, original_hash=asset.original_hash, source_shot_id=binding.shot_id,
        origin_shot_id=origin_shot, origin_request_hash=request_hash, origin_delivery_hash=delivery_hash,
        origin_job_id=source.job_id if source else None, origin_candidate_id=source.candidate_id if source else None)
    # Reject any chain that would return to the target shot, even before a new binding exists.
    seen = {target_shot_id}
    cursor = intent.intent.get("targetUse")
    while cursor:
        inherited = CrossShotTargetUse.model_validate(cursor)
        if inherited.target_shot_id in seen or inherited.source.source_shot_id in seen:
            raise InvalidTransitionError("cross-shot use would create a shot cycle")
        seen.add(inherited.target_shot_id)
        cursor = session.get(VisualIntentRow, inherited.source.visual_intent_id).intent.get("targetUse")
    return frozen, asset
