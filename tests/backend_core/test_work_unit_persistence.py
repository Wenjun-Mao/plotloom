from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

import pytest
from alembic import command
from sqlalchemy import create_engine, select, text

import plotloom.validation as validation_module
from plotloom.domain import (
    Artifact,
    ArtifactKind,
    AttemptStatus,
    MediaKind,
    MediaTaskStatus,
    RunKind,
    RunStatus,
    StageName,
    WorkUnitFailureDisposition,
    WorkUnitStatus,
)
from plotloom.exceptions import InvalidTransitionError
from plotloom.generation.fragments import (
    SceneBeatsFragment,
    StoryBibleFragment,
    StoryboardFragment,
    StoryGraphFragment,
)
from plotloom.generation.dialogue_capacity import (
    DIALOGUE_CAPACITY_POLICY_V1,
    plan_dialogue_capacity,
)
from plotloom.generation.planning import (
    PlanningError,
    StagePlan,
    _stage_plan_hash,
    assert_work_unit_input_contract,
)
from plotloom.persistence import (
    GenerationWorkUnitRow,
    MediaTaskRow,
    SQLiteRepository,
    StagePlanRow,
    stable_hash,
)
from plotloom.schema import SchemaMigrator

from .conftest import all_stage_payloads


def _running_bible_unit(repository: SQLiteRepository, brief):
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(run.id)
    repository.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    return run, repository.list_generation_work_units(run.id)[0]


def _persist_bible_unit_evidence(
    repository: SQLiteRepository,
    run_id: str,
    payload,
    *,
    validation_content: object | None = None,
):
    return _persist_stage_unit_evidence(
        repository,
        run_id,
        StageName.STORY_BIBLE,
        payload,
        validation_content=validation_content,
    )


def _persist_stage_unit_evidence(
    repository: SQLiteRepository,
    run_id: str,
    stage: StageName,
    payload,
    *,
    validation_content: object | None = None,
):
    stage_plan = repository.get_or_create_stage_plan(run_id, stage)
    unit = repository.list_generation_work_units(run_id)[0]
    if stage != StageName.STORY_BIBLE:
        unit = next(
            work_unit
            for work_unit in repository.list_generation_work_units(run_id)
            if work_unit.stage == stage
        )
    attempt = repository.allocate_attempt_for_work_unit(unit.id, provider="local", model="qwen")
    repository.mark_attempt_dispatched(attempt.id)
    prompt = {"messages": [{"role": "user", "content": "make a bible"}]}
    repository.add_artifact(
        Artifact(
            run_id=run_id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=stage,
            kind=ArtifactKind.PROMPT,
            content=prompt,
            content_hash=stable_hash(prompt),
        )
    )
    repository.persist_attempt_response(attempt.id, {"rawResponse": "{}"}, provider_request_id="req-1")
    validation = validation_content if validation_content is not None else {"accepted": True, "issues": []}
    repository.add_artifact(
        Artifact(
            run_id=run_id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=stage,
            kind=ArtifactKind.VALIDATION,
            content=validation,
            content_hash=stable_hash(validation),
        )
    )
    fragment_type = {
        StageName.STORY_BIBLE: StoryBibleFragment,
        StageName.STORY_GRAPH: StoryGraphFragment,
    }[stage]
    fragment = fragment_type(
        stage_plan_hash=stage_plan.stage_plan_hash,
        work_unit_id=unit.id,
        payload=payload,
    )
    fragment_data = fragment.model_dump(mode="json", by_alias=False)
    candidate = repository.add_artifact(
        Artifact(
            run_id=run_id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=stage,
            kind=ArtifactKind.CANDIDATE,
            content=fragment_data,
            content_hash=stable_hash(fragment_data),
        )
    )
    return stage_plan, unit, attempt, candidate


def _seal_bible_unit(repository: SQLiteRepository, run_id: str, payload) -> str:
    _, _, attempt, candidate = _persist_bible_unit_evidence(repository, run_id, payload)
    repository.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    aggregate = repository.seal_stage_aggregate(
        run_id,
        StageName.STORY_BIBLE,
        candidate_artifact_ids=[candidate.id],
    )
    return aggregate.id


def _seal_graph_unit(repository: SQLiteRepository, run_id: str, payload) -> str:
    _, _, attempt, candidate = _persist_stage_unit_evidence(
        repository, run_id, StageName.STORY_GRAPH, payload
    )
    repository.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    aggregate = repository.seal_stage_aggregate(
        run_id,
        StageName.STORY_GRAPH,
        candidate_artifact_ids=[candidate.id],
    )
    return aggregate.id


