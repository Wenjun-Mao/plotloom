from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from plotloom.api import create_app
from plotloom.domain import (
    Artifact,
    ArtifactKind,
    AttemptStatus,
    RunKind,
    RunStatus,
    StageName,
    WorkUnitFailureDisposition,
)
from plotloom.exceptions import InvalidTransitionError, NotFoundError, RepairEligibilityError
from plotloom.persistence import FragmentReuseBindingRow, SQLiteRepository, WorkUnitRepairScopeRow, stable_hash
from plotloom.pipeline import PipelineEngine, RunSecretBroker

from .conftest import all_stage_payloads
from .test_pipeline import QueueProvider, RecordingResolver, _responses, _run, _work_unit_responses


class RecordingScheduler:
    """A scheduler port deliberately without its own deduplication."""

    def __init__(self) -> None:
        self.submissions: list[str] = []

    def submit(self, run_id: str, *, session_api_key: str | None = None) -> None:
        self.submissions.append(run_id)

    def request_cancel(self, run_id: str) -> None:
        raise AssertionError(f"unexpected cancellation for {run_id}")


def _quarantined_bible_unit(
    repository: SQLiteRepository,
    brief,
    *,
    failure_disposition: WorkUnitFailureDisposition = WorkUnitFailureDisposition.QUARANTINED,
    outcome_unknown: bool = False,
):
    project = repository.create_project(brief)
    source = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot={"textModel": "fixture-model"},
    )
    repository.start_run(source.id)
    repository.get_or_create_stage_plan(source.id, StageName.STORY_BIBLE)
    unit = repository.list_generation_work_units(source.id)[0]
    attempt = repository.allocate_attempt_for_work_unit(unit.id, provider="fixture", model="fixture-model")
    repository.mark_attempt_dispatched(attempt.id)
    if outcome_unknown:
        repository.mark_attempt_outcome_unknown(attempt.id, error="provider outcome is unknown")
        repository.finish_run(
            source.id,
            quarantine_reason="provider outcome is unknown",
            failure_code="provider.outcome_unknown",
            failed_stage=StageName.STORY_BIBLE,
        )
        return project, source, unit
    response = {"rawResponse": "rejected source output"}
    repository.persist_attempt_response(attempt.id, response)
    validation = {"accepted": False, "issues": [{"code": "schema.rejected"}]}
    repository.add_artifact(
        Artifact(
            run_id=source.id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.VALIDATION,
            content=validation,
            content_hash=stable_hash(validation),
        )
    )
    repository.finish_attempt(
        attempt.id,
        AttemptStatus.FAILED,
        error="rejected source output",
        outcome_code="schema.rejected",
        failure_disposition=failure_disposition,
    )
    repository.finish_run(
        source.id,
        quarantine_reason="rejected source output",
        failure_code="schema.rejected",
        failed_stage=StageName.STORY_BIBLE,
    )
    return project, source, unit


@pytest.mark.parametrize(
    ("failure_disposition", "outcome_unknown", "expected_code"),
    [
        (WorkUnitFailureDisposition.FAILED, False, "repair.target_not_quarantined"),
        (WorkUnitFailureDisposition.QUARANTINED, True, "repair.target_outcome_unknown"),
    ],
)
def test_exact_repair_rejects_nonreplayable_target_outcomes(
    repository: SQLiteRepository,
    brief,
    failure_disposition: WorkUnitFailureDisposition,
    outcome_unknown: bool,
    expected_code: str,
) -> None:
    _, source, unit = _quarantined_bible_unit(
        repository,
        brief,
        failure_disposition=failure_disposition,
        outcome_unknown=outcome_unknown,
    )

    with pytest.raises(RepairEligibilityError, match=expected_code):
        repository.create_work_unit_repair_run(
            source.id,
            unit.id,
            idempotency_key=f"reject-{expected_code}",
        )


def test_exact_repair_rejects_stale_snapshot_and_cross_run_unit(
    repository: SQLiteRepository,
    brief,
) -> None:
    project, source, unit = _quarantined_bible_unit(repository, brief)
    repository.update_project(
        project.id,
        expected_revision=project.revision,
        brief=brief.model_copy(update={"synopsis": "snapshot changed after quarantine"}),
    )
    with pytest.raises(RepairEligibilityError, match="repair.snapshot_stale"):
        repository.create_work_unit_repair_run(
            source.id,
            unit.id,
            idempotency_key="stale-source",
        )

    _, fresh_source, _ = _quarantined_bible_unit(repository, brief)
    _, _, foreign_unit = _quarantined_bible_unit(repository, brief)
    with pytest.raises(RepairEligibilityError, match="repair.target_not_in_source_run"):
        repository.create_work_unit_repair_run(
            fresh_source.id,
            foreign_unit.id,
            idempotency_key="cross-run-unit",
        )


