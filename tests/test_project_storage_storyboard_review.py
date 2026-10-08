"""F5A source storyboard review lifecycle and admission contracts."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.project_storage.operational_state import (
    ProjectBusyError, close_blockers, specialist_publication_blockers,
)
from plotloom.script_contracts import ScriptReopenRequest, ScriptSectionSaveRequest
from plotloom.storyboard_review_contracts import StoryboardReviewAcceptRequest
from tests.test_project_storage_art import _accepted_f4_script, _deliver_stage


def test_f5a_freezes_current_f4_identity_blocks_lifecycle_and_refuses_late_delivery(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        _accepted_f4_script(store)
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "s" * 32)
        assert candidate.binding.script_revision == 1
        assert candidate.binding.script_content_hash == store.script_state().accepted_script.content_hash  # type: ignore[union-attr]
        assert request.input_artifacts.keys() == {"script.json", "outline.json", "cast.json", "art.json", "storyboard-admission.json"}
        assert request.input_artifacts["storyboard-admission.json"]["sectionBindings"] == [
            {"sectionId": "opening", "episode": 1}, {"sectionId": "ending-a", "episode": 2}, {"sectionId": "ending-b", "episode": 3},
        ]
        assert "storyboard_review_publication_active" in close_blockers(store)
        assert "storyboard_review_publication_active" in specialist_publication_blockers(store)
        store.close()
        with pytest.raises(ProjectBusyError, match="storyboard_review_publication_active"):
            storage.recovery.create_snapshot(project_id)
        store = storage.projects.open(project_id)
        store.cancel_storyboard_review_candidate(candidate.job_id)
        with pytest.raises(Exception, match="current prepared|unavailable|cancelled"):
            store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", {"episodes": []}, "late-storyboard"))
    finally:
        store.close()
    assert storage.recovery.create_snapshot(project_id).status == "complete"


def test_f5a_requires_exact_f4_episode_mapping_before_upstream_validation(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        _candidate, request = store.prepare_storyboard_review_candidate("ch_" + "r" * 32)
        with pytest.raises(ValueError, match="exactly match the frozen F4 section-to-episode mapping"):
            store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", {"episodes": [{"ep": 2}, {"ep": 1}, {"ep": 3}]}, "swapped-storyboard"))
    finally:
        store.close()


def test_f5a_rejects_delivery_timing_that_raises_frozen_limits_before_upstream_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """F5A owns its frozen review caps; the upstream gate is an additional check."""
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        candidate, _request = store.prepare_storyboard_review_candidate("ch_" + "t" * 32)
        # The candidate is structurally enough for the local F5A gate. A mock
        # upstream process proves this rejection happens before its invocation.
        called = False
        def upstream(*_args: object, **_kwargs: object) -> object:
            nonlocal called
            called = True
            return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        monkeypatch.setattr("plotloom.persistence.project.storyboard_review.subprocess.run", upstream)
        board = {"params": {"maxCutSeconds": 9, "maxSegmentSeconds": 15}, "episodes": [
            {"ep": 1, "segments": [{"cuts": [{"seconds": 3}]}]},
            {"ep": 2, "segments": [{"cuts": [{"seconds": 3}]}]},
            {"ep": 3, "segments": [{"cuts": [{"seconds": 3}]}]},
        ]}
        with pytest.raises(ValueError, match="frozen review timing limits"):
            from plotloom.persistence.project.storyboard_review import ProjectStoryboardReviewPersistence
            ProjectStoryboardReviewPersistence._validate(board, candidate.binding, {}, {}, {})
        assert called is False
    finally:
        store.close()


def test_f5a_uses_a_distinct_source_review_api_not_the_canonical_storyboard_review(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        _accepted_f4_script(store)
    finally:
        store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    state = client.get(f"/api/v2/projects/{project_id}/storyboard-source-review")
    assert state.status_code == 200, state.text
    assert state.json()["status"] == "missing"
    prepared = client.post(f"/api/v2/projects/{project_id}/storyboard-source-review/candidates")
    assert prepared.status_code == 201, prepared.text
    assert prepared.json()["binding"]["scriptRevision"] == 1
    assert prepared.json()["assignment"].startswith("Plotloom F5A storyboard review assignment")
    bridge = client.get(f"/api/v2/projects/{project_id}/production-bridge")
    assert bridge.status_code == 200, bridge.text
    assert bridge.json() == {
        "proposal": None,
        "status": "missing",
        "staleReasons": [],
        "installation": None,
        "preparation": {
            "status": "unavailable",
            "reason": "a current accepted F5 storyboard review is required",
        },
        "intentJob": None,
        "simulationLabel": None,
        "intentGeneration": {"status": "unavailable", "reason": "not_configured"},
        "nativeIntentGeneration": {"status": "unavailable", "reason": "not_configured"},
        "nativeIntentTask": None,
    }


def test_f5a_explicit_longer_cut_review_survives_restart_and_preserves_old_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    monkeypatch.setattr("plotloom.persistence.project.storyboard_review.ProjectStoryboardReviewPersistence._validate", staticmethod(lambda *_args: None))
    try:
        _accepted_f4_script(store)
        old, old_request = store.prepare_storyboard_review_candidate("ch_trialoldpolicy20260925aaaaaaaaaaaa")
        old_ready = store.admit_storyboard_review_delivery(_deliver_stage(store, old_request, "storyboard.json", {"episodes": []}, "old-eight"))
        accepted = store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=old.job_id, expected_review_revision=0, binding=old_ready.binding))
        assert accepted.status == "accepted"
        assert accepted.accepted_review.binding.review_max_cut_seconds == 8  # type: ignore[union-attr]
    finally:
        store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    assert client.get(f"/api/v2/projects/{project_id}/storyboard-source-review").json()["status"] == "accepted"
    assert client.post(f"/api/v2/projects/{project_id}/storyboard-source-review/candidates", json={"maxCutSeconds": 16}).status_code == 422
    prepared = client.post(f"/api/v2/projects/{project_id}/storyboard-source-review/candidates", json={"maxCutSeconds": 12})
    assert prepared.status_code == 201, prepared.text
    assert prepared.json()["binding"]["reviewMaxCutSeconds"] == 12
    job_id = prepared.json()["jobId"]
    store = storage.projects.open(project_id)
    try:
        request = store.storyboard_review_candidate_request(job_id)
        assert request.input_artifacts["storyboard-admission.json"]["reviewTiming"]["maxCutSeconds"] == 12
        store.creative_handoff_exchange().write_package(request, store.creative_handoff_execution_pin(request))
        _deliver_stage(store, request, "storyboard.json", {"episodes": []}, "longer-twelve")
    finally:
        store.close()
    refreshed = client.post(f"/api/v2/projects/{project_id}/storyboard-source-review/candidates/{job_id}/refresh")
    assert refreshed.status_code == 200, refreshed.text
    chosen = client.post(f"/api/v2/projects/{project_id}/storyboard-source-review/accept", json={
        "jobId": job_id, "expectedReviewRevision": 1, "binding": refreshed.json()["binding"],
    })
    assert chosen.status_code == 200, chosen.text
    assert chosen.json()["acceptedReview"]["binding"]["reviewMaxCutSeconds"] == 12
    assert chosen.json()["staleReasons"] == []


def test_f5a_accepted_review_stales_when_accepted_f4_script_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Lifecycle proof; the separate validator owns candidate-content checks."""
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        monkeypatch.setattr("plotloom.persistence.project.storyboard_review.ProjectStoryboardReviewPersistence._validate", staticmethod(lambda *_args: None))
        candidate, request = store.prepare_storyboard_review_candidate("ch_" + "u" * 32)
        board = {"episodes": [{"ep": 1}, {"ep": 2}, {"ep": 3}]}
        ready = store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", board, "storyboard-fixture"))
        # Client input cannot replace the admitted raw JSON that the report describes.
        with pytest.raises(ValueError, match="storyboard"):
            StoryboardReviewAcceptRequest.model_validate({
                "jobId": candidate.job_id, "expectedReviewRevision": 0, "binding": ready.binding.model_dump(mode="json", by_alias=True),
                "storyboard": {"episodes": [{"ep": 3}, {"ep": 2}, {"ep": 1}]},
            })
        accepted = store.accept_storyboard_review_candidate(StoryboardReviewAcceptRequest(job_id=candidate.job_id, expected_review_revision=0, binding=ready.binding))
        assert accepted.accepted_review and accepted.accepted_review.storyboard == board
        script = store.script_state().accepted_script
        assert script is not None
        store.reopen_script(ScriptReopenRequest(expected_script_revision=script.revision))
        opening = dict(script.script["episodes"][0]); opening["cliff"] = "Changed F4 source authority."
        store.save_script_section(ScriptSectionSaveRequest(expected_script_revision=script.revision, binding=script.binding, section_id="opening", episode=opening))
        assert store.storyboard_review_state().status == "stale"
    finally:
        store.close()


def test_f5a_requires_explicit_decision_before_replacing_a_ready_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        _accepted_f4_script(store)
        monkeypatch.setattr("plotloom.persistence.project.storyboard_review.ProjectStoryboardReviewPersistence._validate", staticmethod(lambda *_args: None))
        _candidate, request = store.prepare_storyboard_review_candidate("ch_" + "v" * 32)
        store.admit_storyboard_review_delivery(_deliver_stage(store, request, "storyboard.json", {"episodes": [{"ep": 1}, {"ep": 2}, {"ep": 3}]}, "ready-storyboard"))
        with pytest.raises(Exception, match="accept or cancel the current storyboard review candidate"):
            store.prepare_storyboard_review_candidate("ch_" + "w" * 32)
    finally:
        store.close()

