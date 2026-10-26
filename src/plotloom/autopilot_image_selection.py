"""Technical provisional selection; never supplies human review observations."""
from sqlalchemy import select

from .autopilot_contracts import CheckpointEvidence, ProvisionalFrame
from .autopilot_materials import AutomaticMaterialBundle, GalleryMaterial
from plotloom.stage_contracts import StageName
from .exceptions import InvalidTransitionError
from .image_commands import image_context
from .keyframe_preparation import has_matching_aspect
from .persistence.schema import (
    AutopilotCheckpointRow,
    ImageJobRow,
    ManagedAssetRow,
    ProductionUnitRow,
)


def select_image(store, view, subject, checkpoint, inventory):
    evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
    candidates = evidence.result.get("candidateAssetIds", [])
    context = image_context(store, subject.owner, evidence.job_id)
    if not context["current"] or context["state"] != "delivered":
        raise InvalidTransitionError("native image material is no longer currently applicable")
    expected_role = context["request"]["kind"]
    if evidence.result.get("deliveryState") != "accepted" or len(candidates) != 1 or evidence.result.get("outputRoles") != [expected_role]:
        raise InvalidTransitionError("完整素材包要求一个可用初始输出；交付与全部图片已保留，请接管检查。")
    repository = store.repository
    with repository._read() as session:
        asset = session.get(ManagedAssetRow, candidates[0])
        if asset is None or asset.project_id != view.project_id:
            raise InvalidTransitionError("material candidate bytes unavailable")
        compatible = subject.owner != "image" or has_matching_aspect(asset.width, asset.height, view.policy.image_width, view.policy.image_height)
        selection = {"assetId": asset.id, "originalHash": asset.original_hash}
        result = evidence.result | {"assetId": asset.id, "originalHash": asset.original_hash,
            "width": asset.width, "height": asset.height, "geometryCompatible": compatible}
        if subject.owner == "character-reference":
            bible = repository._canonical._load_stage_payload(session, view.project_id, StageName.STORY_BIBLE)
            cast = store.cast_state().accepted_cast
            if cast is None or cast.revision != inventory.cast_revision:
                raise InvalidTransitionError("reference selection requires the frozen accepted Cast mapping")
            character_id = next((item.consumer_character_id for item in cast.consumer_mappings
                if item.cast_character_id == subject.id), None)
            if character_id is None or not any(item.id == character_id for item in bible.characters):
                raise InvalidTransitionError("reference selection requires its explicit current canonical character")
            if character_id != subject.consumer_character_id or character_id != evidence.subject_id:
                raise InvalidTransitionError("reference selection consumer differs from its frozen inventory and proposal")
            values = store.media.list_character_reference_decisions(view.project_id)
            current = next((item for item in values["states"] if item["characterId"] == character_id), None)
            decision = store.media.create_character_reference_decision(view.project_id, character_id=character_id,
                primary_asset_id=asset.id, complementary_asset_ids=[], expected_reference_revision=current["revision"] if current else 0,
                reviewer=None, notes="AI 暂选；待完整素材包人类审阅。", authority="story_bible")
            result["referenceDecisionId"] = decision["id"]
            result["consumerCharacterId"] = character_id
            result["canonicalCharacterContextHash"] = decision["characterContextHash"]
        elif subject.owner == "art-reference":
            values = store.media.list_art_reference_decisions(view.project_id)
            current = next((item for item in values["decisions"] if item["subjectType"] == subject.subject_type and item["subjectId"] == subject.id and item["current"]), None)
            decision = store.media.create_art_reference_decision(view.project_id, subject_type=subject.subject_type,
                subject_id=subject.id, asset_id=asset.id, expected_reference_revision=current["referenceRevision"] if current else 0)
            result["referenceDecisionId"] = decision["id"]
        retained = repository.autopilot.checkpoint(checkpoint["operationKey"], state="adopted", expected_revision=checkpoint["revision"],
            evidence=evidence.model_copy(update={"result": result}))
        decision_id = repository.autopilot.decide(retained, subject={"owner": subject.owner, "id": subject.id, **result},
            selected_assets=[selection], rationale="原任务交付通过技术完整性、来源与当前性检查；AI 暂选不代表人类审阅或身份通过。")
        if subject.owner == "image" and compatible:
            job = session.get(ImageJobRow, evidence.job_id)
            unit = session.get(ProductionUnitRow, job.production_unit_id)
            repository.autopilot.select_frame(ProvisionalFrame(shot_id=subject.id, scene_id=subject.scene_id,
                job_id=job.id, asset_id=asset.id, original_hash=asset.original_hash, storyboard_revision=inventory.storyboard_revision,
                storyboard_hash=inventory.storyboard_hash, request_hash=job.request_hash,
                width=asset.width, height=asset.height, character_identity=unit.snapshot["characterIdentity"]), decision_id=decision_id)
        repository.autopilot.progress("first-frames" if subject.owner == "image" else "references")


def publish_bundle(store, view, inventory):
    from .persistence.codec import stable_hash
    from .persistence.schema import AutopilotRunRow
    with store.repository._read() as session:
        run = session.get(AutopilotRunRow, view.id)
        current = store.repository.autopilot.view_in_session(session, run)
        for checkpoint in current.checkpoints:
            evidence = checkpoint["evidence"]
            if evidence["owner"] in {"image", "character-reference", "art-reference"} and checkpoint["state"] == "adopted":
                context = image_context(store, evidence["owner"], evidence["jobId"])
                if not context["current"] or context["state"] != "delivered":
                    raise InvalidTransitionError("completed bundle contains withdrawn native material")
        shots = [item.id for item in inventory.subjects if item.owner == "image"]
        if {frame.shot_id for frame in current.frames} != set(shots) or len(current.frames) != len(shots):
            raise InvalidTransitionError("every unique reachable filmed shot requires one compatible provisional frame")
        refs = []
        for subject in inventory.subjects:
            if subject.owner == "image":
                continue
            checkpoint = session.scalar(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == run.id,
                AutopilotCheckpointRow.operation_key == subject.operation_key))
            if checkpoint is None or checkpoint.state != "adopted":
                raise InvalidTransitionError("required gallery reference is missing")
            result = checkpoint.evidence["result"]
            refs.append(GalleryMaterial(owner=subject.owner, id=subject.id, subject_type=subject.subject_type,
                job_id=checkpoint.evidence["jobId"], request_hash=checkpoint.evidence["requestHash"], delivery_hash=checkpoint.evidence["deliveryHash"],
                reference_decision_id=result["referenceDecisionId"], asset_id=result["assetId"], original_hash=result["originalHash"],
                width=result["width"], height=result["height"]))
        bundle = AutomaticMaterialBundle(run_id=run.id, policy_hash=run.policy_hash,
            inventory=inventory, references=refs, frames=current.frames).model_dump(mode="json", by_alias=True)
        run.bundle, run.bundle_hash = bundle, stable_hash(bundle)
        run.phase, run.state, run.blocker = "material-review", "awaiting_review", None
