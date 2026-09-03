from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue
from threading import Barrier

import pytest
from sqlalchemy import event, text

from plotloom.domain import (
    STAGE_ORDER,
    Artifact,
    ArtifactKind,
    AttemptStatus,
    MediaKind,
    MediaTaskStatus,
    ProviderSettings,
    RunKind,
    RunStatus,
    StageName,
    StageStatus,
)
from plotloom.exceptions import (
    IdempotencyConflictError,
    InvalidTransitionError,
    RevisionConflictError,
)
from plotloom.persistence import (
    ArtifactRow,
    ProjectCreationIdempotencyRow,
    SQLiteRepository,
    stable_hash,
)
from plotloom.validation import DomainValidationError

from .conftest import all_stage_payloads, make_story_graph


def _install_all_manually(repository: SQLiteRepository, project_id: str) -> None:
    for stage, payload in zip(STAGE_ORDER, all_stage_payloads(), strict=True):
        repository.update_stage(project_id, stage, 0, payload)


def test_project_and_stage_revision_conflicts(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    assert [head.status for head in repository.list_stage_heads(project.id)] == [StageStatus.MISSING] * 4
    with pytest.raises(RevisionConflictError):
        repository.update_project(project.id, 99, brief)
    bible = all_stage_payloads()[0]
    head = repository.update_stage(project.id, StageName.STORY_BIBLE, 0, bible)
    assert head.revision == 1
    assert repository.update_stage(project.id, StageName.STORY_BIBLE, 1, bible).revision == 1
    with pytest.raises(RevisionConflictError):
        repository.update_stage(project.id, StageName.STORY_BIBLE, 0, bible)


def test_stage_change_marks_existing_downstream_stale(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    _install_all_manually(repository, project.id)
    bible = all_stage_payloads()[0].model_copy(update={"themes": ["身份"]})
    repository.update_stage(project.id, StageName.STORY_BIBLE, 1, bible)
    heads = {head.stage: head for head in repository.list_stage_heads(project.id)}
    assert heads[StageName.STORY_BIBLE].status == StageStatus.READY
    assert all(heads[stage].status == StageStatus.STALE for stage in STAGE_ORDER[1:])


def test_atomic_four_stage_run_installs_and_succeeds(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, STAGE_ORDER)
    repository.start_run(run.id)
    payloads = dict(zip(STAGE_ORDER, all_stage_payloads(), strict=True))
    heads = repository.install_generated_stages(run.id, payloads)
    completed = repository.finish_run(run.id)
    assert [head.stage for head in heads] == list(STAGE_ORDER)
    assert all(head.status == StageStatus.READY for head in repository.list_stage_heads(project.id))
    assert completed.status == RunStatus.SUCCEEDED
    assert len(completed.result_revision_ids) == 4
    trace = repository.get_run_trace(run.id)
    canonical = [
        artifact
        for artifact in trace.artifacts
        if artifact.kind == ArtifactKind.CANONICAL
    ]
    assert trace.snapshot_is_current is True
    assert len(canonical) == 4
    assert {artifact.stage for artifact in canonical} == set(STAGE_ORDER)
    assert {
        artifact.content["entityRevisionId"] for artifact in canonical
    } == set(completed.result_revision_ids)


def test_canonical_artifact_insert_failure_rolls_back_entire_commit(
    repository: SQLiteRepository,
    brief,
) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, STAGE_ORDER)
    repository.start_run(run.id)

    def fail_canonical_insert(_mapper, _connection, row) -> None:
        if row.run_id == run.id and row.kind == ArtifactKind.CANONICAL.value:
            raise RuntimeError("injected canonical artifact failure")

    event.listen(ArtifactRow, "before_insert", fail_canonical_insert)
    try:
        with pytest.raises(RuntimeError, match="injected canonical artifact failure"):
            repository.commit_run_outputs(
                run.id,
                dict(zip(STAGE_ORDER, all_stage_payloads(), strict=True)),
            )
    finally:
        event.remove(ArtifactRow, "before_insert", fail_canonical_insert)

    reloaded = repository.get_run(run.id)
    assert reloaded.status == RunStatus.RUNNING
    assert reloaded.result_revision_ids == []
    assert all(
        head.status == StageStatus.MISSING
        for head in repository.list_stage_heads(project.id)
    )
    assert repository.get_run_trace(run.id).artifacts == []


def test_project_bootstrap_rolls_back_everything_when_a_later_stage_is_invalid(
    repository: SQLiteRepository,
    brief,
) -> None:
    bible, graph, *_ = all_stage_payloads()
    invalid_graph = graph.model_copy(update={"edges": []})

    with pytest.raises(DomainValidationError):
        repository.create_project(
            brief,
            initial_stages=[
                {"stage": StageName.STORY_BIBLE, "payload": bible.model_dump(mode="json")},
                {"stage": StageName.STORY_GRAPH, "payload": invalid_graph.model_dump(mode="json")},
            ],
        )

    with repository.engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM v2_projects")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM v2_stage_heads")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM v2_entity_revisions")).scalar_one() == 0


