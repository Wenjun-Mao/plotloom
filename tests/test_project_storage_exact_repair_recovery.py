"""Crash-recovery coverage for exact work-unit repairs through ``ProjectStore``."""

from __future__ import annotations

from pathlib import Path
from threading import Event

import pytest

from plotloom.artifacts import LocalArtifactStore
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import ArtifactKind, RunStatus, STAGE_ORDER, StageName
from plotloom.pipeline import PipelineEngine, RunSecretBroker
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.providers import ProviderPorts
from plotloom.runtime import RunContext
from tests.project_storage_exact_repair_support import (
    create_exact_repair,
    execute_repair,
    storage,
)
from tests.project_storage_fixtures import FixtureProvider, fixture_profile


class _RejectFinalSceneProvider:
    """Quarantine the last split Scene Beats unit, then repair it normally."""

    def __init__(self) -> None:
        self.delegate = FixtureProvider()
        self.name = self.delegate.name
        self.capabilities = self.delegate.capabilities
        self.scene_requests = 0
        self.requests = []

    def generate(self, request, secret):
        self.requests.append(request)
        prompt = "\n".join(message.content for message in request.messages)
        if "【目标故事节点】" in prompt:
            self.scene_requests += 1
            if self.scene_requests == 9:
                from plotloom.generation.contracts import ProviderResponse, ProviderUsage

                return ProviderResponse(
                    provider=self.name,
                    model=request.model,
                    raw={"choices": [{"message": {"role": "assistant", "content": "{}"}}]},
                    usage=ProviderUsage(input_tokens=1, output_tokens=1),
                )
        return self.delegate.generate(request, secret)


class _ShardRecoveryResolver:
    def __init__(self) -> None:
        self.provider = _RejectFinalSceneProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


class _ProcessLoss(BaseException):
    """Represent a process ending after durable candidate materialization."""


def test_exact_repair_reexecutes_only_the_failed_scene_shard_after_preseal_process_loss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    resolver = _ShardRecoveryResolver()
    parent = ProjectPipelineExecutor(resolver).execute(
        store, profile=fixture_profile(max_semantic_corrections=0)
    )
    assert parent.status == RunStatus.QUARANTINED
    target = next(
        unit
        for unit in store.generation.list_generation_work_units(parent.id)
        if unit.status.value == "quarantined"
    )
    assert target.stage == StageName.SCENE_BEATS
    parent_trace_before = store.run_trace(parent.id).model_dump(mode="json")
    child = create_exact_repair(store, parent.id, target.id, key="recover-one-scene-shard").run
    broker = RunSecretBroker()
    engine = PipelineEngine(store.generation, resolver, broker)
    original_seal = store.generation.seal_repair_stage_aggregate

    def lose_after_target_candidate(child_run_id: str, stage: StageName, **kwargs):
        if child_run_id == child.id and stage == StageName.SCENE_BEATS:
            raise _ProcessLoss()
        return original_seal(child_run_id, stage, **kwargs)

    monkeypatch.setattr(store.generation, "seal_repair_stage_aggregate", lose_after_target_candidate)
    try:
        with pytest.raises(_ProcessLoss):
            engine.execute(
                store.generation.start_run(child.id),
                RunContext(providers=ProviderPorts(), artifacts=LocalArtifactStore(store.home / "runs")),
                Event(),
            )
        requests_after_target = len(resolver.provider.requests)
        child_trace = store.run_trace(child.id)
        repaired_attempts = [
            attempt for attempt in child_trace.attempts if attempt.stage == StageName.SCENE_BEATS
        ]
        assert len(repaired_attempts) == 1
        assert repaired_attempts[0].work_unit_id is not None
        monkeypatch.setattr(store.generation, "seal_repair_stage_aggregate", original_seal)
        assert store.generation.reconcile_startup_jobs().resubmit_run_ids == [child.id]
        assert execute_repair(store, child.id, resolver).status == RunStatus.SUCCEEDED
    finally:
        broker.close()

    child_trace = store.run_trace(child.id)
    repaired_attempts = [
        attempt for attempt in child_trace.attempts if attempt.stage == StageName.SCENE_BEATS
    ]
    reused_scene_candidates = [
        artifact
        for artifact in child_trace.artifacts
        if artifact.stage == StageName.SCENE_BEATS
        and artifact.kind == ArtifactKind.CANDIDATE
        and artifact.source_artifact_id is not None
    ]
    assert len(resolver.provider.requests) == requests_after_target + 9
    assert len(repaired_attempts) == 1
    assert len(reused_scene_candidates) == 8
    canonical_stages = store.canonical_stages()
    assert [envelope.head.stage for envelope in canonical_stages] == list(STAGE_ORDER)
    assert all(envelope.head.revision == 1 for envelope in canonical_stages)
    parent_trace_after = store.run_trace(parent.id).model_dump(mode="json")
    assert parent_trace_after.pop("snapshot_is_current") is False
    assert parent_trace_before.pop("snapshot_is_current") is True
    assert parent_trace_after == parent_trace_before
