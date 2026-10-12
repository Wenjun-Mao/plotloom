"""Historical bundle bytes bind exact native evidence; currentness is separate."""
import json
from ..autopilot_materials import AutomaticMaterialBundle
from ..keyframe_preparation import has_matching_aspect


def assert_material_bundle(connection, run_id, project_id, policy_hash, policy, raw):
    bundle = AutomaticMaterialBundle.model_validate(raw)
    if bundle.run_id != run_id or bundle.policy_hash != policy_hash:
        raise ValueError("bundle policy identity changed")
    from ..persistence.project.autopilot_inventory_validation import assert_inventory_binding
    assert_inventory_binding(connection, project_id, raw["inventory"])
    revision = connection.execute("SELECT project_id,revision,content_hash FROM v2_entity_revisions WHERE id=?", (bundle.inventory.entity_revision_id,)).fetchone()
    if revision != (project_id, bundle.inventory.storyboard_revision, bundle.inventory.storyboard_hash):
        raise ValueError("bundle canonical inventory owner changed")
    for reference in bundle.references:
        checkpoint = connection.execute("SELECT id,state,evidence FROM v2_autopilot_checkpoints WHERE run_id=? AND project_id=? AND json_extract(evidence,'$.jobId')=?",
            (run_id, project_id, reference.job_id)).fetchone()
        if checkpoint is None or checkpoint[1] != "adopted":
            raise ValueError("bundle reference lacks its exact adopted operation")
        evidence = json.loads(checkpoint[2])
        result = evidence["result"]
        if (evidence["owner"] != reference.owner or evidence["subjectId"] != reference.id
                or evidence["requestHash"] != reference.request_hash or evidence["deliveryHash"] != reference.delivery_hash
                or result.get("referenceDecisionId") != reference.reference_decision_id
                or result.get("assetId") != reference.asset_id or result.get("originalHash") != reference.original_hash
                or result.get("candidateAssetIds") != [reference.asset_id]):
            raise ValueError("bundle reference differs from retained selection")
        asset = connection.execute("SELECT project_id,original_hash,width,height FROM v2_managed_assets WHERE id=?", (reference.asset_id,)).fetchone()
        if asset != (project_id, reference.original_hash, reference.width, reference.height):
            raise ValueError("bundle reference bytes changed")
        if reference.owner == "character-reference":
            decision = connection.execute("SELECT project_id,character_id,primary_asset_id,asset_hashes FROM v2_character_reference_decisions WHERE id=?", (reference.reference_decision_id,)).fetchone()
            if decision is None or decision[:3] != (project_id, reference.id, reference.asset_id) or {"assetId": reference.asset_id, "originalHash": reference.original_hash} not in json.loads(decision[3]):
                raise ValueError("bundle character decision owner changed")
        else:
            decision = connection.execute("SELECT project_id,subject_type,subject_id,asset_id,asset_hash,proposal_id FROM v2_art_reference_decisions WHERE id=?", (reference.reference_decision_id,)).fetchone()
            if decision != (project_id, reference.subject_type, reference.id, reference.asset_id, reference.original_hash, reference.job_id):
                raise ValueError("bundle Art decision owner changed")
    for frame in bundle.frames:
        retained = connection.execute("SELECT frame FROM v2_autopilot_frames WHERE run_id=? AND project_id=? AND shot_id=?", (run_id, project_id, frame.shot_id)).fetchone()
        if retained is None or json.loads(retained[0]) != frame.model_dump(mode="json", by_alias=True):
            raise ValueError("bundle frame differs from exact retained provisional selection")
        if not has_matching_aspect(frame.width, frame.height, policy.image_width, policy.image_height):
            raise ValueError("bundle contains an incompatible provisional frame")
