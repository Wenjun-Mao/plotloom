"""Regression coverage for production project-folder ownership boundaries."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from plotloom.config import PlotloomSettings
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import RunKind, STAGE_ORDER, StartupRecoveryPlan
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.project.repository_generation import ProjectGenerationRepository
from plotloom.project_storage import (
    ProjectFolderStorage,
    ProjectStorageCorruptionError,
    ProjectStore,
)
from plotloom.runtime import build_runtime_app

from tests.project_storage_fixtures import FixtureResolver, fixture_profile


def _settings(tmp_path: Path) -> PlotloomSettings:
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<main>Plotloom</main>", encoding="utf-8")
    return PlotloomSettings(
        repo_root=tmp_path,
        outputs_dir=tmp_path / "outputs",
        application_data_dir=tmp_path / "application",
        static_dir=static,
        text_auth_mode="none",
    )


def _activate_fixture_profile(client: TestClient) -> None:
    catalog = client.get("/api/v2/text-provider-profiles")
    profile = fixture_profile().model_dump(mode="json", by_alias=True)
    created = client.post(
        "/api/v2/text-provider-profiles",
        json={
            "profileId": profile["profileId"],
            "displayName": "Offline fixture",
            "configuration": profile,
        },
    )
    assert created.status_code == 201
    activated = client.post(
        f"/api/v2/text-provider-profiles/{profile['profileId']}/activate",
        json={"expectedSelectionRevision": catalog.json()["selectionRevision"]},
    )
    assert activated.status_code == 200


def _create_project(client: TestClient) -> str:
    response = client.post(
        "/api/v2/projects",
        json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_closed_project_run_commands_and_startup_leave_db_and_evidence_unchanged(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    app = build_runtime_app(settings, text_provider_resolver=FixtureResolver())

    with TestClient(app) as client:
        _activate_fixture_profile(client)
        project_id = _create_project(client)
        created = client.post(f"/api/v2/projects/{project_id}/pipeline-runs", json={})
        assert created.status_code == 202
        run_id = created.json()["id"]
        for _ in range(100):
            run = client.get(f"/api/v2/runs/{run_id}")
            assert run.status_code == 200
            if run.json()["status"] not in {"queued", "running", "cancel_requested"}:
                break
            time.sleep(0.02)
        else:
            raise AssertionError("fixture run did not finish")
        trace_before = client.get(f"/api/v2/runs/{run_id}/trace").json()
        store = app.state.project_folder_storage.projects.inspect(project_id)
        try:
            database = store.database_path
            project_home = store.home
        finally:
            store.close()
        connection = sqlite3.connect(database)
        try:
            runtime_artifacts = list(
                connection.execute(
                    "SELECT relative_path, content_hash, size_bytes "
                    "FROM v2_run_artifact_blobs WHERE run_id = ?",
                    (run_id,),
                )
            )
        finally:
            connection.close()
        assert len(runtime_artifacts) == 1
        relative_path, content_hash, size_bytes = runtime_artifacts[0]
        assert relative_path.startswith("assets/")
        runtime_bytes = (project_home / relative_path).read_bytes()
        assert len(runtime_bytes) == size_bytes
        assert sha256(runtime_bytes).hexdigest() == content_hash

        snapshot = client.post(f"/api/v2/projects/{project_id}/snapshots")
        assert snapshot.status_code == 201
        assert relative_path in {
            item["relativePath"] for item in snapshot.json()["manifest"]["files"]
        }
        assert client.post(f"/api/v2/projects/{project_id}/close").status_code == 200

        # Snapshot databases are DELETE-mode by contract. Inspection and
        # rejected commands must preserve that mode and the exact bytes.
        connection = sqlite3.connect(database)
        try:
            assert connection.execute("PRAGMA journal_mode=DELETE").fetchone() == (
                "delete",
            )
        finally:
            connection.close()
        database_before = database.read_bytes()
        lock_path = project_home / ".project-operation.lock"
        lock_path.unlink()
        assert not lock_path.exists()

    restarted = build_runtime_app(settings, text_provider_resolver=FixtureResolver())
    with TestClient(restarted) as client:
        # Closed projects remain indexable/readable but startup performs no
        # generation reconciliation transaction against their database.
        assert restarted.state.startup_recovery[project_id] == StartupRecoveryPlan()
        assert client.get(f"/api/v2/runs/{run_id}/trace").json() == trace_before
        assert database.read_bytes() == database_before
        assert not lock_path.exists()

        assert client.post(f"/api/v2/runs/{run_id}/cancel").status_code == 409
        exact = client.post(
            f"/api/v2/runs/{run_id}/work-units/missing/repairs",
            json={},
            headers={"Idempotency-Key": "closed-project-exact-repair"},
        )
        assert exact.status_code == 409
        assert client.get(f"/api/v2/runs/{run_id}/trace").json() == trace_before
        assert database.read_bytes() == database_before

    restored_storage = ProjectFolderStorage(
        outputs_root=tmp_path / "restored-outputs",
        application_data_root=tmp_path / "restored-application",
    )
    restored_storage.recovery.restore(Path(snapshot.json()["location"]))
    restored = restored_storage.projects.inspect(project_id)
    try:
        assert restored.artifacts.get(relative_path) == runtime_bytes
    finally:
        restored.close()


def test_new_project_visual_workbench_is_readable_before_story_bible_exists(
    tmp_path: Path,
) -> None:
    """A production project may inspect visual state before authoring canon."""

    app = build_runtime_app(_settings(tmp_path))

    with TestClient(app) as client:
        project_id = _create_project(client)
        response = client.get(f"/api/v2/projects/{project_id}/visual-workbench")

    assert response.status_code == 200
    assert response.json()["characterReferences"] == {"states": [], "decisions": []}


def test_format_7_project_folder_is_rejected_before_runtime_admission(
    tmp_path: Path,
) -> None:
    """The typed runtime-artifact inventory is a format-9 schema contract."""

    app = build_runtime_app(_settings(tmp_path))
    with TestClient(app) as client:
        project_id = _create_project(client)
        store = app.state.project_folder_storage.projects.inspect(project_id)
        try:
            manifest_path = store.home / "project.json"
        finally:
            store.close()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["formatVersion"] = 7
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        with pytest.raises(ProjectStorageCorruptionError):
            ProjectStore.open(manifest_path.parent, read_only=True)


def test_profile_view_round_trips_after_public_configuration_edit(tmp_path: Path) -> None:
    """The V3 hash returned to a browser is derived again on its next save."""

    app = build_runtime_app(_settings(tmp_path))

    with TestClient(app) as client:
        current = client.get("/api/v2/text-provider-profiles/default").json()
        configuration = current["configuration"] | {
            "textModel": "browser-edited-model",
            "presetId": "custom",
        }
        response = client.put(
            "/api/v2/text-provider-profiles/default",
            json={
                "expectedRevision": current["revision"],
                "displayName": current["displayName"],
                "configuration": configuration,
                "adapterId": current["adapterId"],
                "adapterVersion": current["adapterVersion"],
            },
        )

    assert response.status_code == 200
    assert response.json()["configuration"]["textModel"] == "browser-edited-model"
    assert response.json()["configuration"]["profileHash"] != current["configuration"]["profileHash"]


def test_disabled_profile_remains_selected_but_cannot_be_reactivated(tmp_path: Path) -> None:
    """Availability is an admission guard, including the active selector route."""

    app = build_runtime_app(_settings(tmp_path), text_provider_resolver=FixtureResolver())
    with TestClient(app) as client:
        initial = client.get("/api/v2/text-provider-profiles/default")
        assert initial.status_code == 200
        disabled = client.put(
            "/api/v2/text-provider-profiles/default/availability",
            json={
                "expectedAvailabilityRevision": initial.json()["availabilityRevision"],
                "enabled": False,
            },
        )
        assert disabled.status_code == 200
        assert disabled.json()["enabled"] is False
        default_delete = client.delete(
            "/api/v2/text-provider-profiles/default",
            params={"expectedRevision": initial.json()["revision"]},
        )
        assert default_delete.status_code == 409

        project = client.post(
            "/api/v2/projects",
            json={"brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True)},
        )
        assert project.status_code == 201
        rejected_run = client.post(
            f"/api/v2/projects/{project.json()['id']}/pipeline-runs", json={}
        )
        assert rejected_run.status_code == 409
        assert "disabled" in rejected_run.json()["message"]
        assert client.get(f"/api/v2/projects/{project.json()['id']}/runs").json()["runs"] == []

        catalog = client.get("/api/v2/text-provider-profiles")
        assert catalog.status_code == 200
        assert catalog.json()["activeProfileId"] == "default"
        refused = client.post(
            "/api/v2/text-provider-profiles/default/activate",
            json={"expectedSelectionRevision": catalog.json()["selectionRevision"]},
        )
        assert refused.status_code == 409
        assert "disabled" in refused.json()["message"]
        assert client.get("/api/v2/text-provider-profiles").json()["activeProfileId"] == "default"


def test_profile_delete_is_guarded_across_run_reservation_and_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = build_runtime_app(_settings(tmp_path), text_provider_resolver=FixtureResolver())
    profiles = app.state.application_profile_repository
    guarded_id = "frozen_fixture"
    guarded = profiles.create_text_provider_profile(
        guarded_id,
        "Frozen fixture",
        configuration=fixture_profile().model_copy(update={"profile_id": guarded_id}),
    )

    with TestClient(app) as client:
        _activate_fixture_profile(client)
        project_id = _create_project(client)
        dispatcher = app.state.run_runner
        original_create = ProjectGenerationRepository.create_run
        observed_guard = False

        def delete_in_creation_gap(
            repository: ProjectGenerationRepository, *args: object, **kwargs: object
        ) -> object:
            nonlocal observed_guard
            with pytest.raises(InvalidTransitionError, match="nonterminal run"):
                profiles.delete_text_provider_profile(guarded_id, guarded.revision)
            observed_guard = True
            return original_create(repository, *args, **kwargs)

        monkeypatch.setattr(
            ProjectGenerationRepository, "create_run", delete_in_creation_gap
        )
        run = dispatcher.create_run(
            project_id,
            kind=RunKind.PIPELINE,
            requested_stages=list(STAGE_ORDER),
            provider_snapshot=guarded.configuration.model_dump(mode="json", by_alias=True),
        )
        assert observed_guard
        with pytest.raises(InvalidTransitionError, match="nonterminal run"):
            profiles.delete_text_provider_profile(guarded_id, guarded.revision)

        # The real production dispatcher executes with its configured fixture
        # resolver; no alternate runner or repository composition is injected.
        dispatcher.submit(run.id).result(timeout=10)
        dispatcher.rebuild_index()
        profiles.delete_text_provider_profile(guarded_id, guarded.revision)
        assert all(item.profile_id != guarded_id for item in profiles.list_text_provider_profiles())


def test_route_reservation_keeps_a_run_recoverable_when_confirmation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = build_runtime_app(_settings(tmp_path), text_provider_resolver=FixtureResolver())
    with TestClient(app) as client:
        _activate_fixture_profile(client)
        project_id = _create_project(client)
        dispatcher = app.state.run_runner
        application = app.state.project_folder_storage.application
        reserved_ids: list[str] = []
        reserve = application.reserve_run_route

        def record_reservation(route: object) -> None:
            reserved_ids.append(route.run_id)  # type: ignore[attr-defined]
            reserve(route)  # type: ignore[arg-type]

        monkeypatch.setattr(application, "reserve_run_route", record_reservation)
        monkeypatch.setattr(
            application,
            "confirm_run_route",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("index unavailable")),
        )
        with pytest.raises(OSError, match="index unavailable"):
            dispatcher.create_run(
                project_id,
                kind=RunKind.PIPELINE,
                requested_stages=list(STAGE_ORDER),
                provider_snapshot=fixture_profile().model_dump(mode="json", by_alias=True),
            )
        assert len(reserved_ids) == 1
        run_id = reserved_ids[0]
        assert application.project_for_run(run_id) == project_id
        inspected = dispatcher.inspect_run_project(run_id)
        try:
            assert inspected.generation.get_run(run_id).status.value == "queued"
        finally:
            inspected.close()
