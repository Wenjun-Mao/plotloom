"""Finite H3 retries retain separate jobs and every possible prior charge."""
from contextlib import closing
from uuid import uuid4

import pytest

from plotloom.generation_retry_policy import ManualExecutionRetry
from plotloom.video_batch_contracts import BatchControl, BatchSetup
from plotloom.video_provider import RemoteOutcomeUnknown
from tests.video_batch_fixtures import batch_environment, ready_batch, start_batch
from tests.test_video_batch_review import native_batch_take as _native_batch_take

native_batch_take = _native_batch_take


def setup_retry(tmp_path, limit, *, max_jobs=None):
    storage,client,service,provider,project,view=batch_environment(tmp_path)
    service.control(project,BatchControl(batchId=view["id"],expectedControlRevision=view["controlRevision"],action="cancel"))
    view=service.setup(project,BatchSetup(profileId="minimax_h3_quality8_portrait_576x1024_v2",
        shotIds=[view["manifest"]["targets"][0]["shotId"]],automaticRetryLimit=limit,maxJobs=max_jobs))
    return storage,client,service,provider,project,view


@pytest.mark.parametrize("limit",[0,1,3])
def test_h3_unknown_attempts_use_fresh_ids_preserve_charge_and_exhaust_finitely(tmp_path,limit):
    storage,_client,service,provider,project,view=setup_retry(tmp_path,limit)
    started=start_batch(service,project,ready_batch(service,project,view))
    provider.submit_error=RemoteOutcomeUnknown("synthetic lost response")
    for _ in range(4):service.step(project)
    current=service.current(project)
    assert len(provider.submits)==limit+1
    with closing(storage.projects.open(project)) as store:
        jobs=service.video.jobs(store)
        assert len(jobs)==len({j["id"] for j in jobs})==limit+1
        assert all(j["state"]=="outcome_unknown" for j in jobs)
        latest=next(j for j in jobs if j["id"] in current["execution"]["jobs"].values())
        assert latest["retry"]["automaticRetriesUsed"]==limit
        assert len(latest["retry"]["predecessorJobIds"])==limit
        assert latest["retry"]["possiblePriorCost"]
    assert current["state"]=="blocked" and current["execution"]["failures"]
    for _ in range(2):service.step(project)
    assert len(provider.submits)==limit+1
    # The explicit command grants one additional attempt, not a fresh auto allowance.
    command=ManualExecutionRetry(commandId=uuid4(),failedJobId=latest["id"],expectedRevision=current["revision"])
    changed=service.retry_execution(project,command)
    repeated=service.retry_execution(project,command)
    assert repeated["execution"]==changed["execution"] and repeated["revision"]==changed["revision"]
    service.step(project)
    assert len(provider.submits)==limit+2


def test_original_finite_h3_budget_cannot_be_replenished_by_unknown_or_retry(tmp_path):
    storage,_client,service,provider,project,view=setup_retry(tmp_path,3,max_jobs=1)
    start_batch(service,project,ready_batch(service,project,view))
    provider.submit_error=RemoteOutcomeUnknown("synthetic lost response")
    for _ in range(4):service.step(project)
    assert len(provider.submits)==1
    with closing(storage.projects.open(project)) as store:
        jobs=service.video.jobs(store)
        assert len(jobs)==1 and jobs[0]["state"]=="outcome_unknown"


def test_cancelling_original_unknown_fences_current_child_and_keeps_history(tmp_path):
    storage,_client,service,provider,project,view=setup_retry(tmp_path,0)
    start_batch(service,project,ready_batch(service,project,view))
    provider.submit_error=RemoteOutcomeUnknown("synthetic lost response")
    for _ in range(3):service.step(project)
    view=service.current(project)
    original=next(iter(view["execution"]["jobs"].values()))
    command=ManualExecutionRetry(commandId=uuid4(),failedJobId=original,expectedRevision=view["revision"])
    retried=service.retry_execution(project,command)
    child=next(iter(retried["execution"]["jobs"].values()))
    assert child!=original
    with closing(storage.projects.open(project)) as store:
        service.video.cancel(store,original)
        jobs={job["id"]:job for job in service.video.jobs(store)}
        assert jobs[original]["state"]=="outcome_unknown"
        assert jobs[original]["cancelRequestedAt"]
        assert jobs[child]["state"]=="cancelled"
    for _ in range(3):service.step(project)
    view=service.current(project)
    assert view["execution"]["cancelledTargets"]
    assert len(provider.submits)==1 and view["state"]=="blocked"
    assert next(iter(view["execution"]["jobs"].values()))==child


