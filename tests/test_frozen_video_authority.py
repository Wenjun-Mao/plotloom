"""Retained media authority survives compiler policy changes without new dispatch."""
# ruff: noqa: F811 -- Imported pytest fixture is injected by argument name.
from contextlib import closing
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from plotloom.api import create_project_folder_authoring_app
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.schema import VideoBatchRow
from plotloom.project_storage import ProjectFolderStorage
from plotloom.video_batch_basis import assert_new_dispatch_authority
from plotloom.video_fidelity import validate_retained_fidelity
from plotloom.video_fidelity_contracts import FidelityReference
from tests.test_video_batch_review import complete_batch, confirmation, native_batch_take  # noqa: F401


def change_compilation(monkeypatch):
    from plotloom import production_brief as briefs
    from plotloom.video_backends.minimax_h3 import prompt
    original_prompt, original_brief = prompt.compile_i2va_prompt, briefs.production_brief
    monkeypatch.setattr(prompt, "compile_i2va_prompt", lambda *a, **kw: original_prompt(*a, **kw) + " Updated compiler policy.")
    def brief(*a, **kw):
        result = original_brief(*a, **kw)
        result["briefHash"] = "f" * 64
        return result
    monkeypatch.setattr(briefs, "production_brief", brief)


def test_selected_bytes_reopen_and_restore_after_compiler_drift(tmp_path, native_batch_take, monkeypatch):
    storage, client, service, project_id, current = complete_batch(tmp_path, native_batch_take)
    service.confirm(project_id, confirmation(current, service.review(project_id)))
    base = f"/api/v2/projects/{project_id}"
    with closing(storage.projects.open(project_id)) as store:
        jobs = service.video.jobs(store)
    expected = {job["id"]: client.get(f"{base}/video-jobs/{job['id']}/playback").content for job in jobs}
    change_compilation(monkeypatch)
    storage.projects.close_project(project_id)
    current_jobs = client.get(f"{base}/video-jobs").json()["jobs"]
    assert len(current_jobs) == 6
    assert all(job["inputStatus"] == "stale" and not job["productionEligible"] for job in current_jobs)
    for job in current_jobs:
        with pytest.raises(InvalidTransitionError, match="编译规则"):
            assert_new_dispatch_authority(job["snapshot"])
        response = client.get(f"{base}/video-jobs/{job['id']}/playback")
        assert response.status_code == 200 and response.content == expected[job["id"]]
    snapshot = storage.recovery.create_snapshot(project_id)
    restored = ProjectFolderStorage(outputs_root=tmp_path / "restored", application_data_root=tmp_path / "restored-app")
    restored.recovery.restore(Path(snapshot.location))
    restored.projects.close_project(project_id)
    restored_client = TestClient(create_project_folder_authoring_app(restored))
    for identifier, content in expected.items():
        response = restored_client.get(f"{base}/video-jobs/{identifier}/playback")
        assert response.status_code == 200 and response.content == content
    assert client.get(f"{base}/video-batch/review").status_code == 200


@pytest.mark.parametrize("mutation", ["brief", "source", "prompt", "capacity", "candidate", "adopted-brief"])
def test_native_manifest_commitment_refuses_coordinated_tampering(tmp_path, native_batch_take, mutation):
    storage, _client, _service, project_id, _current = complete_batch(tmp_path, native_batch_take)
    with closing(storage.projects.open(project_id)) as store:
        with store.repository._read() as session:
            row = session.scalar(select(VideoBatchRow))
            manifest, data, batch_id = deepcopy(row.manifest), deepcopy(row.execution["fidelity"]), row.id
    target = manifest["targets"][0]
    reference = FidelityReference.model_validate(target["directions"]["fidelityCheck"])
    assert validate_retained_fidelity(data, project_id, batch_id, target, reference, manifest=manifest)["verdict"] == "pass"
    if mutation == "brief":
        target["productionBrief"]["adapterConstraints"][0] += " changed"
    elif mutation == "source":
        target["snapshot"]["shot"]["action"] += " changed"
    elif mutation == "prompt":
        target["compiledPrompt"] += " changed"
    elif mutation == "capacity":
        manifest["setup"]["maxJobs"] = 99
    elif mutation == "candidate":
        data["candidateBinding"] = "changed"
    else:
        target = deepcopy(target)
        target["productionBrief"]["adapterConstraints"][0] += " changed"
    with pytest.raises(ValueError):
        validate_retained_fidelity(data, project_id, batch_id, target, reference, manifest=manifest)


def test_known_prediction_reconciles_after_compiler_drift(tmp_path, native_batch_take, monkeypatch):
    from plotloom.video_ingestion import probe_video
    from tests.video_batch_fixtures import batch_environment, ready_batch, start_batch
    storage, _client, service, provider, project_id, view = batch_environment(tmp_path)
    provider._outputs = [native_batch_take]
    service.video._probe = probe_video
    start_batch(service, project_id, ready_batch(service, project_id, view))
    service.step(project_id)
    service.step(project_id)
    with closing(storage.projects.open(project_id)) as store:
        job = service.video.jobs(store)[0]
    assert job["state"] == "submitted" and job["providerPredictionId"]
    assert len(provider.submits) == 1
    change_compilation(monkeypatch)
    service.step(project_id)  # Existing predictions are observed before new-dispatch validation.
    with closing(storage.projects.open(project_id)) as store:
        reconciled = next(item for item in service.video.jobs(store) if item["id"] == job["id"])
    assert reconciled["state"] == "ingested"
    assert reconciled["providerPredictionId"] == job["providerPredictionId"]
    assert reconciled["inputStatus"] == "stale" and len(provider.submits) == 1
