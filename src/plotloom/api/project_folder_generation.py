"""Generation routes resolved through the project-folder run index."""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, Request, status

from ..domain import GenerationRun, ProviderAuthMode, RunExecutionTrace, RunKind, RunProgress, RunTrace, STAGE_ORDER
from ..exceptions import InvalidTransitionError
from ..generation.exceptions import SecretLeaseError
from ..project_storage.text_dispatch import ProjectRunDispatcher
from ..provider_profiles import DEFAULT_PROVIDER_PROFILE_ID
from .models import (
    ExactWorkUnitRepairRequest,
    PipelineRunRequest,
    RebuildRequest,
    RepairRequest,
    _normalize_idempotency_key,
    _session_api_key,
)
from .text_admission import TextAdmissionService


def register_project_folder_generation_routes(
    app: FastAPI,
    dispatcher: ProjectRunDispatcher,
    *,
    admission: TextAdmissionService,
) -> None:
    """Keep existing run endpoints while routing each one to one project home."""

    def submit(run: GenerationRun, request: Request) -> None:
        admission.submit_text_run(run, request)

    @app.post(
        "/api/v2/projects/{project_id}/pipeline-runs",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_pipeline_run(
        project_id: str, body: PipelineRunRequest, request: Request
    ) -> GenerationRun:
        snapshot = admission.admit_text_backend(body.provider_profile_id, request)
        admission.text_submission_session_key(snapshot, request)
        run = dispatcher.create_run(
            project_id,
            kind=RunKind.PIPELINE,
            requested_stages=body.stages or list(STAGE_ORDER),
            instructions=body.instructions,
            provider_snapshot=snapshot,
        )
        submit(run, request)
        return run

    @app.post(
        "/api/v2/projects/{project_id}/rebuilds",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_rebuild(
        project_id: str, body: RebuildRequest, request: Request
    ) -> GenerationRun:
        start = STAGE_ORDER.index(body.from_stage)
        end = STAGE_ORDER.index(body.through_stage) if body.through_stage else len(STAGE_ORDER) - 1
        snapshot = admission.admit_text_backend(body.provider_profile_id, request)
        admission.text_submission_session_key(snapshot, request)
        run = dispatcher.create_run(
            project_id,
            kind=RunKind.REBUILD,
            requested_stages=STAGE_ORDER[start : end + 1],
            instructions=body.instructions,
            provider_snapshot=snapshot,
        )
        submit(run, request)
        return run

    @app.get("/api/v2/runs/{run_id}", response_model=GenerationRun)
    def get_run(run_id: str) -> GenerationRun:
        store = dispatcher.open_run_project(run_id)
        try:
            return store.generation.get_run(run_id)
        finally:
            store.close()

    @app.get("/api/v2/runs/{run_id}/trace", response_model=RunTrace)
    def get_run_trace(run_id: str) -> RunTrace:
        store = dispatcher.open_run_project(run_id)
        try:
            return store.run_trace(run_id)
        finally:
            store.close()

    @app.get("/api/v2/runs/{run_id}/execution-trace", response_model=RunExecutionTrace)
    def get_run_execution_trace(run_id: str) -> RunExecutionTrace:
        store = dispatcher.open_run_project(run_id)
        try:
            return store.run_execution_trace(run_id)
        finally:
            store.close()

    @app.get("/api/v2/runs/{run_id}/progress", response_model=RunProgress)
    def get_run_progress(run_id: str) -> RunProgress:
        store = dispatcher.open_run_project(run_id)
        try:
            return store.generation.get_run_progress(run_id)
        finally:
            store.close()

    @app.post(
        "/api/v2/runs/{run_id}/resume",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def resume_run(run_id: str, request: Request) -> GenerationRun:
        store = dispatcher.open_run_project(run_id)
        try:
            run = store.generation.get_run(run_id)
        finally:
            store.close()
        if run.status.value not in {"queued", "running"}:
            raise InvalidTransitionError(
                f"cannot resume a generation run while it is {run.status.value}"
            )
        auth_mode = str(run.provider_snapshot.get("textAuthMode") or run.provider_snapshot.get("text_auth_mode") or ProviderAuthMode.BEARER.value)
        try:
            dispatcher.submit(
                run_id,
                session_api_key=_session_api_key(request) if auth_mode == ProviderAuthMode.BEARER.value else None,
            )
        except SecretLeaseError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="this queued run needs its profile's browser-session key",
            ) from error
        return run

    @app.post("/api/v2/runs/{run_id}/cancel", response_model=GenerationRun)
    def cancel_run(run_id: str) -> GenerationRun:
        return dispatcher.request_cancel(run_id)

    @app.post(
        "/api/v2/runs/{run_id}/repairs",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
        deprecated=True,
    )
    def create_repair(run_id: str, body: RepairRequest, request: Request) -> GenerationRun:
        snapshot = admission.admit_text_backend(body.provider_profile_id, request)
        admission.text_submission_session_key(snapshot, request)
        run = dispatcher.create_repair(
            run_id,
            provider_snapshot=snapshot,
            stage=body.stage,
            instructions=body.instructions,
        )
        submit(run, request)
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
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    ) -> GenerationRun:
        source = get_run(run_id)
        profile_id = str(source.provider_snapshot.get("profileId") or source.provider_snapshot.get("profile_id") or DEFAULT_PROVIDER_PROFILE_ID)
        admission.admit_text_backend(profile_id, request, frozen_snapshot=source.provider_snapshot)
        admission.text_submission_session_key(source.provider_snapshot, request)
        key = _normalize_idempotency_key(idempotency_key)
        assert key is not None
        run, created = dispatcher.create_exact_repair(run_id, work_unit_id, idempotency_key=key)
        if created:
            submit(run, request)
        return run
