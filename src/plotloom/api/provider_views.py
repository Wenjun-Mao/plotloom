from __future__ import annotations

from typing import Any, Mapping

from plotloom.provider_contracts import (
    PUBLIC_PROVIDER_SETTING_FIELDS,
    ProviderSettings,
    ProviderSnapshot,
)
from plotloom.provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID,
    PresetId,
    StageMaxOutputTokens,
    TextProviderCapabilities,
    TextProviderProfileSnapshot,
    V2ExtractionPolicy,
    execution_preset,
)
from plotloom.provider_snapshot import validate_public_provider_snapshot


def _merge_provider_settings(
    persisted: ProviderSettings,
    defaults: ProviderSettings,
    key_availability: Mapping[str, bool],
) -> ProviderSettings:
    if persisted.revision == 0:
        # No row means environment-owned defaults still define the profile.
        values = {
            field: getattr(defaults, field) for field in PUBLIC_PROVIDER_SETTING_FIELDS
        }
    else:
        values = {
            field: getattr(persisted, field)
            if getattr(persisted, field) is not None
            else getattr(defaults, field)
            for field in PUBLIC_PROVIDER_SETTING_FIELDS
        }
    values.update(
        profile_version=persisted.revision,
        revision=persisted.revision,
        updated_at=persisted.updated_at,
        text_key_available=bool(key_availability.get("text_key_available", False)),
        image_key_available=bool(key_availability.get("image_key_available", False)),
        video_key_available=bool(key_availability.get("video_key_available", False)),
    )
    return ProviderSettings.model_validate(values)


def _public_provider_snapshot(settings: ProviderSettings) -> dict[str, Any]:
    snapshot = ProviderSnapshot.model_validate(
        settings.model_dump(
            mode="json",
            by_alias=False,
            include=set(ProviderSnapshot.model_fields),
        )
    )
    return validate_public_provider_snapshot(
        snapshot.model_dump(mode="json", by_alias=True)
    )


def _default_text_profile_snapshot(
    defaults: ProviderSettings,
) -> TextProviderProfileSnapshot:
    """Translate the old runtime defaults into the first V2 named profile."""

    preset = execution_preset(PresetId.COMPATIBLE_V1)
    values: dict[str, Any] = {
        "profile_schema_version": 2,
        "profile_id": DEFAULT_PROVIDER_PROFILE_ID,
        "profile_version": 0,
        "text_provider": defaults.text_provider or "openai-compatible",
        "text_base_url": defaults.text_base_url or "https://api.atlascloud.ai/v1",
        "text_model": defaults.text_model or "deepseek-v3",
        "text_auth_mode": defaults.text_auth_mode.value,
        "text_capabilities": TextProviderCapabilities(
            chat_completions=defaults.text_capabilities.chat_completions,
            json_object=defaults.text_capabilities.json_object,
            json_schema=defaults.text_capabilities.json_schema,
            chat_template_kwargs=False,
        ),
        "text_context_window_tokens": defaults.text_context_window_tokens,
        "text_max_output_tokens": defaults.text_max_output_tokens,
        "text_temperature": defaults.text_temperature,
        "text_max_concurrency": defaults.text_max_concurrency,
        "text_connect_timeout_seconds": defaults.text_connect_timeout_seconds,
        "text_attempt_timeout_seconds": defaults.text_attempt_timeout_seconds,
        "redirect_policy": "no_follow",
        "request_extension": preset.request_extension,
        "reasoning_mode": preset.reasoning_mode,
        "extraction_policy": V2ExtractionPolicy(),
        "stage_max_output_tokens": StageMaxOutputTokens(
            story_bible=min(8192, defaults.text_max_output_tokens),
            story_graph=min(8192, defaults.text_max_output_tokens),
            scene_beats=min(4096, defaults.text_max_output_tokens),
            storyboard=min(4096, defaults.text_max_output_tokens),
        ),
        "max_semantic_corrections": 2,
        "preset_id": PresetId.COMPATIBLE_V1,
        "preset_version": preset.preset_version,
    }
    try:
        return TextProviderProfileSnapshot.model_validate(values)
    except ValueError:
        values["preset_id"] = PresetId.CUSTOM
        return TextProviderProfileSnapshot.model_validate(values)
