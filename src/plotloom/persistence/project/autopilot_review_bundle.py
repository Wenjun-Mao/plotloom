"""Read current complete material without granting generation or human authority."""
from sqlalchemy import select
from ...autopilot_contracts import LaunchPolicy, ProvisionalFrame
from ...autopilot_materials import initial_inventory
from ...autopilot_handoff_contracts import CurrentReviewBundle, ReviewReference, ReviewFrame, ReviewAsset
from plotloom.stage_contracts import StageName
from ...exceptions import InvalidTransitionError
from ...keyframe_preparation import has_matching_aspect
from ...source_structures import complete_routes
from ..codec import stable_hash
from ..schema import AutopilotFrameRow, ManagedAssetRow, ImageJobRow, ReviewedShotBindingRow
from .autopilot_closure import material_closure


def current_review_bundle(store, session, run):
    repository, project_id = store.repository, run.project_id
    inventory = initial_inventory(store, LaunchPolicy.model_validate(run.policy), enforce_limits=False)
    load = lambda stage: repository._canonical._load_stage_payload(session, project_id, stage)
    graph, beats, bible, board = (load(stage) for stage in (
        StageName.STORY_GRAPH, StageName.SCENE_BEATS, StageName.STORY_BIBLE, StageName.STORYBOARD))
    characters = {item.id: item.name for item in bible.characters}
    accepted_cast = store.cast_state().accepted_cast
    cast = accepted_cast.cast
    consumers = {item.cast_character_id: item.consumer_character_id for item in accepted_cast.consumer_mappings}
    art = store.art_state().accepted_art.art
    names = {("character-reference", None, item["id"]): item.get("name", item["id"]) for item in cast["characters"]}
    for kind, field in (("scene", "scenes"), ("prop", "props")):
        names.update({("art-reference", kind, item["id"]): item.get("name", item["id"]) for item in art[field]})
    char_refs = {item["characterId"]: item for item in store.media.list_character_reference_decisions(project_id)["decisions"] if item["current"]}
    art_refs = {(item["subjectType"], item["subjectId"]): item for item in store.media.list_art_reference_decisions(project_id)["decisions"] if item["current"]}
    references = []
    for subject in inventory.subjects:
        if subject.owner == "image":
            continue
        character_id = consumers.get(subject.id) if subject.owner == "character-reference" else None
        decision = char_refs.get(character_id) if subject.owner == "character-reference" else art_refs.get((subject.subject_type, subject.id))
        if decision is None:
            raise InvalidTransitionError("every current Cast and Art subject requires a current selected reference")
        asset = session.get(ManagedAssetRow, decision.get("primaryAssetId", decision.get("assetId")))
        assets = [asset, *(session.get(ManagedAssetRow, identifier) for identifier in decision.get("complementaryAssetIds", []))]
        references.append(ReviewReference(owner=subject.owner, subject_id=subject.id, character_id=character_id, subject_type=subject.subject_type,
            decision_id=decision["id"], asset_id=asset.id, original_hash=asset.original_hash,
            name=names[(subject.owner, subject.subject_type, subject.id)],
            assets=[ReviewAsset(asset_id=item.id, original_hash=item.original_hash, width=item.width, height=item.height) for item in assets]))
    provisional = {row.shot_id: row for row in session.scalars(select(AutopilotFrameRow).where(AutopilotFrameRow.run_id == run.id))}
    bindings = session.scalars(select(ReviewedShotBindingRow).where(ReviewedShotBindingRow.project_id == project_id)
        .order_by(ReviewedShotBindingRow.selection_revision.desc())).all()
    brief = repository._project_access.rows.project(session, project_id).brief
    ratio = [int(value) for value in brief["aspect_ratio"].split(":")]
    frames = []
    scene_names = {item.id: item.title for item in beats.scenes}
    for shot in board.shots:
        binding = next((item for item in bindings if item.shot_id == shot.id and
            repository._media.admission.reviewed_binding_admission_eligible_in_session(session, project_id, item)), None)
        if binding is not None:
            asset = session.get(ManagedAssetRow, binding.asset_id)
            origin, source_id = "human_binding", binding.id
        else:
            retained = provisional.get(shot.id)
            frame = ProvisionalFrame.model_validate(retained.frame) if retained else None
            job = session.get(ImageJobRow, frame.job_id) if frame else None
            if (frame is None or frame.storyboard_revision != inventory.storyboard_revision
                    or frame.storyboard_hash != inventory.storyboard_hash or job is None or job.state != "delivered"
                    or not repository._media.image_currentness.image_job_is_current_in_session(session, job)):
                raise InvalidTransitionError("every filmed shot requires current first-frame material; complete missing shots manually")
            asset = session.get(ManagedAssetRow, frame.asset_id)
            from .image_source_lineage import current_source_in_session
            source = current_source_in_session(session, project_id, frame.asset_id, repository._media.image_currentness, shot_id=shot.id)
            if source is None or source.geometry != frame.geometry_preparation:
                raise InvalidTransitionError("provisional frame lineage changed")
            if asset.original_hash != frame.original_hash:
                raise InvalidTransitionError("provisional frame bytes changed")
            origin, source_id = "machine_provisional", retained.id
        if not has_matching_aspect(asset.width, asset.height, *ratio):
            raise InvalidTransitionError("current frame geometry does not match the current Brief")
        from .image_source_lineage import source_in_session
        from .image_reviewed_use import use_in_session
        lineage = use_in_session(session, binding) if binding is not None else source_in_session(session, project_id, asset.id, shot_id=shot.id)
        from ..schema import VisualIntentRow
        intent = session.get(VisualIntentRow, binding.visual_intent_id) if binding else None
        from .handoff_intent_context import context_for_frame
        frames.append(ReviewFrame(intent_context=context_for_frame(inventory, shot, intent), target_use=intent.intent.get("targetUse") if intent else None, geometry_preparation=lineage.geometry if lineage else None,shot_id=shot.id, scene_id=shot.scene_id, asset_id=asset.id,
            title=shot.title, scene_name=scene_names[shot.scene_id], direction=shot.visual_intent + " " + shot.composition,
            original_hash=asset.original_hash, width=asset.width, height=asset.height,
            character_ids=shot.character_ids, description=shot.action,
            origin=origin, source_id=source_id))
    script = store.script_state().accepted_script
    report_owners = {"outline": "source-outline", "branches": "branch-suggestions", "characters": "cast", "art": "art",
        "script": "script", "storyboard": "storyboard-source-review"}
    report_names = {"outline": "故事大纲", "branches": "剧情分支", "characters": "角色设定", "art": "美术设定", "script": "剧本", "storyboard": "分镜"}
    checkpoints = repository.autopilot.view_in_session(session, run).checkpoints
    reports = []
    for checkpoint in checkpoints:
        evidence = checkpoint["evidence"]
        owner = evidence["owner"]
        if owner in report_owners and evidence.get("jobId") and checkpoint["state"] == "adopted":
            middle = f'{report_owners[owner]}/' + ("" if owner == "branches" else "candidates/")
            reports.append({"name": report_names[owner], "url": f'/api/v2/projects/{project_id}/{middle}{evidence["jobId"]}/report'})
    story = {"characters": characters, "graph": graph.model_dump(mode="json", by_alias=True), "routes": complete_routes(graph),
        "scenes": beats.model_dump(mode="json", by_alias=True),
        "script": script.script, "scriptRevision": script.revision, "scriptHash": script.content_hash,
        "scriptBinding": script.binding.model_dump(mode="json", by_alias=True), "reports": reports}
    bundle = CurrentReviewBundle(run_id=run.id, material_closure=material_closure(session, project_id),
        inventory=inventory, references=references, frames=frames, story=story)
    raw = bundle.model_dump(mode="json", by_alias=True)
    return {"bundle": raw, "bundleHash": stable_hash(raw), "runRevision": run.revision}
