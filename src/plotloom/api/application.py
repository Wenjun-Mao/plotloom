from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles

from ..domain import (
    GenerationRun,
    ProviderAuthMode,
    ProviderProfileCapabilities,
    ProviderSettings,
)
from ..exceptions import (
    InvalidTransitionError,
    NotFoundError,
)
from ..persistence import SQLiteRepository
from ..artifacts import ArtifactStore, MemoryArtifactStore
from ..managed_media import (
    ManagedMediaError,
    ManagedMediaLimits,
)
from ..video_backends.minimax_h3.adapter import H3_PROFILES_BY_ID
from ..image_job_exchange import ImageJobExchange
from ..video_jobs import VideoJobService
from ..provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID,
    PresetId,
    TextProviderProfile,
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
    preset_values,
)
from ..generation.exceptions import SecretLeaseError
from ..generation.secrets import InMemorySecretVault, SecretLease
from ..text_adapters import DEFAULT_TEXT_ADAPTER_REGISTRY
from .models import (
    MediaPromptCompiler,
    MediaScheduler,
    RunScheduler,
    TextBackendReadiness,
    TextProfileSecretSource,
    TextProviderProfileView,
    TextProviderProfilesResponse,
    TextProviderResolver,
    _default_text_profile_snapshot,
    _merge_provider_settings,
    _session_api_key,
)
from .errors import register_api_error_handlers
from .projects import register_project_routes
from .video import register_video_routes
from .managed_media import register_managed_media_routes
from .image_jobs import register_image_job_routes
from .generation import register_generation_routes
from .text_backends import register_text_profile_routes


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
    # None is intentional in the standard runtime until the director enables
    # a reviewed real transport.  Offline tests inject a fake service.
    app.state.video_job_service = video_job_service
    # Imports use a separate byte-store dependency from generation evidence.
    # Runtime supplies LocalArtifactStore; the in-memory default keeps isolated
    # API tests deterministic without silently opening a filesystem root.
    app.state.artifact_store = artifact_store or MemoryArtifactStore()
    app.state.managed_media_limits = managed_media_limits or ManagedMediaLimits()
    app.state.image_job_exchange = ImageJobExchange(
        image_exchange_root, limits=app.state.managed_media_limits
    )
    # Observations are intentionally application-lifetime state: no secrets,
    # no persistence, and no implication that a profile is qualified.
    readiness_observations: dict[str, TextBackendReadiness] = {}

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

    def has_server_key(profile_id: str) -> bool:
        if profile_key_available is not None:
            return bool(profile_key_available(profile_id))
        if text_secret_source is not None:
            return bool(text_secret_source.server_key_available(profile_id))
        return profile_id == DEFAULT_PROVIDER_PROFILE_ID and bool(
            availability.get("text_key_available", False)
        )

    def active_text_profile() -> TextProviderProfile:
        selection = repo.get_provider_profile_selection()
        return repo.get_text_provider_profile(selection.active_profile_id)

    def provider_settings_projection(
        profile: TextProviderProfile,
        media: ProviderSettings,
    ) -> ProviderSettings:
        """Project one text profile and the global media singleton."""

        text = profile.configuration
        return ProviderSettings(
            profile_id=profile.profile_id,
            text_provider=text.text_provider,
            text_base_url=text.text_base_url,
            text_model=text.text_model,
            text_auth_mode=ProviderAuthMode(text.text_auth_mode),
            text_capabilities=ProviderProfileCapabilities(
                chat_completions=text.text_capabilities.chat_completions,
                json_object=text.text_capabilities.json_object,
                json_schema=text.text_capabilities.json_schema,
            ),
            text_context_window_tokens=text.text_context_window_tokens,
            text_max_output_tokens=text.text_max_output_tokens,
            text_temperature=text.text_temperature,
            text_max_concurrency=text.text_max_concurrency,
            text_connect_timeout_seconds=text.text_connect_timeout_seconds,
            text_attempt_timeout_seconds=text.text_attempt_timeout_seconds,
            image_provider=media.image_provider,
            image_base_url=media.image_base_url,
            image_model=media.image_model,
            image_auth_mode=media.image_auth_mode,
            video_provider=media.video_provider,
            video_base_url=media.video_base_url,
            video_model=media.video_model,
            video_auth_mode=media.video_auth_mode,
            profile_version=profile.revision,
            profile_hash=text.profile_hash,
            text_key_available=has_server_key(profile.profile_id),
            image_key_available=media.image_key_available,
            video_key_available=media.video_key_available,
            revision=profile.revision,
            updated_at=profile.updated_at,
        )

    def effective_provider_settings() -> ProviderSettings:
        """Compatibility projection: active text profile plus global media settings."""

        media = _merge_provider_settings(
            repo.get_provider_settings(), public_defaults, availability
        )
        return provider_settings_projection(active_text_profile(), media)

    def provider_snapshot(profile_id: str | None = None) -> dict[str, Any]:
        selected = (
            repo.get_text_provider_profile(profile_id)
            if profile_id is not None
            else active_text_profile()
        )
        if not selected.enabled:
            raise InvalidTransitionError(
                f"text provider profile {selected.profile_id} is disabled; enable it before admitting a new run"
            )
        # Existing V2 profile settings keep their exact stored/hash contract.
        # Only a newly admitted run gets the additive V3 frozen adapter fields.
        values = selected.configuration.model_dump(
            mode="python", by_alias=False, exclude={"profile_hash"}
        )
        values.update(
            profile_schema_version=3,
            profile_id=selected.profile_id,
            profile_version=selected.revision,
            profile_hash="",
            adapter_id=selected.adapter_id,
            adapter_version=selected.adapter_version,
        )
        return TextProviderProfileSnapshotV3.model_validate(values).model_dump(
            mode="json", by_alias=True
        )

    def readiness_for(profile: TextProviderProfile) -> TextBackendReadiness:
        if not profile.enabled:
            return TextBackendReadiness(
                profile_id=profile.profile_id,
                profile_revision=profile.revision,
                state="disabled",
                reason_code="readiness.profile_disabled",
            )
        observation = readiness_observations.get(profile.profile_id)
        if observation is None or observation.profile_revision != profile.revision:
            return TextBackendReadiness(
                profile_id=profile.profile_id,
                profile_revision=profile.revision,
                state="unverified",
                reason_code="readiness.not_checked",
            )
        return observation

    def store_readiness(
        profile: TextProviderProfile, state: str, reason_code: str
    ) -> TextBackendReadiness:
        observation = TextBackendReadiness(
            profile_id=profile.profile_id,
            profile_revision=profile.revision,
            state=state,
            reason_code=reason_code,
            observed_at=datetime.now(timezone.utc),
        )
        readiness_observations[profile.profile_id] = observation
        return observation

    def profile_view(profile: TextProviderProfile) -> TextProviderProfileView:
        return TextProviderProfileView(
            **profile.model_dump(mode="python"),
            server_key_available=has_server_key(profile.profile_id),
            readiness=readiness_for(profile),
        )

    def profiles_response() -> TextProviderProfilesResponse:
        selection = repo.get_provider_profile_selection()
        return TextProviderProfilesResponse(
            profiles=[
                profile_view(profile) for profile in repo.list_text_provider_profiles()
            ],
            active_profile_id=selection.active_profile_id,
            selection_revision=selection.revision,
            presets={
                preset.value: preset_values(preset)
                for preset in (
                    PresetId.COMPATIBLE_V1,
                    PresetId.QUALITY_REASONING_V1,
                    PresetId.FINAL_ONLY_V1,
                )
            },
            trusted_adapters=DEFAULT_TEXT_ADAPTER_REGISTRY.supported(),
        )

    def require_trusted_adapter(adapter_id: str, adapter_version: str) -> None:
        supported = {
            (item["adapterId"], item["adapterVersion"])
            for item in DEFAULT_TEXT_ADAPTER_REGISTRY.supported()
        }
        if (adapter_id, adapter_version) not in supported:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="unsupported text provider adapter selection",
            )

    def text_submission_session_key(
        snapshot: Mapping[str, Any], request: Request
    ) -> str | None:
        """Resolve request-scoped auth without touching a key for authMode=none."""

        auth_mode = str(
            snapshot.get("textAuthMode")
            or snapshot.get("text_auth_mode")
            or ProviderAuthMode.BEARER.value
        )
        if auth_mode == ProviderAuthMode.NONE.value:
            return None
        profile_id = str(
            snapshot.get("profileId")
            or snapshot.get("profile_id")
            or DEFAULT_PROVIDER_PROFILE_ID
        )
        session_key = _session_api_key(request)
        if session_key is None and not has_server_key(profile_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"text provider profile {profile_id!r} requires a server key "
                    "or a browser-session key"
                ),
            )
        return session_key

    def submit_text_run(run: GenerationRun, request: Request) -> None:
        if run_scheduler is None:
            return
        session_key = text_submission_session_key(run.provider_snapshot, request)
        try:
            if session_key is None:
                run_scheduler.submit(run.id)
            else:
                run_scheduler.submit(run.id, session_api_key=session_key)
        except SecretLeaseError as error:
            # Safe restart recovery can leave a bearer run queued while its
            # browser-only credential is unavailable.  It remains resumable;
            # never turn the missing ephemeral value into durable evidence.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="this queued run needs its profile's browser-session key",
            ) from error

    def check_text_backend(
        profile: TextProviderProfile,
        request: Request,
        *,
        snapshot: Mapping[str, Any] | None = None,
        record_observation: bool = True,
    ) -> TextBackendReadiness:
        """Perform one optional non-generative adapter preflight.

        A missing cheap check is explicitly unverified.  The temporary browser
        lease is never stored in the observation or profile state.
        """

        if not profile.enabled and snapshot is None:
            return readiness_for(profile)
        frozen_snapshot = snapshot or provider_snapshot(profile.profile_id)

        def observed(state: str, reason_code: str) -> TextBackendReadiness:
            if record_observation:
                return store_readiness(profile, state, reason_code)
            return TextBackendReadiness(
                profile_id=str(
                    frozen_snapshot.get("profileId")
                    or frozen_snapshot.get("profile_id")
                    or profile.profile_id
                ),
                profile_revision=int(
                    frozen_snapshot.get("profileVersion")
                    or frozen_snapshot.get("profile_version")
                    or profile.revision
                ),
                state=state,
                reason_code=reason_code,
            )

        # Lightweight embedding/tests that do not install a runtime resolver
        # cannot claim a protocol preflight.  They remain explicitly
        # unverified; the production runtime always injects its resolver.
        if text_provider_resolver is None:
            return observed("unverified", "readiness.check_unsupported")
        temporary_vault: InMemorySecretVault | None = None
        lease: SecretLease | None = None
        try:
            if frozen_snapshot["textAuthMode"] == ProviderAuthMode.BEARER.value:
                session_key = _session_api_key(request)
                if session_key is not None:
                    temporary_vault = InMemorySecretVault()
                    temporary_vault.put("preflight", session_key)
                    lease = temporary_vault.lease(
                        "preflight", ttl_seconds=60, max_uses=1
                    )
                elif text_secret_source is not None:
                    lease = text_secret_source.lease_for_profile(
                        profile.profile_id, auth_mode=ProviderAuthMode.BEARER
                    )
                else:
                    return observed(
                        "authentication_failed", "readiness.credential_unavailable"
                    )
            adapter, _model = text_provider_resolver.resolve(frozen_snapshot)
            checker = getattr(adapter, "check_readiness", None)
            if checker is None:
                return observed("unverified", "readiness.check_unsupported")
            result = checker(str(frozen_snapshot["textModel"]), lease)
            return observed(result.state, result.reason_code)
        except SecretLeaseError:
            return observed("authentication_failed", "readiness.credential_unavailable")
        except ValueError:
            return observed("capability_mismatch", "readiness.adapter_unsupported")
        except Exception:
            # A preflight has no creative request body, so its failed request
            # is a definite inability to establish readiness, not an unknown
            # generation outcome.  Keep all transport details server-private.
            return observed("unreachable", "readiness.preflight_failed")
        finally:
            if lease is not None:
                lease.revoke()
            if temporary_vault is not None:
                temporary_vault.clear()

    def admit_text_backend(
        profile_id: str | None,
        request: Request,
        *,
        frozen_snapshot: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        selected = (
            repo.get_text_provider_profile(profile_id)
            if profile_id
            else active_text_profile()
        )
        snapshot = (
            dict(frozen_snapshot)
            if frozen_snapshot is not None
            else provider_snapshot(selected.profile_id)
        )
        frozen_revision = snapshot.get("profileVersion") or snapshot.get(
            "profile_version"
        )
        observation = check_text_backend(
            selected,
            request,
            snapshot=snapshot,
            record_observation=(
                frozen_revision is None or int(frozen_revision) == selected.revision
            ),
        )
        if observation.state in {
            "disabled",
            "missing_configuration",
            "unreachable",
            "authentication_failed",
            "model_mismatch",
            "capability_mismatch",
        }:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"selected text backend is {observation.state} "
                    f"({observation.reason_code}); re-probe or correct this profile before creating a run"
                ),
            )
        return snapshot

    register_api_error_handlers(app)
    register_project_routes(app, repo)
    register_video_routes(app, repo)
    register_managed_media_routes(app, repo, selectable_h3_target)
    register_image_job_routes(app, repo, selectable_h3_target)
    register_generation_routes(
        app,
        repo,
        run_scheduler=run_scheduler,
        admit_text_backend=admit_text_backend,
        submit_text_run=submit_text_run,
        text_submission_session_key=text_submission_session_key,
    )
    register_text_profile_routes(
        app,
        repo,
        public_defaults=public_defaults,
        availability=availability,
        readiness_observations=readiness_observations,
        effective_provider_settings=effective_provider_settings,
        provider_settings_projection=provider_settings_projection,
        profiles_response=profiles_response,
        require_trusted_adapter=require_trusted_adapter,
        profile_view=profile_view,
        check_text_backend=check_text_backend,
    )

    def observe_definite_generation_failure(run: GenerationRun) -> None:
        """Reflect only certain provider failures into ephemeral readiness."""

        code = run.failure_code or ""
        if code == "provider.outcome_unknown" or not (
            code == "provider.request_not_sent" or code.startswith("provider.http_")
        ):
            return
        profile_id = str(
            run.provider_snapshot.get("profileId")
            or run.provider_snapshot.get("profile_id")
            or DEFAULT_PROVIDER_PROFILE_ID
        )
        try:
            profile = repo.get_text_provider_profile(profile_id)
        except NotFoundError:
            return
        frozen_revision = run.provider_snapshot.get(
            "profileVersion"
        ) or run.provider_snapshot.get("profile_version")
        if frozen_revision is not None and int(frozen_revision) != profile.revision:
            return
        if code in {"provider.http_401", "provider.http_403"}:
            store_readiness(
                profile,
                "authentication_failed",
                "readiness.generation_authentication_rejected",
            )
        else:
            store_readiness(
                profile, "unreachable", "readiness.generation_transport_failed"
            )

    set_completion_observer = getattr(run_scheduler, "set_completion_observer", None)
    if callable(set_completion_observer):
        set_completion_observer(observe_definite_generation_failure)

    if static_dir is not None:
        app.mount(
            "/v2",
            StaticFiles(directory=static_dir, html=True, check_dir=False),
            name="v2-static",
        )

    return app
