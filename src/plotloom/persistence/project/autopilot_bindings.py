"""Resolve retained machine facts against immutable native owner evidence.

Uses the already-admitted SQLite connection both inside the command transaction
and on ordinary folder reads. Historical rows need not remain currently usable.
"""
import json

from ...creative_handoff_contracts import CreativeHandoffRequest
from ...creative_handoff_exchange import request_hash, execution_pin_for_request
from ..codec import stable_hash
from ...source_outline_contracts import SourceMaterial

CREATIVE_OWNERS = {
    "outline": "v2_source_outline_candidates", "branches": "v2_source_outline_candidates",
    "characters": "v2_cast_candidates", "art": "v2_art_candidates",
    "script": "v2_script_candidates", "storyboard": "v2_storyboard_review_candidates",
    "bridge-intent": "v2_production_bridge_intent_jobs",
    "bridge-presentation": "v2_production_bridge_intent_jobs",
}
IMAGE_OWNERS = {
    "image": ("v2_image_jobs", "v2_image_job_deliveries", "job_id"),
    "character-reference": ("v2_character_reference_proposals", "v2_character_reference_proposal_deliveries", "proposal_id"),
    "art-reference": ("v2_art_reference_proposals", "v2_art_reference_proposal_deliveries", "proposal_id"),
}


def _row(connection, sql, values):
    cursor = connection.execute(sql, values)
    row = cursor.fetchone()
    if row is None:
        raise ValueError("autopilot evidence has no native owner")
    return dict(zip((column[0] for column in cursor.description), row, strict=True))


