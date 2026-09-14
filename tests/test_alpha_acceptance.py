from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from plotloom import alpha_acceptance
from plotloom.domain import ProviderSettings
from plotloom.project_storage.application_profiles import ApplicationProfileRepository
from plotloom.project_storage.application_store import ApplicationStore
from plotloom.project_storage.application_profile_snapshot import load_saved_text_profiles
from plotloom.provider_profiles import PresetId, StageMaxOutputTokens, TextProviderProfileSnapshot

from tests.project_storage_fixtures import FixtureResolver


class DeterministicReviewRandom:
    """Test-only permutation/ID source; production uses ``SystemRandom``."""

    def __init__(self) -> None:
        self._next_id = 1

    def sample(self, population: list[int], k: int) -> list[int]:
        assert k == len(population)
        return list(reversed(population))

    def getrandbits(self, k: int) -> int:
        assert k == 128
        value = self._next_id
        self._next_id += 1
        return value


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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> alpha_acceptance._AlphaSourceProvenance:
    checkout_root = tmp_path / "fixture-source-checkout"
    checkout_root.mkdir()
    provenance = alpha_acceptance._AlphaSourceProvenance(
        checkout_root=checkout_root, commit_sha="a" * 40
    )
    monkeypatch.setattr(
        alpha_acceptance, "_resolve_alpha_source_provenance", lambda _commit: provenance
    )
    return provenance


def test_alpha_uses_current_profiles_and_project_folders_for_all_18_samples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application_data_dir, _profiles = _application_data_dir(tmp_path)
    _fixture_provenance(monkeypatch, tmp_path)
    review_directory = tmp_path / "untracked-review"
    roots: list[Path] = []
    temporary_directory = alpha_acceptance.tempfile.TemporaryDirectory

    class TrackedTemporaryDirectory(temporary_directory):
        def __enter__(self):
            path = super().__enter__()
            roots.append(Path(path))
            return path

    monkeypatch.setattr(
        alpha_acceptance.tempfile, "TemporaryDirectory", TrackedTemporaryDirectory
    )
    result = alpha_acceptance.run_alpha_acceptance(
        application_data_dir=application_data_dir,
        profile_ids=["real_looking_a", "real_looking_b"],
        review_directory=review_directory,
        provider_resolver=FixtureResolver(),
        commit_sha="a" * 40,
        review_random_source=DeterministicReviewRandom(),
    )

    assert len(result.receipts) == 18
    assert result.qualification_issues == ()
    assert alpha_acceptance.alpha_qualification_issue_codes(result.receipts) == []
    assert {receipt["profileId"] for receipt in result.receipts} == {
        "profile-01",
        "profile-02",
    }
    assert all(receipt["status"] == "succeeded" for receipt in result.receipts)
    assert all(
        receipt["scores"]["firstPass"]["accepted"] == 4
        and receipt["scores"]["maxAttemptsPerWorkUnit"] == 1
        for receipt in result.receipts
    )
    receipt_text = json.dumps(result.receipts)
    for forbidden in ("real_looking", "fixture-provider", "fixture-model", "127.0.0.1"):
        assert forbidden not in receipt_text
    assert roots and all(not root.exists() for root in roots)

    assert [path.name for path in result.review_paths] == [
        f"review-{ordinal:032x}.json" for ordinal in range(1, 7)
    ]
    assert result.review_mapping_path is not None
    assert stat.S_IMODE(result.review_mapping_path.stat().st_mode) == 0o600
    for review_path in result.review_paths:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
        assert set(payload) == {"storyBible", "storyGraph", "sceneBeats", "storyboard"}
        review_text = review_path.read_text(encoding="utf-8")
        for forbidden in ("profile", "provider", "fixture", "prompt", "response", "runId"):
            assert forbidden not in review_text


def test_alpha_profile_snapshot_is_read_only_and_refuses_disabled_profiles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application_data_dir, profiles = _application_data_dir(tmp_path)
    database_path = application_data_dir / "application.sqlite3"
    before = database_path.read_bytes()
    loaded = load_saved_text_profiles(application_data_dir, ["real_looking_a"])
    assert [profile.profile_id for profile in loaded] == ["real_looking_a"]
    assert database_path.read_bytes() == before

    current = profiles.get_text_provider_profile("real_looking_a")
    profiles.set_text_provider_profile_enabled(
        current.profile_id, current.availability_revision, enabled=False
    )
    _fixture_provenance(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="disabled text provider profile"):
        alpha_acceptance.run_alpha_acceptance(
            application_data_dir=application_data_dir,
            profile_ids=["real_looking_a", "real_looking_b"],
            review_directory=tmp_path / "review",
            provider_resolver=FixtureResolver(),
        )


def test_alpha_preserves_review_directory_and_hides_setup_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    application_data_dir, _profiles = _application_data_dir(tmp_path)
    provenance = _fixture_provenance(monkeypatch, tmp_path)
    review_directory = tmp_path / "review"
    review_directory.mkdir()
    (review_directory / "keep.txt").write_text("do not replace", encoding="utf-8")
    with pytest.raises(ValueError, match="must be empty"):
        alpha_acceptance.run_alpha_acceptance(
            application_data_dir=application_data_dir,
            profile_ids=["real_looking_a", "real_looking_b"],
            review_directory=review_directory,
            provider_resolver=FixtureResolver(),
        )
    with pytest.raises(ValueError, match="absolute path"):
        alpha_acceptance.run_alpha_acceptance(
            application_data_dir=application_data_dir,
            profile_ids=["real_looking_a", "real_looking_b"],
            review_directory=Path("relative-review"),
            provider_resolver=FixtureResolver(),
        )
    with pytest.raises(ValueError, match="outside the source checkout"):
        alpha_acceptance.run_alpha_acceptance(
            application_data_dir=application_data_dir,
            profile_ids=["real_looking_a", "real_looking_b"],
            review_directory=provenance.checkout_root / "review",
            provider_resolver=FixtureResolver(),
        )

    monkeypatch.setattr(
        alpha_acceptance,
        "run_alpha_acceptance",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("private source details")),
    )
    assert alpha_acceptance.main(
        [
            "--profile",
            "one",
            "--profile",
            "two",
            "--review-directory",
            str(tmp_path / "other-review"),
        ]
    ) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "private source details" not in captured.err


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


