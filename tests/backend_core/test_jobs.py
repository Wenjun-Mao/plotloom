from __future__ import annotations

from concurrent.futures import Future
from threading import Event

import pytest

from plotloom.artifacts import MemoryArtifactStore
from plotloom.domain import STAGE_ORDER, ProviderSnapshot, RunKind, RunStatus, StageName
from plotloom.generation.aggregation import AggregateValidationError
from plotloom.generation.exceptions import SecretLeaseError
from plotloom.generation.planning import PlanningError
from plotloom.jobs import LifecycleJobRunner
from plotloom.providers import ProviderPorts
from plotloom.runtime import RunContext, RunExecutionResult
from plotloom.project_storage import ProjectStore

from .conftest import all_stage_payloads


class CompleteEngine:
    def execute(self, run, context, cancellation: Event) -> RunExecutionResult:
        return RunExecutionResult(
            stage_payloads={
                stage: payload.model_dump(mode="json", by_alias=False)
                for stage, payload in zip(STAGE_ORDER, all_stage_payloads(), strict=True)
            }
        )


class CountingEngine(CompleteEngine):
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, run, context, cancellation: Event) -> RunExecutionResult:
        self.calls += 1
        return super().execute(run, context, cancellation)


class FailingEngine:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def execute(self, run, context, cancellation: Event) -> RunExecutionResult:
        raise self.error


class BlockingEngine(CompleteEngine):
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()

    def execute(self, run, context, cancellation: Event) -> RunExecutionResult:
        self.started.set()
        assert self.release.wait(timeout=5)
        return super().execute(run, context, cancellation)


class RecordingSecretRegistrar:
    def __init__(self, *, server_available: bool = False) -> None:
        self.server_available = server_available
        self.registrations: list[tuple[str, str | None, str]] = []
        self.releases: list[str] = []

    def server_key_available(self, profile_id: str = "default") -> bool:
        return self.server_available

    def register_run_override(
        self, run_id: str, value: str | None, *, profile_id: str = "default"
    ) -> None:
        self.registrations.append((run_id, value, profile_id))

    def release_run(self, run_id: str) -> None:
        self.releases.append(run_id)


def _create_run(
    store: ProjectStore,
    *,
    stages=STAGE_ORDER,
    provider_snapshot: dict | None = None,
):
    snapshot = provider_snapshot or ProviderSnapshot(
        text_auth_mode="none"
    ).model_dump(mode="json", by_alias=True)
    with store.generation.admit_provider_snapshot(snapshot):
        return store.generation.create_run(
            store.manifest.project_id,
            RunKind.PIPELINE,
            stages,
            provider_snapshot=snapshot,
        )


def test_generation_future_cleanup_preserves_newer_mapping(project_store) -> None:
    runner = LifecycleJobRunner(
        project_store.generation,
        CompleteEngine(),
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        max_workers=1,
    )
    stale: Future = Future()
    replacement: Future = Future()
    runner._futures["same-run"] = replacement
    try:
        runner._forget_future("same-run", stale)
        assert runner._futures["same-run"] is replacement
    finally:
        runner._futures.pop("same-run", None)
        runner.close()


def test_runner_starts_installs_and_finishes_without_name_error(project_store) -> None:
    run = _create_run(project_store)
    runner = LifecycleJobRunner(
        project_store.generation,
        CompleteEngine(),
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        max_workers=1,
    )
    try:
        callbacks_finished = Event()
        future = runner.submit(run.id)
        future.add_done_callback(lambda _completed: callbacks_finished.set())
        completed = future.result(timeout=5)
        assert callbacks_finished.wait(timeout=1)
        assert run.id not in runner._futures
        assert completed.status == RunStatus.SUCCEEDED
    finally:
        runner.close()


def test_runner_ignores_session_header_for_auth_none_and_waits_for_missing_bearer_key(
    project_store,
) -> None:
    anonymous = _create_run(
        project_store,
        provider_snapshot=ProviderSnapshot(text_auth_mode="none").model_dump(
            mode="json", by_alias=True
        ),
    )
    registrar = RecordingSecretRegistrar()
    runner = LifecycleJobRunner(
        project_store.generation,
        CompleteEngine(),
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        max_workers=1,
        secret_registrar=registrar,
    )
    try:
        assert runner.submit(
            anonymous.id, session_api_key="must-not-be-registered"
        ).result(timeout=5).status == RunStatus.SUCCEEDED
        assert registrar.registrations == []

        bearer = _create_run(
            project_store,
            provider_snapshot=ProviderSnapshot(text_auth_mode="bearer").model_dump(
                mode="json", by_alias=True
            ),
        )
        with pytest.raises(SecretLeaseError):
            runner.submit(bearer.id)
        assert project_store.generation.get_run(bearer.id).status == RunStatus.QUEUED
        assert registrar.registrations == []
    finally:
        runner.close()


