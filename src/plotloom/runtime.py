from __future__ import annotations

import socket
from collections.abc import Callable
from contextlib import asynccontextmanager
from threading import Event
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import Field

from .artifacts import ArtifactStore
from .domain import Artifact, CamelModel, GenerationRun, StageName, StartupRecoveryPlan
from .generation.exceptions import SecretLeaseError
from .providers import ProviderPorts

if TYPE_CHECKING:
    from .config import PlotloomSettings
    from .video_ingestion import ObservedVideo
    from .video_provider import VideoAdapterPort, VideoProviderPort


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
            # The probe must use the same normal-restart semantics as the
            # Uvicorn listener. Otherwise a just-stopped local server can
            # leave the configured port in TIME_WAIT and make this preflight
            # reject a replacement process that could safely bind it.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
        try:
            run_runner.submit(run_id)
        except SecretLeaseError:
            # Browser-session credentials are intentionally not durable.  A
            # safely recoverable bearer run remains queued until a browser
            # explicitly resumes it with the matching profile key.
            continue
    for task_id in (
        *plan.resubmit_media_task_ids,
        *plan.resume_media_poll_task_ids,
    ):
        media_runner.submit(task_id)
    return plan


def build_runtime_app(
    settings: PlotloomSettings,
    *,
    test_video_provider: VideoProviderPort | None = None,
    test_video_adapter: VideoAdapterPort | None = None,
    test_video_probe: Callable[[bytes], ObservedVideo] | None = None,
    text_provider_resolver: Any | None = None,
) -> object:
    """Build the production project-folder runtime.

    The optional typed transports are test seams for the same production
    composition; they do not select a retained repository or alternate route
    surface.
    """

    from .api import create_project_folder_authoring_app
    from .domain import ProviderProfileCapabilities, ProviderSettings
    from .video_backends.minimax_h3 import (
        H3_PROFILES_BY_ID,
        MiniMaxH3GatewayAdapter,
        MiniMaxH3GatewayTransport,
    )
    from .pipeline import (
        RunSecretBroker,
        SnapshotTextProviderResolver,
    )
    from .project_storage import ProjectFolderStorage
    from .project_storage.application_profiles import ApplicationProfileRepository
    from .project_storage.text_dispatch import ProjectRunDispatcher
    from .provider_profiles import (
        PresetId,
        StageMaxOutputTokens,
        TextProviderCapabilities,
        TextProviderProfileSnapshot,
        TextProviderProfileSnapshotV3,
        V2ExtractionPolicy,
    )
    from .generation.contracts import ReasoningMode, RequestExtension

    storage = ProjectFolderStorage(
        outputs_root=settings.outputs_dir,
        application_data_root=settings.application_data_dir,
    )
    run_secrets = RunSecretBroker(
        settings.text_api_key.get_secret_value() if settings.text_api_key else None,
        server_key_resolver=lambda profile_id: (
            key.get_secret_value()
            if (key := settings.text_api_key_for_profile(profile_id)) is not None
            else None
        ),
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
    provider_resolver = text_provider_resolver or SnapshotTextProviderResolver()
    text_profile_values = {
        "profile_schema_version": 3,
        "profile_id": "default",
        "profile_version": 0,
        "text_provider": settings.text_provider,
        "text_base_url": settings.text_base_url,
        "text_model": settings.text_model,
        "text_auth_mode": settings.text_auth_mode,
        "text_capabilities": TextProviderCapabilities(
            json_object=settings.text_supports_json_object,
            json_schema=settings.text_supports_json_schema,
            chat_template_kwargs=settings.text_supports_chat_template_kwargs,
        ),
        "text_context_window_tokens": settings.text_context_window_tokens,
        "text_max_output_tokens": settings.text_max_output_tokens,
        "text_temperature": settings.text_temperature,
        "text_max_concurrency": settings.text_max_concurrency,
        "text_connect_timeout_seconds": settings.text_connect_timeout_seconds,
        "text_attempt_timeout_seconds": settings.text_attempt_timeout_seconds,
        "request_extension": RequestExtension(settings.text_request_extension),
        "reasoning_mode": ReasoningMode(settings.text_reasoning_mode),
        "extraction_policy": V2ExtractionPolicy(
            allow_json_fence=settings.text_extraction_allow_json_fence,
            allow_leading_think_block=(
                settings.text_extraction_allow_leading_think_block
            ),
        ),
        "stage_max_output_tokens": StageMaxOutputTokens(
            story_bible=settings.text_story_bible_max_output_tokens,
            story_graph=settings.text_story_graph_max_output_tokens,
            scene_beats=settings.text_scene_beats_max_output_tokens,
            storyboard=settings.text_storyboard_max_output_tokens,
        ),
        "max_semantic_corrections": settings.text_max_semantic_corrections,
        "preset_id": PresetId(settings.text_preset_id),
        "preset_version": "1",
        "adapter_id": "openai_compatible",
        "adapter_version": "1",
    }
    try:
        text_profile_default = TextProviderProfileSnapshotV3.model_validate(
            text_profile_values
        )
    except ValueError:
        # Existing pre-M1.5 environment combinations remain valid, but they
        # are explicitly frozen as custom instead of impersonating a preset.
        text_profile_values["preset_id"] = PresetId.CUSTOM
        text_profile_default = TextProviderProfileSnapshotV3.model_validate(
            text_profile_values
        )
    profile_repository = ApplicationProfileRepository(storage.application, provider_defaults)
    profile_repository.bootstrap_default_text_provider_profile(text_profile_default)
    dispatcher = ProjectRunDispatcher(
        storage,
        provider_resolver=provider_resolver,
        secrets=run_secrets,
        max_workers=settings.run_workers,
    )
    from .api.text_admission import TextAdmissionService

    admission = TextAdmissionService(
        profile_repository,  # type: ignore[arg-type] - capability-compatible application owner
        run_scheduler=dispatcher,
        public_defaults=provider_defaults,
        key_availability={
            "text_key_available": settings.text_api_key is not None,
            "image_key_available": settings.image_api_key is not None,
            "video_key_available": settings.video_api_key is not None,
        },
        profile_key_available=run_secrets.server_key_available,
        text_provider_resolver=provider_resolver,
        text_secret_source=run_secrets,
    )
    # A runtime selects one trusted server-owned backend. Browser payloads
    # cannot choose an endpoint, adapter, or Atlas/Wan fallback.
    if test_video_provider is not None:
        video_provider = test_video_provider
        video_adapter = test_video_adapter or MiniMaxH3GatewayAdapter()
    elif test_video_probe is not None:
        raise ValueError("a test video probe requires a typed test video provider")
    elif settings.h3_gateway_enabled:
        if settings.video_api_key is None:
            raise RuntimeError("H3 gateway requires VIDEO_MODEL_API_KEY")
        if (
            settings.video_provider != "minimax_h3_gateway"
            or settings.video_model not in {
                "minimax_h3_gateway_catalog_v2",
                *H3_PROFILES_BY_ID,
            }
        ):
            raise RuntimeError("H3 gateway runtime must use the trusted MiniMax H3 catalog")
        video_provider = MiniMaxH3GatewayTransport(
            settings.video_api_key.get_secret_value(),
            base_url=settings.video_base_url,
        )
        video_adapter = MiniMaxH3GatewayAdapter()
    else:
        video_provider = None
        video_adapter = None

    @asynccontextmanager
    async def runtime_lifespan(_app: Any):
        try:
            _app.state.startup_recovery = dispatcher.reconcile_startup()
            yield
        finally:
            dispatcher.close()
            run_secrets.close()

    app = create_project_folder_authoring_app(
        storage,
        video_provider=video_provider,
        video_adapter=video_adapter,
        video_probe=test_video_probe,
        run_dispatcher=dispatcher,
        text_admission=admission,
        static_dir=settings.static_dir,
        lifespan=runtime_lifespan,
    )
    app.state.project_folder_storage = storage
    app.state.application_profile_repository = profile_repository
    app.state.run_runner = dispatcher
    app.state.run_secrets = run_secrets
    return app


def main() -> None:
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        from .project_storage.operator import restore_command

        raise SystemExit(restore_command(sys.argv[2:]))

    import uvicorn

    from .config import PlotloomSettings

    settings = PlotloomSettings.from_env()
    port = select_available_port(settings.host, settings.port, settings.port_fallback_count)
    app = build_runtime_app(settings)
    uvicorn.run(app, host=settings.host, port=port)