def test_external_review_gate_requires_the_full_secret_free_frozen_pack(
    tmp_path: Path,
) -> None:
    pack = _review_pack()
    approved = [_external_review(manifest) for manifest in pack.samples]
    assert alpha_acceptance.codex_external_review_gate(
        approved, review_pack=pack
    ).passed

    rejected = [dict(review) for review in approved]
    rejected[0]["fatalContradiction"] = True
    rejected[1]["scores"] = {**rejected[1]["scores"], "continuity": 2}
    gate = alpha_acceptance.codex_external_review_gate(rejected, review_pack=pack)
    assert not gate.passed
    assert gate.issue_codes == (
        "codex_external_review.fatal_contradiction",
        "codex_external_review.score_floor",
    )

    mapping_path = tmp_path / "review-mapping.private.json"
    mapping_path.write_text(
        json.dumps(
            {
                "version": "alpha_review_mapping.v2",
                "commit": pack.commit,
                "contractHash": pack.contract_hash,
                "reviewCount": 6,
                "entries": [
                    {
                        "reviewId": sample.review_id,
                        "profileId": "profile-01",
                        "storyId": "story-01",
                        "sampleId": "story-01-repeat-01",
                        "contentHash": sample.content_hash,
                    }
                    for sample in pack.samples
                ],
            }
        ),
        encoding="utf-8",
    )
    assert alpha_acceptance.load_private_review_manifest(mapping_path) == pack


def test_external_review_gate_rejects_malformed_sheets_and_frozen_identity_mismatches() -> None:
    pack = _review_pack()
    approved = [_external_review(manifest) for manifest in pack.samples]

    malformed = [dict(review) for review in approved]
    malformed[0]["reviewerComment"] = "Untrusted prose must not cross the receipt boundary."
    malformed[1]["scores"] = {
        **malformed[1]["scores"],
        "continuity": 4.0,
    }
    malformed_gate = alpha_acceptance.codex_external_review_gate(
        malformed, review_pack=pack
    )
    assert {
        "codex_external_review.schema",
        "codex_external_review.count",
        "codex_external_review.identity",
    } <= set(malformed_gate.issue_codes)

    mismatched = [dict(review) for review in approved]
    mismatched[0]["commit"] = "c" * 40
    mismatched[1]["contractHash"] = "d" * 64
    mismatched[2]["contentHash"] = "e" * 64
    mismatched[3]["reviewId"] = approved[4]["reviewId"]
    mismatch_gate = alpha_acceptance.codex_external_review_gate(
        mismatched, review_pack=pack
    )
    assert {
        "codex_external_review.commit_identity",
        "codex_external_review.contract_identity",
        "codex_external_review.content_identity",
        "codex_external_review.identity",
    } <= set(mismatch_gate.issue_codes)


def test_external_review_gate_enforces_quality_thresholds_and_full_manifest() -> None:
    pack = _review_pack()
    low_quality = [_external_review(manifest, score=3) for manifest in pack.samples]
    quality_gate = alpha_acceptance.codex_external_review_gate(
        low_quality, review_pack=pack
    )
    assert {
        "codex_external_review.sample_average",
        "codex_external_review.dimension_median",
    } <= set(quality_gate.issue_codes)

    undersized_pack = alpha_acceptance.ReviewPackManifest(
        commit=pack.commit,
        contract_hash=pack.contract_hash,
        samples=pack.samples[:-1],
    )
    manifest_gate = alpha_acceptance.codex_external_review_gate(
        [_external_review(manifest) for manifest in undersized_pack.samples],
        review_pack=undersized_pack,
    )
    assert {
        "codex_external_review.expected_manifest_count",
        "codex_external_review.count",
    } <= set(manifest_gate.issue_codes)


def test_external_review_receipt_filters_invalid_sheets_and_private_mapping_rejects_partial_pack(
    tmp_path: Path,
) -> None:
    pack = _review_pack()
    reviews = [_external_review(manifest) for manifest in pack.samples]
    reviews[0]["reviewerComment"] = "Untrusted prose must not be persisted."

    receipt = alpha_acceptance.codex_external_review_receipt(reviews, review_pack=pack)
    serialized = receipt.model_dump_json(by_alias=True)
    assert len(receipt.reviews) == 5
    assert "Untrusted prose" not in serialized
    assert "reviewerComment" not in serialized
    assert "codex_external_review.schema" in receipt.gate.issue_codes

    mapping_path = tmp_path / "partial-review-mapping.private.json"
    mapping_path.write_text(
        json.dumps(
            {
                "version": "alpha_review_mapping.v2",
                "commit": pack.commit,
                "contractHash": pack.contract_hash,
                "reviewCount": 6,
                "entries": [
                    {
                        "reviewId": sample.review_id,
                        "profileId": "profile-01",
                        "storyId": "story-01",
                        "sampleId": "story-01-repeat-01",
                        "contentHash": sample.content_hash,
                    }
                    for sample in pack.samples[:-1]
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="all six Alpha samples"):
        alpha_acceptance.load_private_review_manifest(mapping_path)
