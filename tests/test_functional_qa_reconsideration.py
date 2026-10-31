"""Functional-only QA reuses media without rewriting rejection or dispatch proof."""
# ruff: noqa: F811 -- Imported pytest fixtures are injected by argument name.
from contextlib import closing
from copy import deepcopy

import pytest
from pydantic import ValidationError

from plotloom import functional_qa
from plotloom.delegated_qa_contracts import QaAvInspection
from plotloom.exceptions import InvalidTransitionError
from plotloom.persistence.project import media_video_preparation
from plotloom.project_storage.project_video import ProjectVideoRepository
from plotloom.video_batch_contracts import BatchConfirmation, BatchControl, BatchSetup
from plotloom.video_ingestion import probe_video
from tests.delegated_qa_fixtures import INSPECTION, qa_environment, qa_start
from tests.test_video_batch_review import native_batch_take  # noqa: F401
from tests.video_batch_fixtures import ready_batch

pytestmark = pytest.mark.usefixtures("offline_media")


def rejected_single(tmp_path, monkeypatch, take):
    storage, client, service, provider, project, view, actor = qa_environment(tmp_path, monkeypatch)
    service.control(project, BatchControl(batchId=view["id"], expectedControlRevision=view["controlRevision"], action="cancel"))
    setup = view["manifest"]["setup"] | {"shotIds": [view["manifest"]["targets"][0]["shotId"]]}
    view = ready_batch(service, project, service.setup(project, BatchSetup.model_validate(setup)))
    provider._outputs = [take]
    service.video._probe = probe_video
    qa_start(service, project, view, actor)
    for _ in range(40):
        service.step(project)
        view = service.current(project)
        if view["state"] in {"awaiting_review", "blocked"}: break
    assert view["state"] == "awaiting_review", view["execution"].get("error")
    job = next(iter(view["execution"]["jobs"].values()))
    base = f"/api/v2/projects/{project}/video-jobs/{job}"
    rejected = client.post(base+"/review", json={"attribution": actor.model_dump(mode="json", by_alias=True),
        "decision": "reject", "note": "Synthetic quality issue, retained as failed quality evidence.", "expectedSelectionRevision": 0})
    assert rejected.status_code == 201, rejected.text
    service.control(project, BatchControl(batchId=view["id"], expectedControlRevision=view["controlRevision"], action="cancel"))
    return storage, client, service, provider, project, view, actor, base, rejected.json()


@pytest.mark.parametrize("version", ["plotloom.h3-production-brief.v10", "plotloom.h3-production-brief.v9"])
def test_explicit_functional_reconsideration_confirms_original_media_with_no_new_dispatch(tmp_path, monkeypatch, native_batch_take, version):
    with monkeypatch.context() as old:
        old.setattr(media_video_preparation, "COMPILER_VERSION", version)
        storage, client, service, provider, project, _view, actor, base, rejection = rejected_single(tmp_path, monkeypatch, native_batch_take)
    monkeypatch.setattr(functional_qa, "FUNCTIONAL_QA_SCOPES", ((project, actor.scope_id),))
    original = deepcopy(service.current(project)["manifest"])
    stale = service.review(project)
    body = {"attribution": actor.model_dump(mode="json", by_alias=True),
        "acceptanceBasis": "functional_workflow_only", "reason": "Synthetic owner criterion amendment; quality failure remains.",
        "expectedSelectionRevision": 0}
    response = client.post(base+"/review/reopen", json=body)
    assert response.status_code == 201, response.text
    assert response.json()["selectionRevision"] == 0
    assert response.json()["attribution"] == body["attribution"]
    assert client.post(base+"/review/reopen", json=body).status_code == 409
    current = service.current(project)
    assert current["manifest"] == original
    assert len(provider.submits) == 1
    current = service.control(project, BatchControl(batchId=current["id"], expectedControlRevision=current["controlRevision"], action="resume"))
    for _ in range(3): service.step(project)
    current = service.current(project)
    assert current["state"] == "awaiting_review", current["execution"].get("error")
    review = service.review(project)
    assert review["ready"] and review["reviewHash"] != stale["reviewHash"]
    with pytest.raises(InvalidTransitionError):
        service.confirm(project, BatchConfirmation(expectedRevision=current["revision"], reviewHash=stale["reviewHash"],
            basis="source-bound-selections.v1", attribution=actor))
    # The same functional-only authority cannot waive corrupt retained bytes.
    with closing(storage.projects.open(project)) as store:
        artifact_type = type(store.artifacts)
    original_get = artifact_type.get
    def corrupt_take(self, uri):
        data = original_get(self, uri)
        return b"corrupt retained mp4" if data == native_batch_take else data
    with monkeypatch.context() as corrupt:
        corrupt.setattr(artifact_type, "get", corrupt_take)
        assert not service.review(project)["ready"]
        with pytest.raises(InvalidTransitionError, match="unresolved exceptions"):
            service.confirm(project, BatchConfirmation(expectedRevision=current["revision"], reviewHash=review["reviewHash"],
                basis="source-bound-selections.v1", attribution=actor))
    confirmation = BatchConfirmation(expectedRevision=current["revision"], reviewHash=review["reviewHash"],
        basis="source-bound-selections.v1", attribution=actor)
    receipt = service.confirm(project, confirmation)
    assert receipt["version"] == "source-bound-selections.v1"
    assert receipt["attribution"] == actor.model_dump(mode="json", by_alias=True)
    assert "inspection" not in receipt and "confirmation" not in receipt
    assert service.confirm(project, confirmation) == receipt
    assert len(provider.submits) == 1
    with closing(storage.projects.open(project)) as store:
        job = next(item for item in service.video.jobs(store) if item["id"] == rejection["videoJobId"])
        assert job["selected"]
        assert job["reviews"][0]["decision"] == "reject"
        assert job["reviews"][0]["id"] == rejection["id"]
        assert job["reviews"][0]["note"] == rejection["note"]
        assert [r["decision"] for r in job["reviews"]] == ["reject", "reopen", "select"]
    assert client.get(base+"/playback").status_code == 200


