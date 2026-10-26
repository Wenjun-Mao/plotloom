from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from ..codex_image_dispatch import NativeCodexImageDispatcher
from ..managed_media import (
    ManagedMediaError,
)
from ..project_storage import (
    ProjectFolderStorage,
)
from ..project_storage.text_dispatch import ProjectRunDispatcher
from ..project_storage.video_service import ProjectVideoService
from ..specialist_settings import ImageSpecialist, SpecialistRegistry
from ..video_backends.minimax_h3 import MiniMaxH3GatewayAdapter
from ..video_backends.minimax_h3.catalog import H3_ALL_PROFILES_BY_ID
from ..video_ingestion import ObservedVideo, probe_video
from ..video_provider import VideoAdapterPort, VideoProviderPort
from .draft_scope import require_media_draft_scope
from .errors import register_api_error_handlers
from .project_access import register_project_access
from .project_folder_art import register_project_folder_art_routes
from .project_folder_authoring_views import register_project_authoring_view_routes
from .project_folder_autopilot import register_autopilot_runtime
from .project_folder_canonical import register_project_canonical_routes
from .project_folder_cast import register_project_folder_cast_routes
from .project_folder_character_references import (
    register_project_character_reference_routes,
)
from .project_folder_generation import register_project_folder_generation_routes
from .project_folder_graph import register_project_folder_graph_routes
from .project_folder_image_jobs import register_project_folder_image_job_routes
from .project_folder_lifecycle import register_project_lifecycle_routes
from .project_folder_media import register_project_folder_media_routes
from .project_folder_production_bridge import (
    register_project_folder_production_bridge_routes,
)
from .project_folder_script import register_project_folder_script_routes
from .project_folder_source_outline import register_project_folder_source_outline_routes
from .project_folder_specialists import register_specialist_routes
from .project_folder_storyboard_review import (
    register_project_folder_storyboard_review_routes,
)
from .project_folder_video import register_project_folder_video_routes
from .static_assets import RevalidatingStaticFiles
from .text_admission import TextAdmissionService
from .text_backends import register_text_profile_routes


def create_project_folder_authoring_app(
    storage: ProjectFolderStorage,
    *,
    video_provider: VideoProviderPort | None = None,
    video_adapter: VideoAdapterPort | None = None,
    video_probe: Callable[[bytes], ObservedVideo] | None = None,
    run_dispatcher: ProjectRunDispatcher | None = None,
    text_admission: TextAdmissionService | None = None,
    bridge_intent_service: Any | None = None,
    bridge_simulation_label: str | None = None,
    image_dispatcher: NativeCodexImageDispatcher | None = None,
    specialist_executable: str | None = None,
    specialist_environment: dict[str, str] | None = None,
    static_dir: Path | None = None,
    lifespan: Any | None = None,
) -> FastAPI:
    """Compose one project-folder runtime with no retained storage fallback."""

    if (run_dispatcher is None) != (text_admission is None):
        raise ValueError(
            "project text dispatch and admission must be configured together"
        )
    app = FastAPI(
        title="Plotloom project-folder authoring",
        version="2.0.0-storage-2e",
        lifespan=lifespan,
    )
    app.state.project_folder_storage = storage
    if video_adapter is not None and video_adapter.adapter_id != "minimax_h3_gateway":
        raise ValueError(
            "project-folder video accepts only the frozen MiniMax H3 adapter"
        )
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
    app.state.run_dispatcher = run_dispatcher
    app.state.text_admission = text_admission

    def _project_h3_target(profile_id: str) -> dict[str, Any]:
        """Resolve a trusted adaptation target without project configuration."""

        # Existing quality-1 preparation targets remain meaningful after the
        # new video-job catalog begins offering quality 8.
        profile = H3_ALL_PROFILES_BY_ID.get(profile_id)
        if profile is None:
            raise ManagedMediaError(
                "keyframe_target_profile_invalid",
                "keyframe preparation needs one reviewed MiniMax-H3 profile",
            )
        return {
            "id": profile.profile_id,
            "version": profile.profile_version,
            "width": profile.width,
            "height": profile.height,
            "orientation": profile.orientation,
        }

    opened_project, inspected_project, inspected_open_project = register_project_access(
        app, storage
    )

    register_api_error_handlers(app)

    @app.get("/api/v2/runtime-capabilities")
    def runtime_capabilities() -> dict[str, bool]:
        return {
            "durableProjectDrafts": True,
            "durableMediaDrafts": True,
            "explicitProjectClose": True,
            "portableSnapshots": True,
            "apiTextPipeline": text_admission is not None
            and run_dispatcher is not None,
        }

    register_project_lifecycle_routes(
        app, storage, opened_project, inspected_project, inspected_open_project
    )

    register_project_canonical_routes(app, opened_project)

    register_project_authoring_view_routes(app, storage, opened_project)

    # The direct storage workbench deliberately reuses the existing media
    # repository contract.  The only composition difference is that each
    # request opens the manifest-selected project handle and uses its confined
    # artifact adapter and timestamped run-local exchange.
    register_project_folder_media_routes(
        app,
        opened_project,
        require_media_draft_scope=require_media_draft_scope,
        inspected_project=inspected_open_project,
    )
    specialists = SpecialistRegistry(
        storage.application.root,
        image_dispatcher,
        executable=specialist_executable,
        environment=specialist_environment,
    )
    app.state.specialists = specialists
    from ..native_bridge_intent_service import NativeBridgeIntentService

    native_intent_service = NativeBridgeIntentService(storage, specialists)
    app.state.native_bridge_intent_service = native_intent_service
    from ..native_bridge_presentation_service import NativeBridgePresentationService

    native_presentation_service = NativeBridgePresentationService(storage, specialists)
    app.state.native_bridge_presentation_service = native_presentation_service
    register_specialist_routes(app, opened_project, specialists)
    register_autopilot_runtime(app, opened_project, specialists)
    from .project_folder_abandonment import register_abandonment_routes

    register_abandonment_routes(app, storage, specialists)
    register_project_character_reference_routes(
        app, opened_project, image_dispatcher=ImageSpecialist(specialists)
    )
    register_project_folder_image_job_routes(
        app,
        opened_project,
        require_media_draft_scope=require_media_draft_scope,
        project_h3_target=_project_h3_target,
        image_dispatcher=ImageSpecialist(specialists),
    )
    from .project_folder_video_batch import register_video_batch_runtime

    register_video_batch_runtime(app, storage, specialists, video_service)
    register_project_folder_video_routes(
        app,
        opened_project,
        application=storage.application,
        service=video_service,
    )
    register_project_folder_source_outline_routes(app, opened_project)
    register_project_folder_graph_routes(app, opened_project)
    register_project_folder_cast_routes(app, opened_project)
    register_project_folder_art_routes(
        app, opened_project, ImageSpecialist(specialists)
    )
    register_project_folder_script_routes(app, opened_project)
    register_project_folder_storyboard_review_routes(app, opened_project)
    register_project_folder_production_bridge_routes(
        app,
        opened_project,
        intent_service=bridge_intent_service,
        text_admission=text_admission,
        simulation_label=bridge_simulation_label,
        native_intent_service=native_intent_service,
        native_presentation_service=native_presentation_service,
    )
    if run_dispatcher is not None and text_admission is not None:
        register_project_folder_generation_routes(
            app, run_dispatcher, admission=text_admission
        )
        register_text_profile_routes(
            app, text_admission.repository, admission=text_admission
        )
    if static_dir is not None:
        app.mount(
            "/v2",
            RevalidatingStaticFiles(directory=static_dir, html=True, check_dir=False),
            name="v2-static",
        )
    return app
