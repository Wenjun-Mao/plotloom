"""Atomic genuine-human facts and video authority; deterministic media only."""
from contextlib import closing
from copy import deepcopy
import pytest
from plotloom.autopilot_handoff_contracts import HumanHandoffRequest
from plotloom.autopilot_contracts import RunControlRequest, RunView
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.project.autopilot_handoff import review_material, record_handoff
from plotloom.persistence.project.autopilot_authority import video_eligible
from tests.autopilot_image_fixtures import image_environment, run_pack


def observation(review):
    bundle = review["bundle"]
    return {"expectedRunRevision": review["runRevision"], "bundleHash": review["bundleHash"],
        "reviewer": "Fixture human", "notes": "Fixture observations; not owner product acceptance.",
        "endorsedReferenceIds": [item["decisionId"] for item in bundle["references"]],
        "frames": [{"shotId": frame["shotId"], "assetId": frame["assetId"],
            "intent": {"role": "shot_keyframe", "compositionIntent": "Keep the visible action and framing readable.", "sourceRefs": [frame["shotId"]]},
            "compatibilityNote": "Inspected this exact fixture frame against its current shot.",
            "comparisons": [{"characterId": identifier, "judgment": "pass", "identityNotes": "Observed the visible face relative to the displayed reference.",
                "stateNotes": "Observed the pose and wardrobe in this frame."} for identifier in frame["characterIds"]]} for frame in bundle["frames"]]}


