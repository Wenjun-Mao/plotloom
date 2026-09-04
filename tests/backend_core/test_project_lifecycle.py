from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from plotloom.api import create_app
from plotloom.domain import MediaKind, MediaTask, MediaTaskStatus, RunKind, StageName, StageStatus
from plotloom.exceptions import InvalidTransitionError, NotFoundError, ProjectBusyError, RevisionConflictError
from plotloom.persistence import MediaTaskRow, SQLiteRepository, StageHeadRow

from .conftest import all_stage_payloads


def _create_project(client: TestClient, brief, *, initial_stage_count: int = 0) -> dict:
    payloads = all_stage_payloads()
    response = client.post(
        "/api/v2/projects",
        json={
            "brief": brief.model_dump(mode="json", by_alias=True),
            "initialStages": [
                {
                    "stage": stage.value,
                    "payload": payload.model_dump(mode="json", by_alias=True),
                }
                for stage, payload in zip(
                    (StageName.STORY_BIBLE, StageName.STORY_GRAPH, StageName.SCENE_BEATS, StageName.STORYBOARD)[
                        :initial_stage_count
                    ],
                    payloads[:initial_stage_count],
                    strict=True,
                )
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_archive_restore_and_archived_write_guards(repository: SQLiteRepository, brief) -> None:
    client = TestClient(create_app(repository))
    project = _create_project(client, brief, initial_stage_count=1)

    archived = client.post(
        f"/api/v2/projects/{project['id']}/archive",
        json={"expectedLifecycleRevision": 1},
    )
    assert archived.status_code == 200
    assert archived.json()["lifecycleStatus"] == "archived"
    assert archived.json()["lifecycleRevision"] == 2
    assert archived.json()["archivedAt"] is not None
    assert client.get(f"/api/v2/projects/{project['id']}").status_code == 200

    assert client.patch(
        f"/api/v2/projects/{project['id']}",
        json={"expectedRevision": 1, "brief": project["brief"]},
    ).json()["code"] == "invalid_transition"
    assert client.patch(
        f"/api/v2/projects/{project['id']}/stages/story_bible",
        json={"expectedRevision": 1, "payload": all_stage_payloads()[0].model_dump(mode="json", by_alias=True)},
    ).json()["code"] == "invalid_transition"
    assert client.post(
        f"/api/v2/projects/{project['id']}/pipeline-runs", json={"stages": ["story_bible"]}
    ).json()["code"] == "invalid_transition"

    conflict = client.post(
        f"/api/v2/projects/{project['id']}/restore",
        json={"expectedLifecycleRevision": 1},
    )
    assert conflict.status_code == 409
    assert conflict.json()["resource"] == "project-lifecycle"
    restored = client.post(
        f"/api/v2/projects/{project['id']}/restore",
        json={"expectedLifecycleRevision": 2},
    )
    assert restored.status_code == 200
    assert restored.json()["lifecycleStatus"] == "active"
    assert restored.json()["lifecycleRevision"] == 3
    assert restored.json()["archivedAt"] is None


def test_project_listing_paginates_by_immutable_created_at_then_id(repository: SQLiteRepository, brief) -> None:
    client = TestClient(create_app(repository))
    first = _create_project(client, brief)
    second = _create_project(client, brief)
    third = _create_project(client, brief)

    page_one = client.get("/api/v2/projects", params={"status": "all", "limit": 2})
    assert page_one.status_code == 200
    body = page_one.json()
    assert [project["id"] for project in body["projects"]] == [third["id"], second["id"]]
    assert body["nextCursor"]
    assert all(set(project["stageStatuses"]) == {stage.value for stage in StageName} for project in body["projects"])
    assert all(project["latestRun"] is None for project in body["projects"])

    updated_brief = {**first["brief"], "title": "已更新的首个项目"}
    updated = client.patch(
        f"/api/v2/projects/{first['id']}",
        json={"expectedRevision": 1, "brief": updated_brief},
    )
    assert updated.status_code == 200

    page_two = client.get(
        "/api/v2/projects",
        params={"status": "all", "limit": 2, "cursor": body["nextCursor"]},
    )
    assert page_two.status_code == 200
    assert [project["id"] for project in page_two.json()["projects"]] == [first["id"]]
    assert page_two.json()["nextCursor"] is None


def test_lifecycle_revision_is_atomic_across_repository_instances(tmp_path, brief) -> None:
    database_url = f"sqlite:///{tmp_path / 'lifecycle-concurrency.sqlite3'}"
    first = SQLiteRepository(database_url, sqlite_busy_timeout_ms=5_000)
    second = SQLiteRepository(database_url, create_schema=False, sqlite_busy_timeout_ms=5_000)
    project = first.create_project(brief)
    barrier = Barrier(2)

    def archive(repository: SQLiteRepository):
        barrier.wait(timeout=5)
        return repository.archive_project(project.id, 1)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(archive, repository) for repository in (first, second)]
            outcomes = []
            for future in futures:
                try:
                    outcomes.append(future.result(timeout=10))
                except RevisionConflictError as error:
                    outcomes.append(error)

        assert sum(not isinstance(outcome, RevisionConflictError) for outcome in outcomes) == 1
        assert sum(isinstance(outcome, RevisionConflictError) for outcome in outcomes) == 1
        assert first.get_project(project.id).lifecycle_revision == 2
    finally:
        first.close()
        second.close()


def test_duplicate_copies_only_ready_prefix_and_replays_idempotently(
    repository: SQLiteRepository, brief
) -> None:
    client = TestClient(create_app(repository))
    source = _create_project(client, brief, initial_stage_count=2)
    body = {"expectedLifecycleRevision": source["lifecycleRevision"], "title": "复制后的项目"}
    headers = {"Idempotency-Key": "duplicate-prefix-001"}

    created = client.post(f"/api/v2/projects/{source['id']}/duplicate", json=body, headers=headers)
    assert created.status_code == 200
    result = created.json()
    assert result["project"]["id"] != source["id"]
    assert result["project"]["brief"]["title"] == "复制后的项目"
    assert result["copiedThrough"] == "story_graph"
    assert result["omittedStages"] == ["scene_beats", "storyboard"]
    assert [stage["head"]["status"] for stage in result["project"]["stages"]] == [
        "ready",
        "ready",
        "missing",
        "missing",
    ]

    replay = client.post(f"/api/v2/projects/{source['id']}/duplicate", json=body, headers=headers)
    assert replay.status_code == 200
    assert replay.json() == result
    conflict = client.post(
        f"/api/v2/projects/{source['id']}/duplicate",
        json={**body, "title": "不同的副本"},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_duplicate_stops_at_a_nonready_gap_even_if_later_stages_are_ready(
    repository: SQLiteRepository, brief
) -> None:
    client = TestClient(create_app(repository))
    source = _create_project(client, brief, initial_stage_count=4)
    with repository._write() as session:
        graph = session.scalar(
            select(StageHeadRow).where(
                StageHeadRow.project_id == source["id"],
                StageHeadRow.stage == StageName.STORY_GRAPH.value,
            )
        )
        assert graph is not None
        graph.status = StageStatus.STALE.value

    duplicate = client.post(
        f"/api/v2/projects/{source['id']}/duplicate",
        json={"expectedLifecycleRevision": source["lifecycleRevision"]},
    )
    assert duplicate.status_code == 200
    result = duplicate.json()
    assert result["copiedThrough"] == "story_bible"
    assert result["omittedStages"] == ["story_graph", "scene_beats", "storyboard"]
    assert [stage["head"]["status"] for stage in result["project"]["stages"]] == [
        "ready",
        "missing",
        "missing",
        "missing",
    ]


def test_permanent_delete_requires_archived_terminal_project(repository: SQLiteRepository, brief) -> None:
    client = TestClient(create_app(repository))
    project = repository.create_project(brief)
    with pytest.raises(InvalidTransitionError, match="only archived"):
        repository.permanent_delete_project(project.id, 1, brief.title)

    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    with pytest.raises(ProjectBusyError):
        repository.archive_project(project.id, 1)
    busy = client.post(
        f"/api/v2/projects/{project.id}/archive",
        json={"expectedLifecycleRevision": 1},
    )
    assert busy.status_code == 409
    assert busy.json()["code"] == "project_busy"

    repository.cancel_run(run.id)
    archived = repository.archive_project(project.id, 1)
    assert archived.lifecycle_status.value == "archived"
    deleted = client.post(
        f"/api/v2/projects/{project.id}/permanent-delete",
        json={"expectedLifecycleRevision": 2, "confirmationTitle": brief.title},
    )
    assert deleted.status_code == 204
    with pytest.raises(NotFoundError):
        repository.get_project(project.id)


def test_busy_guard_includes_nonterminal_work_units(repository: SQLiteRepository, brief) -> None:
    project = repository.create_project(brief)
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    repository.start_run(run.id)
    repository.get_or_create_stage_plan(run.id, StageName.STORY_BIBLE)
    repository.finish_run(run.id, error="worker stopped after planning")

    assert repository.get_run(run.id).status.value == "failed"
    assert repository.list_generation_work_units(run.id)[0].status.value == "queued"
    with pytest.raises(ProjectBusyError):
        repository.archive_project(project.id, 1)


def test_permanent_delete_never_unlinks_an_opaque_media_output_uri(
    repository: SQLiteRepository, brief, tmp_path
) -> None:
    payloads = all_stage_payloads()
    project = repository.create_project(
        brief,
        initial_stages=[
            {"stage": stage, "payload": payload.model_dump(mode="json", by_alias=True)}
            for stage, payload in zip(StageName, payloads, strict=True)
        ],
    )
    opaque_output = tmp_path / "provider-owned-output.png"
    opaque_output.write_bytes(b"provider-owned-output")
    # A terminal historical row must not cause permanent deletion to touch a
    # provider-owned URI. Current V2 media creation is hard-stopped pending a
    # ProductionSnapshot, so this is deliberately not created through it.
    task = MediaTask(
        project_id=project.id, shot_id=payloads[-1].shots[0].id,
        storyboard_revision=1, kind=MediaKind.IMAGE,
        derived_prompt="A provider-owned result", prompt_components={},
    ).model_copy(update={
        "status": MediaTaskStatus.SUCCEEDED,
        "output_uri": opaque_output.as_uri(),
    })
    with repository._write() as session:
        session.add(MediaTaskRow(
            id=task.id, project_id=task.project_id, shot_id=task.shot_id,
            storyboard_revision=task.storyboard_revision, kind=task.kind.value,
            status=task.status.value, derived_prompt=task.derived_prompt,
            prompt_components=task.prompt_components, provider=None, public_settings={},
            provider_task_id=None, output_uri=task.output_uri, error=None,
            created_at=task.created_at, updated_at=task.updated_at,
            started_at=task.created_at, finished_at=task.updated_at,
        ))

    archived = repository.archive_project(project.id, 1)
    repository.permanent_delete_project(project.id, archived.lifecycle_revision, brief.title)

    assert opaque_output.read_bytes() == b"provider-owned-output"
