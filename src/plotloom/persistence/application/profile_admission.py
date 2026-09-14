"""Profile selection, availability, and new-run admission persistence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import TERMINAL_RUN_STATUSES, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ...provider_profiles import DEFAULT_PROVIDER_PROFILE_ID, ProviderProfileSelection, TextProviderProfile, is_v3_snapshot
from ..schema import GenerationRunRow, ProviderProfileSelectionRow, TextProviderProfileRow
from .access import ApplicationControlAccess
from .profile_values import ApplicationProfileValues


class TextProviderProfileAdmissionPersistence:
    """Own active-profile selection and fresh-run availability admission."""

    def __init__(self, access: ApplicationControlAccess, values: ApplicationProfileValues) -> None:
        self._access = access
        self._values = values

    def get_provider_profile_selection(self) -> ProviderProfileSelection:
        with self._access.read() as session:
            row = session.get(ProviderProfileSelectionRow, 1)
            if row is None:
                raise NotFoundError("text provider profile selection has not been initialized")
            return self._values.provider_profile_selection(row)


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
            return self._values.provider_profile_selection(row)

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
            return self._values.text_provider_profile(row)


    def assert_new_run_profile_enabled(
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

        profile_id = self._values.profile_id_from_snapshot(provider_snapshot)
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
