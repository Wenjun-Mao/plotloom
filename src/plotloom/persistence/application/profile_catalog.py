"""CRUD persistence for reusable public text-provider profiles."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select

from ...domain import utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...provider_profiles import PROFILE_ID_PATTERN, TextProviderProfile, TextProviderProfileSnapshot
from ..schema import TextProviderProfileRow
from .access import ApplicationControlAccess
from .profile_values import ApplicationProfileValues


class TextProviderProfileCatalogPersistence:
    """Own reusable profile records and their revisioned configuration CRUD."""

    def __init__(self, access: ApplicationControlAccess, values: ApplicationProfileValues) -> None:
        self._access = access
        self._values = values

    def get_text_provider_profile(self, profile_id: str) -> TextProviderProfile:
        with self._access.read() as session:
            row = session.get(TextProviderProfileRow, profile_id)
            if row is None:
                raise NotFoundError(f"text provider profile not found: {profile_id}")
            return self._values.text_provider_profile(row)

    def list_text_provider_profiles(self) -> list[TextProviderProfile]:
        with self._access.read() as session:
            rows = session.scalars(
                select(TextProviderProfileRow).order_by(TextProviderProfileRow.id)
            ).all()
            return [self._values.text_provider_profile(row) for row in rows]

    def get_provider_profile_selection(self) -> ProviderProfileSelection:
        with self._access.read() as session:
            row = session.get(ProviderProfileSelectionRow, 1)
            if row is None:
                raise NotFoundError("text provider profile selection has not been initialized")
            return self._provider_profile_selection(row)


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
            parsed = self._values.profile_configuration_for_revision(profile_id, 1, configuration)
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
            return self._values.text_provider_profile(row)

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
            proposed = self._values.profile_configuration_for_revision(
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
                return self._values.text_provider_profile(row)
            row.revision += 1
            row.display_name = normalized_name
            row.settings = proposed.model_dump(mode="json", by_alias=True)
            row.adapter_id = next_adapter_id
            row.adapter_version = next_adapter_version
            row.updated_at = utc_now()
            return self._values.text_provider_profile(row)
