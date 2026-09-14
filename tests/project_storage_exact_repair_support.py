"""Shared production-entrypoint helpers for exact-repair regression tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from plotloom.artifacts import LocalArtifactStore
from plotloom.jobs import LifecycleJobRunner
from plotloom.pipeline import PipelineEngine, RunSecretBroker
from plotloom.project_storage import ProjectFolderStorage, ProjectStore
from plotloom.providers import ProviderPorts
from plotloom.runtime import RunContext


def storage(tmp_path: Path) -> ProjectFolderStorage:
    return ProjectFolderStorage(
        outputs_root=tmp_path / "outputs",
        application_data_root=tmp_path / "application",
    )


def execute_repair(store: ProjectStore, run_id: str, resolver: Any):
    broker = RunSecretBroker()
    runner = LifecycleJobRunner(
        store.generation,
        PipelineEngine(store.generation, resolver, broker),
        RunContext(providers=ProviderPorts(), artifacts=LocalArtifactStore(store.home / "runs")),
        max_workers=1,
        secret_registrar=broker,
    )
    try:
        return runner.submit(run_id).result()
    finally:
        runner.close()
        broker.close()


def create_exact_repair(store: ProjectStore, source_run_id: str, unit_id: str, *, key: str):
    source = store.generation.get_run(source_run_id)
    with store.generation.admit_provider_snapshot(source.provider_snapshot):
        return store.generation.create_work_unit_repair_run(
            source_run_id, unit_id, idempotency_key=key
        )