def test_project_bootstrap_persistence_failure_rolls_back_project_stages_and_key(
    repository: SQLiteRepository,
    brief,
) -> None:
    bible = all_stage_payloads()[0]

    def fail_idempotency_insert(_mapper, _connection, row) -> None:
        if row.idempotency_key == "rollback-key":
            raise RuntimeError("injected idempotency persistence failure")

    event.listen(ProjectCreationIdempotencyRow, "before_insert", fail_idempotency_insert)
    try:
        with pytest.raises(RuntimeError, match="injected idempotency persistence failure"):
            repository.create_project(
                brief,
                initial_stages=[
                    {"stage": StageName.STORY_BIBLE, "payload": bible.model_dump(mode="json")}
                ],
                idempotency_key="rollback-key",
            )
    finally:
        event.remove(ProjectCreationIdempotencyRow, "before_insert", fail_idempotency_insert)

    with repository.engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM v2_projects")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM v2_stage_heads")).scalar_one() == 0
        assert connection.execute(text("SELECT COUNT(*) FROM v2_entity_revisions")).scalar_one() == 0
        assert (
            connection.execute(text("SELECT COUNT(*) FROM v2_project_creation_idempotency")).scalar_one()
            == 0
        )


def test_idempotent_bootstrap_converges_across_repository_instances(tmp_path: Path, brief) -> None:
    database_url = f"sqlite:///{tmp_path / 'concurrent-bootstrap.sqlite3'}"
    first = SQLiteRepository(database_url)
    second = SQLiteRepository(database_url, create_schema=False)
    barrier = Barrier(2)

    def create(repository: SQLiteRepository):
        barrier.wait()
        return repository.create_project(brief, idempotency_key="cross-instance-key")

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            created = list(executor.map(create, (first, second)))

        assert created[0].id == created[1].id
        assert created[0].stages == created[1].stages
        with first.engine.connect() as connection:
            assert connection.execute(text("SELECT COUNT(*) FROM v2_projects")).scalar_one() == 1
            assert (
                connection.execute(text("SELECT COUNT(*) FROM v2_project_creation_idempotency")).scalar_one()
                == 1
            )
        with pytest.raises(IdempotencyConflictError):
            second.create_project(
                brief.model_copy(update={"title": "changed retry"}),
                idempotency_key="cross-instance-key",
            )
    finally:
        first.close()
        second.close()


def test_idempotent_replay_waits_for_held_writer_then_converges_or_conflicts(
    tmp_path: Path,
    brief,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'held-writer-bootstrap.sqlite3'}"
    holder = SQLiteRepository(database_url)
    requester = SQLiteRepository(database_url, create_schema=False, sqlite_busy_timeout_ms=1_000)
    created = holder.create_project(brief, idempotency_key="held-writer-key")
    begin_attempts: Queue[None] = Queue()

    def observe_begin(_connection, _cursor, statement, _parameters, _context, _executemany) -> None:
        if statement == "BEGIN IMMEDIATE":
            begin_attempts.put(None)

    event.listen(requester.engine, "before_cursor_execute", observe_begin)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            with holder._bootstrap_write():
                replay = executor.submit(
                    requester.create_project,
                    brief,
                    idempotency_key="held-writer-key",
                )
                begin_attempts.get(timeout=1)
                assert not replay.done()
            assert replay.result(timeout=1) == created

            with holder._bootstrap_write():
                conflict = executor.submit(
                    requester.create_project,
                    brief.model_copy(update={"title": "changed while waiting"}),
                    idempotency_key="held-writer-key",
                )
                begin_attempts.get(timeout=1)
                assert not conflict.done()
            with pytest.raises(IdempotencyConflictError):
                conflict.result(timeout=1)
    finally:
        event.remove(requester.engine, "before_cursor_execute", observe_begin)
        holder.close()
        requester.close()


