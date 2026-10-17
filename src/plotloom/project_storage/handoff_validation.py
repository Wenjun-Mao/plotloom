"""Historical exact human evidence binding; current eligibility is a separate check."""
import json

from ..autopilot_handoff_contracts import parse_handoff_receipt
from ..canonical_schema import SceneBeatPlanV2, StoryBibleV2, StoryboardV2, StoryGraphV2
from ..persistence.codec import stable_hash
from ..persistence.project.autopilot_inventory_validation import (
    assert_inventory_binding,
)


def assert_handoff(connection, identifier, run_id, project_id, approval_id, raw, digest, *, asset_home=None):
    receipt = parse_handoff_receipt(raw)
    if stable_hash(raw) != digest or (receipt.id, receipt.run_id, receipt.project_id, receipt.approval_id) != (identifier, run_id, project_id, approval_id):
        raise ValueError("human handoff identity changed")
    bundle = receipt.bundle.model_dump(mode="json", by_alias=True)
    if stable_hash(bundle) != receipt.bundle_hash or receipt.observation.bundle_hash != receipt.bundle_hash or receipt.bundle.run_id != run_id:
        raise ValueError("human review bundle changed")
    run_policy = connection.execute("SELECT policy FROM v2_autopilot_runs WHERE id=? AND project_id=?", (run_id, project_id)).fetchone()
    if run_policy is None:
        raise ValueError("human handoff has no exact frozen run")
    contract = json.loads(run_policy[0]).get("executorBinding", {}).get("contractVersion")
    assert_inventory_binding(connection, project_id, bundle["inventory"], executor_contract=contract)
    canonical = connection.execute("SELECT payload,input_revisions FROM v2_entity_revisions WHERE id=?", (receipt.bundle.inventory.entity_revision_id,)).fetchone()
    board = StoryboardV2.model_validate_json(canonical[0]).model_dump(mode="json", by_alias=True)
    shots_by_id = {item["id"]: item for item in board["shots"]}
    inputs = json.loads(canonical[1])
    story = bundle["story"]
    upstreams = {}
    for stage, model in (("story_graph", StoryGraphV2), ("scene_beats", SceneBeatPlanV2), ("story_bible", StoryBibleV2)):
        row = connection.execute("SELECT payload FROM v2_entity_revisions WHERE project_id=? AND stage=? AND revision=?", (project_id, stage, inputs[stage])).fetchone()
        upstreams[stage] = model.model_validate_json(row[0]).model_dump(mode="json", by_alias=True)
    if story.get("graph") != upstreams["story_graph"] or story.get("scenes") != upstreams["scene_beats"] or story.get("characters") != {item["id"]: item["name"] for item in upstreams["story_bible"]["characters"]}:
        raise ValueError("human-readable story differs from its historical canonical owners")
    from ..source_structures import complete_routes
    if story.get("routes") != complete_routes(StoryGraphV2.model_validate(upstreams["story_graph"])):
        raise ValueError("human-readable routes differ from the complete canonical route set")
    script = connection.execute("SELECT content_hash,script,binding FROM v2_script_revisions WHERE project_id=? AND revision=?", (project_id, story.get("scriptRevision"))).fetchone()
    if script is None or script[0] != story.get("scriptHash") or json.loads(script[1]) != story.get("script") or json.loads(script[2]) != story.get("scriptBinding"):
        raise ValueError("human-readable script differs from its historical source owner")
    scenes_by_id = {item["id"]: item["title"] for item in upstreams["scene_beats"]["scenes"]}
    approval = connection.execute("SELECT project_id,entity_revision_id,decision,reviewer,note FROM v2_approval_decisions WHERE id=?", (approval_id,)).fetchone()
    if approval is None or approval[:3] != (project_id, receipt.bundle.inventory.entity_revision_id, "approve"):
        raise ValueError("human handoff approval changed")
    if receipt.approval_origin == "created" and approval[3:] != (receipt.stored_reviewer, receipt.observation.notes):
        raise ValueError("new human approval attribution changed")
    references = receipt.bundle.references
    cast = connection.execute("SELECT consumer_mappings FROM v2_cast_revisions WHERE project_id=? AND revision=?", (project_id, receipt.bundle.inventory.cast_revision)).fetchone()
    consumers = {item["castCharacterId"]: item["consumerCharacterId"] for item in json.loads(cast[0])}
    required = [(item.owner, item.subject_type, item.id) for item in receipt.bundle.inventory.subjects if item.owner != "image"]
    if [(item.owner, item.subject_type, item.subject_id) for item in references] != required or sorted(receipt.observation.endorsed_reference_ids) != sorted(item.decision_id for item in references):
        raise ValueError("human handoff reference endorsements are incomplete")
    for reference in references:
        table = "v2_character_reference_decisions" if reference.owner == "character-reference" else "v2_art_reference_decisions"
        row = connection.execute(f'SELECT * FROM "{table}" WHERE id=?', (reference.decision_id,)).fetchone()
        keys = [column[1] for column in connection.execute(f'PRAGMA table_info("{table}")')]
        decision = dict(zip(keys, row, strict=True)) if row else {}
        native_subject = reference.subject_id
        if reference.owner == "character-reference":
            if reference.character_id != consumers.get(reference.subject_id):
                raise ValueError("human gallery character consumer mapping changed")
            native_subject = reference.character_id
        if decision.get("project_id") != project_id or decision.get("character_id", decision.get("subject_id")) != native_subject or decision.get("primary_asset_id", decision.get("asset_id")) != reference.asset_id:
            raise ValueError("endorsed reference owner changed")
        asset = connection.execute("SELECT project_id,original_hash FROM v2_managed_assets WHERE id=?", (reference.asset_id,)).fetchone()
        if asset != (project_id, reference.original_hash):
            raise ValueError("endorsed reference bytes changed")
        expected_assets = [reference.asset_id]
        if reference.owner == "character-reference":
            expected_assets.extend(json.loads(decision["complementary_asset_ids"]))
        if [item.asset_id for item in reference.assets] != expected_assets:
            raise ValueError("displayed reference set omits or changes complementary assets")
        for item in reference.assets:
            asset = connection.execute("SELECT project_id,original_hash,width,height FROM v2_managed_assets WHERE id=?", (item.asset_id,)).fetchone()
            if asset != (project_id, item.original_hash, item.width, item.height):
                raise ValueError("displayed reference set bytes changed")
        if reference.owner == "character-reference" and [{"assetId": item.asset_id, "originalHash": item.original_hash} for item in reference.assets] != json.loads(decision["asset_hashes"]):
            raise ValueError("displayed reference set differs from the endorsed decision")
    frames = receipt.bundle.frames
    shots = [item for item in receipt.bundle.inventory.subjects if item.owner == "image"]
    if [item.shot_id for item in frames] != [item.id for item in shots] or len(receipt.bindings) != len(frames) or len(receipt.observation.frames) != len(frames):
        raise ValueError("human handoff shot coverage changed")
    for frame, subject, observation, fact in zip(frames, shots, receipt.observation.frames, receipt.bindings, strict=True):
        shot = shots_by_id[frame.shot_id]
        if frame.title != shot["title"] or frame.description != shot["action"] or frame.direction != shot["visualIntent"] + " " + shot["composition"] or frame.scene_name != scenes_by_id[frame.scene_id]:
            raise ValueError("displayed human frame context differs from its historical shot")
        if frame.character_ids != subject.character_ids or frame.scene_id != subject.scene_id or observation.asset_id != frame.asset_id or observation.shot_id != frame.shot_id or [item.character_id for item in observation.comparisons] != frame.character_ids:
            raise ValueError("human frame observation identity changed")
        source_table = "v2_autopilot_frames" if frame.origin == "machine_provisional" else "v2_reviewed_shot_bindings"
        source = connection.execute(f'SELECT project_id,shot_id,asset_id FROM "{source_table}" WHERE id=?', (frame.source_id,)).fetchone()
        asset = connection.execute("SELECT project_id,original_hash,width,height FROM v2_managed_assets WHERE id=?", (frame.asset_id,)).fetchone()
        if source != (project_id, frame.shot_id, frame.asset_id) or asset != (project_id, frame.original_hash, frame.width, frame.height):
            raise ValueError("reviewed frame source bytes changed")
        from ..persistence.project.image_source_lineage import resolve_image_source
        if frame.origin == "human_binding":
            from ..persistence.project.image_reviewed_use import resolve_reviewed_use
            source_intent = connection.execute("SELECT i.intent FROM v2_visual_intents i JOIN v2_reviewed_shot_bindings b ON b.visual_intent_id=i.id WHERE b.id=?", (frame.source_id,)).fetchone()
            frozen_use = frame.target_use.model_dump(mode="json", by_alias=True) if frame.target_use else None
            if json.loads(source_intent[0]).get("targetUse") != frozen_use:
                raise ValueError("displayed target use differs from its exact reviewed binding")
            lineage = resolve_reviewed_use(connection, project_id, frame.asset_id, frame.shot_id, json.loads(source_intent[0]), asset_home=asset_home)
        else:
            lineage = resolve_image_source(connection, project_id, frame.asset_id, shot_id=frame.shot_id, asset_home=asset_home)
        if (lineage.geometry if lineage else None) != frame.geometry_preparation:
            raise ValueError("human handoff geometry lineage changed")
        binding = connection.execute("SELECT project_id,shot_id,scene_id,asset_id,visual_intent_id,approval_id,compatibility_note FROM v2_reviewed_shot_bindings WHERE id=?", (fact.get("bindingId"),)).fetchone()
        if binding != (project_id, frame.shot_id, frame.scene_id, frame.asset_id, fact.get("intentId"), approval_id, observation.compatibility_note) or fact.get("shotId") != frame.shot_id or fact.get("assetId") != frame.asset_id:
            raise ValueError("human handoff native binding changed")
        intent = connection.execute("SELECT project_id,asset_id,intent FROM v2_visual_intents WHERE id=?", (fact["intentId"],)).fetchone()
        from ..persistence.project.handoff_visual_intents import authored_intent
        frozen_use = frame.target_use.model_dump(mode="json", by_alias=True) if frame.target_use else None
        if (intent is None or intent[:2] != (project_id, frame.asset_id)
                or authored_intent(json.loads(intent[2])) != observation.intent.model_dump(mode="json", by_alias=True)
                or json.loads(intent[2]).get("targetUse") != frozen_use):
            raise ValueError("human authored intent changed")
        if frame.character_ids:
            review = connection.execute("SELECT project_id,binding_id,reviewer,notes,comparisons,reference_bindings FROM v2_same_person_reviews WHERE id=?", (fact.get("samePersonReviewId"),)).fetchone()
            comparisons = [item.model_dump(mode="json", by_alias=True, exclude_none=True) for item in observation.comparisons]
            from ..persistence.project.media_same_person_reviews import (
                SamePersonReviewPersistence,
            )
            if review is None or review[:4] != (project_id, fact["bindingId"], receipt.stored_reviewer, observation.compatibility_note) or json.loads(review[4]) != comparisons or not SamePersonReviewPersistence.comparisons_authorize_production(comparisons):
                raise ValueError("human identity observations changed")
            mapping = json.loads(review[5])
            if [item.get("characterId") for item in mapping] != frame.character_ids:
                raise ValueError("human comparison reference order changed")
            for item in mapping:
                endorsed = next((reference for reference in references if reference.owner == "character-reference" and reference.character_id == item["characterId"]), None)
                reference = connection.execute("SELECT project_id,character_id,reference_revision,asset_hashes FROM v2_character_reference_decisions WHERE id=?", (item.get("referenceDecisionId"),)).fetchone()
                if endorsed is None or endorsed.decision_id != item.get("referenceDecisionId") or reference is None or reference[:3] != (project_id, item["characterId"], item.get("referenceRevision")) or item.get("assetHashes") != [value["originalHash"] for value in json.loads(reference[3])]:
                    raise ValueError("human comparison reference bytes changed")
                if frame.geometry_preparation and (item.get("frameHash") != frame.original_hash or item.get("geometryPreparationHash") != frame.geometry_preparation.preparation_hash):
                    raise ValueError("human derivative observation lineage changed")
                expected_origin = "cross_shot_target_use" if frame.target_use else "human_current_material"
                if frame.target_use is not None and item.get("comparisonOrigin") != expected_origin:
                    raise ValueError("cross-shot target lacks its independent identity observation")
                if item.get("comparisonOrigin") is not None and (item["comparisonOrigin"] != expected_origin or item.get("frameHash") != frame.original_hash):
                    raise ValueError("manual comparison context changed")
        elif fact.get("samePersonReviewId") is not None or observation.comparisons:
            raise ValueError("character-free frame cannot fabricate an identity pass")
    return receipt