def _seal_partitioned_stage(
    repository: SQLiteRepository,
    run_id: str,
    stage: StageName,
    payload,
) -> str:
    """Persist valid fragment evidence for every Scene Beats/Storyboard unit."""

    stage_plan = repository.get_or_create_stage_plan(run_id, stage)
    work_units = [
        unit
        for unit in repository.list_generation_work_units(run_id)
        if unit.stage == stage
    ]
    candidate_ids: list[str] = []
    for index, (planned_unit, work_unit) in enumerate(
        zip(stage_plan.work_units, work_units, strict=True), start=1
    ):
        attempt = repository.allocate_attempt_for_work_unit(
            work_unit.id, provider="local", model="qwen"
        )
        repository.mark_attempt_dispatched(attempt.id)
        prompt = {"messages": [{"role": "user", "content": f"make {stage.value}"}]}
        repository.add_artifact(
            Artifact(
                run_id=run_id,
                attempt_id=attempt.id,
                work_unit_id=work_unit.id,
                stage=stage,
                kind=ArtifactKind.PROMPT,
                content=prompt,
                content_hash=stable_hash(prompt),
            )
        )
        repository.persist_attempt_response(
            attempt.id,
            {"rawResponse": "{}"},
            provider_request_id=f"partitioned-{stage.value}-{index}",
        )
        accepted = {"accepted": True, "issues": []}
        repository.add_artifact(
            Artifact(
                run_id=run_id,
                attempt_id=attempt.id,
                work_unit_id=work_unit.id,
                stage=stage,
                kind=ArtifactKind.VALIDATION,
                content=accepted,
                content_hash=stable_hash(accepted),
            )
        )
        selector = planned_unit.selector.stable_id
        if stage == StageName.SCENE_BEATS:
            fragment = SceneBeatsFragment(
                stage_plan_hash=stage_plan.stage_plan_hash,
                work_unit_id=work_unit.id,
                story_node_id=selector,
                scenes=tuple(scene for scene in payload.scenes if scene.story_node_id == selector),
                beats=tuple(
                    beat
                    for beat in payload.beats
                    if any(scene.id == beat.scene_id for scene in payload.scenes if scene.story_node_id == selector)
                ),
                dialogue_cues=(),
            )
        elif stage == StageName.STORYBOARD:
            fragment = StoryboardFragment(
                stage_plan_hash=stage_plan.stage_plan_hash,
                work_unit_id=work_unit.id,
                scene_id=selector,
                shots=tuple(shot for shot in payload.shots if shot.scene_id == selector),
                shot_beat_links=tuple(
                    link
                    for link in payload.shot_beat_links
                    if any(shot.id == link.shot_id for shot in payload.shots if shot.scene_id == selector)
                ),
            )
        else:
            raise AssertionError(f"unsupported partitioned stage: {stage.value}")
        candidate_data = fragment.model_dump(mode="json", by_alias=False)
        candidate = repository.add_artifact(
            Artifact(
                run_id=run_id,
                attempt_id=attempt.id,
                work_unit_id=work_unit.id,
                stage=stage,
                kind=ArtifactKind.CANDIDATE,
                content=candidate_data,
                content_hash=stable_hash(candidate_data),
            )
        )
        candidate_ids.append(candidate.id)
        repository.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    return repository.seal_stage_aggregate(
        run_id,
        stage,
        candidate_artifact_ids=candidate_ids,
    ).id


def _replace_scene_beats_plan_with_obsolete_contract(
    repository: SQLiteRepository,
    run_id: str,
) -> dict:
    """Install a hash-valid pre-allocation StagePlan fixture without rewriting it later."""

    current = repository.get_or_create_stage_plan(run_id, StageName.SCENE_BEATS)
    obsolete_dependency_hash = "f" * 64
    legacy_units = tuple(
        unit.model_copy(update={"dependency_hash": obsolete_dependency_hash})
        for unit in current.work_units
    )
    draft = StagePlan.model_construct(
        run_id=current.run_id,
        stage=current.stage,
        generation_plan_hash=current.generation_plan_hash,
        dependency_hash=obsolete_dependency_hash,
        scene_timing_allocation=None,
        work_units=legacy_units,
        stage_plan_hash="",
    )
    legacy_plan = StagePlan(
        run_id=draft.run_id,
        stage=draft.stage,
        generation_plan_hash=draft.generation_plan_hash,
        dependency_hash=draft.dependency_hash,
        work_units=draft.work_units,
        stage_plan_hash=_stage_plan_hash(draft),
    )
    persisted = legacy_plan.model_dump(mode="json", by_alias=False)

    with repository._write() as session:
        plan_row = session.scalar(
            select(StagePlanRow).where(
                StagePlanRow.run_id == run_id,
                StagePlanRow.stage == StageName.SCENE_BEATS.value,
            )
        )
        assert plan_row is not None
        plan_row.plan = deepcopy(persisted)
        plan_row.dependency_hash = legacy_plan.dependency_hash
        plan_row.stage_plan_hash = legacy_plan.stage_plan_hash
        units = session.scalars(
            select(GenerationWorkUnitRow).where(
                GenerationWorkUnitRow.stage_plan_id == plan_row.id
            )
        ).all()
        for unit in units:
            unit.dependency_hash = obsolete_dependency_hash
    return persisted


def _replace_scene_beats_dialogue_contract_with_obsolete_contract(
    repository: SQLiteRepository,
    run_id: str,
    *,
    field: str,
    replacement: object,
) -> dict:
    """Corrupt one frozen dialogue field without allowing recovery to rewrite it."""

    current = repository.get_or_create_stage_plan(run_id, StageName.SCENE_BEATS)
    persisted = current.model_dump(mode="json", by_alias=False)
    if replacement is None:
        persisted.pop(field)
    else:
        persisted[field] = replacement

    with repository._write() as session:
        plan_row = session.scalar(
            select(StagePlanRow).where(
                StagePlanRow.run_id == run_id,
                StagePlanRow.stage == StageName.SCENE_BEATS.value,
            )
        )
        assert plan_row is not None
        plan_row.plan = deepcopy(persisted)
    return persisted


def _persisted_scene_beats_plan(repository: SQLiteRepository, run_id: str) -> dict:
    with repository._read() as session:
        plan_row = session.scalar(
            select(StagePlanRow).where(
                StagePlanRow.run_id == run_id,
                StagePlanRow.stage == StageName.SCENE_BEATS.value,
            )
        )
        assert plan_row is not None
        return deepcopy(plan_row.plan)