@pytest.mark.parametrize(
    "provider_snapshot",
    [
        {"apiKey": "must-not-persist"},
        {"temperature": 0.2},
        {"textModel": "Bearer must-not-persist"},
        {"textModel": "sk-must-not-persist"},
        {"textBaseUrl": "https://user:password@example.test/v1"},
        {"textBaseUrl": "https://example.test/v1?api_key=must-not-persist"},
        {"textModel": "https://example.test/models?access_token=must-not-persist"},
    ],
)
def test_repository_rejects_non_public_provider_snapshots(
    repository: SQLiteRepository,
    brief,
    provider_snapshot,
) -> None:
    project = repository.create_project(brief)

    with pytest.raises(ValueError):
        repository.create_run(
            project.id,
            RunKind.PIPELINE,
            [StageName.STORY_BIBLE],
            provider_snapshot=provider_snapshot,
        )

    assert repository.list_project_runs(project.id) == []


def test_cancel_after_atomic_install_preserves_committed_success(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, STAGE_ORDER)
    repository.start_run(run.id)
    repository.install_generated_stages(
        run.id,
        dict(zip(STAGE_ORDER, all_stage_payloads(), strict=True)),
    )
    assert repository.cancel_run(run.id).status == RunStatus.SUCCEEDED


def test_concurrent_project_edit_quarantines_without_partial_install(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, STAGE_ORDER)
    repository.start_run(run.id)
    changed_brief = brief.model_copy(update={"synopsis": f"{brief.synopsis} 新线索。"})
    repository.update_project(project.id, project.revision, changed_brief)
    with pytest.raises(RevisionConflictError) as captured:
        repository.install_generated_stages(
            run.id,
            dict(zip(STAGE_ORDER, all_stage_payloads(), strict=True)),
        )
    completed = repository.finish_run(run.id, quarantine_reason=str(captured.value))
    assert completed.status == RunStatus.QUARANTINED
    assert all(head.status == StageStatus.MISSING for head in repository.list_stage_heads(project.id))


def test_unrequested_downstream_edit_does_not_quarantine_upstream_run(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    _install_all_manually(repository, project.id)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(run.id)

    user_graph = make_story_graph()
    user_graph.nodes[2].summary = "用户在运行期间重写了控制室线索。"
    repository.update_stage(project.id, StageName.STORY_GRAPH, 1, user_graph)

    candidate_bible = all_stage_payloads()[0].model_copy(update={"themes": ["生成的新主题"]})
    completed = repository.commit_run_outputs(run.id, {StageName.STORY_BIBLE: candidate_bible})
    heads = {head.stage: head for head in repository.list_stage_heads(project.id)}
    assert completed.status == RunStatus.SUCCEEDED
    assert heads[StageName.STORY_BIBLE].revision == 2
    assert heads[StageName.STORY_GRAPH].revision == 2
    assert heads[StageName.STORY_GRAPH].status == StageStatus.STALE
    stored_graph = repository.get_stage_payload(project.id, StageName.STORY_GRAPH)
    assert stored_graph.nodes[2].summary == user_graph.nodes[2].summary
    assert repository.get_run_trace(run.id).snapshot_is_current is True


def test_snapshot_freezes_brief_and_reads_upstream_by_revision(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    original_bible = all_stage_payloads()[0]
    repository.update_stage(project.id, StageName.STORY_BIBLE, 0, original_bible)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_GRAPH])
    changed_bible = original_bible.model_copy(update={"themes": ["后来修改"]})
    repository.update_stage(project.id, StageName.STORY_BIBLE, 1, changed_bible)
    frozen = repository.get_snapshot_stage_payload(run.id, StageName.STORY_BIBLE)
    assert run.canonical_snapshot.brief == brief
    assert frozen.themes == []
    assert repository.get_stage_payload(project.id, StageName.STORY_BIBLE).themes == ["后来修改"]


