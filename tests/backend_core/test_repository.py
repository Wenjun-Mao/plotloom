from __future__ import annotations

from copy import deepcopy
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
    ContinuityState,
    AttemptStatus,
    MediaKind,
    MediaTask,
    MediaTaskStatus,
    ProviderSettings,
    RunKind,
    RunStatus,
    StageName,
    StageStatus,
    Shot,
    ShotSize,
    StoryBible,
    Storyboard,
)
from plotloom.exceptions import (
    IdempotencyConflictError,
    InvalidTransitionError,
    ProductionPipelineNotReadyError,
    RevisionConflictError,
    SchemaResetRequiredError,
)
from plotloom.persistence import (
    ArtifactRow,
    EntityRevisionRow,
    GenerationRunRow,
    MediaTaskRow,
    ProjectCreationIdempotencyRow,
    SQLiteRepository,
    StageHeadRow,
    stable_hash,
)
from plotloom.validation import DomainValidationError

from .conftest import all_stage_payloads, make_story_graph


def _install_all_manually(repository: SQLiteRepository, project_id: str) -> None:
    for stage, payload in zip(STAGE_ORDER, all_stage_payloads(), strict=True):
        repository.update_stage(project_id, stage, 0, payload)


def _install_historical_v1_media_context(repository: SQLiteRepository, project_id: str) -> Shot:
    """Replace two stored V2 revisions with pre-versioning evidence.

    Media prompt context is intentionally a V1-only internal compatibility
    reader.  This fixture therefore models data that existed before the V2
    authoring cutover instead of using current-stage writes as a bypass.
    """

    bible = StoryBible(logline="历史领航员寻找身份。", premise="历史记忆决定生存。")
    shot = Shot(
        id="historical-shot-1",
        scene_id="historical-scene-1",
        order=1,
        title="历史苏醒",
        shot_size=ShotSize.MEDIUM,
        duration_seconds=8,
        action="领航员在旧记录中醒来。",
        entry_state=ContinuityState(facts={"pose": "lying"}),
        exit_state=ContinuityState(facts={"pose": "sitting"}),
    )
    storyboard = Storyboard(shots=[shot])
    with repository._write() as session:
        for stage, payload in (
            (StageName.STORY_BIBLE, bible),
            (StageName.STORYBOARD, storyboard),
        ):
            head = session.get(StageHeadRow, f"{project_id}:{stage.value}")
            assert head is not None and head.entity_revision_id is not None
            revision = session.get(EntityRevisionRow, head.entity_revision_id)
            assert revision is not None
            serialized = payload.model_dump(mode="json", by_alias=True)
            content_hash = stable_hash(serialized)
            revision.payload = serialized
            revision.schema_version = 1
            revision.content_hash = content_hash
            head.schema_version = 1
            head.content_hash = content_hash
    return shot


def _insert_historical_media_task(
    repository: SQLiteRepository,
    *,
    project_id: str,
    shot_id: str,
) -> MediaTask:
    """Create a frozen pre-ProductionSnapshot task for recovery coverage."""

    task = MediaTask(
        project_id=project_id,
        shot_id=shot_id,
        storyboard_revision=1,
        kind=MediaKind.IMAGE,
        derived_prompt="historical cinematic image",
        prompt_components={},
        provider="openai",
        public_settings={"imageBaseUrl": "https://api.example.test/v1"},
    )
    with repository._write() as session:
        session.add(
            MediaTaskRow(
                id=task.id,
                project_id=task.project_id,
                shot_id=task.shot_id,
                storyboard_revision=task.storyboard_revision,
                kind=task.kind.value,
                status=task.status.value,
                derived_prompt=task.derived_prompt,
                prompt_components=task.prompt_components,
                provider=task.provider,
                public_settings=task.public_settings,
                provider_task_id=None,
                output_uri=None,
                error=None,
                created_at=task.created_at,
                updated_at=task.updated_at,
                started_at=None,
                finished_at=None,
            )
        )
    return task


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


