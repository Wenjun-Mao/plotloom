"""Project-folder routes for locally retained H3 video candidates."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import Response

from ..project_storage.application_store import ApplicationStore
from ..project_storage.project_handle import ProjectStore
from ..project_storage.project_video import ProjectVideoRepository
from ..project_storage.video_service import ProjectVideoService
from ..video_contracts import VideoJobRequest, VideoReviewRequest


def register_project_folder_video_routes(
    app: FastAPI,
    opened_project: Callable[[str], Any],
    *,
    application: ApplicationStore,
    service: ProjectVideoService | None,
) -> None:
    """Expose only the configured typed H3 direct-composition service."""

    def require_service() -> ProjectVideoService:
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "h3_video_not_configured",
                    "message": "project-folder video requires an explicitly configured H3 backend",
                },
            )
        return service

    @app.get("/api/v2/video-pilot-budget")
    def get_video_budget() -> dict[str, Any]:
        if service is None:
            return {
                "configured": False,
                "limitUnits": None,
                "reservedUnits": None,
                "remainingUnits": None,
                "limitSeconds": 0,
                "reservedSeconds": 0,
                "remainingSeconds": 0,
                "attempts": [],
            }
        return service.budget()

    @app.get("/api/v2/video-backend")
    def get_video_backend() -> dict[str, Any]:
        if service is None:
            return {
                "enabled": False,
                "tracksPaidWanPilot": False,
                "reason": "h3_video_not_configured",
            }
        return service.public_capability()

    @app.get("/api/v2/projects/{project_id}/video-jobs")
    def get_video_jobs(project_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return {"jobs": _local_repository(store).list_video_jobs(project_id)}

    @app.post(
        "/api/v2/projects/{project_id}/video-jobs", status_code=status.HTTP_201_CREATED
    )
    def prepare_video_job(project_id: str, body: VideoJobRequest) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return require_service().prepare(
                store,
                approval_id=body.approval_id,
                shot_id=body.shot_id,
                storyboard_revision=body.storyboard_revision,
                expected_selection_revision=body.expected_selection_revision,
                idempotency_key=body.idempotency_key,
                requested_seconds=body.requested_duration_seconds,
                resolution=body.resolution,
                audio=body.audio,
                aspect_policy=body.aspect_policy,
                allow_letterbox=body.allow_letterbox,
                seed=body.seed,
                profile_id=body.profile_id,
            )

    @app.post("/api/v2/projects/{project_id}/video-jobs/{video_job_id}/submit")
    def submit_video_job(project_id: str, video_job_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return require_service().submit(store, video_job_id)

    @app.post("/api/v2/projects/{project_id}/video-jobs/{video_job_id}/reconcile")
    def reconcile_video_job(project_id: str, video_job_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return require_service().reconcile(store, video_job_id)

    @app.post("/api/v2/projects/{project_id}/video-jobs/{video_job_id}/cancel")
    def cancel_video_job(project_id: str, video_job_id: str) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return _local_repository(store).cancel_video_job(project_id, video_job_id)

    @app.post(
        "/api/v2/projects/{project_id}/video-jobs/{video_job_id}/review",
        status_code=status.HTTP_201_CREATED,
    )
    def review_video_job(
        project_id: str, video_job_id: str, body: VideoReviewRequest
    ) -> dict[str, Any]:
        with opened_project(project_id) as store:
            return _local_repository(store).review_video_job(
                project_id,
                video_job_id,
                reviewer=body.reviewer,
                decision=body.decision,
                note=body.note,
            )

    @app.get("/api/v2/projects/{project_id}/video-jobs/{video_job_id}/media")
    def serve_video_media(
        project_id: str, video_job_id: str, request: Request
    ) -> Response:
        with opened_project(project_id) as store:
            storage = _local_repository(store).get_video_output_storage(
                project_id, video_job_id
            )
            content = store.artifacts.get(storage["uri"])
        if sha256(content).hexdigest() != storage["hash"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "video_artifact_corrupt"},
            )
        return _range_response(content, storage["mimeType"], request.headers.get("range"))

    def _local_repository(store: ProjectStore) -> ProjectVideoRepository:
        return ProjectVideoRepository(store, application)


def _range_response(content: bytes, mime_type: str, raw_range: str | None) -> Response:
    headers = {"Accept-Ranges": "bytes", "Content-Type": mime_type}
    if not raw_range:
        headers["Content-Length"] = str(len(content))
        return Response(content=content, media_type=mime_type, headers=headers)
    if not raw_range.startswith("bytes=") or "," in raw_range:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{len(content)}"})
    try:
        start_text, end_text = raw_range.removeprefix("bytes=").split("-", 1)
        if start_text:
            start = int(start_text)
            end = int(end_text) if end_text else len(content) - 1
        else:
            suffix = int(end_text)
            start, end = max(0, len(content) - suffix), len(content) - 1
        if start < 0 or end < start or start >= len(content):
            raise ValueError
    except ValueError:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{len(content)}"})
    piece = content[start : min(end + 1, len(content))]
    headers.update(
        {
            "Content-Length": str(len(piece)),
            "Content-Range": f"bytes {start}-{start + len(piece) - 1}/{len(content)}",
        }
    )
    return Response(content=piece, status_code=206, media_type=mime_type, headers=headers)