def test_functional_only_authority_does_not_waive_changed_generation_provenance(tmp_path, monkeypatch, native_batch_take):
    from plotloom.persistence.schema import VideoJobRow

    storage, client, _service, provider, project, _view, actor, base, rejection = rejected_single(tmp_path, monkeypatch, native_batch_take)
    monkeypatch.setattr(functional_qa, "FUNCTIONAL_QA_SCOPES", ((project, actor.scope_id),))
    with closing(storage.projects.open(project)) as store, store.repository.manual_command() as session:
        row = session.get(VideoJobRow, rejection["videoJobId"])
        row.snapshot = row.snapshot | {"compiledPrompt": "Tampered final provider request."}
    response = client.post(base+"/review/reopen", json={
        "attribution": actor.model_dump(mode="json", by_alias=True),
        "acceptanceBasis": "functional_workflow_only", "reason": "Cannot waive provenance.",
        "expectedSelectionRevision": 0})
    assert response.status_code == 409, response.text
    assert len(provider.submits) == 1


def test_reconsideration_refuses_uncovered_actors_stale_cas_and_missing_runtime_context(tmp_path, monkeypatch, native_batch_take):
    storage, client, service, provider, project, _view, actor, base, rejection = rejected_single(tmp_path, monkeypatch, native_batch_take)
    body = {"attribution": actor.model_dump(mode="json", by_alias=True),
        "acceptanceBasis": "functional_workflow_only", "reason": "Synthetic functional criterion amendment.",
        "expectedSelectionRevision": 0}
    assert client.post(base+"/review/reopen", json=body).status_code == 409
    monkeypatch.setattr(functional_qa, "FUNCTIONAL_QA_SCOPES", ((project, actor.scope_id),))
    for changed, status in [
        (body | {"reviewer": "A person"}, 422),
        (body | {"acceptanceBasis": None}, 422),
        (body | {"expectedSelectionRevision": 1}, 409),
        (body | {"attribution": {"kind": "agent_operated_qa", "scopeId": "foreign"}}, 409),
        ({"reviewer": "A person", "reason": "Reconsider", "expectedSelectionRevision": 0}, 409),
        ({"reviewer": "@plotloom:agent-qa:"+actor.scope_id, "reason": "Reconsider", "expectedSelectionRevision": 0}, 409),
    ]:
        assert client.post(base+"/review/reopen", json=changed).status_code == status
    with closing(storage.projects.open(project)) as store, pytest.raises(InvalidTransitionError):
        ProjectVideoRepository(store, storage.application).reopen_video_job_review(project, rejection["videoJobId"], reviewer=actor,
            reason="No native runtime command context", expected_selection_revision=0,
            acceptance_basis="functional_workflow_only")
    with closing(storage.projects.open(project)) as store:
        job = next(j for j in service.video.jobs(store) if j["id"] == rejection["videoJobId"])
        assert [r["decision"] for r in job["reviews"]] == ["reject"]
        assert not job["selected"] and job["selectionRevision"] == 0
    assert len(provider.submits) == 1


def test_old_prepared_source_cannot_inherit_a_new_preparation_contract(tmp_path, monkeypatch):
    with monkeypatch.context() as old:
        old.setattr(media_video_preparation, "COMPILER_VERSION", "plotloom.h3-production-brief.v9")
        _storage, _client, service, provider, project, view, actor = qa_environment(tmp_path, monkeypatch)
        qa_start(service, project, view, actor)
        service.step(project)
    current = service.current(project)
    assert current["execution"]["jobs"] and not provider.submits
    current = service.control(project, BatchControl(batchId=current["id"], expectedControlRevision=current["controlRevision"], action="pause"))
    with pytest.raises(InvalidTransitionError):
        service.control(project, BatchControl(batchId=current["id"], expectedControlRevision=current["controlRevision"], action="resume"))
    assert not provider.submits


def test_legacy_inspection_bytes_stay_canonical_and_functional_limits_are_explicit():
    assert QaAvInspection.model_validate(INSPECTION).model_dump(mode="json", by_alias=True) == INSPECTION
    with pytest.raises(ValidationError):
        QaAvInspection.model_validate(INSPECTION | {"acceptanceBasis": "functional_workflow_only"})