def test_retained_retry_source_tampering_is_refused_on_open(tmp_path):
    import sqlite3
    import json
    from plotloom.persistence.codec import stable_hash
    from plotloom.project_storage.format import ProjectStorageCorruptionError
    storage,_client,service,provider,project,view=setup_retry(tmp_path,1)
    start_batch(service,project,ready_batch(service,project,view))
    provider.submit_error=RemoteOutcomeUnknown("synthetic lost response")
    service.step(project); service.step(project)
    view=service.current(project)
    child=next(iter(view["execution"]["jobs"].values()))
    with closing(storage.projects.open(project)) as store:
        database=store.database_path
    with sqlite3.connect(database) as connection:
        snapshot=json.loads(connection.execute("SELECT snapshot FROM v2_video_jobs WHERE id=?",(child,)).fetchone()[0])
        snapshot["executionRetry"]["automaticRetriesUsed"]=0
        connection.execute("UPDATE v2_video_jobs SET snapshot=?,snapshot_hash=? WHERE id=?",(json.dumps(snapshot),stable_hash(snapshot),child))
    with pytest.raises(ProjectStorageCorruptionError):storage.projects.open(project)


def test_exhausted_h3_target_allows_an_independent_eligible_target_to_proceed(tmp_path):
    storage,_client,service,provider,project,view=batch_environment(tmp_path)
    service.control(project,BatchControl(batchId=view["id"],expectedControlRevision=view["controlRevision"],action="cancel"))
    view=service.setup(project,BatchSetup(profileId=view["manifest"]["setup"]["profileId"],
        shotIds=[target["shotId"] for target in view["manifest"]["targets"][:2]],automaticRetryLimit=0))
    start_batch(service,project,ready_batch(service,project,view))
    provider.submit_error=RemoteOutcomeUnknown("synthetic lost response")
    service.step(project);service.step(project)
    provider.submit_error=None
    service.step(project);service.step(project)
    assert len(provider.submits)==2
    with closing(storage.projects.open(project)) as store:
        jobs=service.video.jobs(store)
        assert {job["state"] for job in jobs}=={"outcome_unknown","submitted"}
        assert len({job["snapshot"]["shot"]["id"] for job in jobs})==2


def test_successful_manual_h3_retry_replaces_current_failure_and_reaches_review(tmp_path,native_batch_take):
    from sqlalchemy import select
    from plotloom.persistence.schema import ProjectVideoDispatchRow
    from plotloom.video_ingestion import probe_video
    storage,_client,service,provider,project,view=setup_retry(tmp_path,0,max_jobs=2)
    provider._outputs=[native_batch_take]
    service.video._probe=probe_video
    start_batch(service,project,ready_batch(service,project,view))
    provider.submit_error=RemoteOutcomeUnknown("synthetic lost response")
    for _ in range(3):service.step(project)
    failed=service.current(project)
    shot,original=next(iter(failed["execution"]["jobs"].items()))
    assert failed["state"]=="blocked" and failed["execution"]["failures"][shot]["jobId"]==original
    provider.submit_error=None
    command=ManualExecutionRetry(commandId=uuid4(),failedJobId=original,expectedRevision=failed["revision"])
    retried=service.retry_execution(project,command)
    child=retried["execution"]["jobs"][shot]
    assert child!=original and retried["state"]=="running"
    assert shot not in retried["execution"]["failures"] and retried["execution"]["error"] is None
    for _ in range(8):
        service.step(project)
        view=service.current(project)
        if view["state"] in {"awaiting_review","blocked"}:break
    with closing(storage.projects.open(project)) as store:
        jobs={job["id"]:job for job in service.video.jobs(store)}
        assert jobs[child]["state"]=="ingested" and jobs[child]["current"]
        assert jobs[child]["segments"] and jobs[child]["segments"][-1]["current"]
        assert jobs[original]["state"]=="outcome_unknown" and jobs[original]["outputHash"] is None
        assert jobs[child]["retry"]["predecessorJobIds"]==[original]
        with store.repository._read() as session:
            claims=session.scalars(select(ProjectVideoDispatchRow)).all()
            assert {claim.video_job_id for claim in claims}=={original,child}
    assert view["state"]=="awaiting_review",view["execution"]
    assert view["execution"]["jobs"][shot]==child and view["execution"]["retryHistory"][shot]==[original]
    assert not view["execution"]["failures"] and view["execution"]["error"] is None
    assert view["progress"]=={"total":1,"ready":1,"failed":0,"blocked":0}
    review=service.review(project)
    assert review["ready"] and review["readyCount"]==1
    assert review["proposals"][0]["jobId"]==child
    assert len(provider.submits)==2 and provider.downloads==1