def _replace_scene_beats_plan_with_complete_v1_capacity_contract(
    repository: SQLiteRepository,
    run_id: str,
) -> dict:
    """Persist a parseable v1 plan whose historic unit hashes omit v2 nulls."""

    current = repository.get_or_create_stage_plan(run_id, StageName.SCENE_BEATS)
    assert current.scene_timing_allocation is not None
    assert current.dialogue_timing_profile is not None
    generation_plan = repository.get_generation_plan(run_id)
    legacy_capacity = plan_dialogue_capacity(
        scene_timing_allocation=current.scene_timing_allocation,
        dialogue_timing_profile=current.dialogue_timing_profile,
        policy_version=DIALOGUE_CAPACITY_POLICY_V1,
    )
    legacy_units = []
    for unit in current.work_units:
        historic_input = {
            "generation_plan_hash": generation_plan.plan_hash,
            "stage": unit.stage.value,
            "selector": unit.selector.model_dump(mode="json"),
            "sequence": unit.sequence,
            "dependency_hash": unit.dependency_hash,
            "unit_dependency_hash": unit.unit_dependency_hash,
            "budget": unit.budget.model_dump(mode="json"),
            "estimated_input_tokens": unit.estimated_input_tokens,
            "context_window_tokens": unit.context_window_tokens,
            "dialogue_timing_profile": current.dialogue_timing_profile.model_dump(
                mode="json",
                by_alias=False,
            ),
            "dialogue_capacity_plan": legacy_capacity.model_dump(
                mode="json",
                by_alias=False,
                exclude_none=True,
            ),
        }
        historic_input_hash = stable_hash(historic_input)
        legacy_units.append(
            unit.model_copy(
                update={
                    "unit_id": (
                        f"unit-{unit.stage.value}-{unit.sequence:04d}-"
                        f"{historic_input_hash[:16]}"
                    ),
                    "input_hash": historic_input_hash,
                    "dialogue_capacity_plan": legacy_capacity,
                }
            )
        )
    draft = StagePlan.model_construct(
        run_id=current.run_id,
        stage=current.stage,
        generation_plan_hash=current.generation_plan_hash,
        dependency_hash=current.dependency_hash,
        scene_timing_allocation=current.scene_timing_allocation,
        dialogue_timing_profile=current.dialogue_timing_profile,
        dialogue_capacity_plan=legacy_capacity,
        work_units=tuple(legacy_units),
        stage_plan_hash="",
    )
    legacy = StagePlan(
        **draft.model_dump(
            mode="python",
            exclude={"stage_plan_hash"},
            exclude_none=True,
        ),
        stage_plan_hash=_stage_plan_hash(draft),
    )
    persisted = legacy.model_dump(mode="json", by_alias=False, exclude_none=True)
    assert StagePlan.model_validate(persisted) == legacy
    with pytest.raises(PlanningError, match="work-unit input hash does not match"):
        assert_work_unit_input_contract(generation_plan, legacy.work_units[0])

    with repository._write() as session:
        plan_row = session.scalar(
            select(StagePlanRow).where(
                StagePlanRow.run_id == run_id,
                StagePlanRow.stage == StageName.SCENE_BEATS.value,
            )
        )
        assert plan_row is not None
        plan_row.plan = deepcopy(persisted)
        plan_row.stage_plan_hash = legacy.stage_plan_hash
    return persisted


def test_run_plan_is_persisted_before_child_rows_and_trace_is_additive(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])

    plan = repository.get_generation_plan(run.id)
    trace = repository.get_run_execution_trace(run.id)

    assert plan.run_id == run.id
    assert plan.canonical_snapshot_hash == run.canonical_snapshot.snapshot_hash
    assert trace.generation_plan is not None
    assert trace.generation_plan.plan_hash == plan.plan_hash
    assert trace.stage_plans == []
    assert trace.work_units == []


def test_run_plan_persists_effective_provider_output_ceiling(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
        provider_snapshot={
            "textContextWindowTokens": 32_768,
            "textMaxOutputTokens": 1_024,
        },
    )

    plan = repository.get_generation_plan(run.id)
    assert plan.stage_budgets[StageName.STORY_BIBLE].max_output_tokens == 1_024

    repository.start_run(run.id)
    stage_plan = repository.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    assert stage_plan.work_units[0].budget.max_output_tokens == 1_024


def test_stage_plan_waits_for_requested_upstream_seal_and_is_idempotent(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH],
    )
    repository.start_run(run.id)

    with pytest.raises(InvalidTransitionError, match="StagePlan exists|aggregate is sealed"):
        repository.get_or_create_stage_plan(run.id, StageName.STORY_GRAPH)

    _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    first = repository.get_or_create_stage_plan(run.id, StageName.STORY_GRAPH)
    replay = repository.get_or_create_stage_plan(run.id, StageName.STORY_GRAPH)

    assert replay == first
    assert [plan.stage for plan in repository.list_stage_plans(run.id)] == [
        StageName.STORY_BIBLE,
        StageName.STORY_GRAPH,
    ]


def test_sealed_aggregate_is_exact_and_commit_reads_only_sealed_payloads(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(run.id)
    aggregate_id = _seal_bible_unit(repository, run.id, all_stage_payloads()[0])

    completed = repository.commit_sealed_run(run.id, sealed_aggregate_ids=[aggregate_id])
    trace = repository.get_run_execution_trace(run.id)

    assert completed.result_revision_ids
    assert trace.sealed_aggregates[0].id == aggregate_id
    assert trace.work_units[0].status == WorkUnitStatus.SUCCEEDED
    with pytest.raises(InvalidTransitionError, match="already been committed|run is succeeded"):
        repository.commit_sealed_run(run.id, sealed_aggregate_ids=[aggregate_id])


def test_sealed_scene_beats_and_storyboard_install_replays_frozen_timing_profile(
    repository,
    brief,
    monkeypatch,
) -> None:
    project = repository.create_project(brief)
    bible, graph, scene_beats, storyboard = all_stage_payloads()
    repository.update_stage(project.id, StageName.STORY_BIBLE, 0, bible)
    repository.update_stage(project.id, StageName.STORY_GRAPH, 0, graph)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.SCENE_BEATS, StageName.STORYBOARD],
    )
    repository.start_run(run.id)
    scene_beats_aggregate_id = _seal_partitioned_stage(
        repository, run.id, StageName.SCENE_BEATS, scene_beats
    )
    storyboard_aggregate_id = _seal_partitioned_stage(
        repository, run.id, StageName.STORYBOARD, storyboard
    )

    def current_default_must_not_be_read():
        raise AssertionError("canonical sealed installation must use the frozen StagePlan profile")

    monkeypatch.setattr(
        validation_module,
        "default_dialogue_timing_profile",
        current_default_must_not_be_read,
    )

    completed = repository.commit_sealed_run(
        run.id,
        sealed_aggregate_ids=[scene_beats_aggregate_id, storyboard_aggregate_id],
    )

    assert completed.status == RunStatus.SUCCEEDED
    assert repository.get_stage_head(project.id, StageName.SCENE_BEATS).revision == 1
    assert repository.get_stage_head(project.id, StageName.STORYBOARD).revision == 1


