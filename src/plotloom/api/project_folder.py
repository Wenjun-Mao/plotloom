from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Callable
from typing import Annotated, Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response

from ..domain import (
    AuthoringDraft,
    AuthoringDraftScope,
    GateEvaluation,
    Project,
    ProjectCreation,
    ProjectSummary,
    StageHead,
    StageName,
)
from ..exceptions import (
    InvalidTransitionError,
    NotFoundError,
    RevisionConflictError,
)
from ..project_storage import (
    ProjectFolderStorage,
    ProjectBusyError,
    ProjectClosedError,
    ProjectSnapshotReceipt,
    ProjectStorageConflictError,
    ProjectStorageError,
)
from ..managed_media import (
    ManagedMediaError,
)
from ..video_backends.minimax_h3.adapter import H3_PROFILES_BY_ID
from ..video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from ..video_ingestion import ObservedVideo, probe_video
from ..video_provider import VideoAdapterPort, VideoProviderPort
from ..validation import STORYBOARD_GATE_SET_VERSION
from .models import (
    ApprovalClosureView,
    AuthoringDraftDiscardRequest,
    AuthoringDraftUpsertRequest,
    CanonicalDraftConsumption,
    ProjectCreateRequest,
    ProjectFolderImageJobCreateRequest,
    ProjectListResponse,
    ProjectOperationalState,
    ProjectMediaTasksResponse,
    ProjectPatchRequest,
    ProjectRunsResponse,
    StageEnvelopesResponse,
    StagePatchRequest,
    StoryboardApprovalRequest,
    StoryboardReviewResponse,
    _approval_closure_view,
)
from .project_folder_media import register_project_folder_media_routes
from .project_folder_image_jobs import register_project_folder_image_job_routes
from .project_folder_video import register_project_folder_video_routes
from ..project_storage.video_service import ProjectVideoService


