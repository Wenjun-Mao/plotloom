from __future__ import annotations

from concurrent.futures import Future
from threading import Event

from plotloom.artifacts import MemoryArtifactStore
from plotloom.domain import STAGE_ORDER, RunKind, RunStatus
from plotloom.jobs import LifecycleJobRunner
from plotloom.providers import ProviderPorts
from plotloom.runtime import RunContext, RunExecutionResult

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


def test_generation_future_cleanup_preserves_newer_mapping(repository) -> None:
    runner = LifecycleJobRunner(
        repository,
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


def test_runner_starts_installs_and_finishes_without_name_error(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, STAGE_ORDER)
    runner = LifecycleJobRunner(
        repository,
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


def test_enqueue_then_brief_edit_fails_preflight_without_provider_cost(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, STAGE_ORDER)
    repository.update_project(
        project.id,
        1,
        brief.model_copy(update={"synopsis": f"{brief.synopsis} 用户补充。"}),
    )
    engine = CountingEngine()
    runner = LifecycleJobRunner(
        repository,
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


def test_enqueue_then_upstream_edit_fails_preflight_without_provider_cost(repository, brief) -> None:
    project = repository.create_project(brief)
    original_bible = all_stage_payloads()[0]
    repository.update_stage(project.id, STAGE_ORDER[0], 0, original_bible)
    run = repository.create_run(project.id, RunKind.PIPELINE, [STAGE_ORDER[1]])
    repository.update_stage(
        project.id,
        STAGE_ORDER[0],
        1,
        original_bible.model_copy(update={"themes": ["用户编辑"]}),
    )
    engine = CountingEngine()
    runner = LifecycleJobRunner(
        repository,
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
