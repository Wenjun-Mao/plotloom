"""Current project-folder HTTP contracts that replaced shared-route coverage."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event

from fastapi.testclient import TestClient
import pytest

from plotloom.api import create_project_folder_authoring_app
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import STAGE_ORDER
from plotloom.persistence import stable_hash
from plotloom.project_storage import ProjectFolderStorage, ProjectStore
from tests.backend_core.conftest import all_stage_payloads


def test_project_folder_bootstrap_replays_a_canonical_prefix_without_duplicate_project(tmp_path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )
    body = {
        "brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True),
        "initialStages": [
            {"stage": stage.value, "payload": payload.model_dump(mode="json", by_alias=True)}
            for stage, payload in zip(STAGE_ORDER, all_stage_payloads(), strict=True)
        ],
    }
    client = TestClient(create_project_folder_authoring_app(storage))
    created = client.post("/api/v2/projects", json=body, headers={"Idempotency-Key": "first-save"})
    replay = client.post("/api/v2/projects", json=body, headers={"Idempotency-Key": "first-save"})

    assert created.status_code == replay.status_code == 201
    assert replay.json() == created.json()
    project = created.json()
    assert [stage["head"]["stage"] for stage in project["stages"]] == [
        stage.value for stage in STAGE_ORDER
    ]
    assert [stage["head"]["status"] for stage in project["stages"]] == ["ready"] * 4
    assert [stage["head"]["revision"] for stage in project["stages"]] == [1] * 4
    assert [stage["payload"] for stage in project["stages"]] == [
        payload.model_dump(mode="json", by_alias=True) for payload in all_stage_payloads()
    ]
    assert client.get(f"/api/v2/projects/{project['id']}/stages").json()["stages"] == project["stages"]
    assert {item.manifest.project_id for item in storage.projects.discover()} == {project["id"]}

    conflicting = client.post(
        "/api/v2/projects",
        json={**body, "brief": {**body["brief"], "title": "conflicting replay"}},
        headers={"Idempotency-Key": "first-save"},
    )
    assert conflicting.status_code == 409
    assert conflicting.json()["code"] == "idempotency_conflict"


def test_project_folder_bootstrap_rejects_a_noncanonical_initial_prefix(tmp_path) -> None:
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )
    graph = all_stage_payloads()[1]
    response = TestClient(create_project_folder_authoring_app(storage)).post(
        "/api/v2/projects",
        json={
            "brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True),
            "initialStages": [{"stage": "story_graph", "payload": graph.model_dump(mode="json", by_alias=True)}],
        },
    )
    assert response.status_code == 422


def test_project_folder_bootstrap_returns_retryable_contention_then_replays(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A same-key request cannot open a manifest before its bootstrap commits."""

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )
    body = {"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)}
    started_initialization = Event()
    release_initialization = Event()
    original_initialize = ProjectStore.initialize.__func__

    def delayed_initialize(cls, *args, **kwargs):
        started_initialization.set()
        assert release_initialization.wait(timeout=5)
        return original_initialize(cls, *args, **kwargs)

    monkeypatch.setattr(ProjectStore, "initialize", classmethod(delayed_initialize))
    headers = {"Idempotency-Key": "concurrent-bootstrap"}
    first_client = TestClient(create_project_folder_authoring_app(storage))
    second_client = TestClient(create_project_folder_authoring_app(storage))
    with ThreadPoolExecutor(max_workers=1) as executor:
        first = executor.submit(first_client.post, "/api/v2/projects", json=body, headers=headers)
        assert started_initialization.wait(timeout=5)
        contention = second_client.post("/api/v2/projects", json=body, headers=headers)
        release_initialization.set()
        created = first.result(timeout=5)

    assert contention.status_code == 503
    assert contention.headers["retry-after"] == "1"
    assert contention.json()["code"] == "bootstrap_contention"
    assert created.status_code == 201
    replay = second_client.post("/api/v2/projects", json=body, headers=headers)
    assert replay.status_code == 201
    assert replay.json() == created.json()


def test_project_folder_bootstrap_recovers_an_expired_crash_reservation(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later retry completes a manifest published before owner loss."""

    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )
    body = {"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)}
    key = "expired-bootstrap"
    fingerprint = stable_hash(
        {
            "brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=False),
            "initialStages": [],
        }
    )
    reservation = storage.application.project_lifecycle.reserve_creation(
        key=key, fingerprint=fingerprint
    )
    original_initialize = ProjectStore.initialize.__func__

    def crash_after_manifest(cls, *args, **kwargs):
        raise RuntimeError("simulated process loss after manifest publication")

    monkeypatch.setattr(ProjectStore, "initialize", classmethod(crash_after_manifest))
    with pytest.raises(RuntimeError, match="manifest publication"):
        storage.projects.create(
            FIXED_CHINESE_BRIEF,
            project_id=reservation.target_project_id,
            created_at=reservation.target_created_at,
        )
    monkeypatch.setattr(ProjectStore, "initialize", classmethod(original_initialize))
    # Model a terminated owner after it published the manifest, before a
    # project database or application completion marker existed.
    with storage.application._write() as connection:  # noqa: SLF001 - crash boundary proof
        connection.execute(
            "UPDATE application_project_create_requests "
            "SET initialization_lease_until = ? WHERE idempotency_key = ?",
            ("2000-01-01T00:00:00+00:00", key),
        )

    response = TestClient(create_project_folder_authoring_app(storage)).post(
        "/api/v2/projects", json=body, headers={"Idempotency-Key": key}
    )

    assert response.status_code == 201
    assert response.json()["id"] == reservation.target_project_id
    assert storage.application.project_lifecycle.reserve_creation(
        key=key, fingerprint=fingerprint
    ).complete


def test_project_folder_static_mount_serves_the_current_workbench_index(tmp_path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<main>Project workbench</main>", encoding="utf-8")
    storage = ProjectFolderStorage(
        outputs_root=tmp_path / "outputs", application_data_root=tmp_path / "application"
    )
    response = TestClient(
        create_project_folder_authoring_app(storage, static_dir=static_dir)
    ).get("/v2/")

    assert response.status_code == 200
    assert "<main>Project workbench</main>" in response.text
