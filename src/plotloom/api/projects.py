from __future__ import annotations

from typing import Annotated, Literal

from fastapi import FastAPI, Header, Query, status

from ..domain import (
    Project,
    ProjectCreation,
    ProjectDuplicateResult,
    ProjectLifecycleStatus,
)
from ..persistence import SQLiteRepository
from .models import (
    LifecycleRequest,
    ProjectCreateRequest,
    ProjectDuplicateRequest,
    ProjectListResponse,
    ProjectMediaTasksResponse,
    ProjectPatchRequest,
    ProjectPermanentDeleteRequest,
    ProjectRunsResponse,
    StageEnvelopesResponse,
    _decode_project_cursor,
    _encode_project_cursor,
    _normalize_idempotency_key,
)



def register_project_routes(app: FastAPI, repo: SQLiteRepository) -> None:
    @app.post("/api/v2/projects", response_model=ProjectCreation, status_code=status.HTTP_201_CREATED)
    def create_project(
        body: ProjectCreateRequest,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> ProjectCreation:
        return repo.create_project(
            body.brief,
            initial_stages=body.initial_stages,
            idempotency_key=_normalize_idempotency_key(idempotency_key),
        )

    @app.get("/api/v2/projects", response_model=ProjectListResponse)
    def list_projects(
        project_status: Annotated[
            Literal["active", "archived", "all"], Query(alias="status")
        ] = "active",
        limit: int = Query(default=50, ge=1, le=200),
        cursor: str | None = None,
    ) -> ProjectListResponse:
        lifecycle_status = (
            None if project_status == "all" else ProjectLifecycleStatus(project_status)
        )
        projects, next_cursor = repo.list_projects(
            lifecycle_status=lifecycle_status,
            limit=limit,
            cursor=_decode_project_cursor(cursor),
        )
        return ProjectListResponse(projects=projects, next_cursor=_encode_project_cursor(next_cursor))

    @app.get("/api/v2/projects/{project_id}", response_model=Project)
    def get_project(project_id: str) -> Project:
        return repo.get_project(project_id)

    @app.post("/api/v2/projects/{project_id}/archive", response_model=Project)
    def archive_project(project_id: str, body: LifecycleRequest) -> Project:
        return repo.archive_project(project_id, body.expected_lifecycle_revision)

    @app.post("/api/v2/projects/{project_id}/restore", response_model=Project)
    def restore_project(project_id: str, body: LifecycleRequest) -> Project:
        return repo.restore_project(project_id, body.expected_lifecycle_revision)

    @app.post("/api/v2/projects/{project_id}/duplicate", response_model=ProjectDuplicateResult)
    def duplicate_project(
        project_id: str,
        body: ProjectDuplicateRequest,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> ProjectDuplicateResult:
        return repo.duplicate_project(
            project_id,
            body.expected_lifecycle_revision,
            title=body.title,
            idempotency_key=_normalize_idempotency_key(idempotency_key),
        )

    @app.post("/api/v2/projects/{project_id}/permanent-delete", status_code=status.HTTP_204_NO_CONTENT)
    def permanent_delete_project(project_id: str, body: ProjectPermanentDeleteRequest) -> None:
        repo.permanent_delete_project(
            project_id,
            body.expected_lifecycle_revision,
            body.confirmation_title,
        )

    @app.patch("/api/v2/projects/{project_id}", response_model=Project)
    def patch_project(project_id: str, body: ProjectPatchRequest) -> Project:
        return repo.update_project(project_id, body.expected_revision, body.brief)

    @app.get("/api/v2/projects/{project_id}/stages", response_model=StageEnvelopesResponse)
    def get_stages(project_id: str) -> StageEnvelopesResponse:
        return StageEnvelopesResponse(stages=repo.list_stage_envelopes(project_id))

    @app.get("/api/v2/projects/{project_id}/runs", response_model=ProjectRunsResponse)
    def get_project_runs(project_id: str) -> ProjectRunsResponse:
        return ProjectRunsResponse(runs=repo.list_project_runs(project_id))

    @app.get("/api/v2/projects/{project_id}/media-tasks", response_model=ProjectMediaTasksResponse)
    def get_project_media_tasks(project_id: str) -> ProjectMediaTasksResponse:
        return ProjectMediaTasksResponse(tasks=repo.list_project_media_tasks(project_id))
