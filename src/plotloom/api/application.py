from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ..artifacts import ArtifactStore, MemoryArtifactStore
from ..domain import ProviderSettings
from ..image_job_exchange import ImageJobExchange
from ..managed_media import ManagedMediaError, ManagedMediaLimits
from ..persistence import SQLiteRepository
from ..provider_profiles import TextProviderProfileSnapshot
from ..video_backends.minimax_h3.adapter import H3_PROFILES_BY_ID
from ..video_jobs import VideoJobService
from .errors import register_api_error_handlers
from .generation import register_generation_routes
from .image_jobs import register_image_job_routes
from .managed_media import register_managed_media_routes
from .models import (
    MediaPromptCompiler,
    MediaScheduler,
    RunScheduler,
    TextProfileSecretSource,
    TextProviderResolver,
    _default_text_profile_snapshot,
)
from .projects import register_project_routes
from .text_admission import TextAdmissionService
from .text_backends import register_text_profile_routes
from .video import register_video_routes


def create_app(
    repository: SQLiteRepository | None = None,
    *,
    run_scheduler: RunScheduler | None = None,
    media_scheduler: MediaScheduler | None = None,
    media_prompt_compiler: MediaPromptCompiler | None = None,
    video_job_service: VideoJobService | None = None,
    artifact_store: ArtifactStore | None = None,
    managed_media_limits: ManagedMediaLimits | None = None,
    image_exchange_root: Path | None = None,
    static_dir: Path | None = None,
    provider_defaults: ProviderSettings | None = None,
    key_availability: Mapping[str, bool] | None = None,
    text_profile_default: TextProviderProfileSnapshot | None = None,
    profile_key_available: Callable[[str], bool] | None = None,
    text_provider_resolver: TextProviderResolver | None = None,
    text_secret_source: TextProfileSecretSource | None = None,
    lifespan: Any | None = None,
) -> FastAPI:
    """Compose the retained production API without changing its public contract."""

    repo = repository or SQLiteRepository()
    public_defaults = provider_defaults or ProviderSettings()
    availability = dict(key_availability or {})
    repo.bootstrap_default_text_provider_profile(
        text_profile_default or _default_text_profile_snapshot(public_defaults)
    )

    app = FastAPI(title="Plotloom", version="2.0.0", lifespan=lifespan)
    app.state.repository = repo
    app.state.run_scheduler = run_scheduler
    app.state.media_scheduler = media_scheduler
    app.state.video_job_service = video_job_service
    app.state.artifact_store = artifact_store or MemoryArtifactStore()
    app.state.managed_media_limits = managed_media_limits or ManagedMediaLimits()
    app.state.image_job_exchange = ImageJobExchange(
        image_exchange_root, limits=app.state.managed_media_limits
    )

    admission = TextAdmissionService(
        repo,
        run_scheduler=run_scheduler,
        public_defaults=public_defaults,
        key_availability=availability,
        profile_key_available=profile_key_available,
        text_provider_resolver=text_provider_resolver,
        text_secret_source=text_secret_source,
    )

    def selectable_h3_target(profile_id: str) -> dict[str, Any]:
        """Resolve an opaque browser profile ID at the trusted server boundary."""

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

    register_api_error_handlers(app)
    register_project_routes(app, repo)
    register_video_routes(app, repo)
    register_managed_media_routes(app, repo, selectable_h3_target)
    register_image_job_routes(app, repo, selectable_h3_target)
    register_generation_routes(
        app,
        repo,
        run_scheduler=run_scheduler,
        admit_text_backend=admission.admit_text_backend,
        submit_text_run=admission.submit_text_run,
        text_submission_session_key=admission.text_submission_session_key,
    )
    register_text_profile_routes(app, repo, admission=admission)
    admission.install_completion_observer()

    if static_dir is not None:
        app.mount(
            "/v2",
            StaticFiles(directory=static_dir, html=True, check_dir=False),
            name="v2-static",
        )
    return app