def test_exact_repair_idempotency_replay_does_not_resubmit_child(
    repository: SQLiteRepository,
    brief,
) -> None:
    _, source, unit = _quarantined_bible_unit(repository, brief)
    scheduler = RecordingScheduler()
    client = TestClient(create_app(repository, run_scheduler=scheduler))
    endpoint = f"/api/v2/runs/{source.id}/work-units/{unit.id}/repairs"
    headers = {
        "Idempotency-Key": "repair-once",
        "X-Plotloom-Session-API-Key": "session-only-key",
    }

    first = client.post(endpoint, json={}, headers=headers)
    replay = client.post(endpoint, json={}, headers=headers)

    assert first.status_code == 202
    assert replay.status_code == 202
    assert replay.json()["id"] == first.json()["id"]
    assert scheduler.submissions == [first.json()["id"]]


def test_cancelled_exact_repair_keeps_its_scope_and_never_installs_partial_output(
    repository: SQLiteRepository,
    brief,
) -> None:
    project, source, unit = _quarantined_bible_unit(repository, brief)
    creation = repository.create_work_unit_repair_run(
        source.id,
        unit.id,
        idempotency_key="repair-cancelled-child",
    )
    assert creation.created is True
    child = creation.run
    scope_before = repository.get_work_unit_repair_scope(child.id)

    # Model a cancellation after the repair worker has crossed the dispatch
    # boundary but before it can persist a response or seal any aggregate.
    repository.start_run(child.id)
    repository.get_or_create_repair_stage_plan(child.id, StageName.STORY_BIBLE)
    child_unit = repository.list_generation_work_units(child.id)[0]
    attempt = repository.allocate_attempt_for_work_unit(child_unit.id, provider="fixture", model="fixture-model")
    repository.mark_attempt_dispatched(attempt.id)
    repository.cancel_run(child.id)
    cancelled = repository.finish_run(child.id)

    assert cancelled.status == RunStatus.CANCELLED
    assert repository.get_work_unit_repair_scope(child.id) == scope_before
    replay = repository.create_work_unit_repair_run(
        source.id,
        unit.id,
        idempotency_key="repair-cancelled-child",
    )
    assert replay.created is False
    assert replay.run.id == child.id
    with pytest.raises(RepairEligibilityError, match="repair.already_exists"):
        repository.create_work_unit_repair_run(
            source.id,
            unit.id,
            idempotency_key="replacement-after-cancel",
        )
    assert repository.get_stage_head(project.id, StageName.STORY_BIBLE).revision == 0
    assert repository.get_run_execution_trace(child.id).sealed_aggregates == []


def test_restart_requeues_the_existing_exact_repair_scope_without_partial_installation(
    repository: SQLiteRepository,
    brief,
) -> None:
    project, source, unit = _quarantined_bible_unit(repository, brief)
    creation = repository.create_work_unit_repair_run(
        source.id,
        unit.id,
        idempotency_key="repair-restart-child",
    )
    assert creation.created is True
    child = creation.run
    scope_before = repository.get_work_unit_repair_scope(child.id)

    recovery = repository.reconcile_startup_jobs()

    assert child.id in recovery.resubmit_run_ids
    assert repository.get_run(child.id).status == RunStatus.QUEUED
    assert repository.get_work_unit_repair_scope(child.id) == scope_before
    replay = repository.create_work_unit_repair_run(
        source.id,
        unit.id,
        idempotency_key="repair-restart-child",
    )
    assert replay.created is False
    assert replay.run.id == child.id
    assert repository.get_stage_head(project.id, StageName.STORY_BIBLE).revision == 0
    assert repository.get_run_execution_trace(child.id).sealed_aggregates == []


def test_exact_repair_scope_tampering_fails_closed(repository: SQLiteRepository, brief) -> None:
    _, source, unit = _quarantined_bible_unit(repository, brief)
    creation = repository.create_work_unit_repair_run(
        source.id,
        unit.id,
        idempotency_key="repair-scope-tamper",
    )
    with repository._write() as session:
        row = session.get(WorkUnitRepairScopeRow, creation.run.id)
        assert row is not None
        row.scope = {**row.scope, "targetInputHash": "tampered"}
    with pytest.raises(InvalidTransitionError, match="scope identity is inconsistent"):
        repository.get_work_unit_repair_scope(creation.run.id)


def test_archived_source_is_not_advertised_as_exact_repair_eligible(
    repository: SQLiteRepository,
    brief,
) -> None:
    project, source, unit = _quarantined_bible_unit(repository, brief)
    repository.archive_project(project.id, expected_lifecycle_revision=project.lifecycle_revision)

    eligibility = repository.get_repair_eligible_work_units(source.id)
    assert eligibility == [
        eligibility[0].model_copy(update={"eligible": False, "reason_code": "repair.project_archived"})
    ]
    with pytest.raises(RepairEligibilityError, match="repair.project_archived"):
        repository.create_work_unit_repair_run(
            source.id,
            unit.id,
            idempotency_key="repair-archived-source",
        )