def test_sealed_scene_beats_commit_rejects_missing_frozen_timing_profile(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    bible, graph, scene_beats, _ = all_stage_payloads()
    repository.update_stage(project.id, StageName.STORY_BIBLE, 0, bible)
    repository.update_stage(project.id, StageName.STORY_GRAPH, 0, graph)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.SCENE_BEATS])
    repository.start_run(run.id)
    aggregate_id = _seal_partitioned_stage(
        repository, run.id, StageName.SCENE_BEATS, scene_beats
    )
    with repository._write() as session:
        row = session.scalar(
            select(StagePlanRow).where(
                StagePlanRow.run_id == run.id,
                StagePlanRow.stage == StageName.SCENE_BEATS.value,
            )
        )
        assert row is not None
        row.plan = {**row.plan, "dialogue_timing_profile": None}

    with pytest.raises(
        InvalidTransitionError,
        match="valid frozen Scene Beats dialogue timing profile",
    ):
        repository.commit_sealed_run(run.id, sealed_aggregate_ids=[aggregate_id])

    assert repository.get_stage_head(project.id, StageName.SCENE_BEATS).revision == 0


def test_sealed_storyboard_only_commit_fails_closed_without_run_timing_provenance(
    repository,
    brief,
    monkeypatch,
) -> None:
    project = repository.create_project(brief)
    bible, graph, scene_beats, storyboard = all_stage_payloads()
    for stage, payload in (
        (StageName.STORY_BIBLE, bible),
        (StageName.STORY_GRAPH, graph),
        (StageName.SCENE_BEATS, scene_beats),
    ):
        repository.update_stage(project.id, stage, 0, payload)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORYBOARD])
    repository.start_run(run.id)
    aggregate_id = _seal_partitioned_stage(
        repository, run.id, StageName.STORYBOARD, storyboard
    )

    def current_default_must_not_be_read():
        raise AssertionError("provenance-free sealed storyboard install must fail before default lookup")

    monkeypatch.setattr(
        validation_module,
        "default_dialogue_timing_profile",
        current_default_must_not_be_read,
    )

    with pytest.raises(
        InvalidTransitionError,
        match="frozen Scene Beats dialogue timing profile",
    ):
        repository.commit_sealed_run(run.id, sealed_aggregate_ids=[aggregate_id])

    assert repository.get_stage_head(project.id, StageName.STORYBOARD).revision == 0


def test_work_unit_attempt_requires_dispatch_and_marks_unknown_outcomes(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(run.id)
    repository.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    unit = repository.list_generation_work_units(run.id)[0]
    attempt = repository.allocate_attempt_for_work_unit(unit.id)

    with pytest.raises(InvalidTransitionError, match="dispatch marker"):
        repository.persist_attempt_response(attempt.id, {"rawResponse": "not yet"})
    repository.mark_attempt_dispatched(attempt.id)
    unknown = repository.mark_attempt_outcome_unknown(attempt.id, error="deadline after submission")

    assert unknown.outcome_unknown is True
    assert repository.list_generation_work_units(run.id)[0].status == WorkUnitStatus.OUTCOME_UNKNOWN


def test_work_unit_validation_failure_requires_rebuild_until_exact_repair_exists(
    repository,
    brief,
) -> None:
    run, unit = _running_bible_unit(repository, brief)
    attempt = repository.allocate_attempt_for_work_unit(unit.id)
    repository.mark_attempt_dispatched(attempt.id)
    repository.persist_attempt_response(attempt.id, {"rawResponse": "{}"})
    rejected = {"accepted": False, "issues": [{"code": "schema", "message": "invalid"}]}
    repository.add_artifact(
        Artifact(
            run_id=run.id,
            attempt_id=attempt.id,
            work_unit_id=unit.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.VALIDATION,
            content=rejected,
            content_hash=stable_hash(rejected),
        )
    )
    repository.finish_attempt(
        attempt.id,
        AttemptStatus.FAILED,
        error="invalid candidate",
        outcome_code="schema.invalid",
        failure_disposition=WorkUnitFailureDisposition.QUARANTINED,
    )
    assert repository.list_generation_work_units(run.id)[0].status == (
        WorkUnitStatus.QUARANTINED
    )
    repository.finish_run(run.id, quarantine_reason="invalid candidate")

    with pytest.raises(InvalidTransitionError, match="exact work-unit repair"):
        repository.create_repair_run(run.id)

    assert len(repository.list_project_runs(run.project_id)) == 1


def test_known_work_unit_failure_requires_an_explicit_terminal_disposition(
    repository,
    brief,
) -> None:
    run, unit = _running_bible_unit(repository, brief)
    attempt = repository.allocate_attempt_for_work_unit(unit.id)

    with pytest.raises(InvalidTransitionError, match="explicit failed or quarantined"):
        repository.finish_attempt(
            attempt.id,
            AttemptStatus.FAILED,
            error="known local failure",
            outcome_code="local.known_failure",
        )

    assert repository.get_run_trace(run.id).attempts[0].status == AttemptStatus.RUNNING
    assert repository.list_generation_work_units(run.id)[0].status == (
        WorkUnitStatus.RUNNING
    )
    repository.finish_attempt(
        attempt.id,
        AttemptStatus.FAILED,
        error="known local failure",
        outcome_code="local.known_failure",
        failure_disposition=WorkUnitFailureDisposition.FAILED,
    )
    assert repository.list_generation_work_units(run.id)[0].status == (
        WorkUnitStatus.FAILED
    )


def test_artifacts_cannot_cross_run_or_escape_work_unit_ownership(repository, brief) -> None:
    project = repository.create_project(brief)
    first = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    second = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(first.id)
    repository.get_or_create_stage_plan(first.id, StageName.STORY_BIBLE)
    unit = repository.list_generation_work_units(first.id)[0]
    attempt = repository.allocate_attempt_for_work_unit(unit.id)
    content = {"messages": []}

    with pytest.raises(InvalidTransitionError, match="declared run"):
        repository.add_artifact(
            Artifact(
                run_id=second.id,
                attempt_id=attempt.id,
                work_unit_id=unit.id,
                stage=StageName.STORY_BIBLE,
                kind=ArtifactKind.PROMPT,
                content=content,
                content_hash=stable_hash(content),
            )
        )


def test_work_unit_claim_is_single_use_except_safe_startup_recovery(repository, brief) -> None:
    run, unit = _running_bible_unit(repository, brief)
    first = repository.allocate_attempt_for_work_unit(unit.id)

    with pytest.raises(InvalidTransitionError, match="work unit is running"):
        repository.allocate_attempt_for_work_unit(unit.id)

    recovery = repository.reconcile_startup_jobs()

    assert recovery.resubmit_run_ids == [run.id]
    assert repository.get_run(run.id).status == RunStatus.QUEUED
    assert repository.list_generation_work_units(run.id)[0].status == WorkUnitStatus.RUNNING
    recovered = repository.get_run_trace(run.id).attempts[0]
    assert recovered.id == first.id
    assert recovered.status == AttemptStatus.RUNNING
    assert recovered.dispatched_at is None

    repository.start_run(run.id)
    resumed = repository.get_recoverable_attempt_for_work_unit(unit.id)
    assert resumed is not None
    assert resumed.id == first.id
    assert resumed.attempt_number == 1
    with pytest.raises(InvalidTransitionError, match="work unit is running"):
        repository.allocate_attempt_for_work_unit(unit.id)


def test_attempt_numbers_are_local_to_each_work_unit(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS],
    )
    repository.start_run(run.id)
    bible_id = _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    assert bible_id
    _, _, graph_attempt, graph_candidate = _persist_stage_unit_evidence(
        repository,
        run.id,
        StageName.STORY_GRAPH,
        all_stage_payloads()[1],
    )
    repository.finish_attempt(graph_attempt.id, AttemptStatus.SUCCEEDED)
    repository.seal_stage_aggregate(
        run.id,
        StageName.STORY_GRAPH,
        candidate_artifact_ids=[graph_candidate.id],
    )
    repository.get_or_create_stage_plan(run.id, StageName.SCENE_BEATS)
    units = [
        unit
        for unit in repository.list_generation_work_units(run.id)
        if unit.stage == StageName.SCENE_BEATS
    ]
    assert len(units) > 1

    first = repository.allocate_attempt_for_work_unit(units[0].id)
    second = repository.allocate_attempt_for_work_unit(units[1].id)

    assert (first.attempt_number, second.attempt_number) == (1, 1)


