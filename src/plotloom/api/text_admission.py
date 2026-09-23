from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from fastapi import HTTPException, Request, status

from ..domain import (
    GenerationRun,
    ProviderAuthMode,
    ProviderProfileCapabilities,
    ProviderSettings,
)
from ..exceptions import InvalidTransitionError, NotFoundError
from ..generation.exceptions import SecretLeaseError
from ..generation.secrets import InMemorySecretVault, SecretLease
from ..provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID,
    PresetId,
    TextProviderProfile,
    TextProviderProfileSnapshotV3,
    preset_values,
)
from ..text_adapters import DEFAULT_TEXT_ADAPTER_REGISTRY
from .models import (
    RunScheduler,
    TextBackendReadiness,
    TextProfileSecretSource,
    TextProviderProfileView,
    TextProviderProfilesResponse,
    TextProviderResolver,
    _merge_provider_settings,
    _session_api_key,
)


class TextAdmissionService:
    """Own ephemeral text-backend admission for one FastAPI application.

    Profile records remain repository-owned. Readiness observations and browser
    credentials deliberately remain only in this service's application lifetime.
    """

    def __init__(
        self,
        repository: Any,
        *,
        run_scheduler: RunScheduler | None,
        public_defaults: ProviderSettings,
        key_availability: Mapping[str, bool],
        profile_key_available: Callable[[str], bool] | None,
        text_provider_resolver: TextProviderResolver | None,
        text_secret_source: TextProfileSecretSource | None,
    ) -> None:
        self.repository = repository
        self.run_scheduler = run_scheduler
        self.public_defaults = public_defaults
        self.key_availability = dict(key_availability)
        self.profile_key_available = profile_key_available
        self.text_provider_resolver = text_provider_resolver
        self.text_secret_source = text_secret_source
        self.readiness_observations: dict[str, TextBackendReadiness] = {}

    def has_server_key(self, profile_id: str) -> bool:
        if self.profile_key_available is not None:
            return bool(self.profile_key_available(profile_id))
        if self.text_secret_source is not None:
            return bool(self.text_secret_source.server_key_available(profile_id))
        return profile_id == DEFAULT_PROVIDER_PROFILE_ID and bool(
            self.key_availability.get("text_key_available", False)
        )

    def active_text_profile(self) -> TextProviderProfile:
        selection = self.repository.get_provider_profile_selection()
        return self.repository.get_text_provider_profile(selection.active_profile_id)

    def provider_settings_projection(
        self,
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
            text_key_available=self.has_server_key(profile.profile_id),
            image_key_available=media.image_key_available,
            video_key_available=media.video_key_available,
            revision=profile.revision,
            updated_at=profile.updated_at,
        )

    def effective_provider_settings(self) -> ProviderSettings:
        """Compatibility projection: active text profile plus global media settings."""

        media = _merge_provider_settings(
            self.repository.get_provider_settings(),
            self.public_defaults,
            self.key_availability,
        )
        return self.provider_settings_projection(self.active_text_profile(), media)

    def provider_snapshot(self, profile_id: str | None = None) -> dict[str, Any]:
        selected = (
            self.repository.get_text_provider_profile(profile_id)
            if profile_id is not None
            else self.active_text_profile()
        )
        if not selected.enabled:
            raise InvalidTransitionError(
                f"text provider profile {selected.profile_id} is disabled; enable it before admitting a new run"
            )
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

    def readiness_for(self, profile: TextProviderProfile) -> TextBackendReadiness:
        if not profile.enabled:
            return TextBackendReadiness(
                profile_id=profile.profile_id,
                profile_revision=profile.revision,
                state="disabled",
                reason_code="readiness.profile_disabled",
            )
        observation = self.readiness_observations.get(profile.profile_id)
        if observation is None or observation.profile_revision != profile.revision:
            return TextBackendReadiness(
                profile_id=profile.profile_id,
                profile_revision=profile.revision,
                state="unverified",
                reason_code="readiness.not_checked",
            )
        return observation

    def store_readiness(
        self, profile: TextProviderProfile, state: str, reason_code: str
    ) -> TextBackendReadiness:
        observation = TextBackendReadiness(
            profile_id=profile.profile_id,
            profile_revision=profile.revision,
            state=state,
            reason_code=reason_code,
            observed_at=datetime.now(timezone.utc),
        )
        self.readiness_observations[profile.profile_id] = observation
        return observation

    def profile_view(self, profile: TextProviderProfile) -> TextProviderProfileView:
        return TextProviderProfileView(
            **profile.model_dump(mode="python"),
            server_key_available=self.has_server_key(profile.profile_id),
            readiness=self.readiness_for(profile),
        )

    def profiles_response(self) -> TextProviderProfilesResponse:
        selection = self.repository.get_provider_profile_selection()
        return TextProviderProfilesResponse(
            profiles=[
                self.profile_view(profile)
                for profile in self.repository.list_text_provider_profiles()
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

    def require_trusted_adapter(self, adapter_id: str, adapter_version: str) -> None:
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
        self, snapshot: Mapping[str, Any], request: Request
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
        if session_key is None and not self.has_server_key(profile_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"text provider profile {profile_id!r} requires a server key "
                    "or a browser-session key"
                ),
            )
        return session_key

    def submit_text_run(self, run: GenerationRun, request: Request) -> None:
        if self.run_scheduler is None:
            return
        session_key = self.text_submission_session_key(run.provider_snapshot, request)
        try:
            if session_key is None:
                self.run_scheduler.submit(run.id)
            else:
                self.run_scheduler.submit(run.id, session_api_key=session_key)
        except SecretLeaseError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="this queued run needs its profile's browser-session key",
            ) from error

    def check_text_backend(
        self,
        profile: TextProviderProfile,
        request: Request,
        *,
        snapshot: Mapping[str, Any] | None = None,
        record_observation: bool = True,
    ) -> TextBackendReadiness:
        """Perform one non-generative adapter preflight without retaining secrets."""

        if not profile.enabled and snapshot is None:
            return self.readiness_for(profile)
        frozen_snapshot = snapshot or self.provider_snapshot(profile.profile_id)

        def observed(state: str, reason_code: str) -> TextBackendReadiness:
            if record_observation:
                return self.store_readiness(profile, state, reason_code)
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

        if self.text_provider_resolver is None:
            return observed("unverified", "readiness.check_unsupported")
        temporary_vault: InMemorySecretVault | None = None
        lease: SecretLease | None = None
        try:
            if frozen_snapshot["textAuthMode"] == ProviderAuthMode.BEARER.value:
                session_key = _session_api_key(request)
                if session_key is not None:
                    temporary_vault = InMemorySecretVault()
                    temporary_vault.put("preflight", session_key)
                    lease = temporary_vault.lease("preflight", ttl_seconds=60, max_uses=1)
                elif self.text_secret_source is not None:
                    lease = self.text_secret_source.lease_for_profile(
                        profile.profile_id, auth_mode=ProviderAuthMode.BEARER
                    )
                else:
                    return observed(
                        "authentication_failed", "readiness.credential_unavailable"
                    )
            adapter, _model = self.text_provider_resolver.resolve(frozen_snapshot)
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
            return observed("unreachable", "readiness.preflight_failed")
        finally:
            if lease is not None:
                lease.revoke()
            if temporary_vault is not None:
                temporary_vault.clear()

    def admit_text_backend(
        self,
        profile_id: str | None,
        request: Request,
        *,
        frozen_snapshot: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        selected = (
            self.repository.get_text_provider_profile(profile_id)
            if profile_id
            else self.active_text_profile()
        )
        snapshot = (
            dict(frozen_snapshot)
            if frozen_snapshot is not None
            else self.provider_snapshot(selected.profile_id)
        )
        frozen_revision = snapshot.get("profileVersion") or snapshot.get(
            "profile_version"
        )
        observation = self.check_text_backend(
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

    def observe_definite_generation_failure(self, run: GenerationRun) -> None:
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
            profile = self.repository.get_text_provider_profile(profile_id)
        except NotFoundError:
            return
        frozen_revision = run.provider_snapshot.get(
            "profileVersion"
        ) or run.provider_snapshot.get("profile_version")
        if frozen_revision is not None and int(frozen_revision) != profile.revision:
            return
        if code in {"provider.http_401", "provider.http_403"}:
            self.store_readiness(
                profile,
                "authentication_failed",
                "readiness.generation_authentication_rejected",
            )
        else:
            self.store_readiness(
                profile, "unreachable", "readiness.generation_transport_failed"
            )

    def install_completion_observer(self) -> None:
        set_completion_observer = getattr(
            self.run_scheduler, "set_completion_observer", None
        )
        if callable(set_completion_observer):
            set_completion_observer(self.observe_definite_generation_failure)
