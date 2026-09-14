from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request, status
from pydantic import ValidationError

from ..domain import (
    ProviderSettings,
)
from ..persistence import SQLiteRepository
from ..provider_profiles import (
    ProviderProfileSelection,
)


from .models import (
    ProviderSettingsUpdate,
    TextProviderProfilesResponse,
    TextProviderProfileView,
    TextProviderProfileCreate,
    TextProviderProfileUpdate,
    TextProviderProfileActivate,
    TextProviderProfileAvailabilityUpdate,
    TextProviderProbeResponse,
    _merge_provider_settings,
)
from .text_admission import TextAdmissionService


def register_text_profile_routes(
    app: FastAPI,
    repo: SQLiteRepository,
    *,
    admission: TextAdmissionService,
) -> None:
    @app.get("/api/v2/provider-settings", response_model=ProviderSettings)
    def get_provider_settings() -> ProviderSettings:
        return admission.effective_provider_settings()

    @app.put("/api/v2/provider-settings", response_model=ProviderSettings)
    def put_provider_settings(body: ProviderSettingsUpdate) -> ProviderSettings:
        updates = body.model_dump(
            mode="python",
            by_alias=False,
            exclude_unset=True,
            exclude={"expected_profile_id", "expected_revision"},
        )
        profile, persisted_media = repo.update_provider_settings_projection(
            expected_profile_id=body.expected_profile_id,
            expected_profile_revision=body.expected_revision,
            updates=updates,
            defaults=admission.public_defaults,
        )
        media = _merge_provider_settings(
            persisted_media, admission.public_defaults, admission.key_availability
        )
        return admission.provider_settings_projection(profile, media)

    @app.get(
        "/api/v2/text-provider-profiles",
        response_model=TextProviderProfilesResponse,
    )
    def list_text_provider_profiles() -> TextProviderProfilesResponse:
        return admission.profiles_response()

    @app.post(
        "/api/v2/text-provider-profiles",
        response_model=TextProviderProfileView,
        status_code=status.HTTP_201_CREATED,
    )
    def create_text_provider_profile(
        body: TextProviderProfileCreate,
    ) -> TextProviderProfileView:
        try:
            if body.adapter_id is not None and body.adapter_version is not None:
                admission.require_trusted_adapter(body.adapter_id, body.adapter_version)
            elif body.copy_from_profile_id is not None:
                copied = repo.get_text_provider_profile(body.copy_from_profile_id)
                admission.require_trusted_adapter(copied.adapter_id, copied.adapter_version)
            profile = repo.create_text_provider_profile(
                body.profile_id,
                body.display_name,
                configuration=body.configuration,
                copy_from_profile_id=body.copy_from_profile_id,
                adapter_id=body.adapter_id,
                adapter_version=body.adapter_version,
            )
        except ValidationError:
            raise
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="invalid text provider profile configuration",
            ) from error
        admission.readiness_observations.pop(profile.profile_id, None)
        return admission.profile_view(profile)

    @app.get(
        "/api/v2/text-provider-profiles/{profile_id}",
        response_model=TextProviderProfileView,
    )
    def get_text_provider_profile(profile_id: str) -> TextProviderProfileView:
        return admission.profile_view(repo.get_text_provider_profile(profile_id))

    @app.put(
        "/api/v2/text-provider-profiles/{profile_id}",
        response_model=TextProviderProfileView,
    )
    def update_text_provider_profile(
        profile_id: str,
        body: TextProviderProfileUpdate,
    ) -> TextProviderProfileView:
        try:
            current = repo.get_text_provider_profile(profile_id)
            adapter_id = body.adapter_id or current.adapter_id
            adapter_version = body.adapter_version or current.adapter_version
            admission.require_trusted_adapter(adapter_id, adapter_version)
            updated = repo.update_text_provider_profile(
                profile_id,
                body.expected_revision,
                display_name=body.display_name,
                configuration=body.configuration,
                adapter_id=adapter_id,
                adapter_version=adapter_version,
            )
            if updated.revision != body.expected_revision:
                admission.readiness_observations.pop(profile_id, None)
            return admission.profile_view(updated)
        except ValidationError:
            raise
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="invalid text provider profile configuration",
            ) from error

    @app.delete(
        "/api/v2/text-provider-profiles/{profile_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_text_provider_profile(
        profile_id: str,
        expected_revision: Annotated[int, Query(alias="expectedRevision", ge=0)],
    ) -> None:
        repo.delete_text_provider_profile(profile_id, expected_revision)

    @app.post(
        "/api/v2/text-provider-profiles/{profile_id}/activate",
        response_model=ProviderProfileSelection,
    )
    def activate_text_provider_profile(
        profile_id: str,
        body: TextProviderProfileActivate,
    ) -> ProviderProfileSelection:
        return repo.activate_text_provider_profile(
            profile_id, body.expected_selection_revision
        )

    @app.put(
        "/api/v2/text-provider-profiles/{profile_id}/availability",
        response_model=TextProviderProfileView,
    )
    def set_text_provider_profile_availability(
        profile_id: str,
        body: TextProviderProfileAvailabilityUpdate,
    ) -> TextProviderProfileView:
        updated = repo.set_text_provider_profile_enabled(
            profile_id,
            body.expected_availability_revision,
            enabled=body.enabled,
        )
        if updated.availability_revision != body.expected_availability_revision:
            admission.readiness_observations.pop(profile_id, None)
        return admission.profile_view(updated)

    @app.post(
        "/api/v2/text-provider-profiles/{profile_id}/probe",
        response_model=TextProviderProbeResponse,
    )
    def probe_text_provider_profile(
        profile_id: str,
        request: Request,
    ) -> TextProviderProbeResponse:
        profile = repo.get_text_provider_profile(profile_id)
        return TextProviderProbeResponse.model_validate(
            admission.check_text_backend(profile, request).model_dump(mode="python")
        )