def test_work_unit_claim_is_atomic_across_repository_instances(tmp_path, brief) -> None:
    database_url = f"sqlite:///{tmp_path / 'work-unit-claim.sqlite3'}"
    first_repository = SQLiteRepository(database_url)
    second_repository = SQLiteRepository(database_url)
    try:
        run, unit = _running_bible_unit(first_repository, brief)
        barrier = Barrier(2)

        def claim(repository: SQLiteRepository) -> tuple[str, object]:
            barrier.wait()
            try:
                return "claimed", repository.allocate_attempt_for_work_unit(unit.id)
            except InvalidTransitionError as error:
                return "rejected", error

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(claim, (first_repository, second_repository)))

        claimed = [outcome for outcome in outcomes if outcome[0] == "claimed"]
        rejected = [outcome for outcome in outcomes if outcome[0] == "rejected"]
        assert len(claimed) == 1
        assert len(rejected) == 1
        assert "work unit is running" in str(rejected[0][1])
        attempts = first_repository.get_run_trace(run.id).attempts
        assert [(attempt.work_unit_id, attempt.attempt_number) for attempt in attempts] == [
            (unit.id, 1)
        ]
    finally:
        second_repository.close()
        first_repository.close()


def test_seal_requires_succeeded_producer_and_accepted_object_validation(repository, brief) -> None:
    running, _ = _running_bible_unit(repository, brief)
    _, _, running_attempt, running_candidate = _persist_bible_unit_evidence(
        repository,
        running.id,
        all_stage_payloads()[0],
    )
    with pytest.raises(InvalidTransitionError, match="succeeded"):
        repository.seal_stage_aggregate(
            running.id,
            StageName.STORY_BIBLE,
            candidate_artifact_ids=[running_candidate.id],
        )

    failed, _ = _running_bible_unit(repository, brief)
    _, _, failed_attempt, failed_candidate = _persist_bible_unit_evidence(
        repository,
        failed.id,
        all_stage_payloads()[0],
    )
    repository.finish_attempt(
        failed_attempt.id,
        AttemptStatus.FAILED,
        error="invalid",
        outcome_code="local.fixture_failed",
        failure_disposition=WorkUnitFailureDisposition.FAILED,
    )
    with pytest.raises(InvalidTransitionError, match="succeeded"):
        repository.seal_stage_aggregate(
            failed.id,
            StageName.STORY_BIBLE,
            candidate_artifact_ids=[failed_candidate.id],
        )

    rejected, _ = _running_bible_unit(repository, brief)
    _, _, rejected_attempt, rejected_candidate = _persist_bible_unit_evidence(
        repository,
        rejected.id,
        all_stage_payloads()[0],
        validation_content={"accepted": False, "issues": ["bad"]},
    )
    repository.finish_attempt(rejected_attempt.id, AttemptStatus.SUCCEEDED)
    with pytest.raises(InvalidTransitionError, match="accepted: true"):
        repository.seal_stage_aggregate(
            rejected.id,
            StageName.STORY_BIBLE,
            candidate_artifact_ids=[rejected_candidate.id],
        )

    malformed, _ = _running_bible_unit(repository, brief)
    _, _, malformed_attempt, malformed_candidate = _persist_bible_unit_evidence(
        repository,
        malformed.id,
        all_stage_payloads()[0],
        validation_content=["accepted", True],
    )
    repository.finish_attempt(malformed_attempt.id, AttemptStatus.SUCCEEDED)
    with pytest.raises(InvalidTransitionError, match="object validation"):
        repository.seal_stage_aggregate(
            malformed.id,
            StageName.STORY_BIBLE,
            candidate_artifact_ids=[malformed_candidate.id],
        )

    assert running_attempt.status == AttemptStatus.RUNNING


