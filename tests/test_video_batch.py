"""Batch authorization is complete, source-bound and never automatic dispatch."""
from copy import deepcopy
from contextlib import closing
import pytest
from plotloom.exceptions import InvalidTransitionError
from plotloom.video_batch_contracts import BatchControl, BatchStart
from tests.video_batch_fixtures import batch_environment, ready_batch, start_batch, draft_for


def test_setup_draft_and_explicit_start_have_separate_authority(tmp_path):
    storage, client, service, provider, project_id, view = batch_environment(tmp_path)
    assert not view["manifest"]["blockers"], view["manifest"]["blockers"]
    assert len(view["manifest"]["targets"]) == len(view["manifest"]["scopeShotIds"]) == 6
    assert not provider.submits
    ready = ready_batch(service, project_id, view)
    assert ready["state"] == "ready" and ready["manifestHash"] != view["manifestHash"]
    assert all("reviewedEnglish" not in target["directions"] for target in ready["manifest"]["targets"])
    with pytest.raises(InvalidTransitionError):
        service.start(project_id, BatchStart(expectedRevision=ready["revision"], manifestHash=view["manifestHash"], basis="whole-batch-english.v1"))
    started = start_batch(service, project_id, ready)
    assert started["state"] == "running" and not provider.submits
    service.step(project_id)  # prepare only, linked atomically
    with closing(storage.projects.open(project_id)) as store:
        jobs = service.video.jobs(store)
        assert len(jobs) == 1 and jobs[0]["state"] == "prepared"
        assert jobs[0]["snapshot"]["reviewedDirections"]["reviewBasis"]["manifestHash"] == ready["manifestHash"]
        assert "reviewedEnglish" not in jobs[0]["snapshot"]["reviewedDirections"]
    service.step(project_id)
    assert len(provider.submits) == 1
    # An identical lost-Start acknowledgment reads the durable original batch.
    assert start_batch(service, project_id, ready)["id"] == started["id"]
    assert len(provider.submits) == 1


def test_pause_fences_even_direct_submit_of_a_batch_job(tmp_path):
    storage, _client, service, provider, project_id, view = batch_environment(tmp_path)
    start_batch(service, project_id, ready_batch(service, project_id, view))
    service.step(project_id)
    current = service.current(project_id)
    service.control(project_id, BatchControl(batchId=current["id"], expectedControlRevision=current["controlRevision"], action="pause"))
    with closing(storage.projects.open(project_id)) as store:
        job = service.video.jobs(store)[0]
        with pytest.raises(InvalidTransitionError):
            service.video.submit(store, job["id"])
    assert not provider.submits


def test_draft_rejects_duplicate_missing_source_fields_and_prompt_markup(tmp_path):
    _storage, _client, service, provider, project_id, view = batch_environment(tmp_path)
    draft = draft_for(view)
    bad = draft.model_copy(deep=True)
    bad.targets[0].fields[0].english = "[Shot 2] bypass source"
    with pytest.raises(ValueError): service.edit_directions(project_id, view["revision"], bad)
    bad = draft.model_copy(deep=True)
    bad.targets[0].fields.pop()
    with pytest.raises(ValueError): service.edit_directions(project_id, view["revision"], bad)
    bad = draft.model_copy(deep=True)
    bad.targets.append(deepcopy(bad.targets[0]))
    with pytest.raises(ValueError): service.edit_directions(project_id, view["revision"], bad)
    assert not provider.submits
