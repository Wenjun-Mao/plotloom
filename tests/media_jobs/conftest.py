from __future__ import annotations

import pytest

from plotloom.domain import MediaKind, MediaTask, ProjectBrief, STAGE_ORDER
from plotloom.persistence import MediaTaskRow, SQLiteRepository
from tests.backend_core.conftest import all_stage_payloads


@pytest.fixture
def repository() -> SQLiteRepository:
    repo = SQLiteRepository("sqlite://")
    yield repo
    repo.close()


@pytest.fixture
def prepared_project(repository: SQLiteRepository):
    project = repository.create_project(
        ProjectBrief(
            title="星海回声",
            synopsis="失忆领航员醒来后必须决定是否唤醒飞船人工智能。",
        )
    )
    payloads = all_stage_payloads()
    for stage, payload in zip(STAGE_ORDER, payloads, strict=True):
        repository.update_stage(project.id, stage, 0, payload)
    shot = payloads[-1].shots[0]
    return project, shot


def make_media_task(
    repository: SQLiteRepository,
    prepared_project,
    kind: MediaKind,
    *,
    provider: str,
    public_settings: dict[str, object],
):
    """Materialize a pre-M1-12A task for runner lifecycle coverage.

    Current V2 authoring deliberately has no media-creation path until a
    ProductionSnapshot exists.  These tests exercise the runner's handling of
    an already persisted historical task, rather than reopening that path.
    """

    project, shot = prepared_project
    task = MediaTask(
        project_id=project.id,
        shot_id=shot.id,
        storyboard_revision=1,
        kind=kind,
        derived_prompt="historical cinematic shot with stable character continuity",
        prompt_components={
            "mediaConstraints": {"aspectRatio": "16:9", "durationSeconds": 8},
        },
        provider=provider,
        public_settings=public_settings,
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