def test_duplicate_producer_artifacts_are_rejected_before_they_can_be_sealed(repository, brief) -> None:
    run, _ = _running_bible_unit(repository, brief)
    _, unit, attempt, candidate = _persist_bible_unit_evidence(
        repository,
        run.id,
        all_stage_payloads()[0],
    )
    duplicate_prompt = {"messages": [{"role": "user", "content": "different prompt"}]}

    with pytest.raises(InvalidTransitionError, match="immutable prompt evidence"):
        repository.add_artifact(
            Artifact(
                run_id=run.id,
                attempt_id=attempt.id,
                work_unit_id=unit.id,
                stage=StageName.STORY_BIBLE,
                kind=ArtifactKind.PROMPT,
                content=duplicate_prompt,
                content_hash=stable_hash(duplicate_prompt),
            )
        )

    repository.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    sealed = repository.seal_stage_aggregate(
        run.id,
        StageName.STORY_BIBLE,
        candidate_artifact_ids=[candidate.id],
    )
    assert sealed.manifest["units"][0]["candidateArtifactId"] == candidate.id


def test_seal_freezes_attempt_and_artifact_mutation(repository, brief) -> None:
    run, _ = _running_bible_unit(repository, brief)
    _, unit, attempt, candidate = _persist_bible_unit_evidence(
        repository,
        run.id,
        all_stage_payloads()[0],
    )
    repository.finish_attempt(attempt.id, AttemptStatus.SUCCEEDED)
    repository.seal_stage_aggregate(
        run.id,
        StageName.STORY_BIBLE,
        candidate_artifact_ids=[candidate.id],
    )
    media_trace = {"uri": "local://sealed-trace"}

    with pytest.raises(InvalidTransitionError, match="after its work-unit stage aggregate is sealed"):
        repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error="late change")
    with pytest.raises(InvalidTransitionError, match="after its work-unit stage aggregate is sealed"):
        repository.add_artifact(
            Artifact(
                run_id=run.id,
                attempt_id=attempt.id,
                work_unit_id=unit.id,
                stage=StageName.STORY_BIBLE,
                kind=ArtifactKind.MEDIA,
                content=media_trace,
                content_hash=stable_hash(media_trace),
            )
        )


def test_cancel_wins_before_dispatch_and_before_seal(repository, brief) -> None:
    dispatch_run, dispatch_unit = _running_bible_unit(repository, brief)
    dispatch_attempt = repository.allocate_attempt_for_work_unit(dispatch_unit.id)
    assert repository.cancel_run(dispatch_run.id).status == RunStatus.CANCEL_REQUESTED
    with pytest.raises(InvalidTransitionError, match="run is cancel_requested"):
        repository.mark_attempt_dispatched(dispatch_attempt.id)
    cancelled = repository.finish_run(dispatch_run.id)
    assert cancelled.status == RunStatus.CANCELLED
    assert repository.list_generation_work_units(dispatch_run.id)[0].status == WorkUnitStatus.CANCELLED

    seal_run, _ = _running_bible_unit(repository, brief)
    _, seal_unit, seal_attempt, seal_candidate = _persist_bible_unit_evidence(
        repository,
        seal_run.id,
        all_stage_payloads()[0],
    )
    repository.finish_attempt(seal_attempt.id, AttemptStatus.SUCCEEDED)
    repository.cancel_run(seal_run.id)
    with pytest.raises(InvalidTransitionError, match="run is cancel_requested"):
        repository.seal_stage_aggregate(
            seal_run.id,
            StageName.STORY_BIBLE,
            candidate_artifact_ids=[seal_candidate.id],
        )
    repository.finish_run(seal_run.id)
    assert repository.list_generation_work_units(seal_run.id)[0].status == WorkUnitStatus.SUCCEEDED
    assert seal_unit.id


def test_cancel_preserves_sealed_units_and_cancels_unfinished_units(repository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH],
    )
    repository.start_run(run.id)
    _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    repository.get_or_create_stage_plan(run.id, StageName.STORY_GRAPH)

    repository.cancel_run(run.id)
    repository.finish_run(run.id)

    units = repository.list_generation_work_units(run.id)
    assert [unit.status for unit in units] == [
        WorkUnitStatus.SUCCEEDED,
        WorkUnitStatus.CANCELLED,
    ]


def test_startup_recovery_classifies_work_unit_runs_without_provider_replay(repository, brief) -> None:
    pre_dispatch_run, pre_dispatch_unit = _running_bible_unit(repository, brief)
    pre_dispatch = repository.allocate_attempt_for_work_unit(pre_dispatch_unit.id)

    ambiguous_run, ambiguous_unit = _running_bible_unit(repository, brief)
    ambiguous = repository.allocate_attempt_for_work_unit(ambiguous_unit.id)
    repository.mark_attempt_dispatched(ambiguous.id)

    sealed_run, _ = _running_bible_unit(repository, brief)
    sealed_id = _seal_bible_unit(repository, sealed_run.id, all_stage_payloads()[0])

    recovery = repository.reconcile_startup_jobs()

    assert set(recovery.resubmit_run_ids) == {pre_dispatch_run.id, sealed_run.id}
    assert recovery.terminated_run_ids == [ambiguous_run.id]
    assert repository.get_run(pre_dispatch_run.id).status == RunStatus.QUEUED
    assert repository.list_generation_work_units(pre_dispatch_run.id)[0].status == WorkUnitStatus.RUNNING
    assert repository.get_run_trace(pre_dispatch_run.id).attempts[0].status == AttemptStatus.RUNNING
    recovered_ambiguous = repository.get_run(ambiguous_run.id)
    assert recovered_ambiguous.status == RunStatus.FAILED
    assert recovered_ambiguous.failure_code == "provider.outcome_unknown"
    assert recovered_ambiguous.failed_stage == StageName.STORY_BIBLE
    ambiguous_trace = repository.get_run_trace(ambiguous_run.id).attempts[0]
    assert ambiguous_trace.status == AttemptStatus.FAILED
    assert ambiguous_trace.outcome_unknown is True
    assert repository.list_generation_work_units(ambiguous_run.id)[0].status == WorkUnitStatus.OUTCOME_UNKNOWN
    assert repository.get_run(sealed_run.id).status == RunStatus.QUEUED
    assert sealed_id
    assert pre_dispatch.id


