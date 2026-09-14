"""Compatibility composition for application provider-control persistence.

The class retains the runtime-facing surface only.  Profile bootstrap, reusable
profile CRUD/admission, and settings projection each have focused owners; the
projection owner alone coordinates its two application rows in one transaction.
"""

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

from .access import ApplicationControlAccess
from .profile_admission import TextProviderProfileAdmissionPersistence
from .profile_bootstrap import DefaultProfileBootstrapPersistence
from .profile_catalog import TextProviderProfileCatalogPersistence
from .profile_settings import ProviderSettingsPersistence
from .profile_values import ApplicationProfileValues


class ApplicationProfilePersistence:
    """Explicit compatibility delegation over application-control owners."""

    def __init__(self, access: ApplicationControlAccess) -> None:
        values = ApplicationProfileValues()
        self._bootstrap = DefaultProfileBootstrapPersistence(access, values)
        self._catalog = TextProviderProfileCatalogPersistence(access, values)
        self._admission = TextProviderProfileAdmissionPersistence(access, values)
        self._settings = ProviderSettingsPersistence(access, values)

    @staticmethod
    def _text_provider_profile(row: TextProviderProfileRow) -> TextProviderProfile:
        return ApplicationProfileValues.text_provider_profile(row)

    @staticmethod
    def _provider_profile_selection(row: ProviderProfileSelectionRow) -> ProviderProfileSelection:
        return ApplicationProfileValues.provider_profile_selection(row)

    def get_provider_settings(self) -> ProviderSettings:
        return self._settings.get_provider_settings()

    def bootstrap_default_text_provider_profile(
        self,
        environment_default: TextProviderProfileSnapshot,
    ) -> TextProviderProfile:
        return self._bootstrap.bootstrap_default_text_provider_profile(environment_default)

    def get_text_provider_profile(self, profile_id: str) -> TextProviderProfile:
        return self._catalog.get_text_provider_profile(profile_id)

    def list_text_provider_profiles(self) -> list[TextProviderProfile]:
        return self._catalog.list_text_provider_profiles()

    def get_provider_profile_selection(self) -> ProviderProfileSelection:
        return self._admission.get_provider_profile_selection()

    @staticmethod
    def _profile_configuration_for_revision(
        profile_id: str,
        revision: int,
        value: TextProviderProfileSnapshot | dict[str, Any],
    ) -> TextProviderProfileSnapshot:
        return ApplicationProfileValues.profile_configuration_for_revision(
            profile_id, revision, value
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
        return self._catalog.create_text_provider_profile(
            profile_id,
            display_name,
            configuration=configuration,
            copy_from_profile_id=copy_from_profile_id,
            adapter_id=adapter_id,
            adapter_version=adapter_version,
        )

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
        return self._catalog.update_text_provider_profile(
            profile_id,
            expected_revision,
            display_name=display_name,
            configuration=configuration,
            adapter_id=adapter_id,
            adapter_version=adapter_version,
        )

    def activate_text_provider_profile(
        self,
        profile_id: str,
        expected_selection_revision: int,
    ) -> ProviderProfileSelection:
        return self._admission.activate_text_provider_profile(
            profile_id, expected_selection_revision
        )

    def set_text_provider_profile_enabled(
        self,
        profile_id: str,
        expected_availability_revision: int,
        *,
        enabled: bool,
    ) -> TextProviderProfile:
        return self._admission.set_text_provider_profile_enabled(
            profile_id, expected_availability_revision, enabled=enabled
        )

    @staticmethod
    def _profile_id_from_snapshot(snapshot: Mapping[str, Any]) -> str | None:
        return ApplicationProfileValues.profile_id_from_snapshot(snapshot)

    def _assert_new_run_profile_enabled(
        self, session: Session, provider_snapshot: Mapping[str, Any]
    ) -> None:
        return self._admission.assert_new_run_profile_enabled(session, provider_snapshot)

    def delete_text_provider_profile(
        self,
        profile_id: str,
        expected_revision: int,
    ) -> None:
        return self._admission.delete_text_provider_profile(profile_id, expected_revision)

    def put_provider_settings(self, settings: ProviderSettings) -> ProviderSettings:
        return self._settings.put_provider_settings(settings)

    def update_provider_settings_projection(
        self,
        *,
        expected_profile_id: str,
        expected_profile_revision: int,
        updates: dict[str, Any],
        defaults: ProviderSettings,
    ) -> tuple[TextProviderProfile, ProviderSettings]:
        return self._settings.update_provider_settings_projection(
            expected_profile_id=expected_profile_id,
            expected_profile_revision=expected_profile_revision,
            updates=updates,
            defaults=defaults,
        )

