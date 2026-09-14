from __future__ import annotations

from hashlib import sha256
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import Response

from ..persistence import SQLiteRepository
from ..video_contracts import VideoJobRequest, VideoReviewRequest
from ..video_jobs import VideoJobService


def register_video_routes(app: FastAPI, repo: SQLiteRepository) -> None:
    @app.get("/api/v2/video-pilot-budget")
    def get_video_pilot_budget() -> dict[str, Any]:
        return repo.video_budget()

    @app.get("/api/v2/video-backend")
    def get_video_backend() -> dict[str, Any]:
        service = app.state.video_job_service
        if service is None:
            return {"enabled": False}
        return service.public_capability()

    @app.get("/api/v2/projects/{project_id}/video-jobs")
    def get_video_jobs(project_id: str) -> dict[str, Any]:
        return {"jobs": repo.list_video_jobs(project_id)}

    @app.post(
        "/api/v2/projects/{project_id}/video-jobs", status_code=status.HTTP_201_CREATED
    )
    def prepare_video_job(project_id: str, body: VideoJobRequest) -> dict[str, Any]:
        service = app.state.video_job_service
        if service is not None:
            return service.prepare(
                project_id,
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
        # Offline fixtures retain the original V1 preparation behaviour.  A
        # real runtime cannot enter this branch because submission is already
        # unavailable without a trusted adapter.
        return repo.prepare_video_job(
            project_id,
            approval_id=body.approval_id,
            shot_id=body.shot_id,
            storyboard_revision=body.storyboard_revision,
            expected_selection_revision=body.expected_selection_revision,
            idempotency_key=body.idempotency_key,
            requested_seconds=5
            if body.requested_duration_seconds is None
            else body.requested_duration_seconds,
            resolution="720p" if body.resolution is None else body.resolution,
            audio=True if body.audio is None else body.audio,
        )

    def require_video_service() -> VideoJobService:
        service = app.state.video_job_service
        if service is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "video_transport_not_enabled",
                    "message": "P2 video transport is not enabled in this runtime",
                },
            )
        return service

    @app.post("/api/v2/projects/{project_id}/video-jobs/{video_job_id}/submit")
    def submit_video_job(project_id: str, video_job_id: str) -> dict[str, Any]:
        return require_video_service().submit(project_id, video_job_id)

    @app.post("/api/v2/projects/{project_id}/video-jobs/{video_job_id}/reconcile")
    def reconcile_video_job(project_id: str, video_job_id: str) -> dict[str, Any]:
        return require_video_service().reconcile(project_id, video_job_id)

    @app.post("/api/v2/projects/{project_id}/video-jobs/{video_job_id}/cancel")
    def cancel_video_job(project_id: str, video_job_id: str) -> dict[str, Any]:
        return repo.cancel_video_job(project_id, video_job_id)

    @app.post(
        "/api/v2/projects/{project_id}/video-jobs/{video_job_id}/review",
        status_code=status.HTTP_201_CREATED,
    )
    def review_video_job(
        project_id: str, video_job_id: str, body: VideoReviewRequest
    ) -> dict[str, Any]:
        return repo.review_video_job(
            project_id,
            video_job_id,
            reviewer=body.reviewer,
            decision=body.decision,
            note=body.note,
        )

    @app.get("/api/v2/projects/{project_id}/video-jobs/{video_job_id}/media")
    def serve_video_job_media(
        project_id: str, video_job_id: str, request: Request
    ) -> Response:
        """Project-scoped local serving with byte ranges for native seeking.

        Plotloom's existing local server has no user authentication layer; this
        preserves that deployment policy while enforcing resource/project IDs.
        """
        stored = repo.get_video_output_storage(project_id, video_job_id)
        content = app.state.artifact_store.get(stored["uri"])
        if sha256(content).hexdigest() != stored["hash"]:
            raise HTTPException(
                status_code=409, detail={"code": "video_artifact_corrupt"}
            )
        headers = {"Accept-Ranges": "bytes", "Content-Type": stored["mimeType"]}
        raw_range = request.headers.get("range")
        if not raw_range:
            headers["Content-Length"] = str(len(content))
            return Response(
                content=content, media_type=stored["mimeType"], headers=headers
            )
        if not raw_range.startswith("bytes=") or "," in raw_range:
            return Response(
                status_code=416, headers={"Content-Range": f"bytes */{len(content)}"}
            )
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
            return Response(
                status_code=416, headers={"Content-Range": f"bytes */{len(content)}"}
            )
        piece = content[start : min(end + 1, len(content))]
        headers.update(
            {
                "Content-Length": str(len(piece)),
                "Content-Range": f"bytes {start}-{start + len(piece) - 1}/{len(content)}",
            }
        )
        return Response(
            content=piece,
            status_code=206,
            media_type=stored["mimeType"],
            headers=headers,
        )