def test_startup_recovery_terminates_obsolete_scene_timing_contract_without_rewriting_history(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS],
    )
    repository.start_run(run.id)
    _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    _seal_graph_unit(repository, run.id, all_stage_payloads()[1])
    legacy_plan = _replace_scene_beats_plan_with_obsolete_contract(repository, run.id)
    artifact = repository.add_artifact(
        Artifact(
            run_id=run.id,
            stage=StageName.SCENE_BEATS,
            kind=ArtifactKind.PROMPT,
            content={"legacy": "scene timing allocation absent"},
            content_hash=stable_hash({"legacy": "scene timing allocation absent"}),
        )
    )

    recovery = repository.reconcile_startup_jobs()

    assert recovery.resubmit_run_ids == []
    assert recovery.terminated_run_ids == [run.id]
    recovered = repository.get_run(run.id)
    assert recovered.status == RunStatus.FAILED
    assert recovered.failure_code == "recovery.scene_timing_contract_obsolete"
    assert recovered.failed_stage == StageName.SCENE_BEATS
    assert "Submit a new run" in (recovered.error or "")
    assert all(
        unit.status != WorkUnitStatus.QUEUED
        for unit in repository.list_generation_work_units(run.id)
        if unit.stage == StageName.SCENE_BEATS
    )
    assert repository.get_artifact(artifact.id).content == {
        "legacy": "scene timing allocation absent"
    }
    recovered_plan = next(
        plan
        for plan in repository.list_stage_plans(run.id)
        if plan.stage == StageName.SCENE_BEATS
    )
    assert recovered_plan.model_dump(mode="json", by_alias=False) == legacy_plan


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("dialogue_timing_profile", None),
        ("dialogue_capacity_plan", None),
        ("dialogue_timing_profile", {}),
        ("dialogue_capacity_plan", {}),
    ],
    ids=(
        "missing-dialogue-timing-profile",
        "missing-dialogue-capacity-plan",
        "unparseable-dialogue-timing-profile",
        "unparseable-dialogue-capacity-plan",
    ),
)
def test_startup_recovery_terminates_nonterminal_scene_beats_with_obsolete_dialogue_contract(
    repository,
    brief,
    field: str,
    replacement: object,
) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS],
    )
    repository.start_run(run.id)
    _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    _seal_graph_unit(repository, run.id, all_stage_payloads()[1])
    obsolete_plan = _replace_scene_beats_dialogue_contract_with_obsolete_contract(
        repository,
        run.id,
        field=field,
        replacement=replacement,
    )
    artifact = repository.add_artifact(
        Artifact(
            run_id=run.id,
            stage=StageName.SCENE_BEATS,
            kind=ArtifactKind.PROMPT,
            content={"obsolete": field},
            content_hash=stable_hash({"obsolete": field}),
        )
    )

    recovery = repository.reconcile_startup_jobs()

    assert recovery.resubmit_run_ids == []
    assert recovery.terminated_run_ids == [run.id]
    recovered = repository.get_run(run.id)
    assert recovered.status == RunStatus.FAILED
    assert recovered.failure_code == "recovery.scene_timing_contract_obsolete"
    assert recovered.failed_stage == StageName.SCENE_BEATS
    assert repository.get_artifact(artifact.id).content == {"obsolete": field}
    assert _persisted_scene_beats_plan(repository, run.id) == obsolete_plan


def test_startup_recovery_terminates_complete_v1_capacity_plan_without_replay(
    repository,
    brief,
) -> None:
    """A parseable v1 plan is historical evidence, not a v2 dispatch contract."""

    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS],
    )
    repository.start_run(run.id)
    _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    _seal_graph_unit(repository, run.id, all_stage_payloads()[1])
    legacy_plan = _replace_scene_beats_plan_with_complete_v1_capacity_contract(
        repository,
        run.id,
    )
    artifact = repository.add_artifact(
        Artifact(
            run_id=run.id,
            stage=StageName.SCENE_BEATS,
            kind=ArtifactKind.PROMPT,
            content={"legacy": "dialogue_capacity.v1"},
            content_hash=stable_hash({"legacy": "dialogue_capacity.v1"}),
        )
    )

    recovery = repository.reconcile_startup_jobs()

    assert recovery.resubmit_run_ids == []
    assert recovery.terminated_run_ids == [run.id]
    recovered = repository.get_run(run.id)
    assert recovered.status == RunStatus.FAILED
    assert recovered.failure_code == "recovery.scene_timing_contract_obsolete"
    assert recovered.failed_stage == StageName.SCENE_BEATS
    assert _persisted_scene_beats_plan(repository, run.id) == legacy_plan
    assert repository.get_artifact(artifact.id).content == {
        "legacy": "dialogue_capacity.v1"
    }


def test_startup_recovery_does_not_rewrite_terminal_obsolete_scene_timing_history(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS],
    )
    repository.start_run(run.id)
    _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    _seal_graph_unit(repository, run.id, all_stage_payloads()[1])
    legacy_plan = _replace_scene_beats_plan_with_obsolete_contract(repository, run.id)
    repository.finish_run(
        run.id,
        error="historical terminal outcome",
        failure_code="fixture.terminal",
        failed_stage=StageName.SCENE_BEATS,
    )

    recovery = repository.reconcile_startup_jobs()

    assert run.id not in recovery.terminated_run_ids
    terminal = repository.get_run(run.id)
    assert terminal.status == RunStatus.FAILED
    assert terminal.failure_code == "fixture.terminal"
    recovered_plan = next(
        plan
        for plan in repository.list_stage_plans(run.id)
        if plan.stage == StageName.SCENE_BEATS
    )
    assert recovered_plan.model_dump(mode="json", by_alias=False) == legacy_plan


def test_startup_recovery_does_not_rewrite_terminal_obsolete_dialogue_contract_history(
    repository,
    brief,
) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS],
    )
    repository.start_run(run.id)
    _seal_bible_unit(repository, run.id, all_stage_payloads()[0])
    _seal_graph_unit(repository, run.id, all_stage_payloads()[1])
    obsolete_plan = _replace_scene_beats_dialogue_contract_with_obsolete_contract(
        repository,
        run.id,
        field="dialogue_capacity_plan",
        replacement={},
    )
    repository.finish_run(
        run.id,
        error="historical terminal outcome",
        failure_code="fixture.terminal",
        failed_stage=StageName.SCENE_BEATS,
    )

    recovery = repository.reconcile_startup_jobs()

    assert run.id not in recovery.terminated_run_ids
    terminal = repository.get_run(run.id)
    assert terminal.status == RunStatus.FAILED
    assert terminal.failure_code == "fixture.terminal"
    assert _persisted_scene_beats_plan(repository, run.id) == obsolete_plan


