"""Public activity is a projection of typed durable evidence, not process guesses."""
from contextlib import closing

from tests.autopilot_controller_fixtures import environment


def test_activity_tracks_one_exact_queued_then_running_text_job(tmp_path, monkeypatch):
    from plotloom.codex_exec_contracts import (
        CodexExecHostStatus,
        transition_exec_attempt,
    )
    storage, registry, service, run, _calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    host = registry._codex_exec_test_host
    original_admit = host.admit
    def enqueue(attempt):
        queued = transition_exec_attempt(attempt, state="queued")
        status = CodexExecHostStatus(state="queued", attempt=queued, dispatchEnabled=True)
        host.statuses[str(attempt.attempt_id)] = status
        return status
    monkeypatch.setattr(registry, "codex_exec_admit", enqueue)
    try:
        assert service.acquire_controller()
        for _ in range(3):
            service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            current = store.repository.autopilot.current(run.project_id)
            assert current.material_current
            assert len(current.activities) == 1
            activity = current.activities[0]
            assert activity.state == "queued" and activity.domain == "text"
            attempt = store.repository.autopilot.exec_attempt_for_operation(run.id, "outline")
            assert activity.job_id == attempt.job_id
            payload = activity.model_dump(mode="json", by_alias=True)
            assert set(payload) == {"operationKey", "owner", "subjectId", "jobId", "domain", "state"}
            host.statuses.pop(str(attempt.attempt_id))
            original_admit(attempt)
        service.step(run.project_id)
        with closing(storage.projects.open(run.project_id)) as store:
            current = store.repository.autopilot.current(run.project_id)
            assert current.activities[0].state == "generating"
            assert current.activities[0].job_id == activity.job_id
    finally:
        service.close()
