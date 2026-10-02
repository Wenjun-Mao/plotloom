"""Mixed-origin assets share a total DTO without rewriting retained evidence."""

import json
import sqlite3
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pydantic import ValidationError

from plotloom.api import create_project_folder_authoring_app
from plotloom.art_contracts import ArtAcceptRequest
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.managed_asset_provenance import project_asset_provenance
from plotloom.project_storage.composition import ProjectFolderStorage
from tests.test_project_storage_art import (
    _deliver,
    _prepare_art_context,
    _write_art_reference_delivery,
)


@pytest.mark.parametrize("declaration", [
    {"origin": "art_reference_proposal", "deliveryId": "retained", "limitations": ["exploratory"]},
    {"origin": "plotloom_keyframe_center_crop", "sourceAssetId": "source", "transform": {"strategy": "cover_center_crop"}},
    {"origin": "manual", "rights": "known", "rightsNote": "owner supplied", "declaredAdditions": ["lamp"]},
])
def test_retained_declarations_project_without_storage_mutation(tmp_path: Path, declaration: dict) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    content = b"immutable asset fixture"
    uri = store.artifacts.put(content)
    asset = store.media.record_managed_import(
        project_id, original_hash=sha256(content).hexdigest(), display_hash=sha256(content).hexdigest(),
        mime_type="image/png", byte_size=len(content), width=1, height=1,
        declaration=declaration, publish=lambda: (uri, uri),
    )
    assert asset["provenance"] == {"rights": "unknown", "rightsNote": None, "declaredAdditions": [], **declaration}
    database = store.home / "project.sqlite3"
    store.close()
    # Emulate the already retained declaration shape, not a new writer.
    encoded = json.dumps(declaration)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE v2_managed_asset_provenance SET declaration=? WHERE asset_id=?", (encoded, asset["id"]))
    client = TestClient(create_project_folder_authoring_app(storage))
    response = client.get(f"/api/v2/projects/{project_id}/visual-workbench")
    assert response.status_code == 200, response.text
    projected = response.json()["assets"][0]["provenance"]
    assert projected == {"rights": "unknown", "rightsNote": None, "declaredAdditions": [], **declaration}
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT declaration FROM v2_managed_asset_provenance WHERE asset_id=?", (asset["id"],)).fetchone()[0] == encoded
    opened = storage.projects.open(project_id)
    try:
        assert opened.artifacts.get(uri) == content
    finally:
        opened.close()


def test_art_delivery_writer_records_complete_common_provenance(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    try:
        binding = _prepare_art_context(store)
        candidate, request = store.prepare_art_candidate("ch_" + "p" * 32, render_style="realistic")
        ready = store.admit_art_delivery(_deliver(store, request))
        store.accept_art_candidate(ArtAcceptRequest(job_id=candidate.job_id, expected_art_revision=0, binding=binding, art=ready.art))
        database = store.home / "project.sqlite3"
    finally:
        store.close()
    client = TestClient(create_project_folder_authoring_app(storage))
    base = f"/api/v2/projects/{project_id}/art-reference-proposals"
    proposal = client.post(base, json={"subjectType": "scene", "subjectId": "S01", "renderDirection": "Cinematic realism, no people."}).json()["proposal"]
    copied = client.post(f"{base}/{proposal['id']}/copy")
    _write_art_reference_delivery(Path(copied.json()["deliveryPath"]), proposal)
    delivered = client.post(f"{base}/{proposal['id']}/refresh")
    assert delivered.status_code == 200, delivered.text
    with sqlite3.connect(database) as connection:
        declaration = json.loads(connection.execute("SELECT declaration FROM v2_managed_asset_provenance").fetchone()[0])
    assert declaration["rights"] == "unknown"
    assert declaration["rightsNote"] is None
    assert declaration["declaredAdditions"] == []
    assert declaration["deliveryId"] == "art-study-001"
    assert declaration["limitations"] == ["fixture bytes only"]


@pytest.mark.parametrize("invalid", [{"rights": "acquired"}, {"declaredAdditions": None}, {"declaredAdditions": [1]}])
def test_invalid_present_common_fields_are_not_defaulted(invalid: dict) -> None:
    with pytest.raises(ValidationError):
        project_asset_provenance({"origin": "art_reference_proposal", **invalid})


def test_missing_origin_is_not_invented() -> None:
    with pytest.raises(ValidationError):
        project_asset_provenance({"source": "unspecified"})


def test_import_post_returns_the_same_complete_asset_as_get(tmp_path: Path) -> None:
    storage = ProjectFolderStorage(outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application")
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    project_id = store.manifest.project_id
    database = store.home / "project.sqlite3"
    store.close()
    image = BytesIO()
    Image.new("RGB", (16, 9), "blue").save(image, format="PNG")
    client = TestClient(create_project_folder_authoring_app(storage))
    base = f"/api/v2/projects/{project_id}"
    response = client.post(base + "/managed-assets", files={"image": ("fixture.png", image.getvalue(), "image/png")},
                           data={"origin": "explicit imported reference", "rights": "known", "rights_note": "owner supplied", "declared_additions_json": '["lamp"]'})
    assert response.status_code == 201, response.text
    asset = response.json()
    assert asset == client.get(base + "/managed-assets").json()["assets"][0]
    assert asset == client.get(base + "/visual-workbench").json()["assets"][0]
    with sqlite3.connect(database) as connection:
        encoded = connection.execute("SELECT declaration FROM v2_managed_asset_provenance WHERE asset_id=?", (asset["id"],)).fetchone()[0]
    assert json.loads(encoded) == asset["provenance"]
