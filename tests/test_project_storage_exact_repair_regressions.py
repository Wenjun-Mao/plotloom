"""Exact-repair regressions owned by one manifest-bound ``ProjectStore``."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.project_folder_generation import register_project_folder_generation_routes
from plotloom.conformance import FIXED_CHINESE_BRIEF
from plotloom.domain import (
    Artifact,
    ArtifactKind,
    AttemptStatus,
    FragmentReuseKind,
    RunKind,
    RunStatus,
    StageName,
    WorkUnitFailureDisposition,
)
from plotloom.exceptions import InvalidTransitionError, RepairEligibilityError
from plotloom.persistence import stable_hash
from plotloom.persistence.schema.project_generation import (
    FragmentReuseBindingRow,
    WorkUnitRepairScopeRow,
)
from plotloom.project_generation_storage import ProjectPipelineExecutor
from plotloom.project_storage import ProjectFolderStorage, ProjectStorageError, ProjectStore
from tests.project_storage_exact_repair_support import (
    create_exact_repair as _create_exact_repair,
    execute_repair as _execute_repair,
    storage as _storage,
)
from tests.project_storage_fixtures import FixtureProvider, fixture_profile


class _RejectFinalStoryboardProvider:
    """Quarantine one final storyboard unit while retaining reusable siblings."""

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


class _Resolver:
    def __init__(self) -> None:
        self.provider = _RejectFinalStoryboardProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


class _RejectFinalSceneThenDownstreamStoryboardProvider:
    """Leave one last Scene Beats target repairable, then fail its child output."""

    def __init__(self) -> None:
        self.delegate = FixtureProvider()
        self.name = self.delegate.name
        self.capabilities = self.delegate.capabilities
        self.scene_requests = 0
        self.child_storyboard_started = False

    def generate(self, request, secret):
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
        if "【目标戏剧场景】" in prompt and self.scene_requests > 9:
            self.child_storyboard_started = True
            from plotloom.generation.contracts import ProviderResponse, ProviderUsage

            return ProviderResponse(
                provider=self.name,
                model=request.model,
                raw={"choices": [{"message": {"role": "assistant", "content": "{}"}}]},
                usage=ProviderUsage(input_tokens=1, output_tokens=1),
            )
        return self.delegate.generate(request, secret)


class _DownstreamFailureResolver:
    def __init__(self) -> None:
        self.provider = _RejectFinalSceneThenDownstreamStoryboardProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


def _rejected_bible_unit(
    store: ProjectStore,
    *,
    failure_disposition: WorkUnitFailureDisposition = WorkUnitFailureDisposition.QUARANTINED,
    outcome_unknown: bool = False,
):
    snapshot = fixture_profile().model_dump(mode="json", by_alias=True)
    with store.generation.admit_provider_snapshot(snapshot):
        run = store.generation.create_run(
            store.project().id,
            RunKind.PIPELINE,
            [StageName.STORY_BIBLE],
            provider_snapshot=snapshot,
        )
    store.generation.start_run(run.id)
    store.generation.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    unit = store.generation.list_generation_work_units(run.id)[0]
    attempt = store.generation.allocate_attempt_for_work_unit(
        unit.id, provider="fixture", model="fixture-model"
    )
    store.generation.mark_attempt_dispatched(attempt.id)
    if outcome_unknown:
        store.generation.mark_attempt_outcome_unknown(attempt.id, error="provider outcome is unknown")
        store.generation.finish_run(
            run.id,
            quarantine_reason="provider outcome is unknown",
            failure_code="provider.outcome_unknown",
            failed_stage=StageName.STORY_BIBLE,
        )
        return run, unit
    response = {"rawResponse": "rejected source output"}
    store.generation.persist_attempt_response(attempt.id, response)
    validation = {"accepted": False, "issues": [{"code": "schema.rejected"}]}
    store.generation.add_artifact(
        Artifact(
            run_id=run.id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.VALIDATION,
            content=validation,
            content_hash=stable_hash(validation),
        )
    )
    store.generation.finish_attempt(
        attempt.id,
        AttemptStatus.FAILED,
        error="rejected source output",
        outcome_code="schema.rejected",
        failure_disposition=failure_disposition,
    )
    store.generation.finish_run(
        run.id,
        quarantine_reason="rejected source output",
        failure_code="schema.rejected",
        failed_stage=StageName.STORY_BIBLE,
    )
    return run, unit


@pytest.mark.parametrize(
    ("failure_disposition", "outcome_unknown", "expected_code"),
    [
        (WorkUnitFailureDisposition.FAILED, False, "repair.target_not_quarantined"),
        (WorkUnitFailureDisposition.QUARANTINED, True, "repair.target_outcome_unknown"),
    ],
)
def test_exact_repair_refuses_nonreplayable_direct_project_targets(
    tmp_path: Path,
    failure_disposition: WorkUnitFailureDisposition,
    outcome_unknown: bool,
    expected_code: str,
) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    run, unit = _rejected_bible_unit(
        store, failure_disposition=failure_disposition, outcome_unknown=outcome_unknown
    )

    with pytest.raises(RepairEligibilityError, match=expected_code):
        _create_exact_repair(store, run.id, unit.id, key=f"reject-{expected_code}")


def test_exact_repair_rejects_stale_or_foreign_direct_project_evidence(tmp_path: Path) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    source, unit = _rejected_bible_unit(store)
    project = store.project()
    store.update_brief(
        project.brief.model_copy(update={"synopsis": "changed after quarantine"}),
        expected_revision=project.revision,
    )
    with pytest.raises(RepairEligibilityError, match="repair.snapshot_stale"):
        _create_exact_repair(store, source.id, unit.id, key="stale")

    fresh_source, _ = _rejected_bible_unit(store)
    _other_source, foreign_unit = _rejected_bible_unit(store)
    with pytest.raises(RepairEligibilityError, match="repair.target_not_in_source_run"):
        _create_exact_repair(store, fresh_source.id, foreign_unit.id, key="foreign-unit")


def test_archived_direct_project_is_not_advertised_or_admitted_for_exact_repair(
    tmp_path: Path,
) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    source, unit = _rejected_bible_unit(store)
    project = store.project()
    store.archive(expected_lifecycle_revision=project.lifecycle_revision)

    progress = store.generation.get_run_progress(source.id)
    assert progress.actions.repair_eligible is False
    assert [(item.work_unit_id, item.repair_eligible, item.repair_reason_code) for item in progress.work_units] == [
        (unit.id, False, "repair.project_archived")
    ]
    with pytest.raises(RepairEligibilityError, match="repair.project_archived"):
        _create_exact_repair(store, source.id, unit.id, key="archived-source")


def test_exact_repair_keeps_one_scope_across_idempotency_cancellation_and_restart(tmp_path: Path) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    source, unit = _rejected_bible_unit(store)
    created = _create_exact_repair(store, source.id, unit.id, key="one-direct-child")
    child = created.run
    scope = store.generation.get_work_unit_repair_scope(child.id)
    assert created.created is True
    assert scope.child_run_id == child.id
    replay = _create_exact_repair(store, source.id, unit.id, key="one-direct-child")
    assert replay.created is False
    assert replay.run.id == child.id

    recovery = store.generation.reconcile_startup_jobs()
    assert recovery.resubmit_run_ids == [child.id]
    assert store.generation.get_run(child.id).status == RunStatus.QUEUED
    assert store.generation.get_work_unit_repair_scope(child.id) == scope
    store.generation.start_run(child.id)
    store.generation.get_or_create_repair_stage_plan(child.id, StageName.STORY_BIBLE)
    repair_unit = store.generation.list_generation_work_units(child.id)[0]
    dispatched = store.generation.allocate_attempt_for_work_unit(
        repair_unit.id, provider="fixture", model="fixture-model"
    )
    dispatched = store.generation.mark_attempt_dispatched(dispatched.id)
    assert dispatched.dispatched_at is not None
    store.generation.cancel_run(child.id)
    cancelled = store.generation.finish_run(child.id)
    assert cancelled.status == RunStatus.CANCELLED
    assert store.generation.get_work_unit_repair_scope(child.id) == scope
    with pytest.raises(RepairEligibilityError, match="repair.already_exists"):
        _create_exact_repair(store, source.id, unit.id, key="replacement-after-cancel")
    assert store.canonical_stages() == []
    assert store.generation.get_run_execution_trace(child.id).sealed_aggregates == []


def test_exact_repair_http_replay_submits_only_the_created_child(tmp_path: Path) -> None:
    """The public endpoint must not resubmit an idempotent repair replay."""

    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    source, unit = _rejected_bible_unit(store)

    class StoreView:
        def __init__(self, project_store: ProjectStore) -> None:
            self.generation = project_store.generation

        def close(self) -> None:
            pass

    class Dispatcher:
        def inspect_run_project(self, run_id: str) -> StoreView:
            assert run_id == source.id
            return StoreView(store)

        def require_open_run_project(self, run_id: str) -> None:
            assert run_id == source.id

        def create_exact_repair(
            self, run_id: str, work_unit_id: str, *, idempotency_key: str
        ):
            assert run_id == source.id
            assert work_unit_id == unit.id
            creation = _create_exact_repair(store, run_id, work_unit_id, key=idempotency_key)
            return creation.run, creation.created

    class Admission:
        def __init__(self) -> None:
            self.submitted_run_ids: list[str] = []

        def admit_text_backend(self, profile_id: str, _request, *, frozen_snapshot):
            assert profile_id == source.provider_snapshot["profileId"]
            assert frozen_snapshot == source.provider_snapshot
            return frozen_snapshot

        def text_submission_session_key(self, _snapshot, _request) -> None:
            return None

        def submit_text_run(self, run, _request) -> None:
            self.submitted_run_ids.append(run.id)

    app = FastAPI()
    admission = Admission()
    register_project_folder_generation_routes(app, Dispatcher(), admission=admission)
    endpoint = f"/api/v2/runs/{source.id}/work-units/{unit.id}/repairs"
    with TestClient(app) as client:
        first = client.post(endpoint, json={}, headers={"Idempotency-Key": "repair-once"})
        replay = client.post(endpoint, json={}, headers={"Idempotency-Key": "repair-once"})

    assert first.status_code == 202
    assert replay.status_code == 202
    assert first.json()["id"] == replay.json()["id"]
    assert admission.submitted_run_ids == [first.json()["id"]]


def test_exact_repair_scope_and_binding_tampering_fail_before_child_materialization(
    tmp_path: Path,
) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    source, unit = _rejected_bible_unit(store)
    child = _create_exact_repair(store, source.id, unit.id, key="scope-and-binding").run
    source_before = store.run_trace(source.id).model_dump(mode="json")
    with store.repository._write() as session:  # noqa: SLF001 - corruption boundary proof
        row = session.get(WorkUnitRepairScopeRow, child.id)
        assert row is not None
        row.scope = {**row.scope, "targetInputHash": "tampered"}
    with pytest.raises(InvalidTransitionError, match="scope identity is inconsistent"):
        store.generation.get_work_unit_repair_scope(child.id)
    assert store.run_trace(source.id).model_dump(mode="json") == source_before


def test_legacy_exact_repair_scope_without_pending_siblings_preserves_its_raw_hash(
    tmp_path: Path,
) -> None:
    """Adding a defaulted field must not rewrite or reject historical scope JSON."""

    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    source, unit = _rejected_bible_unit(store)
    child = _create_exact_repair(store, source.id, unit.id, key="legacy-scope-json").run
    with store.repository._write() as session:  # noqa: SLF001 - historical JSON boundary proof
        row = session.get(WorkUnitRepairScopeRow, child.id)
        assert row is not None
        legacy_scope = {
            key: value
            for key, value in row.scope.items()
            if key not in {"pendingSiblingWorkUnitIds", "scopeHash"}
        }
        legacy_hash = stable_hash(legacy_scope)
        row.scope = {**legacy_scope, "scopeHash": legacy_hash}
        row.scope_hash = legacy_hash

    scope = store.generation.get_work_unit_repair_scope(child.id)
    assert scope.pending_sibling_work_unit_ids == []
    assert scope.scope_hash == legacy_hash


def test_tampered_frozen_upstream_binding_never_materializes_a_child_candidate(
    tmp_path: Path,
) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    resolver = _Resolver()
    parent = ProjectPipelineExecutor(resolver).execute(
        store, profile=fixture_profile(max_semantic_corrections=0)
    )
    assert parent.status == RunStatus.QUARANTINED
    target = next(
        unit
        for unit in store.generation.list_generation_work_units(parent.id)
        if unit.status.value == "quarantined"
    )
    child = _create_exact_repair(store, parent.id, target.id, key="tampered-upstream").run
    parent_before = store.run_trace(parent.id).model_dump(mode="json")
    store.generation.start_run(child.id)
    store.generation.get_or_create_repair_stage_plan(child.id, StageName.STORY_BIBLE)
    binding = store.generation.prepare_repair_stage_reuse(child.id, StageName.STORY_BIBLE)[0]
    assert binding.kind == FragmentReuseKind.UPSTREAM
    with store.repository._write() as session:  # noqa: SLF001 - corruption boundary proof
        row = session.get(FragmentReuseBindingRow, binding.id)
        assert row is not None
        row.binding_hash = "0" * 64

    with pytest.raises(InvalidTransitionError, match="binding identity is inconsistent"):
        store.generation.materialize_fragment_reuse_binding(child.id, binding.id)
    assert store.run_trace(parent.id).model_dump(mode="json") == parent_before
    assert store.canonical_stages() == []
    assert store.generation.get_run_execution_trace(child.id).sealed_aggregates == []


def test_exact_repair_preserves_frozen_upstream_and_sibling_bindings_until_atomic_install(
    tmp_path: Path,
) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    resolver = _Resolver()
    parent = ProjectPipelineExecutor(resolver).execute(store, profile=fixture_profile(max_semantic_corrections=0))
    assert parent.status == RunStatus.QUARANTINED
    parent_trace = store.run_trace(parent.id).model_dump(mode="json")
    target = next(
        unit
        for unit in store.generation.list_generation_work_units(parent.id)
        if unit.status.value == "quarantined"
    )
    child = _create_exact_repair(
        store, parent.id, target.id, key="preserve-frozen-siblings"
    ).run

    # The production runner is the only owner allowed to materialize reusable
    # candidates and install all repaired stages.  It must keep source evidence
    # intact while exposing every frozen parent binding in the child trace.
    completed = _execute_repair(store, child.id, resolver)
    assert completed.status == RunStatus.SUCCEEDED
    bindings = store.generation.get_fragment_reuse_bindings(child.id)
    assert {binding.kind for binding in bindings} >= {FragmentReuseKind.UPSTREAM, FragmentReuseKind.SIBLING}
    assert all(binding.source_run_id == parent.id for binding in bindings)
    assert all(binding.child_run_id == child.id for binding in bindings)
    assert all(binding.source_candidate_artifact_id for binding in bindings)
    parent_after = store.run_trace(parent.id).model_dump(mode="json")
    # Snapshot currentness is derived from the now-installed child output; the
    # frozen parent run/evidence itself must remain byte-for-byte unchanged.
    assert parent_after.pop("snapshot_is_current") is False
    assert parent_trace.pop("snapshot_is_current") is True
    assert parent_after == parent_trace
    assert all(envelope.head.revision == 1 for envelope in store.canonical_stages())


def test_exact_repair_downstream_failure_keeps_child_seals_but_never_partially_installs(
    tmp_path: Path,
) -> None:
    store = _storage(tmp_path).projects.create(FIXED_CHINESE_BRIEF)
    resolver = _DownstreamFailureResolver()
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
    child = _create_exact_repair(store, parent.id, target.id, key="downstream-failure").run

    completed = _execute_repair(store, child.id, resolver)

    assert completed.status == RunStatus.QUARANTINED
    assert resolver.provider.child_storyboard_started is True
    assert store.canonical_stages() == []
    assert {item.stage for item in store.generation.get_run_execution_trace(child.id).sealed_aggregates} == {
        StageName.STORY_BIBLE,
        StageName.STORY_GRAPH,
        StageName.SCENE_BEATS,
    }
    bindings = store.generation.get_fragment_reuse_bindings(child.id)
    assert {binding.kind for binding in bindings} >= {FragmentReuseKind.UPSTREAM, FragmentReuseKind.SIBLING}


def test_project_folder_permanent_delete_removes_terminal_repair_lineage_leaf_first(tmp_path: Path) -> None:
    storage = _storage(tmp_path)
    store = storage.projects.create(FIXED_CHINESE_BRIEF)
    source, unit = _rejected_bible_unit(store)
    child = _create_exact_repair(
        store, source.id, unit.id, key="delete-terminal-lineage"
    ).run
    store.generation.start_run(child.id)
    store.generation.cancel_run(child.id)
    store.generation.finish_run(child.id)
    project = store.project()
    store.close()

    archived = storage.lifecycle.archive(
        project.id, expected_lifecycle_revision=project.lifecycle_revision
    )
    storage.lifecycle.permanently_delete(
        project.id,
        expected_lifecycle_revision=archived.lifecycle_revision,
        confirmation_title=project.brief.title,
    )
    with pytest.raises(ProjectStorageError):
        storage.projects.open(project.id)
