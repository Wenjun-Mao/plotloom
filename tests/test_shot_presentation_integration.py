"""Source-bound creator review preserves unrelated selected synthetic media."""
import shutil
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path

import pytest

from plotloom.canonical_schema import AuthoredVisibleText, V2CoverageRole
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import StageName
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage.video_candidate_transition import (
    ProjectShotPresentationTransitionRequiredError,
)
from tests.project_storage_fixtures import FixtureResolver, fixture_profile
from tests.test_project_storage_image_workflow import _approve
from tests.test_project_storage_video import FakeH3, _fixture_app, _png, _prepare_video


def bind(store, shot, approval, revision, *, presentation_revision=0):
    project = store.manifest.project_id
    # This is an imported fixture, not a generated creative acceptance.
    from plotloom.managed_media import ImportDeclaration, inspect_import_image
    content = _png()
    observed = inspect_import_image(content)
    asset = store.media.record_managed_import(project, original_hash=observed.content_hash,
        display_hash=observed.display_hash, mime_type=observed.mime_type, byte_size=observed.byte_size,
        width=observed.width, height=observed.height,
        declaration=ImportDeclaration(origin="synthetic presentation fixture", rights="unknown").model_dump(mode="json", by_alias=True),
        publish=lambda: (store.artifacts.put(content), store.artifacts.put(observed.display_bytes)))
    intent = store.media.create_visual_intent(project, asset["id"], {
        "role": "shot_keyframe", "identityIntent": "Imported test image.", "sourceRefs": ["synthetic fixture"]})
    selection = store.media.select_reviewed_keyframe(project, asset_id=asset["id"], shot_id=shot.id,
        scene_id=shot.scene_id, expected_selection_revision=store.media.visual_selection_revision(project),
        storyboard_revision=revision, approval_id=approval["id"], compatibility_note="Explicit synthetic binding review.",
        visual_intent_id=intent["id"], visual_intent_revision=intent["revision"], expected_presentation_revision=presentation_revision)
    return {"shot": shot, "revision": revision, "selection": selection}


def body(state, approval, revision, *, mode="popped_out_draft", pointer=None):
    return {"expectedRevision": state["revision"], "sourceHash": state["source"]["sourceHash"],
        "approvalId": approval["id"], "storyboardRevision": revision, "physical": {
            "action": "Review the complete unsent draft while walking." if mode == "popped_out_draft" else "Tap send, then show a clear sent state.",
            "composition": "A large front-facing popped-out reply preview outside the phone.",
            "visualIntent": "Show the authored message legibly.", "motionIntent": "Small hand motions while walking.",
            "cameraMovement": "Gentle following shot."},
        "literalSources": [pointer or {"shotId": state["source"]["shot"]["id"], "index": 0}],
        "messagePresentation": mode, "reason": "The author approved the complete draft preview and separate sending.", "reviewed": True}


