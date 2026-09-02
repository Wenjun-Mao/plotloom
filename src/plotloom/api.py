from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Mapping, Protocol

from fastapi import FastAPI, HTTPException, Header, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, model_validator

from .domain import (
    PUBLIC_PROVIDER_SETTING_FIELDS,
    STAGE_ORDER,
    CamelModel,
    GenerationRun,
    InitialStage,
    MediaKind,
    MediaPromptContext,
    MediaTask,
    Project,
    ProjectBrief,
    ProjectCreation,
    ProviderSettings,
    RunKind,
    RunTrace,
    StageEnvelope,
    StageHead,
    StageName,
    contains_secret_setting,
    contains_secret_value,
    validate_public_provider_snapshot,
    validate_initial_stage_prefix,
)
from .exceptions import (
    BootstrapContentionError,
    IdempotencyConflictError,
    InvalidTransitionError,
    NotFoundError,
    RevisionConflictError,
    StagePrerequisiteError,
)
from .persistence import SQLiteRepository
from .validation import DomainValidationError


class RunScheduler(Protocol):
    def submit(self, run_id: str, *, session_api_key: str | None = None) -> Any: ...

    def request_cancel(self, run_id: str) -> GenerationRun: ...


class MediaScheduler(Protocol):
    def submit(self, task_id: str, *, session_api_key: str | None = None) -> Any: ...


class MediaPromptCompiler(Protocol):
    def compile(self, context: MediaPromptContext, kind: MediaKind) -> tuple[str, dict[str, Any]]: ...


class ProjectCreateRequest(CamelModel):
    brief: ProjectBrief
    initial_stages: list[InitialStage] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_initial_stages(self) -> ProjectCreateRequest:
        validate_initial_stage_prefix(self.initial_stages)
        return self


class ProjectPatchRequest(CamelModel):
    expected_revision: int = Field(ge=1)
    brief: ProjectBrief


class StageEnvelopesResponse(CamelModel):
    stages: list[StageEnvelope]


class ProjectRunsResponse(CamelModel):
    runs: list[GenerationRun]


class ProjectMediaTasksResponse(CamelModel):
    tasks: list[MediaTask]


class StagePatchRequest(CamelModel):
    expected_revision: int = Field(ge=0)
    payload: dict[str, Any]


class PipelineRunRequest(CamelModel):
    stages: list[StageName] | None = Field(default=None, min_length=1)
    instructions: str | None = None

    @model_validator(mode="after")
    def reject_duplicate_stages(self) -> PipelineRunRequest:
        if self.stages is not None and len(self.stages) != len(set(self.stages)):
            raise ValueError("stages must not contain duplicates")
        if self.stages:
            first_index = STAGE_ORDER.index(self.stages[0])
            expected = list(STAGE_ORDER[first_index : first_index + len(self.stages)])
            if self.stages != expected:
                raise ValueError("stages must form one contiguous canonical stage range")
        return self


class RebuildRequest(CamelModel):
    from_stage: StageName
    through_stage: StageName | None = None
    instructions: str | None = None

    @model_validator(mode="after")
    def validate_range(self) -> RebuildRequest:
        if self.through_stage is not None and STAGE_ORDER.index(self.through_stage) < STAGE_ORDER.index(self.from_stage):
            raise ValueError("throughStage must not precede fromStage")
        return self


class RepairRequest(CamelModel):
    stage: StageName | None = None
    instructions: str | None = None


def _session_api_key(request: Request) -> str | None:
    value = (request.headers.get("X-Plotloom-Session-API-Key") or "").strip()
    if len(value) > 4096:
        raise HTTPException(status_code=400, detail="session API key is too long")
    return value or None


def _normalize_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Idempotency-Key must not be blank")
    if len(normalized) > 255:
        raise HTTPException(status_code=400, detail="Idempotency-Key must be at most 255 characters")
    return normalized


def _submit_with_optional_session_key(scheduler: Any, resource_id: str, request: Request) -> Any:
    session_key = _session_api_key(request)
    if session_key is None:
        return scheduler.submit(resource_id)
    return scheduler.submit(resource_id, session_api_key=session_key)


class MediaTaskRequest(CamelModel):
    kind: MediaKind
    provider: str | None = None
    public_settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_secrets(self) -> MediaTaskRequest:
        if contains_secret_value(self.provider):
            raise ValueError("provider must be a public identifier, not a credential")
        if contains_secret_setting(self.public_settings) or contains_secret_value(
            self.public_settings
        ):
            raise ValueError("publicSettings must not contain API keys, tokens, credentials, or other secrets")
        for field, aliases in (
            ("image_base_url", ("imageBaseUrl", "image_base_url")),
            ("video_base_url", ("videoBaseUrl", "video_base_url")),
        ):
            value = next(
                (self.public_settings[name] for name in aliases if self.public_settings.get(name)),
                None,
            )
            if value is not None:
                ProviderSettings.model_validate({field: value})
        generic_base_url = self.public_settings.get("baseUrl") or self.public_settings.get("base_url")
        if generic_base_url is not None:
            ProviderSettings.model_validate(
                {f"{self.kind.value}_base_url": generic_base_url}
            )
        return self


