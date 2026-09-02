from __future__ import annotations

from fastapi.testclient import TestClient

from plotloom.config import PlotloomSettings
from plotloom.domain import StartupRecoveryPlan
from plotloom import runtime


class RecoveryRepository:
    def __init__(self, plan: StartupRecoveryPlan) -> None:
        self.plan = plan
        self.calls = 0

    def reconcile_startup_jobs(self) -> StartupRecoveryPlan:
        self.calls += 1
        return self.plan


class RecordingRunner:
    def __init__(self) -> None:
        self.submissions: list[str] = []

    def submit(self, resource_id: str) -> None:
        self.submissions.append(resource_id)


def test_runtime_recovery_dispatches_only_repository_approved_actions() -> None:
    plan = StartupRecoveryPlan(
        resubmit_run_ids=["run-queued"],
        resubmit_media_task_ids=["media-queued"],
        resume_media_poll_task_ids=["media-polling"],
        terminated_run_ids=["run-interrupted"],
        terminated_media_task_ids=["media-ambiguous"],
    )
    repository = RecoveryRepository(plan)
    run_runner = RecordingRunner()
    media_runner = RecordingRunner()

    result = runtime.recover_runtime_jobs(repository, run_runner, media_runner)

    assert result == plan
    assert repository.calls == 1
    assert run_runner.submissions == ["run-queued"]
    assert media_runner.submissions == ["media-queued", "media-polling"]


def test_runtime_lifespan_performs_reconciliation_before_serving(
    tmp_path,
    monkeypatch,
) -> None:
    plan = StartupRecoveryPlan(terminated_run_ids=["run-interrupted"])
    observed_repositories = []

    def fake_recovery(repository, _run_runner, _media_runner):
        observed_repositories.append(repository)
        return plan

    monkeypatch.setattr(runtime, "recover_runtime_jobs", fake_recovery)
    settings = PlotloomSettings(
        repo_root=tmp_path,
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{tmp_path / 'data' / 'state.sqlite3'}",
        artifact_root=tmp_path / "artifacts",
        static_dir=tmp_path / "static",
        media_poll_interval_seconds=0.1,
    )
    app = runtime.build_runtime_app(settings)

    with TestClient(app):
        assert app.state.startup_recovery == plan
        assert observed_repositories == [app.state.repository]