def test_startup_recovery_preserves_failed_and_quarantined_unit_meanings(
    repository,
    brief,
) -> None:
    failed_run, failed_unit = _running_bible_unit(repository, brief)
    failed_attempt = repository.allocate_attempt_for_work_unit(failed_unit.id)
    repository.finish_attempt(
        failed_attempt.id,
        AttemptStatus.FAILED,
        error="known provider response failure",
        outcome_code="provider.http_503",
        failure_disposition=WorkUnitFailureDisposition.FAILED,
    )

    quarantined_run, quarantined_unit = _running_bible_unit(repository, brief)
    quarantined_attempt = repository.allocate_attempt_for_work_unit(
        quarantined_unit.id
    )
    repository.mark_attempt_dispatched(quarantined_attempt.id)
    repository.persist_attempt_response(
        quarantined_attempt.id,
        {"choices": [{"message": {"content": "{}"}}]},
    )
    repository.finish_attempt(
        quarantined_attempt.id,
        AttemptStatus.FAILED,
        error="semantic rejection exhausted",
        outcome_code="semantic.fixture_rejected",
        failure_disposition=WorkUnitFailureDisposition.QUARANTINED,
    )

    recovery = repository.reconcile_startup_jobs()

    assert set(recovery.terminated_run_ids) == {failed_run.id, quarantined_run.id}
    recovered_failed = repository.get_run(failed_run.id)
    assert recovered_failed.status == RunStatus.FAILED
    assert recovered_failed.failure_code == "provider.http_503"
    assert recovered_failed.failed_stage == StageName.STORY_BIBLE
    recovered_quarantined = repository.get_run(quarantined_run.id)
    assert recovered_quarantined.status == RunStatus.QUARANTINED
    assert recovered_quarantined.failure_code == "semantic.fixture_rejected"
    assert recovered_quarantined.failed_stage == StageName.STORY_BIBLE


def test_work_unit_migration_terminates_open_legacy_attempts(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacy-work-units.sqlite3'}"
    migrator = SchemaMigrator(database_url)
    configuration = migrator._config()
    command.upgrade(configuration, "0004_v2_project_creation_idempotency")
    engine = create_engine(database_url)
    now = "2026-09-02 12:00:00"
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO v2_projects (id, revision, brief, created_at, updated_at)
                    VALUES ('project-open', 0, '{}', :now, :now),
                           ('project-cancel', 0, '{}', :now, :now)
                    """
                ),
                {"now": now},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_generation_runs
                    (id, project_id, kind, parent_run_id, repair_stage, provider_snapshot,
                     requested_stages, status, canonical_snapshot, instructions,
                     result_revision_ids, error, created_at, started_at, finished_at)
                    VALUES
                    ('run-open', 'project-open', 'pipeline', NULL, NULL, '{}', '["story_bible"]',
                     'running', '{}', NULL, '[]', NULL, :now, :now, NULL),
                    ('run-cancel', 'project-cancel', 'pipeline', NULL, NULL, '{}', '["story_bible"]',
                     'cancel_requested', '{}', NULL, '[]', NULL, :now, :now, NULL)
                    """
                ),
                {"now": now},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_generation_attempts
                    (id, run_id, stage, attempt_number, status, provider, model, error, started_at, finished_at)
                    VALUES
                    ('attempt-open', 'run-open', 'story_bible', 1, 'running', NULL, NULL, NULL, :now, NULL),
                    ('attempt-cancel', 'run-cancel', 'story_bible', 1, 'running', NULL, NULL, NULL, :now, NULL)
                    """
                ),
                {"now": now},
            )

        command.upgrade(configuration, "head")

        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT runs.id, runs.status, runs.finished_at, attempts.status, attempts.error,
                           attempts.finished_at, attempts.dispatched_at, attempts.response_persisted_at,
                           attempts.outcome_unknown
                    FROM v2_generation_runs AS runs
                    JOIN v2_generation_attempts AS attempts ON attempts.run_id = runs.id
                    ORDER BY runs.id
                    """
                )
            ).all()
        assert rows[0] == (
            "run-cancel",
            "cancelled",
            rows[0][2],
            "cancelled",
            "Legacy generation attempt cancelled during work-unit migration",
            rows[0][5],
            None,
            None,
            0,
        )
        assert rows[0][2] is not None and rows[0][5] is not None
        assert rows[1][0] == "run-open"
        assert rows[1][1] == "failed"
        assert rows[1][3] == "failed"
        assert "dispatch state is unknown" in rows[1][4]
        assert rows[1][2] is not None and rows[1][5] is not None
        assert rows[1][6:] == (None, None, 0)
    finally:
        engine.dispose()


def test_startup_recovery_terminates_nonterminal_legacy_media_without_resubmission(repository, brief) -> None:
    project = repository.create_project(brief)
    with repository._write() as session:
        session.add(
            MediaTaskRow(
                id="legacy-media-task",
                project_id=project.id,
                shot_id="historical-shot",
                storyboard_revision=1,
                kind=MediaKind.IMAGE.value,
                status=MediaTaskStatus.RUNNING.value,
                derived_prompt="historical prompt",
                prompt_components={"legacy": True},
                provider="legacy-provider",
                public_settings={},
                provider_task_id="remote-legacy-task",
                output_uri=None,
                error=None,
                created_at=project.created_at,
                updated_at=project.created_at,
                started_at=project.created_at,
                finished_at=None,
            )
        )

    recovery = repository.reconcile_startup_jobs()
    task = repository.get_media_task("legacy-media-task")

    assert recovery.resubmit_media_task_ids == []
    assert recovery.resume_media_poll_task_ids == []
    assert recovery.terminated_media_task_ids == ["legacy-media-task"]
    assert task.status == MediaTaskStatus.FAILED
    assert "production_pipeline_not_ready" in (task.error or "")