def test_media_task_persists_compiled_prompt_trace(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    _install_all_manually(repository, project.id)
    shot_id = all_stage_payloads()[3].shots[0].id
    context = repository.get_media_prompt_context(project.id, shot_id)
    assert context.story_bible.logline
    assert context.shot.entry_state == all_stage_payloads()[3].shots[0].entry_state
    task = repository.create_media_task(
        project.id,
        shot_id,
        MediaKind.IMAGE,
        expected_storyboard_revision=context.storyboard_revision,
        derived_prompt="medium shot; clear spatial relationship",
        prompt_components={"shotSize": "medium", "visualIntent": "clear spatial relationship"},
    )
    stored = repository.get_media_task(task.id)
    assert stored.derived_prompt == task.derived_prompt
    assert stored.prompt_components["shotSize"] == "medium"


def test_provider_settings_are_public_and_revisioned(repository: SQLiteRepository) -> None:
    assert repository.get_provider_settings().revision == 0
    saved = repository.put_provider_settings(ProviderSettings(text_provider="openai", text_model="gpt-x"))
    assert saved.revision == 1
    assert repository.put_provider_settings(saved).revision == 1


def test_startup_reconciliation_resubmits_only_safe_jobs_and_closes_interrupted_work(
    repository: SQLiteRepository,
    brief,
) -> None:
    project = repository.create_project(brief)
    queued = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
    )
    with pytest.raises(InvalidTransitionError):
        repository.create_attempt(queued.id, StageName.STORY_BIBLE)
    running = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
    )
    repository.start_run(running.id)
    running_attempt = repository.create_attempt(running.id, StageName.STORY_BIBLE)
    cancelling = repository.create_run(
        project.id,
        RunKind.PIPELINE,
        [StageName.STORY_BIBLE],
    )
    repository.start_run(cancelling.id)
    cancelling_attempt = repository.create_attempt(cancelling.id, StageName.STORY_BIBLE)
    repository.cancel_run(cancelling.id)
    _install_all_manually(repository, project.id)
    storyboard = all_stage_payloads()[-1]
    shot_id = storyboard.shots[0].id
    context = repository.get_media_prompt_context(project.id, shot_id)

    def media_task():
        return repository.create_media_task(
            project.id,
            shot_id,
            MediaKind.IMAGE,
            expected_storyboard_revision=context.storyboard_revision,
            derived_prompt="stable cinematic image",
            prompt_components={},
            provider="openai",
            public_settings={"imageBaseUrl": "https://api.example.test/v1"},
        )

    queued_media = media_task()
    polling_media = media_task()
    repository.start_media_task(polling_media.id, provider="openai")
    repository.record_media_submission(
        polling_media.id,
        provider="openai",
        provider_task_id="provider-task-recovery",
    )
    ambiguous_media = media_task()
    repository.start_media_task(ambiguous_media.id, provider="openai")

    plan = repository.reconcile_startup_jobs()

    assert plan.resubmit_run_ids == [queued.id]
    assert plan.resubmit_media_task_ids == [queued_media.id]
    assert plan.resume_media_poll_task_ids == [polling_media.id]
    assert set(plan.terminated_run_ids) == {
        running.id,
        cancelling.id,
    }
    assert plan.terminated_media_task_ids == [ambiguous_media.id]

    assert repository.get_run(running.id).status == RunStatus.FAILED
    assert repository.get_run(cancelling.id).status == RunStatus.CANCELLED
    attempts = {
        attempt.id: attempt
        for run_id in (running.id, cancelling.id)
        for attempt in repository.get_run_trace(run_id).attempts
    }
    assert attempts[running_attempt.id].status == AttemptStatus.FAILED
    assert attempts[cancelling_attempt.id].status == AttemptStatus.CANCELLED
    assert all(attempt.finished_at is not None for attempt in attempts.values())

    assert repository.get_media_task(polling_media.id).status == MediaTaskStatus.RUNNING
    failed_media = repository.get_media_task(ambiguous_media.id)
    assert failed_media.status == MediaTaskStatus.FAILED
    assert "duplicate billing" in failed_media.error


def test_file_sqlite_uses_alembic_foreign_keys_and_wal(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "v2.sqlite3"
    repository = SQLiteRepository(f"sqlite:///{database_path}")
    try:
        with repository.engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert connection.execute(text("PRAGMA journal_mode")).scalar_one().lower() == "wal"
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                == "0005_v2_generation_work_units"
            )
    finally:
        repository.close()