def test_exact_human_handoff_preserves_machine_origin_and_withdraws_after_edit(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from plotloom.api import create_project_folder_authoring_app
    storage, _registry, service, view, calls, text = image_environment(tmp_path, monkeypatch)
    try:
        complete = run_pack(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            review = review_material(store)
            with store.repository._read() as session:
                assert not video_eligible(session, view.project_id)
            client = TestClient(create_project_folder_authoring_app(storage))
            endpoint = f"/api/v2/projects/{view.project_id}/autopilot"
            assert client.get(endpoint + "/launch-context").json()["eligible"] is False
            assert client.get(endpoint + "/review").json()["bundleHash"] == review["bundleHash"]
            assert client.post(endpoint + "/handoff", json=observation(review) | {"authority": "machine"}).status_code == 422
            response = client.post(endpoint + "/handoff", json=observation(review))
            assert response.status_code == 200, response.text
            result = RunView.model_validate(response.json())
            assert result.state == "handed_off"
            with store.repository._read() as session:
                assert video_eligible(session, view.project_id)
            with store.repository.engine.connect() as connection:
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_autopilot_handoffs").scalar() == 1
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_approval_decisions").scalar() == 1
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_reviewed_shot_bindings").scalar() == len(complete.frames)
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_production_units WHERE approval_id IS NOT NULL").scalar() == 0
                assert connection.exec_driver_sql("SELECT count(*) FROM v2_video_jobs").scalar() == 0
                original = connection.exec_driver_sql("SELECT receipt FROM v2_autopilot_handoffs").scalar()
            with store.repository.manual_command() as session:
                project = store.repository._project_access.rows.project(session, view.project_id)
                project.brief = project.brief | {"title": "Manual title after handoff"}
                project.revision += 1
            with store.repository._read() as session:
                assert not video_eligible(session, view.project_id)
            with store.repository.engine.connect() as connection:
                assert connection.exec_driver_sql("SELECT receipt FROM v2_autopilot_handoffs").scalar() == original
        with closing(storage.projects.open(view.project_id)):
            pass  # Ordinary raw admission validates retained history after an edit.
        assert len(calls) == 29 and len(text) == 8
    finally:
        service.close()


@pytest.mark.parametrize("defect", ["missing", "fail", "hold", "asset", "references"])
def test_invalid_whole_handoff_creates_no_partial_human_authority(tmp_path, monkeypatch, defect):
    storage, _registry, service, view, _calls, _text = image_environment(tmp_path, monkeypatch)
    try:
        run_pack(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            review = review_material(store)
            body = deepcopy(observation(review))
            if defect == "missing": body["frames"].pop()
            elif defect == "fail": body["frames"][0]["comparisons"][0]["judgment"] = "fail"
            elif defect == "hold": body["frames"][0]["comparisons"][0].update(judgment="unassessable", productionDecision="hold", uncertaintyReason="Face occluded")
            elif defect == "asset": body["frames"][0]["assetId"] = "another-asset"
            else: body["endorsedReferenceIds"].pop()
            with pytest.raises(InvalidTransitionError): record_handoff(store, HumanHandoffRequest.model_validate(body))
            with store.repository.engine.connect() as connection:
                for table in ("v2_approval_decisions", "v2_visual_intents", "v2_reviewed_shot_bindings", "v2_same_person_reviews", "v2_autopilot_handoffs", "v2_video_jobs"):
                    assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == 0
    finally:
        service.close()


def test_takeover_accepts_current_bundle_and_explicit_unassessable_authorization(tmp_path, monkeypatch):
    storage, _registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch)
    try:
        complete = run_pack(storage, service, view)
        service.control(view.project_id, RunControlRequest(expected_revision=complete.revision, action="takeover"))
        with closing(storage.projects.open(view.project_id)) as store:
            body = observation(review_material(store))
            body["frames"][0]["comparisons"][0].update(judgment="unassessable", productionDecision="authorize", uncertaintyReason="Face partly hidden; human accepts this exact framing.")
            assert record_handoff(store, HumanHandoffRequest.model_validate(body)).state == "handed_off"
        with closing(storage.projects.open(view.project_id)) as store:
            with store.repository._read() as session: assert video_eligible(session, view.project_id)
        assert len(calls) == 29
    finally:
        service.close()


def test_manual_import_replaces_one_frame_and_can_receive_fresh_human_handoff(tmp_path, monkeypatch):
    from hashlib import sha256
    from io import BytesIO
    from PIL import Image
    from plotloom.persistence.schema import VisualSelectionStateRow, AutopilotHandoffRow, SamePersonReviewRow
    from sqlalchemy import select
    storage, _registry, service, view, calls, _text = image_environment(tmp_path, monkeypatch)
    try:
        run_pack(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            initial = record_handoff(store, HumanHandoffRequest.model_validate(observation(review_material(store))))
            frame = initial.frames[0]
            buffer = BytesIO(); Image.new("RGB", (view.policy.image_width, view.policy.image_height), "blue").save(buffer, format="PNG")
            content = buffer.getvalue(); digest = sha256(content).hexdigest(); uri = store.artifacts.put(content)
            asset = store.media.record_managed_import(view.project_id, original_hash=digest, display_hash=digest,
                mime_type="image/png", byte_size=len(content), width=view.policy.image_width, height=view.policy.image_height,
                declaration={"origin": "manual", "rights": "unknown"}, publish=lambda: (uri, uri))
            intent = store.media.create_visual_intent(view.project_id, asset["id"], {"role": "shot_keyframe", "compositionIntent": "Manual replacement framing.", "sourceRefs": [frame.shot_id]})
            with store.repository._read() as session:
                revision = session.get(VisualSelectionStateRow, view.project_id).revision
                presentation = store.repository._media.shot_presentations.current(session, view.project_id, frame.shot_id)
                retained = session.get(AutopilotHandoffRow, initial.handoff["receiptId"])
                approval = retained.approval_id
            store.media.select_reviewed_keyframe(view.project_id, asset_id=asset["id"], shot_id=frame.shot_id, scene_id=frame.scene_id,
                expected_selection_revision=revision, storyboard_revision=frame.storyboard_revision, approval_id=approval,
                compatibility_note="Inspected manual replacement.", visual_intent_id=intent["id"], visual_intent_revision=intent["revision"],
                expected_presentation_revision=presentation["revision"] if presentation else 0)
            review = review_material(store)
            replacement = next(item for item in review["bundle"]["frames"] if item["shotId"] == frame.shot_id)
            assert replacement["origin"] == "human_binding"
            assert replacement["assetId"] == asset["id"]
            result = record_handoff(store, HumanHandoffRequest.model_validate(observation(review)))
            assert result.state == "handed_off"
            with store.repository._read() as session:
                assert video_eligible(session, view.project_id)
                assert len(session.scalars(select(AutopilotHandoffRow)).all()) == 2
                reviews = session.scalars(select(SamePersonReviewRow).order_by(SamePersonReviewRow.review_revision.desc())).all()
                assert any(item.get("comparisonOrigin") == "human_current_material" for row in reviews for item in row.reference_bindings)
        with closing(storage.projects.open(view.project_id)):
            pass
        from pathlib import Path
        from tests.test_autopilot_recovery import storage_at
        snapshot = storage.recovery.create_snapshot(view.project_id)
        restored = storage_at(tmp_path / "handoff-restored")
        restored.recovery.restore(Path(snapshot.location))
        restored.recovery.acknowledge_recovery(view.project_id)
        with closing(restored.projects.open(view.project_id)) as store:
            with store.repository._read() as session:
                assert video_eligible(session, view.project_id)
                assert len(session.scalars(select(AutopilotHandoffRow)).all()) == 2
            with pytest.raises(InvalidTransitionError, match="portable"):
                store.repository.autopilot.claim(view.project_id, "destination-controller")
        assert len(calls) == 29
    finally:
        service.close()


def test_mid_handoff_failure_rolls_back_all_native_human_rows(tmp_path, monkeypatch):
    storage, _registry, service, view, _calls, _text = image_environment(tmp_path, monkeypatch)
    try:
        run_pack(storage, service, view)
        with closing(storage.projects.open(view.project_id)) as store:
            request = HumanHandoffRequest.model_validate(observation(review_material(store)))
            original = store.repository._media.keyframes.select_reviewed_keyframe
            attempts = []
            def fail_after_first(*args, **kwargs):
                attempts.append(kwargs["shot_id"])
                if len(attempts) == 2: raise RuntimeError("fixture late admission failure")
                return original(*args, **kwargs)
            monkeypatch.setattr(store.repository._media.keyframes, "select_reviewed_keyframe", fail_after_first)
            with pytest.raises(RuntimeError, match="late admission"): record_handoff(store, request)
            with store.repository.engine.connect() as connection:
                for table in ("v2_approval_decisions", "v2_visual_intents", "v2_reviewed_shot_bindings", "v2_same_person_reviews", "v2_autopilot_handoffs"):
                    assert connection.exec_driver_sql(f'SELECT count(*) FROM "{table}"').scalar() == 0
            assert store.repository.autopilot.current(view.project_id).state == "awaiting_review"
    finally:
        service.close()
