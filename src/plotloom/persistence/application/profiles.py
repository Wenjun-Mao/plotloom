"""Installation-owned public provider profiles and settings projections."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ContextManager

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import (
    PUBLIC_PROVIDER_SETTING_FIELDS, TERMINAL_RUN_STATUSES, ProviderSettings,
    contains_secret_setting, contains_secret_value, utc_now,
)
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID, PROFILE_ID_PATTERN, PresetId,
    ProviderProfileSelection, TextProviderProfile, TextProviderProfileSnapshot,
    is_v2_snapshot, is_v3_snapshot,
)
from ..codec import _stored_utc
from ..schema import (
    GenerationRunRow, ProviderProfileSelectionRow, ProviderSettingsRow,
    TextProviderProfileRow,
)


@dataclass(frozen=True)
class ApplicationControlAccess:
    """Only application-wide leases; project state is never reachable here."""

    read: Callable[[], ContextManager[Session]]
    write: Callable[[], ContextManager[Session]]


class ApplicationProfilePersistence:
    """Public settings and named text-profile control plane."""

    def __init__(self, access: ApplicationControlAccess) -> None:
        self._access = access

    @staticmethod
    def _text_provider_profile(row: TextProviderProfileRow) -> TextProviderProfile:
        configuration = TextProviderProfileSnapshot.model_validate(row.settings)
        return TextProviderProfile(
            profile_id=row.id, display_name=row.display_name, configuration=configuration,
            revision=row.revision, enabled=row.enabled,
            availability_revision=row.availability_revision, adapter_id=row.adapter_id,
            adapter_version=row.adapter_version, created_at=_stored_utc(row.created_at),
            updated_at=_stored_utc(row.updated_at),
        )

    @staticmethod
    def _provider_profile_selection(row: ProviderProfileSelectionRow) -> ProviderProfileSelection:
        return ProviderProfileSelection(
            active_profile_id=row.active_profile_id, revision=row.revision,
            updated_at=_stored_utc(row.updated_at),
        )

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

    def bootstrap_default_text_provider_profile(
        self,
        environment_default: TextProviderProfileSnapshot,
    ) -> TextProviderProfile:
        """Materialize the effective legacy/environment text config exactly once.

        Migration 0006 deliberately stores the old singleton payload without
        inventing V2 execution fields.  Runtime startup is the first layer that
        can see the trusted repo-root ``.env`` and host environment.  Once this
        method writes a V2 snapshot, later environment edits cannot silently
        change the saved profile or runs that reference it.
        """

        if environment_default.profile_id != DEFAULT_PROVIDER_PROFILE_ID:
            raise ValueError("the environment bootstrap snapshot must be for default")
        with self._access.write() as session:
            row = session.get(TextProviderProfileRow, DEFAULT_PROVIDER_PROFILE_ID)
            now = utc_now()
            if row is not None and is_v2_snapshot(row.settings):
                return self._text_provider_profile(row)

            legacy = dict(row.settings) if row is not None else {}
            if contains_secret_setting(legacy) or contains_secret_value(legacy):
                # Do not carry a credential forward from a legacy settings bag.
                legacy = {
                    key: value
                    for key, value in legacy.items()
                    if not contains_secret_setting({key: value})
                    and not contains_secret_value(value)
                }
            revision = row.revision if row is not None else 0
            values = environment_default.model_dump(
                mode="python",
                by_alias=False,
                exclude={"profile_hash"},
            )
            if revision > 0:
                aliases = {
                    "textProvider": "text_provider",
                    "textBaseUrl": "text_base_url",
                    "textModel": "text_model",
                    "textAuthMode": "text_auth_mode",
                    "textCapabilities": "text_capabilities",
                    "textContextWindowTokens": "text_context_window_tokens",
                    "textMaxOutputTokens": "text_max_output_tokens",
                    "textTemperature": "text_temperature",
                    "textMaxConcurrency": "text_max_concurrency",
                    "textConnectTimeoutSeconds": "text_connect_timeout_seconds",
                    "textAttemptTimeoutSeconds": "text_attempt_timeout_seconds",
                }
                for source, target in aliases.items():
                    legacy_value = legacy.get(source, legacy.get(target))
                    if legacy_value is not None:
                        if target == "text_capabilities" and isinstance(legacy_value, dict):
                            current = dict(values[target])
                            current.update(legacy_value)
                            values[target] = current
                        else:
                            values[target] = legacy_value
            values.update(
                profile_schema_version=2,
                profile_id=DEFAULT_PROVIDER_PROFILE_ID,
                profile_version=revision,
                profile_hash="",
            )
            try:
                configuration = TextProviderProfileSnapshot.model_validate(values)
            except ValueError:
                # A legacy public setting may legitimately differ from a named
                # published preset. Preserve it, but state that it is custom.
                values["preset_id"] = PresetId.CUSTOM
                configuration = TextProviderProfileSnapshot.model_validate(values)
            stored = configuration.model_dump(mode="json", by_alias=True)
            if row is None:
                row = TextProviderProfileRow(
                    id=DEFAULT_PROVIDER_PROFILE_ID,
                    display_name="Default",
                    settings=stored,
                    revision=revision,
                    enabled=True,
                    availability_revision=0,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
                session.flush()
            else:
                row.settings = stored
                row.updated_at = now

            selection = session.get(ProviderProfileSelectionRow, 1)
            if selection is None:
                session.add(
                    ProviderProfileSelectionRow(
                        id=1,
                        active_profile_id=DEFAULT_PROVIDER_PROFILE_ID,
                        revision=0,
                        updated_at=now,
                    )
                )
            return self._text_provider_profile(row)

    def get_text_provider_profile(self, profile_id: str) -> TextProviderProfile:
        with self._access.read() as session:
            row = session.get(TextProviderProfileRow, profile_id)
            if row is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            return self._text_provider_profile(row)

    def list_text_provider_profiles(self) -> list[TextProviderProfile]:
        with self._access.read() as session:
            rows = session.scalars(
                select(TextProviderProfileRow).order_by(TextProviderProfileRow.id)
            ).all()
            return [self._text_provider_profile(row) for row in rows]

    def get_provider_profile_selection(self) -> ProviderProfileSelection:
        with self._access.read() as session:
            row = session.get(ProviderProfileSelectionRow, 1)
            if row is None:
                raise NotFoundError("text provider profile selection has not been initialized")
            return self._provider_profile_selection(row)

    @staticmethod
    def _profile_configuration_for_revision(
        profile_id: str,
        revision: int,
        value: TextProviderProfileSnapshot | dict[str, Any],
    ) -> TextProviderProfileSnapshot:
        raw = (
            value.model_dump(mode="python", by_alias=False)
            if isinstance(value, TextProviderProfileSnapshot)
            else dict(value)
        )
        if contains_secret_setting(raw) or contains_secret_value(raw):
            raise ValueError("text provider profile configuration must not contain secrets")
        for key in (
            "profileHash",
            "profile_hash",
            "profileId",
            "profile_id",
            "profileVersion",
            "profile_version",
            "profileSchemaVersion",
            "profile_schema_version",
        ):
            raw.pop(key, None)
        raw.update(
            profile_schema_version=2,
            profile_id=profile_id,
            profile_version=revision,
            profile_hash="",
        )
        return TextProviderProfileSnapshot.model_validate(raw)

    def create_text_provider_profile(
        self,
        profile_id: str,
        display_name: str,
        *,
        configuration: TextProviderProfileSnapshot | dict[str, Any] | None = None,
        copy_from_profile_id: str | None = None,
        adapter_id: str | None = None,
        adapter_version: str | None = None,
    ) -> TextProviderProfile:
        if (configuration is None) == (copy_from_profile_id is None):
            raise ValueError("provide exactly one of configuration or copy_from_profile_id")
        if (adapter_id is None) != (adapter_version is None):
            raise ValueError("adapter_id and adapter_version must be provided together")
        if re.fullmatch(PROFILE_ID_PATTERN, profile_id) is None:
            raise ValueError("profile_id must match [a-z][a-z0-9_]{0,62}")
        normalized_name = display_name.strip()
        if not normalized_name:
            raise ValueError("display_name must not be blank")
        with self._access.write() as session:
            if session.get(TextProviderProfileRow, profile_id) is not None:
                raise InvalidTransitionError(f"text provider profile already exists: {profile_id}")
            if copy_from_profile_id is not None:
                source = session.get(TextProviderProfileRow, copy_from_profile_id)
                if source is None:
                    raise NotFoundError(
                        f"text provider profile not found: {copy_from_profile_id}"
                    )
                configuration = dict(source.settings)
            assert configuration is not None
            parsed = self._profile_configuration_for_revision(profile_id, 1, configuration)
            now = utc_now()
            row = TextProviderProfileRow(
                id=profile_id,
                display_name=normalized_name,
                settings=parsed.model_dump(mode="json", by_alias=True),
                revision=1,
                enabled=True,
                availability_revision=0,
                adapter_id=(
                    adapter_id
                    or (source.adapter_id if copy_from_profile_id is not None else "openai_compatible")
                ),
                adapter_version=(
                    adapter_version
                    or (source.adapter_version if copy_from_profile_id is not None else "1")
                ),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            session.flush()
            return self._text_provider_profile(row)

    def update_text_provider_profile(
        self,
        profile_id: str,
        expected_revision: int,
        *,
        display_name: str,
        configuration: TextProviderProfileSnapshot | dict[str, Any],
        adapter_id: str | None = None,
        adapter_version: str | None = None,
    ) -> TextProviderProfile:
        if (adapter_id is None) != (adapter_version is None):
            raise ValueError("adapter_id and adapter_version must be provided together")
        with self._access.write() as session:
            row = session.get(TextProviderProfileRow, profile_id)
            if row is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            if row.revision != expected_revision:
                raise RevisionConflictError(
                    f"text-provider-profile:{profile_id}", expected_revision, row.revision
                )
            normalized_name = display_name.strip()
            if not normalized_name:
                raise ValueError("display_name must not be blank")
            proposed = self._profile_configuration_for_revision(
                profile_id, row.revision + 1, configuration
            )
            current_without_version = dict(row.settings)
            proposed_without_version = proposed.model_dump(mode="json", by_alias=True)
            for key in ("profileVersion", "profileHash"):
                current_without_version.pop(key, None)
                proposed_without_version.pop(key, None)
            next_adapter_id = adapter_id or row.adapter_id
            next_adapter_version = adapter_version or row.adapter_version
            if (
                row.display_name == normalized_name
                and current_without_version == proposed_without_version
                and row.adapter_id == next_adapter_id
                and row.adapter_version == next_adapter_version
            ):
                return self._text_provider_profile(row)
            row.revision += 1
            row.display_name = normalized_name
            row.settings = proposed.model_dump(mode="json", by_alias=True)
            row.adapter_id = next_adapter_id
            row.adapter_version = next_adapter_version
            row.updated_at = utc_now()
            return self._text_provider_profile(row)

    def activate_text_provider_profile(
        self,
        profile_id: str,
        expected_selection_revision: int,
    ) -> ProviderProfileSelection:
        with self._access.write() as session:
            profile = session.get(TextProviderProfileRow, profile_id)
            if profile is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            if not profile.enabled:
                raise InvalidTransitionError(
                    "a disabled text provider profile cannot be activated; enable it first"
                )
            row = session.get(ProviderProfileSelectionRow, 1)
            if row is None:
                raise NotFoundError("text provider profile selection has not been initialized")
            if row.revision != expected_selection_revision:
                raise RevisionConflictError(
                    "text-provider-profile-selection",
                    expected_selection_revision,
                    row.revision,
                )
            if row.active_profile_id != profile_id:
                row.active_profile_id = profile_id
                row.revision += 1
                row.updated_at = utc_now()
            return self._provider_profile_selection(row)

    def set_text_provider_profile_enabled(
        self,
        profile_id: str,
        expected_availability_revision: int,
        *,
        enabled: bool,
    ) -> TextProviderProfile:
        """Toggle future-admission availability without rewriting profile config."""

        with self._access.write() as session:
            row = session.get(TextProviderProfileRow, profile_id)
            if row is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            if row.availability_revision != expected_availability_revision:
                raise RevisionConflictError(
                    f"text-provider-profile-availability:{profile_id}",
                    expected_availability_revision,
                    row.availability_revision,
                )
            if row.enabled != enabled:
                row.enabled = enabled
                row.availability_revision += 1
                row.updated_at = utc_now()
            return self._text_provider_profile(row)

    @staticmethod
    def _profile_id_from_snapshot(snapshot: Mapping[str, Any]) -> str | None:
        value = snapshot.get("profileId") or snapshot.get("profile_id")
        return value if isinstance(value, str) and value else None

    def _assert_new_run_profile_enabled(
        self, session: Session, provider_snapshot: Mapping[str, Any]
    ) -> None:
        """Guard fresh V2 admission without rewriting historical snapshot semantics.

        A V1 snapshot can contain the old singleton ``profileId`` field, but
        its JSON and hash deliberately remain on the pre-profile path and need
        not have a mutable profile row. Reading it must not synthesize a V2
        control-plane dependency. If that legacy name *does* resolve to an
        existing row, however, it is still a current request for a disabled
        backend and must not bypass its availability state.
        """

        profile_id = self._profile_id_from_snapshot(provider_snapshot)
        if profile_id is None:
            # ``validate_public_provider_snapshot`` has already validated V2
            # snapshots, so this protects direct repository callers if that
            # boundary changes rather than treating an anonymous V2 run as
            # available.
            if is_v3_snapshot(provider_snapshot):
                raise InvalidTransitionError(
                    "a managed V3 provider snapshot must name a registered profile before admitting a new run"
                )
            return
        profile = session.get(TextProviderProfileRow, profile_id)
        if profile is None:
            # The historic direct test/runtime path used an unmaterialized
            # default V2 profile. Preserve that exact compatibility path;
            # named V2 and every V3 admission remain control-plane bound.
            if profile_id == DEFAULT_PROVIDER_PROFILE_ID and not is_v3_snapshot(provider_snapshot):
                return
            if not is_v3_snapshot(provider_snapshot):
                raise InvalidTransitionError(
                    f"text provider profile {profile_id} is not registered; register it before admitting a new run"
                )
            raise InvalidTransitionError(
                f"text provider profile {profile_id} is not registered; register it before admitting a new run"
            )
        if not profile.enabled:
            raise InvalidTransitionError(
                f"text provider profile {profile_id} is disabled; enable it before admitting a new run"
            )

    def delete_text_provider_profile(
        self,
        profile_id: str,
        expected_revision: int,
    ) -> None:
        if profile_id == DEFAULT_PROVIDER_PROFILE_ID:
            raise InvalidTransitionError("the default text provider profile cannot be deleted")
        with self._access.write() as session:
            row = session.get(TextProviderProfileRow, profile_id)
            if row is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            if row.revision != expected_revision:
                raise RevisionConflictError(
                    f"text-provider-profile:{profile_id}", expected_revision, row.revision
                )
            selection = session.get(ProviderProfileSelectionRow, 1)
            if selection is not None and selection.active_profile_id == profile_id:
                raise InvalidTransitionError("the active text provider profile cannot be deleted")
            live_runs = session.scalars(
                select(GenerationRunRow).where(
                    GenerationRunRow.status.not_in(
                        [status.value for status in TERMINAL_RUN_STATUSES]
                    )
                )
            ).all()
            if any(
                candidate.provider_snapshot.get("profileId") == profile_id
                for candidate in live_runs
            ):
                raise InvalidTransitionError(
                    "a text provider profile referenced by a non-terminal run cannot be deleted"
                )
            session.delete(row)

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
            proposed = self._profile_configuration_for_revision(
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
                self._text_provider_profile(profile_row),
                ProviderSettings.model_validate(persisted_result),
            )