def test_repair_run_persists_explicit_quarantine_lineage(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    source = repository.create_run(project.id, RunKind.PIPELINE, STAGE_ORDER[:2])
    repository.start_run(source.id)
    attempt = repository.create_attempt(source.id, StageName.STORY_GRAPH)
    repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error="invalid graph")
    response = {"rawResponse": "{}"}
    validation = {"accepted": False, "issues": [{"code": "missing", "message": "missing graph"}]}
    bible_candidate = all_stage_payloads()[0].model_dump(mode="json", by_alias=False)
    repository.add_artifact(
        Artifact(
            run_id=source.id,
            stage=StageName.STORY_BIBLE,
            kind=ArtifactKind.CANDIDATE,
            content=bible_candidate,
            content_hash=stable_hash(bible_candidate),
        )
    )
    repository.add_artifact(
        Artifact(
            run_id=source.id,
            attempt_id=attempt.id,
            stage=StageName.STORY_GRAPH,
            kind=ArtifactKind.RESPONSE,
            content=response,
            content_hash=stable_hash(response),
        )
    )
    repository.add_artifact(
        Artifact(
            run_id=source.id,
            attempt_id=attempt.id,
            stage=StageName.STORY_GRAPH,
            kind=ArtifactKind.VALIDATION,
            content=validation,
            content_hash=stable_hash(validation),
        )
    )
    source = repository.finish_run(source.id, quarantine_reason="invalid graph candidate")
    with pytest.raises(ValueError):
        repository.create_repair_run(
            source.id,
            stage=StageName.STORY_GRAPH,
            provider_snapshot={"textApiKey": "must-not-persist"},
        )
    repair = repository.create_repair_run(
        source.id,
        stage=StageName.STORY_GRAPH,
        instructions="只修复拓扑",
    )
    reloaded = repository.get_run(repair.id)
    assert reloaded.kind == RunKind.REPAIR
    assert reloaded.parent_run_id == source.id
    assert reloaded.repair_stage == StageName.STORY_GRAPH
    assert reloaded.repair_source is not None
    assert reloaded.repair_source.failed_attempt_id == attempt.id
    assert set(reloaded.repair_source.reused_candidate_artifact_ids) == {
        StageName.STORY_BIBLE
    }
    # Valid upstream candidates are replayed into the explicit child run so a
    # first-generation failure can still commit atomically after repair.
    assert reloaded.requested_stages == list(STAGE_ORDER[:2])
    with pytest.raises(InvalidTransitionError):
        repository.create_repair_run(source.id, stage=StageName.STORYBOARD)


def test_non_quarantined_run_cannot_be_repaired(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    queued = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    with pytest.raises(InvalidTransitionError):
        repository.create_repair_run(queued.id)


def test_run_request_rejects_disjoint_stage_ranges(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    with pytest.raises(InvalidTransitionError, match="contiguous canonical range"):
        repository.create_run(
            project.id,
            RunKind.PIPELINE,
            [StageName.STORY_BIBLE, StageName.STORYBOARD],
        )


def test_quarantine_without_rejected_model_evidence_requires_rebuild(
    repository: SQLiteRepository,
    brief,
) -> None:
    project = repository.create_project(brief)
    source = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(source.id)
    repository.finish_run(source.id, quarantine_reason="prerequisite changed")

    with pytest.raises(InvalidTransitionError, match="start a rebuild instead"):
        repository.create_repair_run(source.id)


def test_repair_rejects_source_snapshot_after_manual_canonical_edit(
    repository: SQLiteRepository,
    brief,
) -> None:
    project = repository.create_project(brief)
    source = repository.create_run(project.id, RunKind.PIPELINE, list(STAGE_ORDER[:2]))
    repository.start_run(source.id)
    attempt = repository.create_attempt(source.id, StageName.STORY_GRAPH)
    repository.finish_attempt(attempt.id, AttemptStatus.FAILED, error="invalid graph")
    response = {"rawResponse": "{}"}
    validation = {"accepted": False, "issues": []}
    for kind, content in (
        (ArtifactKind.RESPONSE, response),
        (ArtifactKind.VALIDATION, validation),
    ):
        repository.add_artifact(
            Artifact(
                run_id=source.id,
                attempt_id=attempt.id,
                stage=StageName.STORY_GRAPH,
                kind=kind,
                content=content,
                content_hash=stable_hash(content),
            )
        )
    repository.finish_run(source.id, quarantine_reason="invalid graph candidate")
    repository.update_stage(project.id, StageName.STORY_BIBLE, 0, all_stage_payloads()[0])

    with pytest.raises(InvalidTransitionError, match="inputs changed after quarantine"):
        repository.create_repair_run(source.id, stage=StageName.STORY_GRAPH)