def test_historical_v1_media_context_cannot_reopen_current_media_creation(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    _install_all_manually(repository, project.id)
    shot = _install_historical_v1_media_context(repository, project.id)
    with pytest.raises(SchemaResetRequiredError):
        repository.get_media_prompt_context(project.id, shot.id)


def test_media_repository_boundary_never_looks_up_or_writes_shot_derived_tasks(
    repository: SQLiteRepository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The API hard stop must not be bypassable by an in-process caller."""

    def unexpected_lookup(*_args, **_kwargs):
        raise AssertionError("media creation must stop before project lookup")

    monkeypatch.setattr(repository, "_project_row", unexpected_lookup)

    with pytest.raises(ProductionPipelineNotReadyError):
        repository.create_media_task(
            "unknown-project",
            "unknown-shot",
            MediaKind.IMAGE,
            expected_storyboard_revision=1,
            derived_prompt="must never be persisted",
            prompt_components={"source": "shot"},
        )

    with repository._read() as session:
        assert session.execute(text("SELECT COUNT(*) FROM v2_media_tasks")).scalar_one() == 0


def test_legacy_media_execution_is_hard_stopped_but_can_be_safely_terminalized(
    repository: SQLiteRepository,
    brief,
) -> None:
    project = repository.create_project(brief)
    queued = _insert_historical_media_task(
        repository, project_id=project.id, shot_id="historical-shot"
    )
    with pytest.raises(ProductionPipelineNotReadyError):
        repository.start_media_task(queued.id, provider="legacy-provider")
    assert repository.get_media_task(queued.id).status == MediaTaskStatus.QUEUED

    running = _insert_historical_media_task(
        repository, project_id=project.id, shot_id="historical-running-shot"
    )
    with repository._write() as session:
        row = session.get(MediaTaskRow, running.id)
        assert row is not None
        row.status = MediaTaskStatus.RUNNING.value
        row.started_at = running.created_at

    with pytest.raises(ProductionPipelineNotReadyError):
        repository.record_media_submission(
            running.id,
            provider="legacy-provider",
            provider_task_id="must-not-persist",
        )
    with pytest.raises(ProductionPipelineNotReadyError):
        repository.finish_media_task(
            running.id,
            MediaTaskStatus.SUCCEEDED,
            output_uri="https://example.test/forbidden.png",
        )
    assert repository.get_media_task(running.id).provider_task_id is None

    failed = repository.finish_media_task(
        running.id,
        MediaTaskStatus.FAILED,
        error="upgrade recovery stopped legacy execution",
    )
    assert failed.status == MediaTaskStatus.FAILED
    assert failed.output_uri is None

    cancellable = _insert_historical_media_task(
        repository, project_id=project.id, shot_id="historical-cancellable-shot"
    )
    with repository._write() as session:
        row = session.get(MediaTaskRow, cancellable.id)
        assert row is not None
        row.status = MediaTaskStatus.RUNNING.value
        row.started_at = cancellable.created_at
    cancelled = repository.finish_media_task(cancellable.id, MediaTaskStatus.CANCELLED)
    assert cancelled.status == MediaTaskStatus.CANCELLED


def test_archived_project_rejects_gate_writes_but_keeps_receipts_readable(
    repository: SQLiteRepository,
    brief,
) -> None:
    project = repository.create_project(brief)
    _install_all_manually(repository, project.id)
    head = repository.get_stage_head(project.id, StageName.STORYBOARD)
    assert head.entity_revision_id is not None
    receipt = repository.get_gate_evaluation(head.entity_revision_id, "storyboard.v2")

    repository.archive_project(project.id, expected_lifecycle_revision=1)

    with pytest.raises(InvalidTransitionError, match="archived projects are read-only"):
        repository.record_gate_evaluation(project.id, head.entity_revision_id, receipt)
    assert repository.get_gate_evaluation(head.entity_revision_id, "storyboard.v2") == receipt


def test_historical_run_snapshot_without_schema_version_reads_frozen_v1_payload(
    repository: SQLiteRepository,
    brief,
) -> None:
    """A missing snapshot schemaVersion is immutable V1 evidence, not a V2 default."""

    project = repository.create_project(brief)
    _install_all_manually(repository, project.id)
    _install_historical_v1_media_context(repository, project.id)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])

    with repository._write() as session:
        row = session.get(GenerationRunRow, run.id)
        assert row is not None
        frozen_snapshot = deepcopy(row.canonical_snapshot)
        for head in frozen_snapshot["stage_heads"].values():
            head.pop("schema_version", None)
        row.canonical_snapshot = frozen_snapshot

    historical = repository.get_snapshot_stage_payload(run.id, StageName.STORY_BIBLE)
    assert isinstance(historical, StoryBible)
    assert historical.logline == "历史领航员寻找身份。"
    assert historical.premise == "历史记忆决定生存。"
    with repository._read() as session:
        row = session.get(GenerationRunRow, run.id)
        assert row is not None
        assert all("schema_version" not in head for head in row.canonical_snapshot["stage_heads"].values())


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
    historical_shot_id = "historical-shot-for-recovery"
    queued_media = _insert_historical_media_task(
        repository, project_id=project.id, shot_id=historical_shot_id
    )
    polling_media = _insert_historical_media_task(
        repository, project_id=project.id, shot_id=historical_shot_id
    )
    ambiguous_media = _insert_historical_media_task(
        repository, project_id=project.id, shot_id=historical_shot_id
    )
    # These are pre-M2 persisted rows, not calls through the now-closed
    # execution API.  Recovery must terminalize both a submitted and an
    # ambiguous historical task without polling or resubmitting either one.
    with repository._write() as session:
        polling_row = session.get(MediaTaskRow, polling_media.id)
        ambiguous_row = session.get(MediaTaskRow, ambiguous_media.id)
        assert polling_row is not None and ambiguous_row is not None
        polling_row.status = MediaTaskStatus.RUNNING.value
        polling_row.provider_task_id = "provider-task-recovery"
        polling_row.started_at = polling_media.created_at
        ambiguous_row.status = MediaTaskStatus.RUNNING.value
        ambiguous_row.started_at = ambiguous_media.created_at

    plan = repository.reconcile_startup_jobs()

    assert plan.resubmit_run_ids == [queued.id]
    assert plan.resubmit_media_task_ids == []
    assert plan.resume_media_poll_task_ids == []
    assert set(plan.terminated_run_ids) == {
        running.id,
        cancelling.id,
    }
    assert set(plan.terminated_media_task_ids) == {
        queued_media.id,
        polling_media.id,
        ambiguous_media.id,
    }

    recovered_running = repository.get_run(running.id)
    assert recovered_running.status == RunStatus.FAILED
    assert recovered_running.failure_code == "recovery.legacy_interrupted"
    assert recovered_running.failed_stage == StageName.STORY_BIBLE
    assert repository.get_run(cancelling.id).status == RunStatus.CANCELLED
    attempts = {
        attempt.id: attempt
        for run_id in (running.id, cancelling.id)
        for attempt in repository.get_run_trace(run_id).attempts
    }
    assert attempts[running_attempt.id].status == AttemptStatus.FAILED
    assert attempts[cancelling_attempt.id].status == AttemptStatus.CANCELLED
    assert all(attempt.finished_at is not None for attempt in attempts.values())

    for task_id in (queued_media.id, polling_media.id, ambiguous_media.id):
        failed_media = repository.get_media_task(task_id)
        assert failed_media.status == MediaTaskStatus.FAILED
        assert "production_pipeline_not_ready" in (failed_media.error or "")


def test_file_sqlite_uses_alembic_foreign_keys_and_wal(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "v2.sqlite3"
    repository = SQLiteRepository(f"sqlite:///{database_path}")
    try:
        with repository.engine.connect() as connection:
            assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
            assert connection.execute(text("PRAGMA journal_mode")).scalar_one().lower() == "wal"
            assert (
                connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                    == "0010_v2_schema_approvals"
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
