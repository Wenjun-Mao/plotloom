from __future__ import annotations

import pytest

from plotloom.config import (
    profile_text_api_key_environment_name,
    resolve_text_provider_api_key,
)
from plotloom.domain import ProviderSnapshot
from plotloom.generation.contracts import ReasoningMode, RequestExtension
from plotloom.provider_profiles import (
    DEFAULT_PROVIDER_PROFILE_ID,
    PresetId,
    StageMaxOutputTokens,
    TextProviderCapabilities,
    TextProviderProfileSnapshot,
    V2ExtractionPolicy,
    execution_preset,
    legacy_v1_profile_hash,
    validate_frozen_text_snapshot,
)


def _v2_snapshot(**overrides: object) -> TextProviderProfileSnapshot:
    values: dict[str, object] = {
        "profile_id": "local_llama",
        "profile_version": 4,
        "text_provider": "openai-compatible",
        "text_base_url": "http://127.0.0.1:8080/v1",
        "text_model": "a-local-model",
        "text_auth_mode": "none",
        "text_context_window_tokens": 32_768,
        "text_max_output_tokens": 8_192,
        "text_attempt_timeout_seconds": 300,
        "stage_max_output_tokens": StageMaxOutputTokens(
            story_bible=8192, story_graph=8192, scene_beats=4096, storyboard=4096
        ),
        "preset_id": PresetId.COMPATIBLE_V1,
        "request_extension": RequestExtension.NONE,
        "reasoning_mode": ReasoningMode.PROVIDER_DEFAULT,
        "extraction_policy": V2ExtractionPolicy(),
    }
    values.update(overrides)
    return TextProviderProfileSnapshot.model_validate(values)


def test_published_execution_presets_match_the_versioned_contract() -> None:
    compatible = execution_preset("compatible_v1")
    assert compatible.text_context_window_tokens == 32_768
    assert compatible.text_max_output_tokens == 8_192
    assert compatible.stage_max_output_tokens.model_dump() == {
        "story_bible": 8192,
        "story_graph": 8192,
        "scene_beats": 4096,
        "storyboard": 4096,
    }
    assert compatible.text_attempt_timeout_seconds == 300
    assert compatible.max_semantic_corrections == 2
    assert compatible.request_extension == RequestExtension.NONE

    quality = execution_preset(PresetId.QUALITY_REASONING_V1)
    assert quality.text_context_window_tokens == 131_072
    assert quality.text_max_output_tokens == 32_768
    assert set(quality.stage_max_output_tokens.model_dump().values()) == {32_768}
    assert quality.text_attempt_timeout_seconds == 900
    assert quality.reasoning_mode == ReasoningMode.ENABLED

    final_only = execution_preset(PresetId.FINAL_ONLY_V1)
    assert final_only.text_max_output_tokens == 16_384
    assert set(final_only.stage_max_output_tokens.model_dump().values()) == {8192}
    assert final_only.text_attempt_timeout_seconds == 600
    assert final_only.reasoning_mode == ReasoningMode.DISABLED


def test_profile_requires_explicit_template_capability_and_does_not_enable_embedded_json() -> None:
    with pytest.raises(ValueError, match="explicit provider capability"):
        _v2_snapshot(
            request_extension=RequestExtension.CHAT_TEMPLATE_KWARGS,
            reasoning_mode=ReasoningMode.ENABLED,
        )

    profile = _v2_snapshot(
        preset_id=PresetId.CUSTOM,
        text_capabilities=TextProviderCapabilities(chat_template_kwargs=True),
        request_extension=RequestExtension.CHAT_TEMPLATE_KWARGS,
        reasoning_mode=ReasoningMode.DISABLED,
        extraction_policy=V2ExtractionPolicy(
            allow_json_fence=True, allow_leading_think_block=True
        ),
    )
    _, _, extraction = profile.request_contract()
    assert extraction.markdown_fence is True
    assert extraction.reasoning_tags is True
    assert extraction.embedded_json is False


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "https://user:password@example.test/v1",
        "https://example.test/v1?sig=opaque-secret",
        "https://example.test/v1#credential",
        "ftp://example.test/v1",
        "https://example.test:bad/v1",
    ],
)
def test_profile_rejects_non_root_or_credential_bearing_urls(unsafe_url: str) -> None:
    with pytest.raises(ValueError, match="provider base URLs"):
        _v2_snapshot(text_base_url=unsafe_url)


def test_v1_hash_uses_the_original_field_contract_without_v2_normalization() -> None:
    historical = ProviderSnapshot(text_provider="historic", text_model="v1-model")
    stored = historical.model_dump(mode="json", by_alias=True)
    assert legacy_v1_profile_hash(stored) == historical.profile_hash
    accepted = validate_frozen_text_snapshot(stored)
    assert accepted == stored
    assert "profileSchemaVersion" not in accepted


def test_profile_key_resolution_is_namespaced_and_default_keeps_legacy_fallbacks() -> None:
    values = {
        "PLOTLOOM_PROFILE_LOCAL_LLAMA_TEXT_API_KEY": "local-key",
        "TEXT_MODEL_API_KEY": "legacy-key",
        "ATLASCLOUD_API_KEY": "atlas-key",
    }
    assert profile_text_api_key_environment_name("local_llama") == (
        "PLOTLOOM_PROFILE_LOCAL_LLAMA_TEXT_API_KEY"
    )
    assert resolve_text_provider_api_key("local_llama", values) == "local-key"
    assert resolve_text_provider_api_key(DEFAULT_PROVIDER_PROFILE_ID, values) == "legacy-key"
    assert resolve_text_provider_api_key("other", values) is None
    with pytest.raises(ValueError):
        profile_text_api_key_environment_name("Not-valid")
