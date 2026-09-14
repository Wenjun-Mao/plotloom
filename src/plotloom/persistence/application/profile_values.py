"""Canonical value conversion and validation for application provider control."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...domain import contains_secret_setting, contains_secret_value
from ...provider_profiles import ProviderProfileSelection, TextProviderProfile, TextProviderProfileSnapshot
from ..codec import _stored_utc
from ..schema import ProviderProfileSelectionRow, TextProviderProfileRow


class ApplicationProfileValues:
    """Own pure profile/selection conversion and secret-free configuration shaping."""

    @staticmethod
    def text_provider_profile(row: TextProviderProfileRow) -> TextProviderProfile:
        configuration = TextProviderProfileSnapshot.model_validate(row.settings)
        return TextProviderProfile(
            profile_id=row.id, display_name=row.display_name, configuration=configuration,
            revision=row.revision, enabled=row.enabled,
            availability_revision=row.availability_revision, adapter_id=row.adapter_id,
            adapter_version=row.adapter_version, created_at=_stored_utc(row.created_at),
            updated_at=_stored_utc(row.updated_at),
        )

    @staticmethod
    def provider_profile_selection(row: ProviderProfileSelectionRow) -> ProviderProfileSelection:
        return ProviderProfileSelection(
            active_profile_id=row.active_profile_id, revision=row.revision,
            updated_at=_stored_utc(row.updated_at),
        )

    @staticmethod
    def profile_configuration_for_revision(
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


    @staticmethod
    def profile_id_from_snapshot(snapshot: Mapping[str, Any]) -> str | None:
        value = snapshot.get("profileId") or snapshot.get("profile_id")
        return value if isinstance(value, str) and value else None
