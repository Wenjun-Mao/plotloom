"""Typed test grants over existing real admission owners; no live providers."""
from contextlib import closing

from plotloom import delegated_qa
from plotloom.delegated_qa import DelegatedQaScope, QaMaterial
from plotloom.delegated_qa_contracts import AgentQaAttribution
from plotloom.stage_contracts import StageName
from plotloom.project_storage.delegated_qa_grants import (
    bind_original_qa_scope,
    qa_command,
)
from plotloom.video_batch_contracts import BatchControl, BatchSetup, BatchStart
from tests.video_batch_fixtures import batch_environment, ready_batch


def qa_environment(tmp_path, monkeypatch, *, limits="finite"):
    storage, client, service, provider, project, old = batch_environment(tmp_path)
    targets = old["manifest"]["targets"]
    with closing(storage.projects.open(project)) as store:
        head = store.authoring.get_stage_head(project, StageName.STORYBOARD)
        scope = DelegatedQaScope(id="synthetic-test-scope", project_id=project, storyboard_hash=head.content_hash,
            materials=tuple(QaMaterial(item["shotId"], item["snapshot"]["keyframe"]["assetId"],
                item["snapshot"]["keyframe"]["originalHash"]) for item in targets),
            profile_id=old["manifest"]["setup"]["profileId"], max_submissions=len(targets) if limits == "finite" else limits[0],
            max_requested_seconds=5*len(targets) if limits == "finite" else limits[1])
        monkeypatch.setattr(delegated_qa, "SCOPES", (scope,))
        bind_original_qa_scope(store, storage.application)
        actor = AgentQaAttribution(scope_id=scope.id)
        body = {"expectedRevision": head.revision, "contentHash": head.content_hash,
            "gateSetVersion": "storyboard.v2", "decision": "revoke", "attribution": {"kind": "unnamed_creator"}}
        response = client.post(f"/api/v2/projects/{project}/storyboard-approval", json=body)
        assert response.status_code == 201, response.text
        body |= {"decision": "approve", "attribution": actor.model_dump(mode="json", by_alias=True)}
        response = client.post(f"/api/v2/projects/{project}/storyboard-approval", json=body)
        assert response.status_code == 201, response.text
        approval = response.json()["decision"]
        with qa_command(store, storage.application, actor):
            for target in targets:
                snapshot = target["snapshot"]
                old_intent = snapshot["keyframe"]["intent"]
                intent = store.media.create_visual_intent(project, snapshot["keyframe"]["assetId"],
                    old_intent | {"attribution": body["attribution"]}, target_shot_id=target["shotId"])
                store.media.select_reviewed_keyframe(project, asset_id=snapshot["keyframe"]["assetId"],
                    shot_id=target["shotId"], scene_id=snapshot["shot"]["sceneId"],
                    storyboard_revision=head.revision, approval_id=approval["id"],
                    expected_selection_revision=store.media.visual_selection_revision(project),
                    compatibility_note="Agent-operated synthetic fixture QA observation, not owner review.",
                    visual_intent_id=intent["id"], visual_intent_revision=intent["revision"], attribution=body["attribution"])
    service.control(project, BatchControl(batchId=old["id"], expectedControlRevision=old["controlRevision"], action="cancel"))
    view = service.setup(project, BatchSetup(profileId=scope.profile_id, aspectPolicy="cover_center_crop",
        maxJobs=scope.max_submissions, maxRequestedSeconds=scope.max_requested_seconds))
    assert not view["manifest"]["blockers"], view["manifest"]["blockers"]
    return storage, client, service, provider, project, ready_batch(service, project, view), actor


def qa_start(service, project, view, actor):
    return service.start(project, BatchStart(expectedRevision=view["revision"], manifestHash=view["manifestHash"],
        basis="whole-batch-english.v1", attribution=actor))


INSPECTION = {"clips": True, "nativeAudio": True, "intent": True, "windows": True,
    "visualObservation": "Synthetic blue fixture clip covers the selected native frame window.",
    "audioObservation": "Synthetic 440 Hz tone is retained in the native audio stream.",
    "evidenceRefs": ["test-generated FFmpeg color/sine media; automated contract fixture only"]}