def _scene_beats_parent_with_one_rejected_shard(repository: SQLiteRepository, brief):
    project = repository.create_project(brief)
    source = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS, StageName.STORYBOARD],
        provider_snapshot={"textModel": "fixture-model"},
    )
    topology = repository.get_story_graph_topology(source.id)
    assert topology is not None
    responses = _work_unit_responses(topology, brief)
    failed_index = 2 + len(topology.nodes) - 1
    secrets = RunSecretBroker("server-key")
    completed = _run(
        repository,
        PipelineEngine(
            repository,
            RecordingResolver(QueueProvider([*responses[:failed_index], "{}"])),
            secrets,
        ),
        secrets,
        source.id,
    )
    assert completed.status == RunStatus.QUARANTINED
    failed_unit = next(
        unit
        for unit in repository.list_generation_work_units(source.id)
        if unit.stage == StageName.SCENE_BEATS and unit.status.value == "quarantined"
    )
    return project, source, failed_unit, responses, failed_index


def test_tampered_child_reuse_binding_fails_closed_before_materialization(
    repository: SQLiteRepository,
    brief,
) -> None:
    project, source, failed_unit, _, _ = _scene_beats_parent_with_one_rejected_shard(repository, brief)
    child = repository.create_work_unit_repair_run(
        source.id,
        failed_unit.id,
        idempotency_key="tampered-binding",
    ).run
    parent_before = repository.get_run_trace(source.id).model_dump(mode="json")
    repository.start_run(child.id)
    repository.get_or_create_repair_stage_plan(child.id, StageName.STORY_BIBLE)
    binding = repository.prepare_repair_stage_reuse(child.id, StageName.STORY_BIBLE)[0]
    with repository._write() as session:
        row = session.get(FragmentReuseBindingRow, binding.id)
        assert row is not None
        row.binding_hash = "0" * 64

    with pytest.raises(InvalidTransitionError, match="binding identity is inconsistent"):
        repository.materialize_fragment_reuse_binding(child.id, binding.id)
    assert repository.get_run_trace(source.id).model_dump(mode="json") == parent_before
    assert repository.get_stage_head(project.id, StageName.STORY_BIBLE).revision == 0
    assert repository.get_run_execution_trace(child.id).sealed_aggregates == []


def test_downstream_repair_failure_never_installs_partial_child_seals(
    repository: SQLiteRepository,
    brief,
) -> None:
    project, source, failed_unit, responses, failed_index = _scene_beats_parent_with_one_rejected_shard(repository, brief)
    child = repository.create_work_unit_repair_run(
        source.id,
        failed_unit.id,
        idempotency_key="downstream-failure",
    ).run
    secrets = RunSecretBroker("server-key")
    completed = _run(
        repository,
        PipelineEngine(
            repository,
            RecordingResolver(QueueProvider([responses[failed_index], "{}"])),
            secrets,
        ),
        secrets,
        child.id,
    )

    assert completed.status == RunStatus.QUARANTINED
    assert all(repository.get_stage_head(project.id, stage).revision == 0 for stage in StageName)
    assert {item.stage for item in repository.get_run_execution_trace(child.id).sealed_aggregates} == {
        StageName.STORY_BIBLE,
        StageName.STORY_GRAPH,
        StageName.SCENE_BEATS,
    }


def test_permanent_delete_removes_exact_repair_scope_after_leaf_first_lineage_cleanup(
    repository: SQLiteRepository,
    brief,
) -> None:
    project, source, unit, _, _ = _scene_beats_parent_with_one_rejected_shard(
        repository, brief
    )
    child = repository.create_work_unit_repair_run(
        source.id,
        unit.id,
        idempotency_key="delete-repair-lineage",
    ).run
    repository.start_run(child.id)
    repository.get_or_create_repair_stage_plan(child.id, StageName.STORY_BIBLE)
    binding = repository.prepare_repair_stage_reuse(child.id, StageName.STORY_BIBLE)[0]
    repository.materialize_fragment_reuse_binding(child.id, binding.id)
    assert repository.get_fragment_reuse_bindings(child.id)
    # Project deletion is intentionally blocked while the child is nonterminal;
    # once cancelled, parent/child are both terminal and 0009's RESTRICT
    # scope plus source-artifact binding lineage must be removed leaf-first
    # before the project-owned cascades.
    repository.cancel_run(child.id)
    repository.finish_run(child.id)
    archived = repository.archive_project(project.id, expected_lifecycle_revision=project.lifecycle_revision)
    repository.permanent_delete_project(
        project.id,
        expected_lifecycle_revision=archived.lifecycle_revision,
        confirmation_title=brief.title,
    )

    for reader, identifier in (
        (repository.get_project, project.id),
        (repository.get_run, source.id),
        (repository.get_run, child.id),
        (repository.get_work_unit_repair_scope, child.id),
    ):
        with pytest.raises(NotFoundError):
            reader(identifier)