def test_amendment_shares_image_h3_projection_and_preserves_six_selected_clips(tmp_path: Path):
    if not shutil.which("ffmpeg"):
        pytest.skip("Synthetic selected segments require FFmpeg")
    video = tmp_path / "synthetic.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:size=576x1024:rate=24",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-frames:v", "124", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-shortest", "-y", str(video)], check=True, timeout=60)
    provider = FakeH3(outputs=[video.read_bytes()])
    storage, client = _fixture_app(tmp_path, provider)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project = store.manifest.project_id
    ProjectPipelineExecutor(FixtureResolver()).execute(store, profile=fixture_profile())
    board = store.authoring.get_stage_payload(project, StageName.STORYBOARD)
    draft = board.shots[0].model_copy(update={"duration_units": 2500, "action": "Type the reply on the readable phone screen.",
        "composition": "A small angled phone screen.", "visible_texts": [AuthoredVisibleText(text="今晚不去了，明天见。",
            source_coordinates={"flowIndex": 3}, source_content_hash="b" * 64)]})
    send = draft.model_copy(update={"id": "shot-send", "order": 2, "action": "Send from the readable phone screen.", "visible_texts": []})
    others = [shot.model_copy(update={"duration_units": 2500}) for shot in board.shots[1:]]
    board = board.model_copy(update={"shots": [draft, send, *others], "shot_beat_links": [*board.shot_beat_links,
        *[link.model_copy(update={"shot_id": send.id, "role": V2CoverageRole.SUPPORTING}) for link in board.shot_beat_links if link.shot_id == draft.id]]})
    store.update_stage(StageName.STORYBOARD, board, expected_revision=store.authoring.get_stage_head(project, StageName.STORYBOARD).revision)
    revision = store.authoring.get_stage_head(project, StageName.STORYBOARD).revision
    store.close()
    approval = _approve(client, project, storage)
    base = f"/api/v2/projects/{project}"
    unchanged = client.get(f"{base}/stages").json()
    selected = []
    for index, shot in enumerate(others[:6]):
        with closing(storage.projects.open(project)) as store:
            context = bind(store, shot, approval, revision)
        job = _prepare_video(client, project, approval, context, key=f"selected-{index}")
        assert client.post(f"{base}/video-jobs/{job['id']}/submit").status_code == 200
        assert client.post(f"{base}/video-jobs/{job['id']}/reconcile").status_code == 200
        response = client.post(f"{base}/video-jobs/{job['id']}/segments", json={"inFrame": 0, "outFrame": 60, "expectedSelectionRevision": 0})
        assert response.status_code == 201, response.text
        segment = response.json()
        accepted = client.post(f"{base}/video-segments/{segment['id']}/select", json={"expectedSelectionRevision": 0})
        assert accepted.status_code == 201, accepted.text
        selected.append(job)
    with closing(storage.projects.open(project)) as store:
        context = bind(store, draft, approval, revision)
    old_job = _prepare_video(client, project, approval, context, key="old-draft")
    state = client.get(f"{base}/shots/{draft.id}/production-presentation").json()
    review = body(state, approval, revision)
    wrong = {**review, "sourceHash": "a" * 64}
    assert client.put(f"{base}/shots/{draft.id}/production-presentation", json=wrong).status_code == 409
    response = client.put(f"{base}/shots/{draft.id}/production-presentation", json=review)
    assert response.status_code == 200, response.text
    assert client.put(f"{base}/shots/{draft.id}/production-presentation", json=review).status_code == 409
    assert client.get(f"{base}/stages").json() == unchanged
    workbench = client.get(f"{base}/visual-workbench").json()
    assert draft.id not in {binding["shotId"] for binding in workbench["reviewedKeyframes"]}
    with closing(storage.projects.open(project)) as store:
        with pytest.raises(Exception, match="shot-presentation"):
            bind(store, draft, approval, revision)
        context = bind(store, draft, approval, revision, presentation_revision=1)
        image = store.media.prepare_image_job(project, approval_id=approval["id"], shot_id=draft.id,
            storyboard_revision=revision, presentation_change="Use the reviewed preview treatment.", contract_version=3)
    amended = _prepare_video(client, project, approval, context, key="amended-draft")
    image_snapshot = image["job"]["request"]["frozenSnapshot"]
    for field in ("shot", "resolvedContext", "shotPresentation"):
        assert image_snapshot[field] == amended["snapshot"][field]
    assert "readable phone screen" not in str(amended["snapshot"]["resolvedContext"])
    assert "character-by-character" in amended["snapshot"]["compiledPrompt"]
    assert amended["snapshot"]["shot"]["visibleTexts"][0] == draft.visible_texts[0].model_dump(mode="json", by_alias=True)
    state = client.get(f"{base}/shots/{send.id}/production-presentation").json()
    review_send = body(state, approval, revision, mode="popped_out_send", pointer={"shotId": draft.id, "index": 0})
    sent = client.put(f"{base}/shots/{send.id}/production-presentation", json=review_send)
    assert sent.status_code == 200, sent.text
    assert sent.json()["decision"]["effectiveShot"]["visibleTexts"] == image_snapshot["shot"]["visibleTexts"]
    jobs = {job["id"]: job for job in client.get(f"{base}/video-jobs").json()["jobs"]}
    assert not jobs[old_job["id"]]["current"]
    for original in selected:
        kept = jobs[original["id"]]
        assert kept["current"] and kept["selected"]
        assert kept["snapshot"] == original["snapshot"] and kept["snapshotHash"] == original["snapshotHash"]
    assert client.get(f"{base}/stages").json() == unchanged


def test_exact_predecessor_schema_adds_only_empty_decision_table(tmp_path: Path):
    storage, _ = _fixture_app(tmp_path, FakeH3())
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project, database = store.manifest.project_id, store.database_path
    store.close()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE v2_shot_presentations")
        retained = connection.execute("SELECT * FROM v2_projects").fetchall()
    original = database.read_bytes()
    with pytest.raises(ProjectShotPresentationTransitionRequiredError):
        storage.projects.inspect(project)
    assert database.read_bytes() == original
    with closing(storage.projects.open(project)):
        pass
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT * FROM v2_projects").fetchall() == retained
        assert connection.execute("SELECT * FROM v2_shot_presentations").fetchall() == []
