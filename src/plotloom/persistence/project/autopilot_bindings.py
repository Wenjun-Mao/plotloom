"""Resolve retained machine facts against immutable native owner evidence.

Uses the already-admitted SQLite connection both inside the command transaction
and on ordinary folder reads. Historical rows need not remain currently usable.
"""
import json

from ...autopilot_contracts import POLICY_VERSION
from ...codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecProfile,
    CodexExecReceipt,
    assert_receipt_matches_attempt,
)
from ...creative_handoff_contracts import (
    CREATIVE_CANDIDATE_FILENAMES,
    CreativeHandoffRequest,
)
from ...creative_handoff_exchange import execution_pin_for_request, request_hash
from ...source_outline_contracts import SourceMaterial
from ..codec import stable_hash

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


def _assert_exec_attempt_binding(connection, project_id, run_id, state, evidence, owner, operation_key,
                                 *, profile_construction=None):
    run = _row(connection, "SELECT project_id,policy FROM v2_autopilot_runs WHERE id=?", (run_id,))
    policy = json.loads(run["policy"])
    is_codex_exec = policy.get("version") == POLICY_VERSION
    if not is_codex_exec:
        if evidence.executor_attempt_id is not None or evidence.executor_receipt_hash is not None:
            raise ValueError("retained specialist evidence cannot claim a Codex Exec attempt")
        return None, None
    if run["project_id"] != project_id:
        raise ValueError("Codex Exec checkpoint belongs to a different project run")
    if evidence.executor_attempt_id is None:
        if evidence.executor_receipt_hash is not None:
            raise ValueError("Codex Exec receipt hash requires its exact project attempt")
        return None, None
    if operation_key is None:
        raise ValueError("Codex Exec checkpoint requires its exact operation key")
    row = _row(connection, "SELECT * FROM v2_autopilot_exec_attempts WHERE id=?", (str(evidence.executor_attempt_id),))
    attempt = CodexExecAttempt.model_validate(json.loads(row["snapshot"]))
    expected_domain = "text" if owner in CREATIVE_OWNERS else "image"
    profile = (CodexExecProfile.model_validate(policy.get("executorBinding", {}))
        if profile_construction is None else profile_construction.resolve(run["policy"], policy))
    if (row["run_id"] != run_id or row["project_id"] != project_id
            or row["operation_key"] != operation_key or row["job_id"] != evidence.job_id
            or row["domain"] != expected_domain or attempt.attempt_id != evidence.executor_attempt_id
            or str(attempt.run_id) != run_id or str(attempt.project_id) != project_id
            or attempt.operation_key != operation_key or attempt.job_id != evidence.job_id
            or attempt.request_hash != evidence.request_hash or attempt.domain != expected_domain
            or attempt.profile_hash != profile.profile_hash
            or (profile.contract_version in {"plotloom.codex-exec.v5", "plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}
                and attempt.plotloom_code_revision != policy["codeRevision"])
            or (profile.contract_version in {"plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"} and expected_domain == "text"
                and attempt.validation_plan_hash is None)
            or row["state"] != attempt.state or row["image_budget_state"] != attempt.image_budget_state
            or row["reserved_image_outputs"] != attempt.reserved_image_outputs):
        raise ValueError("Codex Exec checkpoint differs from its immutable project attempt")
    allowed = {
        "prepared": {"reserved"},
        "sent": {"queued", "spawn_intent", "running", "validating", "cancel_requested", "completed", "settled"},
        "outcome_unknown": {
            "outcome_unknown", "running", "validating", "cancel_requested", "completed", "failed", "settled",
        },
        "failed": {"failed", "settled"},
        "delivered": {"completed", "settled"},
        "adopted": {"completed", "settled"},
    }
    if state in allowed and attempt.state not in allowed[state]:
        raise ValueError(
            f"Codex Exec attempt state {attempt.state!r} is not valid for {state!r} checkpoint"
        )
    receipt = CodexExecReceipt.model_validate(json.loads(row["receipt"])) if row["receipt"] is not None else None
    terminal = attempt.state in {"completed", "failed", "settled"}
    if evidence.executor_receipt_hash != (attempt.evidence_hash if terminal else None):
        raise ValueError("checkpoint receipt hash differs from its exact terminal project attempt")
    if attempt.terminal_result == "success":
        if receipt is None:
            raise ValueError("successful Codex Exec project attempt has no retained host receipt")
        assert_receipt_matches_attempt(attempt, receipt)
    elif receipt is not None:
        raise ValueError("failed Codex Exec attempt cannot retain a successful host receipt")
    return attempt, receipt


def assert_checkpoint_binding(connection, project_id, state, evidence, *, run_id, operation_key=None, asset_home=None):
    """Validate current checkpoint authority before mutation, dispatch or adoption."""
    return _assert_checkpoint_binding(connection, project_id, state, evidence,
        run_id=run_id, operation_key=operation_key, asset_home=asset_home,
        validation_plan_for_request=_current_checkpoint_validation_plan)


def assert_retained_checkpoint_provenance(connection, project_id, state, evidence, *, run_id, operation_key=None, asset_home=None):
    """Verify immutable historical evidence during passive database inspection only."""
    return _assert_checkpoint_binding(connection, project_id, state, evidence,
        run_id=run_id, operation_key=operation_key, asset_home=asset_home,
        validation_plan_for_request=_retained_checkpoint_validation_plan)


def _current_checkpoint_validation_plan(request, *, execution_pin, source_revision):
    from ...codex_exec_validation import build_text_validation_plan

    return build_text_validation_plan(request, execution_pin=execution_pin, source_revision=source_revision)


def _retained_checkpoint_validation_plan(request, *, execution_pin, source_revision):
    if request.stage == "outline":
        from ...codex_exec_retained_outline import retained_outline_package_projection
        from ...codex_exec_validation import CodexExecTextValidationPlan

        expected = retained_outline_package_projection(request, execution_pin, source_revision=source_revision)
        return CodexExecTextValidationPlan.model_validate(expected["validationPlan"])
    return _current_checkpoint_validation_plan(request, execution_pin=execution_pin, source_revision=source_revision)


def _assert_checkpoint_binding(connection, project_id, state, evidence, *, run_id, operation_key, asset_home,
                               validation_plan_for_request, profile_construction=None):
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
            run = _row(connection, "SELECT policy FROM v2_autopilot_runs WHERE id=?", (run_id,))
            contract = json.loads(run["policy"]).get("executorBinding", {}).get("contractVersion")
            assert_inventory_binding(connection, project_id, evidence.result["inventory"], executor_contract=contract)
        return
    if not evidence.job_id or not evidence.request_hash or not evidence.execution_pin:
        raise ValueError("native checkpoint requires its exact frozen execution identity")
    exec_attempt, exec_receipt = _assert_exec_attempt_binding(
        connection, project_id, run_id, state, evidence, owner, operation_key,
        profile_construction=profile_construction,
    )
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
        if exec_attempt is not None and exec_attempt.domain == "text":
            raw_policy = _row(
                connection, "SELECT policy FROM v2_autopilot_runs WHERE id=?", (run_id,),
            )["policy"]
            frozen_policy = json.loads(raw_policy)
            executor_profile = (CodexExecProfile.model_validate(frozen_policy.get("executorBinding", {}))
                if profile_construction is None else profile_construction.resolve(raw_policy, frozen_policy))
            if executor_profile.contract_version in {"plotloom.codex-exec.v6", "plotloom.codex-exec.v7", "plotloom.codex-exec.v8"}:
                plan = validation_plan_for_request(
                    request,
                    execution_pin=expected_pin,
                    source_revision=frozen_policy["codeRevision"],
                )
                plan_hash = plan.plan_hash
                if exec_attempt.validation_plan_hash != plan_hash:
                    raise ValueError("Codex Exec attempt differs from the frozen creative validation plan")
                if exec_receipt is not None and (
                    exec_receipt.validation_plan_hash != plan_hash
                    or exec_receipt.text_validation is None
                    or exec_receipt.text_validation.validator_hash != executor_profile.validator_hash
                    or exec_receipt.text_validation.candidate_filename
                    != CREATIVE_CANDIDATE_FILENAMES[request.stage]
                ):
                    raise ValueError("Codex Exec receipt differs from the frozen creative validation evidence")
        proof = json.loads(row["response_evidence"] or "{}").get("manifestHash") if bridge else row["manifest_hash"]
    elif owner in IMAGE_OWNERS:
        table, delivery_table, foreign_key = IMAGE_OWNERS[owner]
        row = _row(connection, f'SELECT * FROM "{table}" WHERE id=?', (evidence.job_id,))
        request = json.loads(row["request"])
        run = _row(connection, "SELECT project_id,policy FROM v2_autopilot_runs WHERE id=?", (run_id,))
        if run["project_id"] != project_id:
            raise ValueError("image checkpoint execution differs from frozen launch policy")
        frozen_policy = json.loads(run["policy"])
        if frozen_policy["executionPins"].get("image") != evidence.execution_pin:
            raise ValueError("image checkpoint execution differs from frozen launch policy")
        subject = request.get("frozenSnapshot", {})
        expected_subject = (subject.get("shot", {}).get("id") if owner == "image"
            else row.get("character_id") if owner == "character-reference" else row.get("subject_id"))
        if (row["project_id"] != project_id or row["request_hash"] != evidence.request_hash
                or stable_hash(request) != evidence.request_hash or evidence.subject_id != expected_subject
                or request.get("specialistPreflight") != evidence.execution_pin):
            raise ValueError("image checkpoint frozen owner binding changed")
        profile = frozen_policy.get("executorBinding", {})
        if owner == "character-reference" and profile.get("contractVersion") == "plotloom.codex-exec.v8":
            cast_subject = subject.get("acceptedCast", {}).get("castCharacterId")
            consumer = subject.get("characterContext", {}).get("characterId")
            if (not cast_subject or consumer != evidence.subject_id
                    or operation_key != f"character-reference:{cast_subject}"):
                raise ValueError("Cast operation and consumer proposal identities differ from frozen provenance")
        proofs = list(connection.execute(f'SELECT manifest_hash,manifest,id,state FROM "{delivery_table}" WHERE "{foreign_key}"=? AND manifest_hash IS NOT NULL', (evidence.job_id,)))
        retained = next((item for item in proofs if item[0] == evidence.delivery_hash), None)
        proof = evidence.delivery_hash if retained is not None else None
        if retained is not None:
            from ...image_job_contracts import ImageDeliveryManifest
            manifest = ImageDeliveryManifest.model_validate_json(retained[1])
            provenance = manifest.executor_provenance
            native_task_identity = manifest.native_task_identity
            if (stable_hash(manifest.canonical_payload()) != proof
                    or manifest.job_id != evidence.job_id or manifest.request_hash != evidence.request_hash
                    or provenance is None or provenance.code_revision != evidence.execution_pin["codeRevision"]
                    or provenance.skill_hash != evidence.execution_pin["skillHash"]
                    or (exec_attempt is None and native_task_identity != frozen_policy["specialistBindings"]["image"])):
                raise ValueError("retained image receipt differs from its frozen execution")
            if exec_attempt is not None and (
                manifest.schema_version != 5 or manifest.executor_profile_hash != exec_attempt.profile_hash
                or manifest.tool_evidence is None
                or manifest.tool_evidence.executor_attempt_id != exec_attempt.attempt_id
                or manifest.tool_evidence.codex_session_id != exec_receipt.session_id
                or manifest.tool_evidence.image_gen_call_id != exec_receipt.image_evidence[0].call_id
                or manifest.tool_evidence.image_gen_event_id != exec_receipt.image_evidence[0].event_id
                or {item.sha256 for item in manifest.outputs} != {item.output_hash for item in exec_receipt.outputs}
            ):
                raise ValueError("retained Codex Exec image receipt differs from its exact host proof")
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
    if terminal and not proof:
        raise ValueError(f"terminal {owner} checkpoint has no retained native delivery proof")
    if evidence.delivery_hash is not None and evidence.delivery_hash != proof:
        raise ValueError(f"{owner} checkpoint delivery hash differs from its retained native proof")


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