def create_project_folder_authoring_app(
    storage: ProjectFolderStorage,
    *,
    video_provider: VideoProviderPort | None = None,
    video_adapter: VideoAdapterPort | None = None,
    video_probe: Callable[[bytes], ObservedVideo] | None = None,
) -> FastAPI:
    """Compose the direct project-folder authoring/image/H3 video slice.

    This deliberately small factory exists only for the bounded storage
    checkpoint and its browser evidence.  The retained runtime continues to
    use ``create_app`` until a later cutover explicitly replaces its full
    lifecycle composition; this is not a browser-selectable storage mode.
    """

    app = FastAPI(title="Plotloom project-folder authoring", version="2.0.0-storage-2e")
    app.state.project_folder_storage = storage
    if video_adapter is not None and video_adapter.adapter_id != "minimax_h3_gateway":
        raise ValueError("project-folder video accepts only the frozen MiniMax H3 adapter")
    video_service = (
        ProjectVideoService(
            storage.application,
            video_provider,
            video_adapter or MiniMaxH3GatewayAdapter(),
            probe=video_probe or probe_video,
        )
        if video_provider is not None
        else None
    )
    app.state.project_video_service = video_service

    def _project_h3_target(profile_id: str) -> dict[str, Any]:
        """Resolve a trusted adaptation target without project configuration."""

        profile = H3_PROFILES_BY_ID.get(profile_id)
        if profile is None or not profile.selectable:
            raise ManagedMediaError(
                "keyframe_target_profile_invalid",
                "keyframe preparation needs one selectable MiniMax-H3 profile",
            )
        return {
            "id": profile.profile_id,
            "version": profile.profile_version,
            "width": profile.width,
            "height": profile.height,
            "orientation": profile.orientation,
        }

    @contextmanager
    def opened_project(project_id: str):
        store = storage.projects.open(project_id)
        try:
            yield store
        finally:
            store.close()

    @contextmanager
    def inspected_project(project_id: str):
        store = storage.projects.inspect(project_id)
        try:
            yield store
        finally:
            store.close()

    def creation_response(project_id: str) -> ProjectCreation:
        with opened_project(project_id) as store:
            project = store.project()
            return ProjectCreation(
                **project.model_dump(mode="python"),
                stages=store.repository.list_stage_envelopes(project_id),
            )

    def assert_canonical_draft_scope(
        consumption: CanonicalDraftConsumption | None,
        *,
        required_scope: AuthoringDraftScope,
    ) -> None:
        if consumption is None:
            return
        if consumption.editor_scope != required_scope:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="canonical save may consume only its own editor draft",
            )

    def require_media_draft_scope(
        consumption: CanonicalDraftConsumption,
        *,
        required_scope: AuthoringDraftScope,
        required_entity_id: str,
    ) -> None:
        if (
            consumption.editor_scope != required_scope
            or consumption.entity_id != required_entity_id
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="media action must consume its exact editor draft",
            )

    def image_job_target_id(body: ProjectFolderImageJobCreateRequest) -> str:
        """Name the exact manual-job target that owns an image-direction draft."""

        if body.parent_candidate_asset_id is not None:
            return f"refinement:{body.parent_candidate_asset_id}"
        if body.keyframe_adaptation_profile_id is not None:
            return f"keyframe_adaptation:{body.keyframe_adaptation_profile_id}"
        return "original"

    @app.exception_handler(ProjectStorageConflictError)
    async def project_storage_conflict_handler(
        _request: Request, error: ProjectStorageConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "revision_conflict", "message": str(error)},
        )

    @app.exception_handler(ProjectBusyError)
    async def project_busy_handler(
        _request: Request, error: ProjectBusyError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "project_busy", "message": str(error)},
        )

    @app.exception_handler(ProjectClosedError)
    async def project_closed_handler(
        _request: Request, error: ProjectClosedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "project_closed", "message": str(error)},
        )

    @app.exception_handler(NotFoundError)
    async def project_folder_not_found_handler(
        _request: Request, error: NotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"code": "not_found", "message": str(error)},
        )

    @app.exception_handler(InvalidTransitionError)
    async def project_folder_transition_handler(
        _request: Request, error: InvalidTransitionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "invalid_transition", "message": str(error)},
        )

    @app.exception_handler(ProjectStorageError)
    async def project_storage_error_handler(
        _request: Request, error: ProjectStorageError
    ) -> JSONResponse:
        missing = str(error).startswith("project not found")
        if missing:
            response_status = status.HTTP_404_NOT_FOUND
            code = "not_found"
        else:
            response_status = status.HTTP_422_UNPROCESSABLE_CONTENT
            code = "project_storage_error"
        return JSONResponse(
            status_code=response_status,
            content={"code": code, "message": str(error)},
        )

    @app.exception_handler(RevisionConflictError)
    async def authoring_revision_conflict_handler(
        _request: Request, error: RevisionConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"code": "revision_conflict", "message": str(error)},
        )

    @app.exception_handler(ValueError)
    async def authoring_validation_handler(
        _request: Request, error: ValueError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"code": "authoring_draft_invalid", "message": str(error)},
        )

    @app.get("/api/v2/authoring-draft-capabilities")
    def authoring_draft_capabilities() -> dict[str, bool]:
        return {
            "durableProjectDrafts": True,
            "durableMediaDrafts": True,
            "explicitProjectClose": True,
            "portableSnapshots": True,
        }

    @app.post(
        "/api/v2/projects",
        response_model=ProjectCreation,
        status_code=status.HTTP_201_CREATED,
    )
    def create_project(body: ProjectCreateRequest) -> ProjectCreation:
        store = storage.projects.create(body.brief)
        project_id = store.manifest.project_id
        try:
            for initial_stage in body.initial_stages:
                store.update_stage(
                    initial_stage.stage,
                    initial_stage.payload,
                    expected_revision=0,
                )
        finally:
            store.close()
        return creation_response(project_id)

    @app.get("/api/v2/projects", response_model=ProjectListResponse)
    def list_projects(
        project_status: Annotated[
            Literal["active", "archived", "all"], Query(alias="status")
        ] = "active",
        limit: int = Query(default=50, ge=1, le=200),
        cursor: str | None = None,
    ) -> ProjectListResponse:
        # Project-folder discovery is bounded by the explicit storage root;
        # cursor and archive lifecycle are deferred with the rest of close/
        # restore work, so this 2B composition exposes active homes only.
        del cursor
        if project_status == "archived":
            return ProjectListResponse(projects=[])
        summaries: list[ProjectSummary] = []
        for home in storage.projects.discover()[:limit]:
            with inspected_project(home.manifest.project_id) as store:
                project = store.project()
                operational_state, _revision = store.repository.operational_state()
                summaries.append(
                    ProjectSummary(
                        **project.model_dump(mode="python"),
                        stage_statuses={
                            head.stage: head.status
                            for head in store.repository.list_stage_heads(project.id)
                        },
                        operational_state=operational_state,
                    )
                )
        return ProjectListResponse(projects=summaries)

    @app.get("/api/v2/projects/{project_id}", response_model=Project)
    def get_project(project_id: str) -> Project:
        with opened_project(project_id) as store:
            return store.project()

    @app.post(
        "/api/v2/projects/{project_id}/close",
        response_model=ProjectOperationalState,
    )
    def close_project(project_id: str) -> ProjectOperationalState:
        revision = storage.projects.close_project(project_id)
        return ProjectOperationalState(project_id=project_id, state="closed", revision=revision)

    @app.post(
        "/api/v2/projects/{project_id}/open",
        response_model=ProjectOperationalState,
    )
    def open_project(project_id: str) -> ProjectOperationalState:
        revision = storage.projects.reopen_project(project_id)
        return ProjectOperationalState(project_id=project_id, state="open", revision=revision)

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
    def get_project_snapshot(project_id: str, snapshot_id: str) -> ProjectSnapshotReceipt:
        return storage.recovery.snapshot_status(project_id, snapshot_id)

    @app.patch("/api/v2/projects/{project_id}", response_model=Project)
    def patch_project(
        project_id: str,
        body: ProjectPatchRequest,
        response: Response,
    ) -> Project:
        with opened_project(project_id) as store:
            assert_canonical_draft_scope(body.consumed_draft, required_scope="brief")
            if body.consumed_draft is None:
                updated = store.update_brief(
                    body.brief, expected_revision=body.expected_revision
                )
            else:
                updated = store.update_brief_consuming_authoring_draft(
                    body.brief,
                    expected_revision=body.expected_revision,
                    entity_id=body.consumed_draft.entity_id,
                    expected_draft_revision=body.consumed_draft.draft_revision,
                )
                # The repository consumed this receipt in the same SQLite
                # transaction that installed canonical content.
                response.headers["X-Plotloom-Draft-Consumed-Revision"] = str(
                    body.consumed_draft.draft_revision
                )
            return updated

    @app.get(
        "/api/v2/projects/{project_id}/stages", response_model=StageEnvelopesResponse
    )
    def get_stages(project_id: str) -> StageEnvelopesResponse:
        with opened_project(project_id) as store:
            return StageEnvelopesResponse(
                stages=store.repository.list_stage_envelopes(project_id)
            )

    @app.patch("/api/v2/projects/{project_id}/stages/{stage}", response_model=StageHead)
    def patch_stage(
        project_id: str,
        stage: StageName,
        body: StagePatchRequest,
        response: Response,
    ) -> StageHead:
        with opened_project(project_id) as store:
            assert_canonical_draft_scope(
                body.consumed_draft, required_scope=stage.value
            )
            if body.consumed_draft is None:
                updated = store.update_stage(
                    stage, body.payload, expected_revision=body.expected_revision
                )
            else:
                updated = store.update_stage_consuming_authoring_draft(
                    stage,
                    body.payload,
                    expected_revision=body.expected_revision,
                    entity_id=body.consumed_draft.entity_id,
                    expected_draft_revision=body.consumed_draft.draft_revision,
                )
                response.headers["X-Plotloom-Draft-Consumed-Revision"] = str(
                    body.consumed_draft.draft_revision
                )
            return updated

    @app.get(
        "/api/v2/projects/{project_id}/authoring-drafts",
        response_model=list[AuthoringDraft],
    )
    def list_authoring_drafts(project_id: str) -> list[AuthoringDraft]:
        with opened_project(project_id) as store:
            return store.authoring_drafts()

    @app.put(
        "/api/v2/projects/{project_id}/authoring-drafts", response_model=AuthoringDraft
    )
    def save_authoring_draft(
        project_id: str,
        body: AuthoringDraftUpsertRequest,
    ) -> AuthoringDraft:
        with opened_project(project_id) as store:
            return store.save_authoring_draft(
                editor_scope=body.editor_scope,
                entity_id=body.entity_id,
                base_canonical_revision=body.base_canonical_revision,
                expected_draft_revision=body.expected_draft_revision,
                payload=body.payload,
            )

    @app.delete(
        "/api/v2/projects/{project_id}/authoring-drafts",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def discard_authoring_draft(
        project_id: str,
        body: AuthoringDraftDiscardRequest,
    ) -> Response:
        with opened_project(project_id) as store:
            consumed = store.discard_authoring_draft(
                editor_scope=body.editor_scope,
                entity_id=body.entity_id,
                expected_draft_revision=body.expected_draft_revision,
            )
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers={
                "X-Plotloom-Draft-Consumed-Revision": str(body.expected_draft_revision)
                if consumed
                else "",
            },
        )

    @app.get("/api/v2/projects/{project_id}/runs", response_model=ProjectRunsResponse)
    def get_project_runs(project_id: str) -> ProjectRunsResponse:
        with opened_project(project_id) as store:
            return ProjectRunsResponse(runs=store.generation_runs())

    @app.get(
        "/api/v2/projects/{project_id}/storyboard-review",
        response_model=StoryboardReviewResponse,
    )
    def get_project_storyboard_review(project_id: str) -> StoryboardReviewResponse:
        with opened_project(project_id) as store:
            repository = store.repository
            head = repository.get_stage_head(project_id, StageName.STORYBOARD)
            gate_evaluation: GateEvaluation | None = None
            if head.entity_revision_id is not None:
                try:
                    gate_evaluation = repository.get_gate_evaluation(
                        head.entity_revision_id, STORYBOARD_GATE_SET_VERSION
                    )
                except NotFoundError:
                    pass
            decisions = [
                _approval_closure_view(repository.get_approval_closure(item.id))
                for item in repository.list_approval_decisions(project_id)
            ]
            active = next(
                (
                    item.decision
                    for item in reversed(decisions)
                    if item.active and item.decision.decision == "approve"
                ),
                None,
            )
            return StoryboardReviewResponse(
                head=head,
                gate_evaluation=gate_evaluation,
                decisions=decisions,
                active_approval=active,
            )

    @app.post(
        "/api/v2/projects/{project_id}/storyboard-approval",
        response_model=ApprovalClosureView,
        status_code=status.HTTP_201_CREATED,
    )
    def decide_project_storyboard_approval(
        project_id: str, body: StoryboardApprovalRequest
    ) -> ApprovalClosureView:
        with opened_project(project_id) as store:
            decision = store.repository.decide_storyboard_approval(
                project_id,
                expected_revision=body.expected_revision,
                expected_content_hash=body.content_hash,
                decision=body.decision,
                reviewer=body.reviewer,
                gate_set_version=body.gate_set_version,
                note=body.note,
            )
            return _approval_closure_view(
                store.repository.get_approval_closure(decision.id)
            )

    @app.get(
        "/api/v2/projects/{project_id}/media-tasks",
        response_model=ProjectMediaTasksResponse,
    )
    def get_project_media_tasks(project_id: str) -> ProjectMediaTasksResponse:
        with opened_project(project_id):
            return ProjectMediaTasksResponse(tasks=[])

    # The direct storage workbench deliberately reuses the existing media
    # repository contract.  The only composition difference is that each
    # request opens the manifest-selected project handle and uses its confined
    # artifact adapter and timestamped run-local exchange.
    register_project_folder_media_routes(
        app,
        opened_project,
        require_media_draft_scope=require_media_draft_scope,
    )
    register_project_folder_image_job_routes(
        app,
        opened_project,
        image_job_target_id=image_job_target_id,
        require_media_draft_scope=require_media_draft_scope,
        project_h3_target=_project_h3_target,
    )
    register_project_folder_video_routes(
        app,
        opened_project,
        application=storage.application,
        service=video_service,
    )
    return app