def test_cancel_before_worker_start_releases_the_registered_run_key(
    project_store,
) -> None:
    blocker = _create_run(
        project_store,
        provider_snapshot=ProviderSnapshot(text_auth_mode="none").model_dump(
            mode="json", by_alias=True
        ),
    )
    queued = _create_run(
        project_store,
        provider_snapshot=ProviderSnapshot(text_auth_mode="bearer").model_dump(
            mode="json", by_alias=True
        ),
    )
    engine = BlockingEngine()
    registrar = RecordingSecretRegistrar()
    runner = LifecycleJobRunner(
        project_store.generation,
        engine,
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        max_workers=1,
        secret_registrar=registrar,
    )
    try:
        blocker_future = runner.submit(blocker.id)
        assert engine.started.wait(timeout=1)
        queued_future = runner.submit(queued.id, session_api_key="ephemeral")
        runner.request_cancel(queued.id)
        engine.release.set()

        assert blocker_future.result(timeout=5).status == RunStatus.SUCCEEDED
        assert queued_future.result(timeout=5).status == RunStatus.CANCELLED
        assert (queued.id, "ephemeral", "default") in registrar.registrations
        assert queued.id in registrar.releases
        assert queued.id not in runner._cancellations
    finally:
        engine.release.set()
        runner.close()


def test_enqueue_then_brief_edit_fails_preflight_without_provider_cost(project_store, brief) -> None:
    run = _create_run(project_store)
    project_store.update_brief(
        brief.model_copy(update={"synopsis": f"{brief.synopsis} 用户补充。"}),
        expected_revision=1,
    )
    engine = CountingEngine()
    runner = LifecycleJobRunner(
        project_store.generation,
        engine,
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        max_workers=1,
    )
    try:
        completed = runner.submit(run.id).result(timeout=5)
        assert completed.status == RunStatus.QUARANTINED
        assert engine.calls == 0
        assert completed.result_revision_ids == []
    finally:
        runner.close()


def test_enqueue_then_upstream_edit_fails_preflight_without_provider_cost(project_store) -> None:
    original_bible = all_stage_payloads()[0]
    project_store.update_stage(STAGE_ORDER[0], original_bible, expected_revision=0)
    run = _create_run(project_store, stages=[STAGE_ORDER[1]])
    project_store.update_stage(
        STAGE_ORDER[0],
        original_bible.model_copy(update={"themes": ["用户编辑"]}),
        expected_revision=1,
    )
    engine = CountingEngine()
    runner = LifecycleJobRunner(
        project_store.generation,
        engine,
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        max_workers=1,
    )
    try:
        completed = runner.submit(run.id).result(timeout=5)
        assert completed.status == RunStatus.QUARANTINED
        assert engine.calls == 0
    finally:
        runner.close()


def test_runner_persists_stable_pre_attempt_planning_failure(project_store) -> None:
    run = _create_run(project_store)
    runner = LifecycleJobRunner(
        project_store.generation,
        FailingEngine(
            PlanningError(
                "bounded storyboard planning failed",
                code="planning.max_units_exceeded",
                stage=StageName.STORYBOARD,
            )
        ),
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        max_workers=1,
    )
    try:
        completed = runner.submit(run.id).result(timeout=5)
        assert completed.status == RunStatus.FAILED
        assert completed.failure_code == "planning.max_units_exceeded"
        assert completed.failed_stage == StageName.STORYBOARD
        assert project_store.generation.get_run_trace(run.id).attempts == []
    finally:
        runner.close()


def test_runner_quarantines_typed_aggregate_failure(project_store) -> None:
    run = _create_run(project_store)
    runner = LifecycleJobRunner(
        project_store.generation,
        FailingEngine(
            AggregateValidationError(
                "cross-unit identifier collision",
                code="aggregate.identifier_collision",
                stage=StageName.SCENE_BEATS,
            )
        ),
        RunContext(providers=ProviderPorts(), artifacts=MemoryArtifactStore()),
        max_workers=1,
    )
    try:
        completed = runner.submit(run.id).result(timeout=5)
        assert completed.status == RunStatus.QUARANTINED
        assert completed.failure_code == "aggregate.identifier_collision"
        assert completed.failed_stage == StageName.SCENE_BEATS
    finally:
        runner.close()
