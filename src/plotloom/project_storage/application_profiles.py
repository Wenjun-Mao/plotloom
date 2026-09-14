"""Application-owned text-profile control plane for the production folder runtime."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..domain import ProviderSettings, utc_now
from ..exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ..provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID,
    ProviderProfileSelection,
    TextProviderProfile,
    TextProviderProfileSnapshot,
    TextProviderProfileSnapshotV3,
)
from .application_store import ApplicationProfile, ApplicationStore
from .format import ProjectStorageConflictError, ProjectStorageError


class ApplicationProfileRepository:
    """Adapt installation storage to the existing profile-admission contract.

    Project repositories intentionally never receive this object. It owns the
    mutable public profile and selection records that are frozen into a run at
    admission time.
    """

    def __init__(self, store: ApplicationStore, defaults: ProviderSettings) -> None:
        self.store = store
        self.defaults = defaults

    def _application_profile(self, profile_id: str) -> ApplicationProfile:
        with self.store._read() as connection:  # noqa: SLF001 - same storage boundary
            row = connection.execute(
                "SELECT profile_id, revision, configuration_json, updated_at "
                "FROM application_profiles WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"text provider profile not found: {profile_id}")
        return self.store._profile_from_row(row)  # noqa: SLF001 - typed decoder

    def _metadata(self, profile_id: str) -> dict[str, Any]:
        with self.store._read() as connection:  # noqa: SLF001 - same storage boundary
            row = connection.execute(
                "SELECT display_name, enabled, availability_revision, adapter_id, "
                "adapter_version, created_at FROM application_text_profile_metadata "
                "WHERE profile_id = ?",
                (profile_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"text provider profile metadata not found: {profile_id}")
        return dict(row)

    @staticmethod
    def _snapshot(
        profile: ApplicationProfile,
        *,
        adapter_id: str,
        adapter_version: str,
    ) -> TextProviderProfileSnapshotV3:
        values = dict(profile.configuration)
        values.update(
            profileSchemaVersion=3,
            profileId=profile.profile_id,
            profileVersion=profile.revision,
            profileHash="",
            adapterId=adapter_id,
            adapterVersion=adapter_version,
        )
        try:
            return TextProviderProfileSnapshotV3.model_validate(values)
        except ValueError as error:
            raise ProjectStorageError(
                "application text profile is not a valid secret-free V3 profile"
            ) from error

    def _profile(self, profile_id: str) -> TextProviderProfile:
        application = self._application_profile(profile_id)
        metadata = self._metadata(profile_id)
        snapshot = self._snapshot(
            application,
            adapter_id=str(metadata["adapter_id"]),
            adapter_version=str(metadata["adapter_version"]),
        )
        return TextProviderProfile(
            profile_id=profile_id,
            display_name=str(metadata["display_name"]),
            configuration=snapshot,
            revision=application.revision,
            enabled=bool(metadata["enabled"]),
            availability_revision=int(metadata["availability_revision"]),
            adapter_id=str(metadata["adapter_id"]),
            adapter_version=str(metadata["adapter_version"]),
            created_at=metadata["created_at"],
            updated_at=application.updated_at,
        )

    @staticmethod
    def _configuration_values(
        configuration: TextProviderProfileSnapshot | Mapping[str, Any],
    ) -> dict[str, Any]:
        """Normalize an API's camel-case or a caller's Python profile mapping."""

        if isinstance(configuration, TextProviderProfileSnapshot):
            return configuration.model_dump(mode="python", by_alias=False)
        values = dict(configuration)
        try:
            return TextProviderProfileSnapshotV3.model_validate(values).model_dump(
                mode="python", by_alias=False
            )
        except ValueError:
            return TextProviderProfileSnapshot.model_validate(values).model_dump(
                mode="python", by_alias=False
            )

    def bootstrap_default_text_provider_profile(
        self, environment_default: TextProviderProfileSnapshot
    ) -> TextProviderProfile:
        try:
            profile = self._profile(DEFAULT_PROVIDER_PROFILE_ID)
        except NotFoundError:
            profile = self.create_text_provider_profile(
                DEFAULT_PROVIDER_PROFILE_ID,
                "Default",
                configuration=environment_default,
            )
        try:
            self.get_provider_profile_selection()
        except NotFoundError:
            self.activate_text_provider_profile(profile.profile_id, 0)
        return profile

    def get_text_provider_profile(self, profile_id: str) -> TextProviderProfile:
        return self._profile(profile_id)

    def list_text_provider_profiles(self) -> list[TextProviderProfile]:
        with self.store._read() as connection:  # noqa: SLF001 - same storage boundary
            rows = connection.execute(
                "SELECT profile_id FROM application_text_profile_metadata ORDER BY profile_id"
            ).fetchall()
        return [self._profile(str(row["profile_id"])) for row in rows]

    def get_provider_profile_selection(self) -> ProviderProfileSelection:
        with self.store._read() as connection:  # noqa: SLF001 - same storage boundary
            row = connection.execute(
                "SELECT profile_id, revision, updated_at "
                "FROM application_text_profile_selection WHERE id = 1"
            ).fetchone()
        if row is None:
            raise NotFoundError("text provider profile selection has not been initialized")
        return ProviderProfileSelection(
            active_profile_id=row["profile_id"],
            revision=row["revision"],
            updated_at=row["updated_at"],
        )

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
        if copy_from_profile_id is not None:
            source = self._profile(copy_from_profile_id)
            configuration = source.configuration
            adapter_id = adapter_id or source.adapter_id
            adapter_version = adapter_version or source.adapter_version
        assert configuration is not None
        values = self._configuration_values(configuration)
        values.update(
            profile_schema_version=3,
            profile_id=profile_id,
            profile_version=1,
            profile_hash="",
            adapter_id=adapter_id or "openai_compatible",
            adapter_version=adapter_version or "1",
        )
        parsed = TextProviderProfileSnapshotV3.model_validate(values)
        try:
            self.store.save_text_profile_record(
                profile_id,
                parsed.model_dump(mode="json", by_alias=True),
                display_name=display_name.strip(),
                adapter_id=parsed.adapter_id,
                adapter_version=parsed.adapter_version,
                expected_revision=0,
            )
        except ProjectStorageConflictError as error:
            raise InvalidTransitionError("text provider profile already exists") from error
        return self._profile(profile_id)

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
        current = self._profile(profile_id)
        if current.revision != expected_revision:
            raise RevisionConflictError("text-provider-profile", expected_revision, current.revision)
        next_adapter_id = adapter_id or current.adapter_id
        next_adapter_version = adapter_version or current.adapter_version
        values = self._configuration_values(configuration)
        values.update(
            profile_schema_version=3,
            profile_id=profile_id,
            profile_version=current.revision + 1,
            profile_hash="",
            adapter_id=next_adapter_id,
            adapter_version=next_adapter_version,
        )
        parsed = TextProviderProfileSnapshotV3.model_validate(values)
        try:
            self.store.save_text_profile_record(
                profile_id,
                parsed.model_dump(mode="json", by_alias=True),
                display_name=display_name.strip(),
                adapter_id=next_adapter_id,
                adapter_version=next_adapter_version,
                expected_revision=expected_revision,
            )
        except ProjectStorageConflictError as error:
            raise RevisionConflictError("text-provider-profile", expected_revision, current.revision) from error
        return self._profile(profile_id)

    def activate_text_provider_profile(
        self, profile_id: str, expected_selection_revision: int
    ) -> ProviderProfileSelection:
        self._profile(profile_id)
        now = utc_now()
        with self.store._write() as connection:  # noqa: SLF001 - same storage boundary
            current = connection.execute(
                "SELECT revision FROM application_text_profile_selection WHERE id = 1"
            ).fetchone()
            revision = int(current["revision"]) if current is not None else 0
            if revision != expected_selection_revision:
                raise RevisionConflictError("text-provider-profile-selection", expected_selection_revision, revision)
            next_revision = revision + 1
            connection.execute(
                "INSERT INTO application_text_profile_selection (id, profile_id, revision, updated_at) "
                "VALUES (1, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET profile_id = excluded.profile_id, "
                "revision = excluded.revision, updated_at = excluded.updated_at",
                (profile_id, next_revision, now.isoformat()),
            )
            connection.execute(
                "INSERT INTO application_preferences (preference_key, profile_id) VALUES ('selected_profile', ?) "
                "ON CONFLICT(preference_key) DO UPDATE SET profile_id = excluded.profile_id",
                (profile_id,),
            )
        return self.get_provider_profile_selection()

    def set_text_provider_profile_enabled(
        self, profile_id: str, expected_availability_revision: int, *, enabled: bool
    ) -> TextProviderProfile:
        current = self._profile(profile_id)
        if current.availability_revision != expected_availability_revision:
            raise RevisionConflictError(
                "text-provider-profile-availability",
                expected_availability_revision,
                current.availability_revision,
            )
        with self.store._write() as connection:  # noqa: SLF001 - same storage boundary
            connection.execute(
                "UPDATE application_text_profile_metadata SET enabled = ?, availability_revision = ? "
                "WHERE profile_id = ?",
                (int(enabled), current.availability_revision + 1, profile_id),
            )
        return self._profile(profile_id)

    def delete_text_provider_profile(self, profile_id: str, expected_revision: int) -> None:
        current = self._profile(profile_id)
        if current.revision != expected_revision:
            raise RevisionConflictError("text-provider-profile", expected_revision, current.revision)
        selection = self.get_provider_profile_selection()
        if selection.active_profile_id == profile_id:
            raise InvalidTransitionError("cannot delete the active text provider profile")
        with self.store._write() as connection:  # noqa: SLF001 - same storage boundary
            connection.execute("DELETE FROM application_text_profile_metadata WHERE profile_id = ?", (profile_id,))
            connection.execute("DELETE FROM application_profiles WHERE profile_id = ?", (profile_id,))

    def get_provider_settings(self) -> ProviderSettings:
        return self.defaults

    def put_provider_settings(self, settings: ProviderSettings) -> ProviderSettings:
        raise InvalidTransitionError("media dispatch settings are configured at startup")

    def update_provider_settings_projection(
        self,
        *,
        expected_profile_id: str,
        expected_profile_revision: int,
        updates: Mapping[str, Any],
        defaults: ProviderSettings,
    ) -> tuple[TextProviderProfile, ProviderSettings]:
        current = self._profile(expected_profile_id)
        values = current.configuration.model_dump(mode="python", by_alias=False)
        text_keys = {
            "text_provider", "text_base_url", "text_model", "text_auth_mode",
            "text_capabilities", "text_context_window_tokens", "text_max_output_tokens",
            "text_temperature", "text_max_concurrency", "text_connect_timeout_seconds",
            "text_attempt_timeout_seconds",
        }
        values.update({key: value for key, value in updates.items() if key in text_keys})
        updated = self.update_text_provider_profile(
            expected_profile_id,
            expected_profile_revision,
            display_name=current.display_name,
            configuration=values,
            adapter_id=current.adapter_id,
            adapter_version=current.adapter_version,
        )
        return updated, defaults
