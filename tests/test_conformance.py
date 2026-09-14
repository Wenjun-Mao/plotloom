from __future__ import annotations

import json
from pathlib import Path

import pytest

from plotloom import conformance
from plotloom.domain import ProviderSettings
from plotloom.project_storage.application_profiles import ApplicationProfileRepository
from plotloom.project_storage.application_store import ApplicationStore
from plotloom.project_storage.application_profile_snapshot import load_saved_text_profiles
from plotloom.project_storage.format import ProjectStorageCorruptionError
from plotloom.provider_profiles import PresetId, StageMaxOutputTokens, TextProviderProfileSnapshot

from tests.project_storage_fixtures import FixtureResolver


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


def _application_data_dir(
    tmp_path: Path, *profile_ids: str
) -> tuple[Path, ApplicationProfileRepository]:
    application_data_dir = tmp_path / "application"
    application_data_dir.mkdir()
    profiles = ApplicationProfileRepository(
        ApplicationStore(application_data_dir), ProviderSettings()
    )
    for profile_id in profile_ids:
        profiles.create_text_provider_profile(
            profile_id, profile_id, configuration=_profile(profile_id)
        )
    return application_data_dir, profiles


def test_fixed_workload_preserves_storyboard_capacity_for_multi_beat_scenes() -> None:
    brief = conformance.FIXED_CHINESE_BRIEF
    assert brief.shots_per_scene_min == 1
    assert brief.shots_per_scene_max == 4


def test_application_profile_snapshot_refuses_disabled_or_secret_corruption(
    tmp_path: Path,
) -> None:
    application_data_dir, profiles = _application_data_dir(tmp_path, "fixture")
    current = profiles.get_text_provider_profile("fixture")
    profiles.set_text_provider_profile_enabled(
        "fixture", current.availability_revision, enabled=False
    )
    with pytest.raises(ValueError, match="disabled text provider profile"):
        load_saved_text_profiles(application_data_dir, ["fixture"])

    profiles.set_text_provider_profile_enabled(
        "fixture", current.availability_revision + 1, enabled=True
    )
    with ApplicationStore(application_data_dir)._write() as connection:  # noqa: SLF001 - corruption fixture
        configuration = json.loads(
            connection.execute(
                "SELECT configuration_json FROM application_profiles WHERE profile_id = 'fixture'"
            ).fetchone()[0]
        )
        configuration["textApiKey"] = "not-a-real-key"
        connection.execute(
            "UPDATE application_profiles SET configuration_json = ? WHERE profile_id = 'fixture'",
            (json.dumps(configuration),),
        )
    with pytest.raises(ProjectStorageCorruptionError, match="secret configuration"):
        load_saved_text_profiles(application_data_dir, ["fixture"])


def test_conformance_runs_the_production_four_stage_loop_and_deletes_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application_data_dir, _profiles = _application_data_dir(tmp_path, "fixture")
    roots: list[Path] = []
    temporary_directory = conformance.tempfile.TemporaryDirectory

    class TrackedTemporaryDirectory(temporary_directory):
        def __enter__(self):
            path = super().__enter__()
            roots.append(Path(path))
            return path

    monkeypatch.setattr(conformance.tempfile, "TemporaryDirectory", TrackedTemporaryDirectory)
    receipts = conformance.run_conformance(
        application_data_dir=application_data_dir,
        profile_ids=["fixture"],
        sample_count=2,
        provider_resolver=FixtureResolver(),
    )

    assert [receipt["sampleOrdinal"] for receipt in receipts] == [1, 2]
    assert all(receipt["status"] == "succeeded" for receipt in receipts)
    assert all(receipt["firstPass"]["accepted"] == 4 for receipt in receipts)
    assert all(receipt["maxAttemptsPerWorkUnit"] == 1 for receipt in receipts)
    assert conformance.qualification_issue_codes(
        receipts, profile_ids=["fixture"], sample_count=2
    ) == []
    assert roots and all(not root.exists() for root in roots)
    receipt_text = json.dumps(receipts)
    for forbidden in ("fixture-provider", "fixture-model", "127.0.0.1"):
        assert forbidden not in receipt_text


def test_m15_conformance_uses_two_current_application_profiles(tmp_path: Path) -> None:
    application_data_dir, _profiles = _application_data_dir(
        tmp_path, "fixture_a", "fixture_b"
    )
    profile_ids = ["fixture_a", "fixture_b"]
    receipts = conformance.run_conformance(
        application_data_dir=application_data_dir,
        profile_ids=profile_ids,
        sample_count=3,
        provider_resolver=FixtureResolver(),
        parallel_profiles=True,
    )

    assert len(receipts) == 6
    assert conformance.m15_qualification_issue_codes(
        receipts, profile_ids=profile_ids
    ) == []


def test_qualification_rejects_invariant_and_sample_identity_failures() -> None:
    receipts = [
        {
            "profileId": "fixture",
            "profileHash": "profile-hash",
            "workloadHash": conformance.conformance_workload_hash(),
            "sampleOrdinal": 1 if ordinal == 2 else ordinal,
            "runHash": "duplicate" if ordinal < 3 else "run-3",
            "status": "succeeded",
            "issueCodes": ["provider.outcome_unknown"] if ordinal == 1 else [],
            "firstPass": {"total": 4, "accepted": 4},
            "maxAttemptsPerWorkUnit": 1,
        }
        for ordinal in range(1, 4)
    ]
    assert conformance.qualification_issue_codes(
        receipts, profile_ids=["fixture"], sample_count=3
    ) == [
        "qualification.fixture.duplicate_run",
        "qualification.fixture.invariant",
        "qualification.fixture.sample_identity",
    ]


def test_m15_cli_emits_receipts_without_a_legacy_database_option(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    receipts = [
        {
            "profileId": profile_id,
            "profileHash": f"profile-{profile_id}",
            "workloadHash": conformance.conformance_workload_hash(),
            "sampleOrdinal": ordinal,
            "runHash": f"run-{profile_id}-{ordinal}",
            "status": "succeeded",
            "issueCodes": [],
            "firstPass": {"total": 4, "accepted": 4},
            "maxAttemptsPerWorkUnit": 1,
        }
        for profile_id in ("profile_a", "profile_b")
        for ordinal in range(1, 4)
    ]

    class Settings:
        application_data_dir = tmp_path

        @staticmethod
        def text_api_key_for_profile(_profile_id: str):
            return None

    monkeypatch.setattr(conformance.PlotloomSettings, "from_env", lambda: Settings())
    monkeypatch.setattr(conformance, "run_conformance", lambda **_kwargs: receipts)
    assert conformance.main(
        [
            "--qualify-m15",
            "--profile",
            "profile_a",
            "--profile",
            "profile_b",
        ]
    ) == 0
    assert len([line for line in capsys.readouterr().out.splitlines() if line]) == 6
