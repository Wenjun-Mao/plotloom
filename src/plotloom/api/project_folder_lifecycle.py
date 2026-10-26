from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import FastAPI, Header, Query, status

from plotloom.api.contracts import (
    LifecycleRequest,
    ProjectCreateRequest,
    ProjectDuplicateRequest,
    ProjectListResponse,
    ProjectOperationalState,
    ProjectPermanentDeleteRequest,
)
from plotloom.api.request_headers import _normalize_idempotency_key
from plotloom.project_contracts import (
    Project,
    ProjectCreation,
    ProjectDuplicateResult,
    ProjectLifecycleStatus,
    ProjectSummary,
)

from ..exceptions import (
    BootstrapContentionError,
)
from ..persistence import stable_hash
from ..project_storage import (
    ProjectFolderStorage,
    ProjectSnapshotReceipt,
    ProjectStorageConflictError,
)


def register_project_lifecycle_routes(
    app: FastAPI,
    storage: ProjectFolderStorage,
    opened_project: Callable,
    inspected_project: Callable,
    inspected_open_project: Callable,
) -> None:
    def working_project_view(store) -> Project:
        project = store.project()
        drafts = store.authoring.list_authoring_drafts(project.id)
        brief_draft = next(
            (
                draft
                for draft in drafts
                if draft.editor_scope == "brief" and draft.entity_id == "root"
            ),
            None,
        )
        title = (
            str(brief_draft.payload.get("title", ""))
            if brief_draft
            else project.brief.title
            if project.brief
            else ""
        )
        state, _revision = store.repository.operational_state()
        return project.model_copy(
            update={
                "display_title": title.strip() or "未命名项目",
                "operational_state": state,
            }
        )

    def creation_response(project_id: str) -> ProjectCreation:
        with opened_project(project_id) as store:
            project = store.project()
            return ProjectCreation(
                **project.model_dump(mode="python"),
                stages=store.authoring.list_stage_envelopes(project_id),
            )

    @app.post(
        "/api/v2/projects",
        response_model=ProjectCreation,
        status_code=status.HTTP_201_CREATED,
    )
    def create_project(
        body: ProjectCreateRequest,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> ProjectCreation:
        brief = body.brief
        key = _normalize_idempotency_key(idempotency_key)
        if key is None:
            store = storage.projects.create(
                brief, initial_stages=tuple(body.initial_stages)
            )
            project_id = store.manifest.project_id
            store.close()
            return creation_response(project_id)
        fingerprint = stable_hash(
            {
                "brief": brief.model_dump(mode="json", by_alias=False)
                if brief
                else None,
                "initialStages": [
                    stage.model_dump(mode="json", by_alias=False)
                    for stage in body.initial_stages
                ],
            }
        )
        reservation = storage.application.project_lifecycle.reserve_creation(
            key=key, fingerprint=fingerprint
        )
        project_id = reservation.target_project_id
        if not reservation.complete:
            if not reservation.initialization_claimed:
                raise BootstrapContentionError(retry_after_seconds=1)
            try:
                store = storage.projects.create(
                    brief,
                    project_id=project_id,
                    created_at=reservation.target_created_at,
                    initial_stages=tuple(body.initial_stages),
                )
            except ProjectStorageConflictError:
                # The application lease is ours only after an owner expires.
                # Resume its exact reserved home; never open a partial folder,
                # allocate another ID, or substitute request inputs.
                store = storage.projects.resume_creation(
                    brief,
                    project_id=project_id,
                    created_at=reservation.target_created_at,
                    initial_stages=tuple(body.initial_stages),
                )
            store.close()
            storage.application.project_lifecycle.complete_creation(reservation)
        return creation_response(project_id)

    @app.get("/api/v2/projects", response_model=ProjectListResponse)
    def list_projects(
        project_status: Annotated[
            Literal["active", "archived", "all"], Query(alias="status")
        ] = "active",
        limit: int = Query(default=50, ge=1, le=200),
        cursor: str | None = None,
    ) -> ProjectListResponse:
        # Project-folder discovery is bounded by the explicit storage root.
        # Cursoring remains unnecessary for the bounded local workbench list.
        del cursor
        summaries: list[ProjectSummary] = []
        for home in storage.projects.discover():
            with inspected_project(home.manifest.project_id) as store:
                project = working_project_view(store)
                if (
                    project_status != "all"
                    and project.lifecycle_status
                    != ProjectLifecycleStatus(project_status)
                ):
                    continue
                operational_state, _revision = store.repository.operational_state()
                summaries.append(
                    ProjectSummary(
                        **project.model_dump(mode="python"),
                        stage_statuses={
                            head.stage: head.status
                            for head in store.authoring.list_stage_heads(project.id)
                        },
                    )
                )
            if len(summaries) == limit:
                break
        return ProjectListResponse(projects=summaries)

    @app.get("/api/v2/projects/{project_id}", response_model=Project)
    def get_project(project_id: str) -> Project:
        with inspected_open_project(project_id) as store:
            return working_project_view(store)

    @app.post("/api/v2/projects/{project_id}/archive", response_model=Project)
    def archive_project(project_id: str, body: LifecycleRequest) -> Project:
        storage.lifecycle.archive(
            project_id,
            expected_lifecycle_revision=body.expected_lifecycle_revision,
        )
        with inspected_open_project(project_id) as store:
            return working_project_view(store)

    @app.post("/api/v2/projects/{project_id}/restore", response_model=Project)
    def restore_project(project_id: str, body: LifecycleRequest) -> Project:
        storage.lifecycle.restore(
            project_id,
            expected_lifecycle_revision=body.expected_lifecycle_revision,
        )
        with inspected_open_project(project_id) as store:
            return working_project_view(store)

    @app.post(
        "/api/v2/projects/{project_id}/duplicate",
        response_model=ProjectDuplicateResult,
    )
    def duplicate_project(
        project_id: str,
        body: ProjectDuplicateRequest,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> ProjectDuplicateResult:
        return storage.lifecycle.duplicate(
            project_id,
            expected_lifecycle_revision=body.expected_lifecycle_revision,
            title=body.title,
            idempotency_key=_normalize_idempotency_key(idempotency_key),
        )

    @app.post(
        "/api/v2/projects/{project_id}/permanent-delete",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def permanently_delete_project(
        project_id: str, body: ProjectPermanentDeleteRequest
    ) -> None:
        storage.lifecycle.permanently_delete(
            project_id,
            expected_project_revision=body.expected_project_revision,
            expected_lifecycle_revision=body.expected_lifecycle_revision,
            confirmation_title=body.confirmation_title,
            scope_hash=body.scope_hash,
        )

    @app.post(
        "/api/v2/projects/{project_id}/freeze",
        response_model=ProjectOperationalState,
    )
    def close_project(project_id: str) -> ProjectOperationalState:
        revision = storage.projects.close_project(project_id)
        return ProjectOperationalState(
            project_id=project_id, state="closed", revision=revision
        )

    @app.post(
        "/api/v2/projects/{project_id}/unfreeze",
        response_model=ProjectOperationalState,
    )
    def open_project(project_id: str) -> ProjectOperationalState:
        revision = storage.projects.reopen_project(project_id)
        return ProjectOperationalState(
            project_id=project_id, state="open", revision=revision
        )

    @app.post(
        "/api/v2/projects/{project_id}/snapshots",
        response_model=ProjectSnapshotReceipt,
        status_code=status.HTTP_201_CREATED,
    )
    def create_project_snapshot(project_id: str) -> ProjectSnapshotReceipt:
        """Create one application-owned, verified portable recovery copy.

        Browser callers cannot choose a filesystem destination.  The direct
        workbench drains only its own acknowledged editors before this route;
        the exclusive project lease then prevents a concurrent local writer
        from changing the database or specialist publication during capture.
        """

        return storage.recovery.create_snapshot(project_id)

    @app.get(
        "/api/v2/projects/{project_id}/snapshots/{snapshot_id}",
        response_model=ProjectSnapshotReceipt,
    )
    def get_project_snapshot(
        project_id: str, snapshot_id: str
    ) -> ProjectSnapshotReceipt:
        return storage.recovery.snapshot_status(project_id, snapshot_id)