class ProviderSettingsUpdate(CamelModel):
    text_provider: str | None = None
    text_base_url: str | None = None
    text_model: str | None = None
    image_provider: str | None = None
    image_base_url: str | None = None
    image_model: str | None = None
    video_provider: str | None = None
    video_base_url: str | None = None
    video_model: str | None = None

    @model_validator(mode="after")
    def validate_public_settings(self) -> ProviderSettingsUpdate:
        ProviderSettings.model_validate(self.model_dump())
        return self


def _merge_provider_settings(
    persisted: ProviderSettings,
    defaults: ProviderSettings,
    key_availability: Mapping[str, bool],
) -> ProviderSettings:
    values = {
        field: getattr(persisted, field) or getattr(defaults, field)
        for field in PUBLIC_PROVIDER_SETTING_FIELDS
    }
    values.update(
        revision=persisted.revision,
        updated_at=persisted.updated_at,
        text_key_available=bool(key_availability.get("text_key_available", False)),
        image_key_available=bool(key_availability.get("image_key_available", False)),
        video_key_available=bool(key_availability.get("video_key_available", False)),
    )
    return ProviderSettings.model_validate(values)


def _public_provider_snapshot(settings: ProviderSettings) -> dict[str, Any]:
    return validate_public_provider_snapshot(
        settings.model_dump(
            mode="json",
            by_alias=False,
            include=set(PUBLIC_PROVIDER_SETTING_FIELDS),
        )
    )