def assert_checkpoint_binding(connection, project_id, state, evidence, *, run_id, asset_home=None):
    owner = evidence.owner
    if owner == "geometry-preparation":
        if evidence.job_id or evidence.request_hash or evidence.execution_pin or evidence.delivery_hash or evidence.geometry_preparation is None:
            raise ValueError("local geometry cannot impersonate native evidence")
        if evidence.subject_id != evidence.geometry_preparation.shot_id:
            raise ValueError("local geometry shot identity changed")
        from .image_source_lineage import assert_geometry
        assert_geometry(connection, evidence.geometry_preparation, project_id=project_id, run_id=run_id, asset_home=asset_home)
        return
    if evidence.geometry_preparation is not None:
        raise ValueError("geometry lineage belongs only to its typed local owner")
    terminal = state in {"delivered", "adopted"}
    if owner == "source":
        if evidence.job_id or evidence.request_hash or evidence.execution_pin or evidence.delivery_hash or evidence.subject_id != "source":
            raise ValueError("source evidence cannot impersonate a native job")
        row = _row(connection, "SELECT material, content_hash FROM v2_source_outline_source_revisions WHERE project_id=? AND revision=?",
            (project_id, evidence.result.get("revision")))
        raw = json.loads(row["material"])
        material = SourceMaterial.model_validate(raw)
        run = _row(connection, "SELECT project_id, brief_revision, brief_hash, policy FROM v2_autopilot_runs WHERE id=?", (run_id,))
        brief = json.loads(run["policy"])["brief"]
        origin = material.brief_origin
        if (origin is None or run["project_id"] != project_id or stable_hash(raw) != row["content_hash"]
                or origin.revision != run["brief_revision"] or origin.content_hash != run["brief_hash"]
                or stable_hash(brief) != run["brief_hash"] or material.title != brief["title"]
                or material.text != brief["synopsis"]):
            raise ValueError("machine source differs from the exact frozen Brief projection")
        return
    if owner in {"installation", "bundle", "bridge-proposal"}:
        if evidence.job_id or evidence.request_hash or evidence.execution_pin or evidence.delivery_hash:
            raise ValueError("local adoption cannot impersonate a native job")
        table = "v2_production_bridge_revisions" if owner == "bridge-proposal" else "v2_entity_revisions"
        row = _row(connection, f'SELECT project_id, content_hash FROM "{table}" WHERE id=?', (evidence.subject_id,))
        if row["project_id"] != project_id or row["content_hash"] != evidence.result.get("contentHash"):
            raise ValueError("local adoption canonical owner changed")
        if owner == "bundle" and "inventory" in evidence.result:
            from .autopilot_inventory_validation import assert_inventory_binding
            assert_inventory_binding(connection, project_id, evidence.result["inventory"])
        return
    if not evidence.job_id or not evidence.request_hash or not evidence.execution_pin:
        raise ValueError("native checkpoint requires its exact frozen execution identity")
    if owner in CREATIVE_OWNERS:
        bridge = owner.startswith("bridge-")
        table = CREATIVE_OWNERS[owner]
        row = _row(connection, f'SELECT * FROM "{table}" WHERE {"id" if bridge else "job_id"}=?', (evidence.job_id,))
        request = CreativeHandoffRequest.model_validate_json(row["native_request" if bridge else "request"])
        pin = _row(connection, "SELECT * FROM v2_creative_handoff_execution_pins WHERE job_id=?", (evidence.job_id,))
        expected_pin = json.loads(pin["execution_pin"])
        execution_pin_for_request(request, expected_pin)
        if (row["project_id"] != project_id or request.project_id != project_id or request.stage != owner
                or request.job_id != evidence.job_id or evidence.subject_id != evidence.job_id
                or request_hash(request) != evidence.request_hash or pin["request_hash"] != evidence.request_hash
                or pin["project_id"] != project_id or pin["stage"] != owner or expected_pin != evidence.execution_pin):
            raise ValueError("creative checkpoint frozen owner binding changed")
        proof = json.loads(row["response_evidence"] or "{}").get("manifestHash") if bridge else row["manifest_hash"]
    elif owner in IMAGE_OWNERS:
        table, delivery_table, foreign_key = IMAGE_OWNERS[owner]
        row = _row(connection, f'SELECT * FROM "{table}" WHERE id=?', (evidence.job_id,))
        request = json.loads(row["request"])
        run = _row(connection, "SELECT project_id,policy FROM v2_autopilot_runs WHERE id=?", (run_id,))
        if run["project_id"] != project_id or json.loads(run["policy"])["executionPins"].get("image") != evidence.execution_pin:
            raise ValueError("image checkpoint execution differs from frozen launch policy")
        subject = request.get("frozenSnapshot", {})
        expected_subject = (subject.get("shot", {}).get("id") if owner == "image"
            else row.get("character_id") if owner == "character-reference" else row.get("subject_id"))
        if (row["project_id"] != project_id or row["request_hash"] != evidence.request_hash
                or stable_hash(request) != evidence.request_hash or evidence.subject_id != expected_subject
                or request.get("specialistPreflight") != evidence.execution_pin):
            raise ValueError("image checkpoint frozen owner binding changed")
        proofs = list(connection.execute(f'SELECT manifest_hash,manifest,id,state FROM "{delivery_table}" WHERE "{foreign_key}"=? AND manifest_hash IS NOT NULL', (evidence.job_id,)))
        retained = next((item for item in proofs if item[0] == evidence.delivery_hash), None)
        proof = evidence.delivery_hash if retained is not None else None
        if retained is not None:
            from ...image_job_contracts import ImageDeliveryManifest
            manifest = ImageDeliveryManifest.model_validate_json(retained[1])
            frozen_policy = json.loads(run["policy"])
            provenance = manifest.executor_provenance
            native_task_id = (
                str(manifest.tool_evidence.native_task_id)
                if manifest.schema_version == 3
                else manifest.tool_evidence.task_id
            )
            if (stable_hash(manifest.canonical_payload()) != proof
                    or manifest.job_id != evidence.job_id or manifest.request_hash != evidence.request_hash
                    or provenance is None or provenance.code_revision != evidence.execution_pin["codeRevision"]
                    or provenance.skill_hash != evidence.execution_pin["skillHash"]
                    or native_task_id != frozen_policy["specialistBindings"]["image"]):
                raise ValueError("retained image receipt differs from its frozen execution")
            if "candidateAssetIds" in evidence.result:
                candidate_table = delivery_table.replace("deliveries", "candidates")
                candidates = list(connection.execute(f'SELECT candidate.asset_id,candidate.output_filename,candidate.output_hash,candidate.role,asset.project_id,asset.original_hash FROM "{candidate_table}" AS candidate JOIN v2_managed_assets AS asset ON asset.id=candidate.asset_id WHERE candidate."{foreign_key}"=? AND candidate.delivery_id=?', (evidence.job_id, retained[2])))
                actual_assets = [item[0] for item in candidates]
                declared_assets = evidence.result["candidateAssetIds"]
                if len(set(declared_assets)) != len(declared_assets) or set(actual_assets) != set(declared_assets):
                    raise ValueError("image checkpoint candidate set differs from its original native delivery")
                expected_outputs = {(item.filename, item.sha256, item.role) for item in manifest.outputs}
                if retained[3] == "accepted" and (len(candidates) != len(expected_outputs) or {item[1:4] for item in candidates} != expected_outputs):
                    raise ValueError("native candidate bytes differ from exact manifest outputs")
                if any(item[4] != project_id or item[2] != item[5] for item in candidates):
                    raise ValueError("native candidate asset differs from its exact output bytes")
                if evidence.result.get("deliveryState") != retained[3]:
                    raise ValueError("native checkpoint acceptance differs from exact delivery")
            if "outputRoles" in evidence.result and evidence.result["outputRoles"] != [item.role for item in manifest.outputs]:
                raise ValueError("image checkpoint output roles differ from exact native delivery")
    else:
        raise ValueError("unknown checkpoint evidence owner")
    if (terminal and (not proof or evidence.delivery_hash != proof)) or (evidence.delivery_hash is not None and evidence.delivery_hash != proof):
        raise ValueError("terminal checkpoint lacks exact native delivery evidence")


