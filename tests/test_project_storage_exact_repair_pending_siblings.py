"""Exact-repair sibling reuse and pending-work contract regressions."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import FragmentReuseKind, RunStatus, STAGE_ORDER, StageName, WorkUnitStatus
from plotloom.exceptions import RepairEligibilityError
from plotloom.persistence import stable_hash
from plotloom.persistence.schema.project_generation import GenerationWorkUnitRow, SealedStageAggregateRow
from plotloom.project_generation_storage import ProjectPipelineExecutor
from tests.project_storage_exact_repair_support import create_exact_repair, execute_repair, storage
from tests.project_storage_fixtures import FixtureProvider, fixture_profile


class _RejectSceneProvider:
    def __init__(self, reject_scene_number: int) -> None:
        self.delegate = FixtureProvider()
        self.name = self.delegate.name
        self.capabilities = self.delegate.capabilities
        self.reject_scene_number = reject_scene_number
        self.scene_requests = 0

    def generate(self, request, secret):
        prompt = "\n".join(message.content for message in request.messages)
        if "【目标故事节点】" in prompt:
            self.scene_requests += 1
            if self.scene_requests == self.reject_scene_number:
                from plotloom.generation.contracts import ProviderResponse, ProviderUsage

                return ProviderResponse(
                    provider=self.name,
                    model=request.model,
                    raw={"choices": [{"message": {"role": "assistant", "content": "{}"}}]},
                    usage=ProviderUsage(input_tokens=1, output_tokens=1),
                )
        return self.delegate.generate(request, secret)


class _SceneResolver:
    def __init__(self, reject_scene_number: int) -> None:
        self.provider = _RejectSceneProvider(reject_scene_number)

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


class _RejectFinalStoryboardProvider:
    def __init__(self) -> None:
        self.delegate = FixtureProvider()
        self.name = self.delegate.name
        self.capabilities = self.delegate.capabilities
        self.storyboard_requests = 0

    def generate(self, request, secret):
        prompt = "\n".join(message.content for message in request.messages)
        if "【目标戏剧场景】" in prompt:
            self.storyboard_requests += 1
            if self.storyboard_requests == 9:
                from plotloom.generation.contracts import ProviderResponse, ProviderUsage

                return ProviderResponse(
                    provider=self.name,
                    model=request.model,
                    raw={"choices": [{"message": {"role": "assistant", "content": "{}"}}]},
                    usage=ProviderUsage(input_tokens=1, output_tokens=1),
                )
        return self.delegate.generate(request, secret)


class _StoryboardResolver:
    def __init__(self) -> None:
        self.provider = _RejectFinalStoryboardProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


def test_exact_repair_reuses_accepted_siblings_and_executes_frozen_pending_sibling(
    tmp_path: Path,
) -> None:
    store = storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    resolver = _SceneResolver(reject_scene_number=8)
    parent = ProjectPipelineExecutor(resolver).execute(
        store, profile=fixture_profile(max_semantic_corrections=0)
    )
    assert parent.status == RunStatus.QUARANTINED
    scene_units = [
        unit for unit in store.generation.list_generation_work_units(parent.id)
        if unit.stage == StageName.SCENE_BEATS
    ]
    target = next(unit for unit in scene_units if unit.status.value == "quarantined")
    pending = next(unit for unit in scene_units if unit.status.value == "queued")
    parent_trace = store.run_trace(parent.id).model_dump(mode="json")

    child = create_exact_repair(store, parent.id, target.id, key="pending-scene-sibling").run
    scope = store.generation.get_work_unit_repair_scope(child.id)
    assert scope.pending_sibling_work_unit_ids == [pending.id]
    assert {
        item.source_work_unit_id for item in scope.reuse_sources
        if item.kind == FragmentReuseKind.SIBLING
    } == {unit.id for unit in scene_units if unit.status.value == "succeeded"}

    completed = execute_repair(store, child.id, resolver)

    assert completed.status == RunStatus.SUCCEEDED
    assert resolver.provider.scene_requests == 10
    child_trace = store.run_trace(child.id)
    child_scene_attempts = [
        attempt for attempt in child_trace.attempts if attempt.stage == StageName.SCENE_BEATS
    ]
    child_unit_selectors = {
        unit.id: unit.selector for unit in store.generation.list_generation_work_units(child.id)
    }
    assert {
        stable_hash(child_unit_selectors[attempt.work_unit_id])
        for attempt in child_scene_attempts
    } == {stable_hash(target.selector), stable_hash(pending.selector)}
    bindings = [
        binding for binding in store.generation.get_fragment_reuse_bindings(child.id)
        if binding.stage == StageName.SCENE_BEATS
    ]
    assert {binding.source_work_unit_id for binding in bindings} == {
        unit.id for unit in scene_units if unit.status.value == "succeeded"
    }
    assert [envelope.head.stage for envelope in store.canonical_stages()] == list(STAGE_ORDER)
    parent_after = store.run_trace(parent.id).model_dump(mode="json")
    assert parent_after.pop("snapshot_is_current") is False
    assert parent_trace.pop("snapshot_is_current") is True
    assert parent_after == parent_trace


def _quarantined_storyboard_parent(tmp_path: Path):
    store = storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    resolver = _StoryboardResolver()
    parent = ProjectPipelineExecutor(resolver).execute(
        store, profile=fixture_profile(max_semantic_corrections=0)
    )
    target = next(
        unit for unit in store.generation.list_generation_work_units(parent.id)
        if unit.status.value == "quarantined"
    )
    return store, parent, target


def test_exact_repair_fails_closed_when_a_sealed_upstream_manifest_identity_is_tampered(
    tmp_path: Path,
) -> None:
    store, parent, target = _quarantined_storyboard_parent(tmp_path)
    with store.repository._write() as session:  # noqa: SLF001 - corruption boundary proof
        aggregate = session.scalar(select(SealedStageAggregateRow).where(
            SealedStageAggregateRow.run_id == parent.id,
            SealedStageAggregateRow.stage == StageName.STORY_GRAPH.value,
        ))
        assert aggregate is not None
        manifest = dict(aggregate.manifest)
        manifest["units"] = [
            {**item, "candidateArtifactId": "missing-sealed-candidate"}
            for item in manifest["units"]
        ]
        aggregate.manifest = manifest
    with pytest.raises(
        RepairEligibilityError,
        match="sealed source aggregate manifest hash does not match immutable content",
    ):
        create_exact_repair(store, parent.id, target.id, key="tampered-sealed-candidate")


@pytest.mark.parametrize(
    "sibling_status",
    [WorkUnitStatus.FAILED, WorkUnitStatus.CANCELLED, WorkUnitStatus.OUTCOME_UNKNOWN],
)
def test_exact_repair_never_replays_non_pending_nonreusable_siblings(
    tmp_path: Path, sibling_status: WorkUnitStatus
) -> None:
    store, parent, target = _quarantined_storyboard_parent(tmp_path)
    sibling = next(
        unit for unit in store.generation.list_generation_work_units(parent.id)
        if unit.stage == target.stage and unit.id != target.id
    )
    with store.repository._write() as session:  # noqa: SLF001 - corruption boundary proof
        row = session.get(GenerationWorkUnitRow, sibling.id)
        assert row is not None
        row.status = sibling_status.value

    with pytest.raises(RepairEligibilityError, match="repair.parent_evidence_invalid"):
        create_exact_repair(
            store, parent.id, target.id, key=f"nonreplayable-{sibling_status.value}"
        )
