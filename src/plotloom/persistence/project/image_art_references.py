"""Exact selected Art dependencies for automatic physical shot images."""
from ...image_job_contracts import ImageJobError
from ..schema import (
    ArtReferenceDecisionRow,
    ArtReferenceDecisionStateRow,
    ManagedAssetRow,
)
from .media_art_reference_proposals import ArtReferenceProposalPersistence

ART_REFERENCE_CONTRACT = "plotloom.automatic-image-art-references.v1"
ART_REFERENCE_ROLES = frozenset({"scene_environment", "prop_identity"})


def required_art_subjects(shot, resolved_context):
    """Canonical Art IDs already cross the bridge; never guess from names."""
    locations = [shot.location_id, *(item["id"] for item in resolved_context["locations"])]
    props = [*shot.prop_ids, *(item["id"] for item in resolved_context["props"])]
    return list(dict.fromkeys([
        *(("scene", value) for value in locations if value is not None),
        *(("prop", value) for value in props),
    ]))


def freeze_art_references(session, project_id, subjects, art_references: ArtReferenceProposalPersistence):
    result = []
    for kind, subject_id in subjects:
        state = session.get(ArtReferenceDecisionStateRow, (project_id, kind, subject_id))
        decision = session.get(ArtReferenceDecisionRow, state.active_decision_id) if state and state.active_decision_id else None
        if (decision is None or decision.subject_type != kind or decision.subject_id != subject_id
                or state.revision != decision.reference_revision
                or not art_references._decision_is_current_in_session(session, project_id, decision.id)):
            raise ImageJobError("art_reference_missing", f"当前镜头需要已选定且有效的美术参考：{kind}:{subject_id}。")
        asset = session.get(ManagedAssetRow, decision.asset_id)
        result.append({
            "role": "scene_environment" if kind == "scene" else "prop_identity",
            "subjectType": kind, "subjectId": subject_id,
            "referenceDecisionId": decision.id, "referenceRevision": decision.reference_revision,
            "acceptedArtRevision": decision.accepted_art_revision, "acceptedArtHash": decision.accepted_art_hash,
            "subjectHash": decision.subject_hash,
            "assetId": asset.id, "originalHash": asset.original_hash,
            "mimeType": asset.mime_type, "byteSize": asset.byte_size, "width": asset.width, "height": asset.height,
        })
    return result


def art_references_current(session, project_id, snapshot, art_references):
    """A retained snapshot is never repaired or upgraded during a read."""
    if "artReferenceContract" not in snapshot:
        return True
    if snapshot["artReferenceContract"] != ART_REFERENCE_CONTRACT:
        return False
    from types import SimpleNamespace
    try:
        shot = snapshot["shot"]
        subjects = required_art_subjects(SimpleNamespace(location_id=shot["locationId"], prop_ids=shot["propIds"]),
            snapshot["resolvedContext"])
        expected = freeze_art_references(session, project_id, subjects, art_references)
        actual = [item for item in snapshot["references"] if item.get("role") in ART_REFERENCE_ROLES]
        return actual == expected
    except (ImageJobError, KeyError, TypeError, AttributeError):
        return False


def reusable_image_checkpoints(session, checkpoints):
    """Continue can reuse current-contract frames, never missing Art dependencies."""
    from ..schema import ImageJobRow
    result, reusable_jobs = [], set()
    for checkpoint in checkpoints:
        if checkpoint.evidence["owner"] == "image":
            job = session.get(ImageJobRow, checkpoint.evidence.get("jobId"))
            if job is None or job.request["frozenSnapshot"].get("artReferenceContract") != ART_REFERENCE_CONTRACT:
                continue
            reusable_jobs.add(job.id)
        result.append(checkpoint)
    return [row for row in result if row.evidence["owner"] != "geometry-preparation"
        or row.evidence["geometryPreparation"]["source"]["jobId"] in reusable_jobs]
