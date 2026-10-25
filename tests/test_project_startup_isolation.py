"""Inspection-discovered corruption holds one project, not the installation."""
from contextlib import closing
import sqlite3

import pytest
from fastapi.testclient import TestClient

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import RunKind, STAGE_ORDER, StartupRecoveryPlan
from plotloom.project_storage import ProjectStorageCorruptionError
from plotloom.runtime import build_runtime_app
from tests.autopilot_fixtures import start_run
from tests.project_storage_fixtures import FixtureResolver, fixture_profile
from tests.test_production_project_folder_runtime_boundaries import _settings
from tests.working_input_preservation import preservation_inventory


@pytest.mark.parametrize("closed", [False, True])
def test_corrupt_authority_is_catalogued_but_excluded_from_startup_and_run_index(tmp_path, caplog, closed):
    settings = _settings(tmp_path)
    app = build_runtime_app(settings, text_provider_resolver=FixtureResolver())
    storage, dispatcher = app.state.project_folder_storage, app.state.run_runner
    profile = fixture_profile()
    app.state.application_profile_repository.create_text_provider_profile(
        profile.profile_id, "Offline fixture", configuration=profile)
    projects = []
    for title in ("Rejected retained authority", "Healthy project"):
        with closing(storage.projects.create(FIXED_CHINESE_BRIEF.model_copy(update={"title": title}))) as store:
            projects.append(store.manifest.project_id)
    rejected, healthy = projects
    with closing(storage.projects.open(rejected)) as store:
        start_run(store)
        current = store.repository.autopilot.current(rejected)
        store.repository.autopilot.control(rejected, expected_revision=current.revision, action="takeover")
        database = store.database_path
        project_home = store.home
    runs = [dispatcher.create_run(identifier, kind=RunKind.PIPELINE,
        requested_stages=list(STAGE_ORDER),
        provider_snapshot=fixture_profile().model_dump(mode="json", by_alias=True)) for identifier in projects]
    if closed:
        dispatcher.request_cancel(runs[0].id)
        storage.projects.close_project(rejected)
    dispatcher.close()
    app.state.run_secrets.close()
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE v2_autopilot_runs SET policy_hash=?", ("f" * 64,))
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    before = database.read_bytes()
    home_before = preservation_inventory(project_home)
    assert set(home.manifest.project_id for home in storage.projects.discover()) == set(projects)
    with pytest.raises(ProjectStorageCorruptionError, match="autopilot authority"):
        storage.projects.open(rejected)

    restarted = build_runtime_app(settings, text_provider_resolver=FixtureResolver())
    with TestClient(restarted) as client:
        assert restarted.state.startup_recovery[rejected] == StartupRecoveryPlan()
        assert restarted.state.startup_recovery[healthy] == StartupRecoveryPlan(resubmit_run_ids=[runs[1].id])
        query_before = preservation_inventory(tmp_path)
        assert {item["id"] for item in client.get("/api/v2/projects").json()["projects"]} == set(projects)
        # Metadata inspection does not attest unrelated retained authority,
        # including when Frozen. Strict reads and writes must still refuse it.
        metadata = client.get(f"/api/v2/projects/{rejected}")
        assert metadata.status_code == 200, metadata.text
        assert metadata.json()["id"] == rejected
        assert metadata.json()["displayTitle"] == "Rejected retained authority"
        assert metadata.json()["operationalState"] == ("closed" if closed else "open")
        authority = client.get(f"/api/v2/projects/{rejected}/autopilot")
        mutation = client.patch(f"/api/v2/projects/{rejected}", json={
            "expectedRevision": metadata.json()["revision"],
            "brief": FIXED_CHINESE_BRIEF.model_dump(mode="json", by_alias=True),
        })
        for failure in (authority, mutation):
            assert failure.status_code == 422, failure.text
            assert failure.json() == {"code": "project_storage_error", "message": "persisted autopilot authority is invalid"}
        with pytest.raises(ProjectStorageCorruptionError, match="autopilot authority"):
            restarted.state.project_folder_storage.projects.read_open(rejected)
        assert client.get(f"/api/v2/projects/{healthy}").status_code == 200
        assert client.get(f"/api/v2/projects/{healthy}/autopilot").status_code == 200
        assert preservation_inventory(tmp_path) == query_before
        application = restarted.state.project_folder_storage.application
        assert application.project_for_run(runs[0].id) is None
        assert application.project_for_run(runs[1].id) == healthy
        # The same index owner remains safe when explicitly rebuilt later.
        restarted.state.run_runner.rebuild_index()
        assert application.project_for_run(runs[0].id) is None
        assert application.project_for_run(runs[1].id) == healthy
    assert database.read_bytes() == before
    assert preservation_inventory(project_home) == home_before
    assert any(rejected in record.message and "excluded from run index" in record.message
               and "autopilot authority" in record.message for record in caplog.records)
    if not closed:
        assert any(rejected in record.message and "held during startup reconciliation" in record.message
                   and "autopilot authority" in record.message for record in caplog.records)


def test_unexpected_startup_failure_is_not_swallowed(tmp_path, monkeypatch):
    app = build_runtime_app(_settings(tmp_path), text_provider_resolver=FixtureResolver())
    storage = app.state.project_folder_storage
    with closing(storage.projects.create(FIXED_CHINESE_BRIEF)) as store:
        project_id = store.manifest.project_id
    original = storage.projects.open
    def unexpected(identifier):
        if identifier == project_id:
            raise RuntimeError("unexpected startup implementation failure")
        return original(identifier)
    monkeypatch.setattr(storage.projects, "open", unexpected)
    with pytest.raises(RuntimeError, match="unexpected startup implementation failure"):
        with TestClient(app):
            pass
