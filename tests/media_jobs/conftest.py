from __future__ import annotations

import pytest

from plotloom.domain import MediaKind, ProjectBrief, STAGE_ORDER
from plotloom.persistence import SQLiteRepository
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
    project, shot = prepared_project
    context = repository.get_media_prompt_context(project.id, shot.id)
    return repository.create_media_task(
        project.id,
        shot.id,
        kind,
        expected_storyboard_revision=context.storyboard_revision,
        derived_prompt="cinematic shot with stable character continuity",
        prompt_components={
            "mediaConstraints": {
                "aspectRatio": "16:9",
                "durationSeconds": 8,
            }
        },
        provider=provider,
        public_settings=public_settings,
    )
