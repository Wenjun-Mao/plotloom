"""Non-collected Alpha profile, provenance and blinded-review test builders."""
from __future__ import annotations
from pathlib import Path
import pytest
from plotloom import alpha_acceptance
from plotloom.provider_contracts import ProviderSettings
from plotloom.project_storage.application_profiles import ApplicationProfileRepository
from plotloom.project_storage.application_store import ApplicationStore
from plotloom.provider_profiles import PresetId, StageMaxOutputTokens, TextProviderProfileSnapshot


def _profile(profile_id: str) -> TextProviderProfileSnapshot:
    return TextProviderProfileSnapshot.model_validate(
        {
            "profileId": profile_id,
            "profileVersion": 1,
            "textProvider": "fixture-provider",
            "textBaseUrl": "http://127.0.0.1:9/v1",
            "textModel": "fixture-model",
            "textAuthMode": "none",
            "textCapabilities": {"jsonSchema": True},
            "textContextWindowTokens": 32768,
            "textMaxOutputTokens": 8192,
            "textAttemptTimeoutSeconds": 300,
            "stageMaxOutputTokens": StageMaxOutputTokens(
                story_bible=8192,
                story_graph=8192,
                scene_beats=4096,
                storyboard=4096,
            ),
            "presetId": PresetId.COMPATIBLE_V1,
        }
    )


def _application_data_dir(tmp_path: Path) -> tuple[Path, ApplicationProfileRepository]:
    application_data_dir = tmp_path / "application"
    application_data_dir.mkdir()
    profiles = ApplicationProfileRepository(
        ApplicationStore(application_data_dir), ProviderSettings()
    )
    for profile_id in ("real_looking_a", "real_looking_b"):
        profiles.create_text_provider_profile(
            profile_id, profile_id, configuration=_profile(profile_id)
        )
    return application_data_dir, profiles


def _fixture_provenance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    checks: list[str | None] | None = None,
) -> alpha_acceptance._AlphaSourceProvenance:
    checkout_root = tmp_path / "fixture-source-checkout"
    checkout_root.mkdir()
    provenance = alpha_acceptance._AlphaSourceProvenance(
        checkout_root=checkout_root, commit_sha="a" * 40
    )
    monkeypatch.setattr(
        alpha_acceptance,
        "_resolve_alpha_source_provenance",
        lambda commit: (
            checks.append(commit) if checks is not None else None
        ) or provenance,
    )
    return provenance


def _review_manifests() -> tuple[alpha_acceptance.ReviewSampleManifest, ...]:
    return tuple(
        alpha_acceptance.ReviewSampleManifest(
            review_id=f"review-{ordinal:032x}", content_hash=f"{ordinal:064x}"
        )
        for ordinal in range(1, 7)
    )


def _review_pack() -> alpha_acceptance.ReviewPackManifest:
    return alpha_acceptance.ReviewPackManifest(
        commit="a" * 40,
        contract_hash="b" * 64,
        samples=_review_manifests(),
    )


def _external_review(
    manifest: alpha_acceptance.ReviewSampleManifest, *, fatal: bool = False, score: int = 4
) -> dict[str, object]:
    return {
        "commit": "a" * 40,
        "contractHash": "b" * 64,
        "reviewId": manifest.review_id,
        "contentHash": manifest.content_hash,
        "rubricVersion": "m1c_authoring_quality.v1",
        "reviewer": "codex_external_review",
        "scores": {
            "narrativeClarity": score,
            "branchCausality": score,
            "continuity": score,
            "performanceReadability": score,
            "shotLanguage": score,
            "pacingAndEditCost": score,
        },
        "fatalContradiction": fatal,
    }
