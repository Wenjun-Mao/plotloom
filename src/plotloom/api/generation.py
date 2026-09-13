from __future__ import annotations

from typing import Annotated, Any, Callable, Mapping

from fastapi import FastAPI, HTTPException, Header, Request, status

from ..domain import (
    STAGE_ORDER,
    GenerationRun,
    GateEvaluation,
    MediaTask,
    ProviderAuthMode,
    RunKind,
    RunExecutionTrace,
    RunProgress,
    RunTrace,
    StageHead,
    StageName,
)
from ..exceptions import (
    InvalidTransitionError,
    NotFoundError,
    ProductionPipelineNotReadyError,
)
from ..persistence import SQLiteRepository
from ..provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID,
)
from ..generation.exceptions import SecretLeaseError
from ..validation import STORYBOARD_GATE_SET_VERSION



from .models import (
    ApprovalClosureView, PipelineRunRequest, RebuildRequest, RepairRequest, ExactWorkUnitRepairRequest, RunScheduler,
    MediaTaskRequest, StagePatchRequest, StoryboardApprovalRequest, StoryboardReviewResponse,
    _approval_closure_view, _normalize_idempotency_key, _session_api_key
)

def register_generation_routes(
    app: FastAPI, repo: SQLiteRepository, *,
    run_scheduler: RunScheduler | None,
    admit_text_backend: Callable[..., dict[str, Any]],
    submit_text_run: Callable[[GenerationRun, Request], None],
    text_submission_session_key: Callable[[Mapping[str, Any], Request], str | None],
) -> None:
    @app.patch("/api/v2/projects/{project_id}/stages/{stage}", response_model=StageHead)
    def patch_stage(project_id: str, stage: StageName, body: StagePatchRequest) -> StageHead:
        return repo.update_stage(project_id, stage, body.expected_revision, body.payload)

    @app.get(
        "/api/v2/projects/{project_id}/storyboard-review",
        response_model=StoryboardReviewResponse,
    )
    def get_storyboard_review(project_id: str) -> StoryboardReviewResponse:
        head = repo.get_stage_head(project_id, StageName.STORYBOARD)
        gate_evaluation: GateEvaluation | None = None
        if head.entity_revision_id is not None:
            try:
                gate_evaluation = repo.get_gate_evaluation(
                    head.entity_revision_id,
                    STORYBOARD_GATE_SET_VERSION,
                )
            except NotFoundError:
                # A V1 read-only storyboard, or an interrupted pre-gate V2
                # migration, has no production-quality receipt.
                gate_evaluation = None

        decisions = [
            _approval_closure_view(repo.get_approval_closure(decision.id))
            for decision in repo.list_approval_decisions(project_id)
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
    def decide_storyboard_approval(
        project_id: str,
        body: StoryboardApprovalRequest,
    ) -> ApprovalClosureView:
        decision = repo.decide_storyboard_approval(
            project_id,
            expected_revision=body.expected_revision,
            expected_content_hash=body.content_hash,
            decision=body.decision,
            reviewer=body.reviewer,
            gate_set_version=body.gate_set_version,
            note=body.note,
        )
        return _approval_closure_view(repo.get_approval_closure(decision.id))

    @app.post(
        "/api/v2/projects/{project_id}/pipeline-runs",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_pipeline_run(project_id: str, body: PipelineRunRequest, request: Request) -> GenerationRun:
        snapshot = admit_text_backend(body.provider_profile_id, request)
        if run_scheduler is not None:
            # Fail before creating a durable run if no credential can possibly
            # reach a bearer-authenticated provider.
            text_submission_session_key(snapshot, request)
        run = repo.create_run(
            project_id,
            RunKind.PIPELINE,
            body.stages or list(STAGE_ORDER),
            instructions=body.instructions,
            provider_snapshot=snapshot,
        )
        submit_text_run(run, request)
        return run

    @app.post(
        "/api/v2/projects/{project_id}/rebuilds",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_rebuild(project_id: str, body: RebuildRequest, request: Request) -> GenerationRun:
        start_index = STAGE_ORDER.index(body.from_stage)
        end_index = STAGE_ORDER.index(body.through_stage) if body.through_stage else len(STAGE_ORDER) - 1
        snapshot = admit_text_backend(body.provider_profile_id, request)
        if run_scheduler is not None:
            text_submission_session_key(snapshot, request)
        run = repo.create_run(
            project_id,
            RunKind.REBUILD,
            STAGE_ORDER[start_index : end_index + 1],
            instructions=body.instructions,
            provider_snapshot=snapshot,
        )
        submit_text_run(run, request)
        return run

    @app.get("/api/v2/runs/{run_id}", response_model=GenerationRun)
    def get_run(run_id: str) -> GenerationRun:
        return repo.get_run(run_id)

    @app.get("/api/v2/runs/{run_id}/trace", response_model=RunTrace)
    def get_run_trace(run_id: str) -> RunTrace:
        return repo.get_run_trace(run_id)

    @app.get("/api/v2/runs/{run_id}/execution-trace", response_model=RunExecutionTrace)
    def get_run_execution_trace(run_id: str) -> RunExecutionTrace:
        """Additive shard-level trace; legacy /trace remains compact and stable."""

        return repo.get_run_execution_trace(run_id)

    @app.get("/api/v2/runs/{run_id}/progress", response_model=RunProgress)
    def get_run_progress(run_id: str) -> RunProgress:
        """Return bounded polling state without prompt or response evidence."""

        return repo.get_run_progress(run_id)

    @app.post(
        "/api/v2/runs/{run_id}/resume",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def resume_run(run_id: str, request: Request) -> GenerationRun:
        run = repo.get_run(run_id)
        if run.status.value not in {"queued", "running"}:
            raise InvalidTransitionError(
                f"cannot resume a generation run while it is {run.status.value}"
            )
        if run_scheduler is not None:
            auth_mode = str(
                run.provider_snapshot.get("textAuthMode")
                or run.provider_snapshot.get("text_auth_mode")
                or ProviderAuthMode.BEARER.value
            )
            # Let the real scheduler return an already-live Future before it
            # asks for a new credential.  After a restart, the same call raises
            # SecretLeaseError until the browser supplies the frozen profile's
            # session key (or a server key becomes available).
            session_key = (
                _session_api_key(request)
                if auth_mode == ProviderAuthMode.BEARER.value
                else None
            )
            try:
                if session_key is None:
                    run_scheduler.submit(run.id)
                else:
                    run_scheduler.submit(run.id, session_api_key=session_key)
            except SecretLeaseError as error:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="this queued run needs its profile's browser-session key",
                ) from error
        return repo.get_run(run_id)

    @app.post("/api/v2/runs/{run_id}/cancel", response_model=GenerationRun)
    def cancel_run(run_id: str) -> GenerationRun:
        if run_scheduler is not None:
            return run_scheduler.request_cancel(run_id)
        return repo.cancel_run(run_id)

    @app.post(
        "/api/v2/runs/{run_id}/repairs",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
        deprecated=True,
    )
    def create_repair(run_id: str, body: RepairRequest, request: Request) -> GenerationRun:
        snapshot = admit_text_backend(body.provider_profile_id, request)
        if run_scheduler is not None:
            text_submission_session_key(snapshot, request)
        run = repo.create_repair_run(
            run_id,
            stage=body.stage,
            instructions=body.instructions,
            provider_snapshot=snapshot,
        )
        submit_text_run(run, request)
        return run

    @app.post(
        "/api/v2/runs/{run_id}/work-units/{work_unit_id}/repairs",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_exact_work_unit_repair(
        run_id: str,
        work_unit_id: str,
        _body: ExactWorkUnitRepairRequest,
        request: Request,
        idempotency_key: Annotated[
            str,
            Header(alias="Idempotency-Key", min_length=1, max_length=255),
        ],
    ) -> GenerationRun:
        # Validate credentials against the source run's frozen profile before
        # creating a durable child. The active UI profile is not authority.
        source = repo.get_run(run_id)
        frozen_profile_id = str(
            source.provider_snapshot.get("profileId")
            or source.provider_snapshot.get("profile_id")
            or DEFAULT_PROVIDER_PROFILE_ID
        )
        # Exact repair keeps the source's frozen snapshot but still refuses a
        # definitely doomed new child before persistence.
        admit_text_backend(
            frozen_profile_id,
            request,
            frozen_snapshot=source.provider_snapshot,
        )
        if run_scheduler is not None:
            text_submission_session_key(source.provider_snapshot, request)
        normalized_key = _normalize_idempotency_key(idempotency_key)
        assert normalized_key is not None
        creation = repo.create_work_unit_repair_run(
            run_id,
            work_unit_id,
            idempotency_key=normalized_key,
        )
        if creation.created:
            submit_text_run(creation.run, request)
        return creation.run

    @app.post(
        "/api/v2/projects/{project_id}/shots/{shot_id}/media-tasks",
        response_model=MediaTask,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_media_task(project_id: str, shot_id: str, body: MediaTaskRequest, request: Request) -> MediaTask:
        # ADR 0012 keeps this route shape so old clients receive an actionable
        # contract error instead of an ambiguous 404. Rejection occurs before
        # canonical lookup, prompt compilation, credential leasing, persistence,
        # or scheduler dispatch. Reopening it requires an immutable approved
        # ProductionSnapshot.
        _ = (project_id, shot_id, body, request)
        raise ProductionPipelineNotReadyError()

    @app.get("/api/v2/media-tasks/{task_id}", response_model=MediaTask)
    def get_media_task(task_id: str) -> MediaTask:
        return repo.get_media_task(task_id)
