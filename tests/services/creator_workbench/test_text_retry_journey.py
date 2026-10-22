"""Exact API/controller/native-validator correction; provider is deterministic CLI."""
import time
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.project_folder_autopilot import register_autopilot_routes
from plotloom.autopilot_contracts import RunControlRequest
from plotloom.text_correction_contracts import logical_checkpoint
from tests.services.creator_workbench.test_text_content_correction import (
    _journey_environment,
)


def advance_until(service, storage, run, predicate):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            current = store.repository.autopilot.current(run.project_id)
        if predicate(current):
            return current
        time.sleep(0.05)
    raise AssertionError(f"bounded correction journey did not finish: {current.state} {current.blocker}")


@pytest.mark.parametrize("limit", [0, 2], ids=["automatic-off-explicit-one", "two-automatic-then-explicit-one"])
def test_actual_api_one_more_correction_preserves_quota_and_adopts(supervisor, tmp_path, monkeypatch, limit):
    storage, _registry, service, run = _journey_environment(supervisor, tmp_path, monkeypatch, exhaust=True, correction_limit=limit)
    try:
        current = advance_until(service, storage, run, lambda current: current.state == "blocked")
        app = FastAPI()
        register_autopilot_routes(app, lambda project_id: closing(storage.projects.open(project_id)), service)
        # Production routes/controller/host/persistence; no synthetic API outcomes.
        client = TestClient(app)
        base = f"/api/v2/projects/{run.project_id}/autopilot"
        details = client.get(base + "/text-failure").json()
        assert details["canRetry"], details
        assert details["automaticUsed"] == details["automaticLimit"] == limit
        assert len(details["history"]) == limit + 1
        assert details["issues"][1]["field"] == "props[0].image.prompt"
        assert "handheld scale" in details["issues"][1]["rule"]
        assert "brass key" in details["issues"][1]["excerpt"]
        assert details["diagnostics"]
        from plotloom.creative_handoff_contracts import CreativeHandoffRequest
        from plotloom.persistence.project.creative_terminal import CANDIDATE_ROWS
        with closing(storage.projects.open(run.project_id)) as store:
            saved_brief = store.project().brief
            failed_job = logical_checkpoint(current, "art")["evidence"]["jobId"]
            with store.repository._read() as session:
                parent = CreativeHandoffRequest.model_validate(session.get(CANDIDATE_ROWS["art"], failed_job).request)
        if limit:
            assert details["history"][-1]["comparison"] == "repeated"
        grant = {"commandId": str(uuid4()), "expectedRunId": run.id, "expectedRevision": current.revision,
            "failedAttemptId": details["failedAttemptId"], "rejectionHash": details["rejectionHash"],
            "directions": "保留原简报；明确钥匙是手持尺度。"}
        response = client.post(base + "/text-retry", json=grant)
        assert response.status_code == 200, response.text
        after = response.json()
        assert after["state"] == "running"
        assert client.post(base + "/text-retry", json=grant).json() == after
        # A different click using the old failure CAS cannot acquire another job.
        from plotloom.exceptions import RevisionConflictError
        with pytest.raises(RevisionConflictError):
            client.post(base + "/text-retry", json=grant | {"commandId": str(uuid4())})
        adopted = advance_until(service, storage, run, lambda current: logical_checkpoint(current, "art")["state"] == "adopted")
        assert len([c for c in adopted.checkpoints if c["evidence"]["owner"] == "art"]) == limit + 2
        with closing(storage.projects.open(run.project_id)) as store:
            assert store.repository.autopilot.automatic_corrections_used(run.id, "art") == limit
            art = store.art_state().accepted_art
            assert "handheld scale" in art.art["props"][0]["image"]["sheet"]
            with store.repository._read() as session:
                request = CreativeHandoffRequest.model_validate(session.get(CANDIDATE_ROWS["art"], art.candidate_job_id).request)
            assert request.text_correction.manual_grant.directions == grant["directions"]
            assert request.text_correction.ordinal == limit + 1
            assert request.model_dump(exclude={"job_id", "text_correction"}) == parent.model_dump(exclude={"job_id", "text_correction"})
            assert store.project().brief == saved_brief
        service.control(run.project_id, RunControlRequest(expected_revision=adopted.revision, action="pause"))
        service.close()
        snapshot = storage.recovery.create_snapshot(run.project_id)
        from plotloom.project_storage import ProjectFolderStorage
        restored = ProjectFolderStorage(outputs_root=tmp_path / "restore", application_data_root=tmp_path / "restore-application")
        restored.recovery.restore(Path(snapshot.location))
        with closing(restored.projects.open(run.project_id)) as store:
            assert store.art_state().accepted_art.art == art.art
            assert logical_checkpoint(store.repository.autopilot.current(run.project_id), "art")["state"] == "adopted"
    finally:
        service.close()
