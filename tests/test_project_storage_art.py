"""F3A regression: art is source/map/graph/cast bound and text-first."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import (
    ArtAcceptRequest,
    ArtReopenRequest,
    ArtSaveRequest,
)
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.exceptions import NotFoundError
from plotloom.project_storage.composition import ProjectFolderStorage
from plotloom.project_storage.format import ProjectStorageCorruptionError
from plotloom.project_storage.operational_state import close_blockers
from tests.art_delivery_fixtures import (
    _deliver,
    _write_art_reference_delivery,
)
from tests.creative_delivery_fixtures import (
    _prepare_art_context,
)


def test_art_accept_reopen_cancel_and_currentness(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    try:
        binding = _prepare_art_context(store)
        # _prepare_art_context opens and cancels no art handoff; its binding is
        # from the actual accepted source/map/graph/cast revisions.
        candidate, request = store.prepare_art_candidate(
            "ch_" + "a" * 32, render_style="realistic"
        )
        assert request.input_artifacts.keys() == {
            "outline.json",
            "section-map.json",
            "cast.json",
            "art-style-contract.json",
        }
        assert "F3B" in request.creative_brief
        assert "art_publication_active" in close_blockers(store)
        client = TestClient(create_project_folder_authoring_app(storage))
        recovered = client.get(
            f"/api/v2/projects/{store.manifest.project_id}/art/candidates/{candidate.job_id}/handoff"
        )
        assert recovered.status_code == 200
        assert recovered.json()["jobId"] == candidate.job_id
        assert request.job_id in recovered.json()["assignment"]
        ready = store.admit_art_delivery(_deliver(store, request))
        assert ready.art and ready.art["scenes"][0]["id"] == "S01"
        accepted = store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=request.job_id,
                expected_art_revision=0,
                binding=binding,
                art=ready.art,
            )
        )
        assert accepted.accepted_art and accepted.accepted_art.revision == 1
        store.reopen_art(ArtReopenRequest(expected_art_revision=1))
        edited = dict(ready.art or {})
        edited["scenes"] = [dict(edited["scenes"][0], summary="edited text only")]
        saved = store.save_reopened_art(
            ArtSaveRequest(expected_art_revision=1, binding=binding, art=edited)
        )
        assert saved.accepted_art and saved.accepted_art.revision == 2
        assert (
            "does not describe the current accepted revision"
            in store.art_candidate_report(request.job_id)
        )
        prepared, _ = store.prepare_art_candidate(
            "ch_" + "b" * 32, render_style="realistic"
        )
        store.cancel_art_candidate(prepared.job_id)
        with pytest.raises(NotFoundError, match="unavailable"):
            store.art_candidate_request(prepared.job_id)
        assert store.art_state().status == "accepted"
    finally:
        store.close()


def test_art_routes_are_user_reachable(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    response = client.get(f"/api/v2/projects/{project_id}/art")
    assert response.status_code == 200
    assert response.json() == {
        "candidate": None,
        "acceptedArt": None,
        "status": "missing",
        "staleReasons": [],
        "acceptedReviewState": {"status": "missing", "staleReasons": []},
    }


def test_art_reference_study_browser_lifecycle_persists_and_stales(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate(
            "ch_" + "r" * 32, render_style="realistic"
        )
        ready = store.admit_art_delivery(_deliver(store, request))
        accepted = store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=candidate.job_id,
                expected_art_revision=0,
                binding=binding,
                art=ready.art,
            )
        )
        assert accepted.accepted_art
    finally:
        store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    prepared = client.post(
        f"/api/v2/projects/{project_id}/art-reference-proposals",
        json={
            "subjectType": "scene",
            "subjectId": "S01",
            "renderDirection": "Cinematic realism, no people.",
        },
    )
    assert prepared.status_code == 201, prepared.text
    proposal = prepared.json()["proposal"]
    copied = client.post(
        f"/api/v2/projects/{project_id}/art-reference-proposals/{proposal['id']}/copy"
    )
    assert copied.status_code == 200, copied.text
    assert (
        "Cinematic realism" in proposal["request"]["frozenSnapshot"]["renderDirection"]
    )
    _write_art_reference_delivery(Path(copied.json()["deliveryPath"]), proposal)
    delivered = client.post(
        f"/api/v2/projects/{project_id}/art-reference-proposals/{proposal['id']}/refresh"
    )
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["state"] == "accepted"
    assert delivered.json()["candidates"][0]["role"] == "art_reference"
    reopened = storage.projects.open(project_id)
    reopened.close()
    visible = client.get(f"/api/v2/projects/{project_id}/art-reference-proposals")
    assert visible.status_code == 200
    assert visible.json()["proposals"][0]["current"] is True
    # Accepted-art edits keep historic evidence but visibly invalidate its study.
    edit_store = storage.projects.open(project_id)
    try:
        edit_store.reopen_art(ArtReopenRequest(expected_art_revision=1))
        edited = dict(edit_store.art_state().accepted_art.art)  # type: ignore[union-attr]
        edited["scenes"] = [dict(edited["scenes"][0], summary="changed accepted art")]
        edit_store.save_reopened_art(
            ArtSaveRequest(expected_art_revision=1, binding=binding, art=edited)
        )
    finally:
        edit_store.close()
    stale = client.get(f"/api/v2/projects/{project_id}/art-reference-proposals")
    assert stale.json()["proposals"][0]["current"] is False
    later = client.post(
        f"/api/v2/projects/{project_id}/art-reference-proposals",
        json={
            "subjectType": "scene",
            "subjectId": "S01",
            "renderDirection": "Cinematic realism, no people.",
        },
    )
    assert later.status_code == 201, later.text
    active = later.json()["proposal"]
    copied_late = client.post(
        f"/api/v2/projects/{project_id}/art-reference-proposals/{active['id']}/copy"
    )
    assert copied_late.status_code == 200, copied_late.text
    cancellation = client.post(
        f"/api/v2/projects/{project_id}/art-reference-proposals/{active['id']}/cancel",
        json={"reason": "Operator ended the package before delivery."},
    )
    assert cancellation.status_code == 200
    _write_art_reference_delivery(Path(copied_late.json()["deliveryPath"]), active)
    late = client.post(
        f"/api/v2/projects/{project_id}/art-reference-proposals/{active['id']}/refresh"
    )
    assert late.status_code == 200, late.text
    assert late.json()["state"] == "inapplicable"
    assert late.json()["candidates"] == []


def test_art_reference_decisions_are_explicit_cas_bound_historical_and_stale(
    tmp_path: Path,
) -> None:
    """F3B selection is a local persistence contract, not a generation claim.

    The retained test-only delivery helper supplies isolated mocked bytes. It
    exercises the decision admission boundary without presenting fixture
    provenance as real ImageGen evidence or invoking a provider.
    """

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate(
            "ch_" + "d" * 32, render_style="realistic"
        )
        ready = store.admit_art_delivery(_deliver(store, request))
        accepted = store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=candidate.job_id,
                expected_art_revision=0,
                binding=binding,
                art=ready.art,
            )
        )
        assert accepted.accepted_art and accepted.accepted_art.revision == 1
    finally:
        store.close()

    client = TestClient(create_project_folder_authoring_app(storage))

    def deliver_study(direction: str) -> dict[str, object]:
        prepared = client.post(
            f"/api/v2/projects/{project_id}/art-reference-proposals",
            json={
                "subjectType": "scene",
                "subjectId": "S01",
                "renderDirection": direction,
            },
        )
        assert prepared.status_code == 201, prepared.text
        proposal = prepared.json()["proposal"]
        copied = client.post(
            f"/api/v2/projects/{project_id}/art-reference-proposals/{proposal['id']}/copy"
        )
        assert copied.status_code == 200, copied.text
        _write_art_reference_delivery(Path(copied.json()["deliveryPath"]), proposal)
        delivered = client.post(
            f"/api/v2/projects/{project_id}/art-reference-proposals/{proposal['id']}/refresh"
        )
        assert delivered.status_code == 200, delivered.text
        assert delivered.json()["state"] == "accepted"
        candidate = delivered.json()["candidates"][0]
        return {
            "proposal": proposal,
            "assetId": candidate["assetId"],
            "assetHash": candidate["asset"]["originalHash"],
        }

    first = deliver_study("Fixture study one; no people.")
    second = deliver_study("Fixture study two; no people.")
    assert first["assetId"] != second["assetId"]
    initially = client.get(f"/api/v2/projects/{project_id}/art-reference-decisions")
    assert initially.status_code == 200
    assert initially.json() == {"states": [], "decisions": []}

    chosen = client.post(
        f"/api/v2/projects/{project_id}/art-reference-decisions",
        json={
            "subjectType": "scene",
            "subjectId": "S01",
            "assetId": first["assetId"],
            "expectedReferenceRevision": 0,
        },
    )
    assert chosen.status_code == 201, chosen.text
    assert chosen.json()["stateRevision"] == 1
    assert chosen.json()["current"] is True
    assert chosen.json()["acceptedArtRevision"] == 1
    assert chosen.json()["assetHash"] == first["assetHash"]

    stale_cas = client.post(
        f"/api/v2/projects/{project_id}/art-reference-decisions",
        json={
            "subjectType": "scene",
            "subjectId": "S01",
            "assetId": second["assetId"],
            "expectedReferenceRevision": 0,
        },
    )
    assert stale_cas.status_code == 409
    wrong_subject = client.post(
        f"/api/v2/projects/{project_id}/art-reference-decisions",
        json={
            "subjectType": "prop",
            "subjectId": "P01",
            "assetId": second["assetId"],
            "expectedReferenceRevision": 0,
        },
    )
    assert wrong_subject.status_code == 409  # P01 is not an accepted prop subject.

    replacement = client.post(
        f"/api/v2/projects/{project_id}/art-reference-decisions",
        json={
            "subjectType": "scene",
            "subjectId": "S01",
            "assetId": second["assetId"],
            "expectedReferenceRevision": 1,
        },
    )
    assert replacement.status_code == 201, replacement.text
    assert replacement.json()["stateRevision"] == 2
    visible = client.get(
        f"/api/v2/projects/{project_id}/art-reference-decisions"
    ).json()
    assert visible["states"] == [
        {
            "subjectType": "scene",
            "subjectId": "S01",
            "revision": 2,
            "activeDecisionId": replacement.json()["id"],
            "current": True,
        }
    ]
    assert [item["assetId"] for item in visible["decisions"]] == [
        second["assetId"],
        first["assetId"],
    ]
    assert [item["current"] for item in visible["decisions"]] == [True, False]

    # A normal reopen preserves the state head and append-only history.
    reopened = storage.projects.open(project_id)
    reopened.close()
    assert (
        client.get(f"/api/v2/projects/{project_id}/art-reference-decisions").json()[
            "states"
        ][0]["revision"]
        == 2
    )

    # Reopening and editing accepted art invalidates, but never deletes or
    # redirects, the old subject decision.
    edited_store = storage.projects.open(project_id)
    try:
        edited_store.reopen_art(ArtReopenRequest(expected_art_revision=1))
        edited = dict(edited_store.art_state().accepted_art.art)  # type: ignore[union-attr]
        edited["scenes"] = [
            dict(edited["scenes"][0], summary="reference context changed")
        ]
        edited_store.save_reopened_art(
            ArtSaveRequest(expected_art_revision=1, binding=binding, art=edited)
        )
    finally:
        edited_store.close()
    stale = client.get(f"/api/v2/projects/{project_id}/art-reference-decisions").json()
    assert stale["states"][0]["current"] is False
    assert [item["current"] for item in stale["decisions"]] == [False, False]
    assert len(stale["decisions"]) == 2


def test_format_10_folder_is_refused_with_reset_required_guidance(
    tmp_path: Path,
) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id, manifest_path = store.manifest.project_id, store.home / "project.json"
    store.close()
    manifest = json.loads(manifest_path.read_text())
    manifest["formatVersion"] = 10
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(
        ProjectStorageCorruptionError,
        match="format 10 or older is unsupported by F5A; reset required",
    ):
        storage.projects.open(project_id)
