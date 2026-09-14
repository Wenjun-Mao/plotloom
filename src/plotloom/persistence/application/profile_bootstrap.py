"""Bootstrap persistence for the default application text-provider profile."""

from __future__ import annotations

from ...domain import contains_secret_setting, contains_secret_value, utc_now
from ...provider_profiles import DEFAULT_PROVIDER_PROFILE_ID, PresetId, TextProviderProfile, TextProviderProfileSnapshot, is_v2_snapshot
from ..schema import ProviderProfileSelectionRow, TextProviderProfileRow
from .access import ApplicationControlAccess
from .profile_values import ApplicationProfileValues


class DefaultProfileBootstrapPersistence:
    """Own one-time materialization of trusted environment defaults."""

    def __init__(self, access: ApplicationControlAccess, values: ApplicationProfileValues) -> None:
        self._access = access
        self._values = values

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
                return self._values.text_provider_profile(row)

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
            return self._values.text_provider_profile(row)
