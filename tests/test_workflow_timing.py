"""Read-only timing ignores mutable controller and retrieval timestamps."""
from contextlib import closing
from datetime import timedelta

from plotloom.persistence.schema import AutopilotRunRow
from tests.autopilot_controller_fixtures import environment
from tests.video_batch_fixtures import batch_environment
from tests.autopilot_handoff_seed_fixtures import copy_awaiting_handoff_seed


def test_run_timing_uses_creation_and_scoped_immutable_facts_not_claim_updates(tmp_path, monkeypatch):
    storage, _registry, service, run, _calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        with closing(storage.projects.open(run.project_id)) as store:
            initial = store.repository.autopilot.current(run.project_id).timing
            assert initial.created_at.tzinfo is not None and initial.observed_at.tzinfo is not None
            with store.repository._write() as session:
                row = session.get(AutopilotRunRow, run.id)
                row.updated_at += timedelta(hours=2)
            with store.repository._read() as session:
                before = session.connection().exec_driver_sql("SELECT * FROM v2_autopilot_runs").fetchall()
            for _ in range(2):
                timing = store.repository.autopilot.current(run.project_id).timing
                assert timing.created_at == initial.created_at and timing.milestone_at is None
            with store.repository._read() as session:
                assert session.connection().exec_driver_sql("SELECT * FROM v2_autopilot_runs").fetchall() == before
    finally:
        service.close()


def test_batch_get_timing_does_not_write_or_call_provider_and_terminal_has_no_fake_completion(tmp_path):
    storage, client, _service, provider, project, view = batch_environment(tmp_path)
    from plotloom.persistence.schema import VideoBatchRow
    with closing(storage.projects.open(project)) as store:
        with store.repository._write() as session:
            row = session.get(VideoBatchRow, view["id"])
            row.updated_at += timedelta(hours=3)
            row.state = "cancelled"
        with store.repository._read() as session:
            before = session.connection().exec_driver_sql("SELECT * FROM v2_video_batches").fetchall()
        for _ in range(2):
            timing = client.get(f"/api/v2/projects/{project}/video-batch").json()["timing"]
            assert timing["terminal"] and timing["completedAt"] is None and timing["milestoneAt"] is None
        with store.repository._read() as session:
            assert session.connection().exec_driver_sql("SELECT * FROM v2_video_batches").fetchall() == before
    assert not provider.submits


def test_image_preparation_authorization_is_not_a_material_adoption_milestone(tmp_path, awaiting_handoff_seed):
    from sqlalchemy import select
    from plotloom.autopilot_contracts import OperationScope
    from plotloom.persistence.schema import AutopilotDecisionRow
    storage, run, _ = copy_awaiting_handoff_seed(awaiting_handoff_seed, tmp_path / "timing")
    with closing(storage.projects.open(run.project_id)) as store:
        initial = store.repository.autopilot.current(run.project_id).timing
        assert initial.milestone_at is not None
        with store.repository._write() as session:
            authorization = session.scalar(select(AutopilotDecisionRow).where(
                AutopilotDecisionRow.run_id == run.id, AutopilotDecisionRow.scope == OperationScope.IMAGE.value).limit(1))
            assert authorization is not None
            authorization.created_at = initial.observed_at + timedelta(hours=1)
        assert store.repository.autopilot.current(run.project_id).timing.milestone_at == initial.milestone_at


def test_effective_stale_run_uses_terminal_creation_date_even_when_persisted_running(tmp_path, monkeypatch):
    storage, _registry, service, run, _calls = environment(tmp_path, monkeypatch, auto_deliver=False)
    try:
        with closing(storage.projects.open(run.project_id)) as store:
            # Deliberately simulate a closure mismatch without the ordinary
            # manual-command owner (which correctly persists taken_over).
            with store.repository._write() as session:
                row = store.repository._project_access.rows.project(session, run.project_id)
                row.brief = row.brief | {"title": "Changed outside the active run"}
                row.revision += 1
            current = store.repository.autopilot.current(run.project_id)
            assert current.state == "stale" and current.timing.terminal and current.timing.completed_at is None
    finally:
        service.close()
