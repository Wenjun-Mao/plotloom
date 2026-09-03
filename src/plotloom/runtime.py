from __future__ import annotations

import socket
from contextlib import asynccontextmanager
from threading import Event
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import Field

from .artifacts import ArtifactStore
from .domain import Artifact, CamelModel, GenerationRun, StageName, StartupRecoveryPlan
from .providers import ProviderPorts

if TYPE_CHECKING:
    from .config import PlotloomSettings


class RunExecutionResult(CamelModel):
    # Candidate payloads stay non-canonical until the repository verifies the run's
    # optimistic snapshot and installs them in dependency order.
    stage_payloads: dict[StageName, dict[str, Any]] = Field(default_factory=dict)
    # Durable work-unit execution never hands caller-owned stage JSON back to
    # the job runner.  It returns only repository-owned aggregate IDs, which
    # the repository resolves and installs atomically in ``commit_sealed_run``.
    sealed_aggregate_ids: list[str] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)


class RunContext(CamelModel):
    model_config = CamelModel.model_config | {"arbitrary_types_allowed": True}

    providers: ProviderPorts
    artifacts: ArtifactStore


@runtime_checkable
class GenerationEngine(Protocol):
    def execute(
        self,
        run: GenerationRun,
        context: RunContext,
        cancellation: Event,
    ) -> RunExecutionResult: ...


class StartupRecoveryRepository(Protocol):
    def reconcile_startup_jobs(self) -> StartupRecoveryPlan: ...


class StartupRecoveryRunner(Protocol):
    def submit(self, resource_id: str) -> Any: ...


def select_available_port(host: str, preferred_port: int, fallback_count: int) -> int:
    for port in range(preferred_port, preferred_port + fallback_count + 1):
        if port > 65535:
            break
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, port))
            except OSError:
                continue
            return port
    if fallback_count:
        raise OSError(
            f"no available port in {preferred_port}..{min(preferred_port + fallback_count, 65535)}"
        )
    raise OSError(f"configured port {preferred_port} is unavailable")


def recover_runtime_jobs(
    repository: StartupRecoveryRepository,
    run_runner: StartupRecoveryRunner,
    media_runner: StartupRecoveryRunner,
) -> StartupRecoveryPlan:
    """Reconcile durable state once, then dispatch only the safe recovery actions."""

    plan = repository.reconcile_startup_jobs()
    for run_id in plan.resubmit_run_ids:
        run_runner.submit(run_id)
    for task_id in (
        *plan.resubmit_media_task_ids,
        *plan.resume_media_poll_task_ids,
    ):
        media_runner.submit(task_id)
    return plan


def build_runtime_app(settings: PlotloomSettings) -> object:
    from .api import create_app
    from .artifacts import LocalArtifactStore
    from .domain import ProviderProfileCapabilities, ProviderSettings
    from .jobs import LifecycleJobRunner
    from .media import MediaPromptCompiler
    from .media_jobs import MediaJobRunner, MediaTaskSecretBroker
    from .pipeline import (
        PipelineEngine,
        RunSecretBroker,
        SnapshotTextProviderResolver,
    )
    from .persistence import SQLiteRepository
    from .providers import ProviderPorts

    repository = SQLiteRepository(settings.database_url)
    artifact_store = LocalArtifactStore(settings.artifact_root)
    run_secrets = RunSecretBroker(
        settings.text_api_key.get_secret_value() if settings.text_api_key else None
    )
    provider_defaults = ProviderSettings(
        text_provider=settings.text_provider,
        text_base_url=settings.text_base_url,
        text_model=settings.text_model,
        text_auth_mode=settings.text_auth_mode,
        text_capabilities=ProviderProfileCapabilities(
            json_object=settings.text_supports_json_object,
            json_schema=settings.text_supports_json_schema,
        ),
        text_context_window_tokens=settings.text_context_window_tokens,
        text_max_output_tokens=settings.text_max_output_tokens,
        text_temperature=settings.text_temperature,
        text_max_concurrency=settings.text_max_concurrency,
        text_connect_timeout_seconds=settings.text_connect_timeout_seconds,
        text_attempt_timeout_seconds=settings.text_attempt_timeout_seconds,
        image_provider=settings.image_provider,
        image_base_url=settings.image_base_url,
        image_model=settings.image_model,
        image_auth_mode=settings.image_auth_mode,
        video_provider=settings.video_provider,
        video_base_url=settings.video_base_url,
        video_model=settings.video_model,
        video_auth_mode=settings.video_auth_mode,
    )
    provider_resolver = SnapshotTextProviderResolver()
    pipeline = PipelineEngine(repository, provider_resolver, run_secrets)
    run_runner = LifecycleJobRunner(
        repository,
        pipeline,
        RunContext(providers=ProviderPorts(), artifacts=artifact_store),
        max_workers=settings.run_workers,
        secret_registrar=run_secrets,
    )
    media_secrets = MediaTaskSecretBroker(
        image_api_key=(
            settings.image_api_key.get_secret_value() if settings.image_api_key else None
        ),
        video_api_key=(
            settings.video_api_key.get_secret_value() if settings.video_api_key else None
        ),
    )
    media_runner = MediaJobRunner(
        repository,
        media_secrets,
        max_workers=settings.media_workers,
        poll_interval_seconds=settings.media_poll_interval_seconds,
        max_poll_attempts=settings.media_max_poll_attempts,
    )
    @asynccontextmanager
    async def runtime_lifespan(_app: Any):
        try:
            _app.state.startup_recovery = recover_runtime_jobs(
                repository,
                run_runner,
                media_runner,
            )
            yield
        finally:
            run_runner.close()
            media_runner.close()
            run_secrets.close()
            repository.close()

    app = create_app(
        repository,
        run_scheduler=run_runner,
        media_scheduler=media_runner,
        media_prompt_compiler=MediaPromptCompiler(),
        static_dir=settings.static_dir,
        provider_defaults=provider_defaults,
        key_availability={
            "text_key_available": settings.text_api_key is not None,
            "image_key_available": settings.image_api_key is not None,
            "video_key_available": settings.video_api_key is not None,
        },
        lifespan=runtime_lifespan,
    )
    app.state.artifact_store = artifact_store
    app.state.run_runner = run_runner
    app.state.run_secrets = run_secrets
    app.state.media_runner = media_runner
    app.state.media_secrets = media_secrets
    return app


def main() -> None:
    import uvicorn

    from .config import PlotloomSettings

    settings = PlotloomSettings.from_env()
    port = select_available_port(settings.host, settings.port, settings.port_fallback_count)
    app = build_runtime_app(settings)
    uvicorn.run(app, host=settings.host, port=port)