def create_app(
    repository: SQLiteRepository | None = None,
    *,
    run_scheduler: RunScheduler | None = None,
    media_scheduler: MediaScheduler | None = None,
    media_prompt_compiler: MediaPromptCompiler | None = None,
    static_dir: Path | None = None,
    provider_defaults: ProviderSettings | None = None,
    key_availability: Mapping[str, bool] | None = None,
    lifespan: Any | None = None,
) -> FastAPI:
    repo = repository or SQLiteRepository()
    public_defaults = provider_defaults or ProviderSettings()
    availability = dict(key_availability or {})
    app = FastAPI(title="Plotloom", version="2.0.0", lifespan=lifespan)
    app.state.repository = repo
    app.state.run_scheduler = run_scheduler
    app.state.media_scheduler = media_scheduler

    def effective_provider_settings() -> ProviderSettings:
        return _merge_provider_settings(repo.get_provider_settings(), public_defaults, availability)

    def provider_snapshot() -> dict[str, Any]:
        return _public_provider_snapshot(effective_provider_settings())

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_request: Request, error: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"code": "not_found", "message": str(error)})

    @app.exception_handler(RevisionConflictError)
    async def revision_conflict_handler(_request: Request, error: RevisionConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "code": "revision_conflict",
                "message": str(error),
                "resource": error.resource,
                "expectedRevision": error.expected_revision,
                "actualRevision": error.actual_revision,
            },
        )

    @app.exception_handler(StagePrerequisiteError)
    async def prerequisite_handler(_request: Request, error: StagePrerequisiteError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "code": "stage_prerequisite",
                "message": str(error),
                "stage": error.stage.value,
                "prerequisite": error.prerequisite.value,
                "status": error.status,
            },
        )

    @app.exception_handler(InvalidTransitionError)
    async def transition_handler(_request: Request, error: InvalidTransitionError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"code": "invalid_transition", "message": str(error)})

    @app.exception_handler(IdempotencyConflictError)
    async def idempotency_conflict_handler(
        _request: Request, error: IdempotencyConflictError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"code": "idempotency_conflict", "message": str(error)})

    @app.exception_handler(BootstrapContentionError)
    async def bootstrap_contention_handler(
        _request: Request, error: BootstrapContentionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"code": "bootstrap_contention", "message": str(error)},
            headers={"Retry-After": str(error.retry_after_seconds)},
        )

    @app.exception_handler(DomainValidationError)
    async def domain_validation_handler(_request: Request, error: DomainValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": "domain_validation", "message": str(error), "issues": error.issues},
        )

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

    @app.get("/api/v2/projects/{project_id}", response_model=Project)
    def get_project(project_id: str) -> Project:
        return repo.get_project(project_id)

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

    @app.patch("/api/v2/projects/{project_id}/stages/{stage}", response_model=StageHead)
    def patch_stage(project_id: str, stage: StageName, body: StagePatchRequest) -> StageHead:
        return repo.update_stage(project_id, stage, body.expected_revision, body.payload)

    @app.post(
        "/api/v2/projects/{project_id}/pipeline-runs",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_pipeline_run(project_id: str, body: PipelineRunRequest, request: Request) -> GenerationRun:
        run = repo.create_run(
            project_id,
            RunKind.PIPELINE,
            body.stages or list(STAGE_ORDER),
            instructions=body.instructions,
            provider_snapshot=provider_snapshot(),
        )
        if run_scheduler is not None:
            _submit_with_optional_session_key(run_scheduler, run.id, request)
        return run

    @app.post(
        "/api/v2/projects/{project_id}/rebuilds",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_rebuild(project_id: str, body: RebuildRequest, request: Request) -> GenerationRun:
        start_index = STAGE_ORDER.index(body.from_stage)
        end_index = STAGE_ORDER.index(body.through_stage) if body.through_stage else len(STAGE_ORDER) - 1
        run = repo.create_run(
            project_id,
            RunKind.REBUILD,
            STAGE_ORDER[start_index : end_index + 1],
            instructions=body.instructions,
            provider_snapshot=provider_snapshot(),
        )
        if run_scheduler is not None:
            _submit_with_optional_session_key(run_scheduler, run.id, request)
        return run

    @app.get("/api/v2/runs/{run_id}", response_model=GenerationRun)
    def get_run(run_id: str) -> GenerationRun:
        return repo.get_run(run_id)

    @app.get("/api/v2/runs/{run_id}/trace", response_model=RunTrace)
    def get_run_trace(run_id: str) -> RunTrace:
        return repo.get_run_trace(run_id)

    @app.post("/api/v2/runs/{run_id}/cancel", response_model=GenerationRun)
    def cancel_run(run_id: str) -> GenerationRun:
        if run_scheduler is not None:
            return run_scheduler.request_cancel(run_id)
        return repo.cancel_run(run_id)

    @app.post(
        "/api/v2/runs/{run_id}/repairs",
        response_model=GenerationRun,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_repair(run_id: str, body: RepairRequest, request: Request) -> GenerationRun:
        run = repo.create_repair_run(
            run_id,
            stage=body.stage,
            instructions=body.instructions,
            provider_snapshot=provider_snapshot(),
        )
        if run_scheduler is not None:
            _submit_with_optional_session_key(run_scheduler, run.id, request)
        return run

    @app.post(
        "/api/v2/projects/{project_id}/shots/{shot_id}/media-tasks",
        response_model=MediaTask,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def create_media_task(project_id: str, shot_id: str, body: MediaTaskRequest, request: Request) -> MediaTask:
        if media_prompt_compiler is None:
            raise HTTPException(status_code=503, detail="media prompt compiler is not configured")
        prompt_context = repo.get_media_prompt_context(project_id, shot_id)
        derived_prompt, prompt_components = media_prompt_compiler.compile(prompt_context, body.kind)
        current_settings = effective_provider_settings()
        prefix = body.kind.value
        public_settings = dict(body.public_settings)
        public_defaults = {
            f"{prefix}BaseUrl": getattr(current_settings, f"{prefix}_base_url"),
            f"{prefix}Model": getattr(current_settings, f"{prefix}_model"),
        }
        aliases = {
            f"{prefix}BaseUrl": (f"{prefix}BaseUrl", f"{prefix}_base_url", "baseUrl", "base_url"),
            f"{prefix}Model": (f"{prefix}Model", f"{prefix}_model", "model"),
        }
        for name, value in public_defaults.items():
            if value is not None and not any(alias in public_settings for alias in aliases[name]):
                public_settings[name] = value
        provider = body.provider or getattr(current_settings, f"{prefix}_provider")
        task = repo.create_media_task(
            project_id,
            shot_id,
            body.kind,
            expected_storyboard_revision=prompt_context.storyboard_revision,
            derived_prompt=derived_prompt,
            prompt_components=prompt_components,
            provider=provider,
            public_settings=public_settings,
        )
        if media_scheduler is not None:
            _submit_with_optional_session_key(media_scheduler, task.id, request)
        return task

    @app.get("/api/v2/media-tasks/{task_id}", response_model=MediaTask)
    def get_media_task(task_id: str) -> MediaTask:
        return repo.get_media_task(task_id)

    @app.get("/api/v2/provider-settings", response_model=ProviderSettings)
    def get_provider_settings() -> ProviderSettings:
        return effective_provider_settings()

    @app.put("/api/v2/provider-settings", response_model=ProviderSettings)
    def put_provider_settings(body: ProviderSettingsUpdate) -> ProviderSettings:
        repo.put_provider_settings(ProviderSettings.model_validate(body.model_dump()))
        return effective_provider_settings()

    if static_dir is not None:
        app.mount("/v2", StaticFiles(directory=static_dir, html=True, check_dir=False), name="v2-static")

    return app