def assert_frame_binding(connection, run_id, project_id, decision_id, frame, *, asset_home=None):
    job = _row(connection, "SELECT * FROM v2_image_jobs WHERE id=?", (frame.job_id,))
    unit = _row(connection, "SELECT * FROM v2_production_units WHERE id=?", (job["production_unit_id"],))
    asset = _row(connection, "SELECT * FROM v2_managed_assets WHERE id=?", (frame.asset_id,))
    decision = _row(connection, "SELECT * FROM v2_autopilot_decisions WHERE id=?", (decision_id,))
    revision = _row(connection, "SELECT * FROM v2_entity_revisions WHERE id=?", (unit["storyboard_entity_revision_id"],))
    from .image_source_lineage import resolve_image_source
    lineage = resolve_image_source(connection, project_id, frame.asset_id, shot_id=frame.shot_id, asset_home=asset_home)
    if lineage is None or lineage.job_id != frame.job_id or lineage.geometry != frame.geometry_preparation:
        raise ValueError("provisional frame source lineage changed")
    candidate = _row(connection, "SELECT * FROM v2_image_job_candidates WHERE id=?", (lineage.candidate_id,))
    delivery = _row(connection, "SELECT * FROM v2_image_job_deliveries WHERE id=?", (candidate["delivery_id"],))
    selection = _row(connection, "SELECT run_id,project_id,evidence FROM v2_autopilot_checkpoints WHERE id=?", (decision["checkpoint_id"],))
    selected_job = json.loads(selection["evidence"])
    if (selection["run_id"] != run_id or selection["project_id"] != project_id
            or selected_job.get("owner") != ("geometry-preparation" if lineage.geometry else "image")
            or (not lineage.geometry and selected_job.get("jobId") != frame.job_id)
            or (lineage.geometry and selected_job.get("geometryPreparation") != lineage.geometry.model_dump(mode="json", by_alias=True))
            or selected_job.get("subjectId") != frame.shot_id or (not lineage.geometry and selected_job.get("requestHash") != frame.request_hash)):
        raise ValueError("provisional frame differs from its exact selection checkpoint")
    snapshot = json.loads(unit["snapshot"])
    request = json.loads(job["request"])
    generation = _row(connection, "SELECT run_id,project_id,scope,decision FROM v2_autopilot_decisions WHERE id=?", (unit["machine_decision_id"],))
    source = json.loads(generation["decision"])["subject"]
    if (generation["run_id"] != run_id or generation["project_id"] != project_id or generation["scope"] != "image_generation"
            or source.get("entityRevisionId") != revision["id"] or source.get("revision") != revision["revision"]
            or source.get("contentHash") != revision["content_hash"]):
        raise ValueError("provisional frame lacks its exact machine image-generation authority")
    identities = snapshot.get("characterIdentity")
    visible = snapshot.get("visibleCharacterIds")
    if (request.get("schemaVersion") != 3 or snapshot.get("snapshotVersion") != 3
            or not isinstance(identities, list) or not isinstance(visible, list)
            or len(visible) > 8 or len(set(visible)) != len(visible)
            or visible != snapshot.get("shot", {}).get("characterIds")
            or len(identities) != len(visible)
            or [item.get("characterId") for item in identities if isinstance(item, dict)] != visible):
        raise ValueError("provisional frame requires an explicit exact v3 character mapping")
    for identity in identities:
        reference = _row(connection, "SELECT * FROM v2_character_reference_decisions WHERE id=?", (identity.get("referenceDecisionId"),))
        context = json.loads(reference["character_context"])
        ids = [reference["primary_asset_id"], *json.loads(reference["complementary_asset_ids"])]
        if (reference["project_id"] != project_id or reference["character_id"] != identity["characterId"]
                or reference["reference_revision"] != identity.get("referenceRevision")
                or reference["character_context_hash"] != identity.get("characterContextHash")
                or context.get("acceptedCast") != identity.get("acceptedCast")
                or [item.get("assetId") for item in identity.get("assets", [])] != ids):
            raise ValueError("provisional frame character reference binding changed")
        for entry in identity["assets"]:
            original = _row(connection, "SELECT project_id,original_hash FROM v2_managed_assets WHERE id=?", (entry["assetId"],))
            if original["project_id"] != project_id or original["original_hash"] != entry.get("originalHash"):
                raise ValueError("provisional frame identity bytes changed")
    if (any(row["project_id"] != project_id for row in (job, unit, asset, decision, revision))
            or decision["run_id"] != run_id or decision["scope"] != "provisional_selection"
            or frame.request_hash != job["request_hash"] or stable_hash(request) != job["request_hash"]
            or frame.shot_id != unit["shot_id"] or frame.scene_id != unit["scene_id"]
            or frame.storyboard_revision != unit["storyboard_revision"] or frame.storyboard_hash != revision["content_hash"]
            or frame.original_hash != asset["original_hash"] or candidate["output_hash"] != lineage.source_hash
            or (frame.width, frame.height) != (asset["width"], asset["height"])
            or frame.character_identity != snapshot.get("characterIdentity", [])
            or request["frozenSnapshot"] != snapshot or stable_hash(snapshot) != unit["snapshot_hash"]
            or delivery["job_id"] != job["id"] or not delivery["manifest_hash"]):
        raise ValueError("provisional frame native owner binding changed")
    selected = json.loads(decision["decision"]).get("selectedAssets", [])
    if {"assetId": frame.asset_id, "originalHash": frame.original_hash} not in selected:
        raise ValueError("provisional decision does not select these exact bytes")
