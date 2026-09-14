"""Singleton public provider-settings persistence and compatibility projection."""

from __future__ import annotations

from typing import Any

from ...domain import PUBLIC_PROVIDER_SETTING_FIELDS, ProviderSettings, contains_secret_setting, contains_secret_value, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...provider_profiles import PresetId, TextProviderProfile, TextProviderProfileSnapshot
from ..schema import ProviderProfileSelectionRow, ProviderSettingsRow, TextProviderProfileRow
from .access import ApplicationControlAccess
from .profile_values import ApplicationProfileValues


class ProviderSettingsPersistence:
    """Own public media settings and the atomic active-profile projection."""

    def __init__(self, access: ApplicationControlAccess, values: ApplicationProfileValues) -> None:
        self._access = access
        self._values = values

    def get_provider_settings(self) -> ProviderSettings:
        with self._access.read() as session:
            row = session.get(ProviderSettingsRow, 1)
            if row is None:
                return ProviderSettings()
            data = dict(row.settings)
            data.update(
                profile_version=row.revision,
                revision=row.revision,
                updated_at=row.updated_at,
            )
            return ProviderSettings.model_validate(data)


    def put_provider_settings(self, settings: ProviderSettings) -> ProviderSettings:
        # ProviderSettings.extra=forbid is the security boundary: secret-shaped fields cannot enter storage.
        now = utc_now()
        data = settings.model_dump(
            mode="json",
            by_alias=False,
            exclude={
                "revision",
                "updated_at",
                "profile_version",
                "profile_hash",
                "text_key_available",
                "image_key_available",
                "video_key_available",
            },
        )
        with self._access.write() as session:
            row = session.get(ProviderSettingsRow, 1)
            if row is None:
                row = ProviderSettingsRow(id=1, settings=data, revision=1, updated_at=now)
                session.add(row)
            elif row.settings != data:
                row.settings = data
                row.revision += 1
                row.updated_at = now
            result = dict(row.settings)
            result.update(
                profile_version=row.revision,
                revision=row.revision,
                updated_at=row.updated_at,
            )
            return ProviderSettings.model_validate(result)

    def update_provider_settings_projection(
        self,
        *,
        expected_profile_id: str,
        expected_profile_revision: int,
        updates: dict[str, Any],
        defaults: ProviderSettings,
    ) -> tuple[TextProviderProfile, ProviderSettings]:
        """Atomically update the legacy active-profile/media projection.

        The compatibility endpoint spans two durable records: the selected
        named text profile and the singleton media settings.  Reading either
        outside this transaction would allow an activation or named-profile
        edit to interleave and make a stale form overwrite unrelated state.
        """

        if contains_secret_setting(updates) or contains_secret_value(updates):
            raise ValueError("public provider configuration must not contain secrets")
        with self._access.write() as session:
            selection = session.get(ProviderProfileSelectionRow, 1)
            if selection is None:
                raise NotFoundError("text provider profile selection has not been initialized")
            if selection.active_profile_id != expected_profile_id:
                raise InvalidTransitionError(
                    "active text provider profile changed; reload settings"
                )

            profile_row = session.get(TextProviderProfileRow, expected_profile_id)
            if profile_row is None:
                raise NotFoundError(
                    f"text provider profile not found: {expected_profile_id}"
                )
            if profile_row.revision != expected_profile_revision:
                raise RevisionConflictError(
                    f"text-provider-profile:{expected_profile_id}",
                    expected_profile_revision,
                    profile_row.revision,
                )

            media_row = session.get(ProviderSettingsRow, 1)
            if media_row is None:
                persisted = ProviderSettings()
            else:
                persisted_data = dict(media_row.settings)
                persisted_data.update(
                    profile_version=media_row.revision,
                    revision=media_row.revision,
                    updated_at=media_row.updated_at,
                )
                persisted = ProviderSettings.model_validate(persisted_data)

            effective_values = {
                field: (
                    getattr(defaults, field)
                    if persisted.revision == 0
                    else (
                        getattr(persisted, field)
                        if getattr(persisted, field) is not None
                        else getattr(defaults, field)
                    )
                )
                for field in PUBLIC_PROVIDER_SETTING_FIELDS
            }
            profile_configuration = TextProviderProfileSnapshot.model_validate(
                profile_row.settings
            )
            effective_values.update(
                profile_id=expected_profile_id,
                text_provider=profile_configuration.text_provider,
                text_base_url=profile_configuration.text_base_url,
                text_model=profile_configuration.text_model,
                text_auth_mode=profile_configuration.text_auth_mode,
                text_capabilities={
                    "chat_completions": profile_configuration.text_capabilities.chat_completions,
                    "json_object": profile_configuration.text_capabilities.json_object,
                    "json_schema": profile_configuration.text_capabilities.json_schema,
                },
                text_context_window_tokens=profile_configuration.text_context_window_tokens,
                text_max_output_tokens=profile_configuration.text_max_output_tokens,
                text_temperature=profile_configuration.text_temperature,
                text_max_concurrency=profile_configuration.text_max_concurrency,
                text_connect_timeout_seconds=profile_configuration.text_connect_timeout_seconds,
                text_attempt_timeout_seconds=profile_configuration.text_attempt_timeout_seconds,
            )
            effective_values.update(updates)
            settings = ProviderSettings.model_validate(effective_values)

            profile_values = profile_configuration.model_dump(
                mode="python", by_alias=False, exclude={"profile_hash"}
            )
            profile_values.update(
                text_provider=settings.text_provider,
                text_base_url=settings.text_base_url,
                text_model=settings.text_model,
                text_auth_mode=settings.text_auth_mode.value,
                text_capabilities={
                    **profile_configuration.text_capabilities.model_dump(mode="python"),
                    "chat_completions": settings.text_capabilities.chat_completions,
                    "json_object": settings.text_capabilities.json_object,
                    "json_schema": settings.text_capabilities.json_schema,
                },
                text_context_window_tokens=settings.text_context_window_tokens,
                text_max_output_tokens=settings.text_max_output_tokens,
                text_temperature=settings.text_temperature,
                text_max_concurrency=settings.text_max_concurrency,
                text_connect_timeout_seconds=settings.text_connect_timeout_seconds,
                text_attempt_timeout_seconds=settings.text_attempt_timeout_seconds,
            )
            if {
                "text_context_window_tokens",
                "text_max_output_tokens",
                "text_attempt_timeout_seconds",
            } & updates.keys():
                profile_values["preset_id"] = PresetId.CUSTOM
            proposed = self._values.profile_configuration_for_revision(
                expected_profile_id,
                profile_row.revision + 1,
                profile_values,
            )
            current_without_version = dict(profile_row.settings)
            proposed_without_version = proposed.model_dump(mode="json", by_alias=True)
            for key in ("profileVersion", "profileHash"):
                current_without_version.pop(key, None)
                proposed_without_version.pop(key, None)
            if current_without_version != proposed_without_version:
                profile_row.revision += 1
                profile_row.settings = proposed.model_dump(mode="json", by_alias=True)
                profile_row.updated_at = utc_now()

            now = utc_now()
            stored_settings = settings.model_dump(
                mode="json",
                by_alias=False,
                exclude={
                    "revision",
                    "updated_at",
                    "profile_version",
                    "profile_hash",
                    "text_key_available",
                    "image_key_available",
                    "video_key_available",
                },
            )
            if media_row is None:
                media_row = ProviderSettingsRow(
                    id=1,
                    settings=stored_settings,
                    revision=1,
                    updated_at=now,
                )
                session.add(media_row)
            elif media_row.settings != stored_settings:
                media_row.settings = stored_settings
                media_row.revision += 1
                media_row.updated_at = now

            session.flush()
            persisted_result = dict(media_row.settings)
            persisted_result.update(
                profile_version=media_row.revision,
                revision=media_row.revision,
                updated_at=media_row.updated_at,
            )
            return (
                self._values.text_provider_profile(profile_row),
                ProviderSettings.model_validate(persisted_result),
            )
