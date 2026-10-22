"""Provider-fake batches use real current source, admission and selection owners."""
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.video_batch_contracts import BatchSetup, BatchDirectionsDraft, BatchStart
from tests.project_storage_fixtures import FixtureResolver, fixture_profile
from tests.video_storage_fixtures import FakeH3, _fixture_app, _approved_keyframe


def batch_environment(tmp_path):
    provider = FakeH3()
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    ProjectPipelineExecutor(FixtureResolver()).execute(store, profile=fixture_profile())
    from plotloom.domain import StageName
    board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
    board = board.model_copy(update={"shots": [shot.model_copy(update={"duration_units": 5000}) for shot in board.shots]})
    store.update_stage(StageName.STORYBOARD, board, expected_revision=store.authoring.get_stage_head(project_id, StageName.STORYBOARD).revision)
    store.close()
    approval, context = _approved_keyframe(client, storage, project_id)
    from contextlib import closing
    with closing(storage.projects.open(project_id)) as store:
        board = store.authoring.get_stage_payload(project_id, StageName.STORYBOARD)
        from io import BytesIO
        from PIL import Image
        for index, shot in enumerate(board.shots[1:]):
            output = BytesIO()
            Image.new("RGB", (576,1024), (40+index, 55, 65)).save(output, format="PNG")
            response = client.post(f"/api/v2/projects/{project_id}/managed-assets", files={"image": ("frame.png", output.getvalue(), "image/png")}, data={"origin": "Disposable batch fixture", "rights": "unknown"})
            assert response.status_code == 201, response.text
            asset = response.json()
            intent = store.media.create_visual_intent(project_id, asset["id"], {"role": "shot_keyframe", "compositionIntent": "Fixture author observes the same empty beacon room.", "sourceRefs": [shot.id]})
            store.media.select_reviewed_keyframe(project_id, asset_id=asset["id"], shot_id=shot.id, scene_id=shot.scene_id,
                expected_selection_revision=store.media.visual_selection_revision(project_id), storyboard_revision=context["revision"],
                approval_id=approval["id"], compatibility_note="Disposable fixture reviewed beacon room frame.", visual_intent_id=intent["id"], visual_intent_revision=intent["revision"])
    service = client.app.state.video_batch_service
    view = service.setup(project_id, BatchSetup(profileId="minimax_h3_quality8_portrait_576x1024_v2"))
    return storage, client, service, provider, project_id, view


def draft_for(view):
    return BatchDirectionsDraft(targets=[{"shotId": target["shotId"], "sourceHash": target["sourceHash"],
        "fields": [{"path": source["path"], "english": "The keeper holds still beside the beacon in soft light." if source["path"] != "reviewedSoundscape" else "Soft wind and quiet cloth movement."}
            for source in target["sources"]]} for target in view["manifest"]["targets"] if target["mode"] == "generate"])


def ready_batch(service, project_id, view):
    return service.edit_directions(project_id, view["revision"], draft_for(view))


def start_batch(service, project_id, view):
    return service.start(project_id, BatchStart(expectedRevision=view["revision"], manifestHash=view["manifestHash"], basis="whole-batch-english.v1"))
