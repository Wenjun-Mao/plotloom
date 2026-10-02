"""A second requirements-based study never replaces accepted art or a choice."""

from pathlib import Path

from fastapi.testclient import TestClient

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import ArtAcceptRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.project_storage.composition import ProjectFolderStorage
from tests.test_project_storage_art import (
    _deliver,
    _prepare_art_context,
    _write_art_reference_delivery,
)


def test_another_candidate_preserves_first_request_bytes_and_selected_reference(
    tmp_path,
):
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate(
            "ch_" + "a" * 32, render_style="realistic"
        )
        ready = store.admit_art_delivery(_deliver(store, request))
        store.accept_art_candidate(
            ArtAcceptRequest(
                job_id=candidate.job_id,
                expected_art_revision=0,
                binding=binding,
                art=ready.art,
            )
        )
    finally:
        store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    project_url = f"/api/v2/projects/{project_id}"
    url = f"{project_url}/art-reference-proposals"

    def prepare(direction):
        result = client.post(
            url,
            json={
                "subjectType": "scene",
                "subjectId": "S01",
                "renderDirection": direction,
            },
        )
        assert result.status_code == 201, result.text
        return result.json()["proposal"]

    def deliver(proposal):
        copied = client.post(f"{url}/{proposal['id']}/copy")
        assert copied.status_code == 200, copied.text
        directory = Path(copied.json()["deliveryPath"])
        _write_art_reference_delivery(directory, proposal)
        result = client.post(f"{url}/{proposal['id']}/refresh")
        assert result.status_code == 200, result.text
        assert result.json()["state"] == "accepted"
        return result.json()["candidates"][0]["assetId"], directory.parent

    first = prepare("初次图片要求。")
    first_asset, first_job = deliver(first)
    chosen = client.post(
        f"{project_url}/art-reference-decisions",
        json={
            "subjectType": "scene",
            "subjectId": "S01",
            "assetId": first_asset,
            "expectedReferenceRevision": 0,
        },
    )
    assert chosen.status_code == 201, chosen.text
    decisions = client.get(f"{project_url}/art-reference-decisions").json()
    art = client.get(f"{project_url}/art").json()
    first_record = client.get(url).json()["proposals"][0]
    first_bytes = {
        file.relative_to(first_job): file.read_bytes()
        for file in first_job.rglob("*")
        if file.is_file()
    }

    second = prepare("降低观察角度；保留已接受的环境布局。")
    assert second["id"] != first["id"]
    assert second["requestHash"] != first["requestHash"]
    assert second["state"] == "prepared"
    assert second["exportedAt"] is None
    assert (
        second["request"]["frozenSnapshot"]["acceptedArt"]
        == first["request"]["frozenSnapshot"]["acceptedArt"]
    )
    assert client.get(f"{project_url}/art-reference-decisions").json() == decisions
    second_asset, _ = deliver(second)
    assert second_asset != first_asset

    # Reconstruct the API/storage owner as a reload, retaining both candidates.
    reopened_storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )
    reopened = TestClient(create_project_folder_authoring_app(reopened_storage))
    proposals = reopened.get(url).json()["proposals"]
    assert len(proposals) == 2
    assert all(item["current"] and item["state"] == "delivered" for item in proposals)
    assert next(item for item in proposals if item["id"] == first["id"]) == first_record
    assert reopened.get(f"{project_url}/art-reference-decisions").json() == decisions
    assert reopened.get(f"{project_url}/art").json() == art
    assert {
        file.relative_to(first_job): file.read_bytes()
        for file in first_job.rglob("*")
        if file.is_file()
    } == first_bytes
