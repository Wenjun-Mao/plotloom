from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

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
    assert conformance.CONFORMANCE_WORKLOAD_VERSION == "fixed_chinese_interactive_story.v8"
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
    assert all(
        set(receipt)
        == {
            "profileId",
            "profileHash",
            "workloadHash",
            "sampleOrdinal",
            "runHash",
            "topologyHash",
            "status",
            "issueCodes",
            "durationMilliseconds",
            "tokens",
            "firstPass",
            "maxAttemptsPerWorkUnit",
        }
        for receipt in receipts
    )
    assert all(receipt["profileId"] == "fixture" for receipt in receipts)
    assert all(receipt["workloadHash"] == conformance.conformance_workload_hash() for receipt in receipts)
    assert all(receipt["topologyHash"] for receipt in receipts)
    assert all(receipt["issueCodes"] == [] for receipt in receipts)
    assert all(
        receipt["tokens"] == {
            "inputTokens": 140,
            "outputTokens": 220,
            "totalTokens": 360,
        }
        for receipt in receipts
    )
    assert all(receipt["firstPass"]["accepted"] == 4 for receipt in receipts)
    assert all(
        receipt["firstPass"]
        == {
            "total": 4,
            "accepted": 4,
            "rejected": 0,
            "outcomeUnknown": 0,
            "cancelled": 0,
            "notRun": 0,
        }
        for receipt in receipts
    )
    assert all(receipt["maxAttemptsPerWorkUnit"] == 1 for receipt in receipts)
    assert conformance.qualification_issue_codes(
        receipts, profile_ids=["fixture"], sample_count=2
    ) == []
    assert roots and all(not root.exists() for root in roots)
    receipt_text = json.dumps(receipts)
    for forbidden in ("雾港", "fixture-provider", "fixture-model", "127.0.0.1"):
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
    for profile_id in profile_ids:
        samples = [receipt for receipt in receipts if receipt["profileId"] == profile_id]
        assert [sample["sampleOrdinal"] for sample in samples] == [1, 2, 3]
        assert all(sample["status"] == "succeeded" for sample in samples)
        assert all(
            sample["firstPass"]
            == {
                "total": 4,
                "accepted": 4,
                "rejected": 0,
                "outcomeUnknown": 0,
                "cancelled": 0,
                "notRun": 0,
            }
            for sample in samples
        )
        assert all(sample["maxAttemptsPerWorkUnit"] == 1 for sample in samples)
    assert conformance.m15_qualification_issue_codes(
        receipts, profile_ids=profile_ids
    ) == []


def test_conformance_closes_prepared_project_stores_when_later_setup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application_data_dir, _profiles = _application_data_dir(tmp_path, "fixture")
    prepared: list[SimpleNamespace] = []

    class Projects:
        def create(self, _brief: object) -> SimpleNamespace:
            if prepared:
                raise RuntimeError("fixture initialization failure")
            store = SimpleNamespace(closed=False)
            store.close = lambda: setattr(store, "closed", True)
            prepared.append(store)
            return store

    class Storage:
        def __init__(self, **_kwargs: object) -> None:
            self.projects = Projects()

    monkeypatch.setattr(conformance, "ProjectFolderStorage", Storage)
    with pytest.raises(RuntimeError, match="fixture initialization failure"):
        conformance.run_conformance(
            application_data_dir=application_data_dir,
            profile_ids=["fixture"],
            sample_count=2,
            provider_resolver=FixtureResolver(),
        )

    assert len(prepared) == 1
    assert prepared[0].closed is True


def test_conformance_invariant_codes_require_an_atomic_four_stage_install() -> None:
    def store_for(*, status: str, installed_count: int, result_revision_ids: tuple[str, ...]) -> SimpleNamespace:
        return SimpleNamespace(
            generation=SimpleNamespace(
                get_run=lambda _run_id: SimpleNamespace(
                    status=SimpleNamespace(value=status),
                    project_id="fixture-project",
                    result_revision_ids=result_revision_ids,
                )
            ),
            authoring=SimpleNamespace(
                list_stage_envelopes=lambda _project_id: [
                    SimpleNamespace(
                        head=SimpleNamespace(status=conformance.StageStatus.READY),
                        payload={},
                    )
                    for _index in range(installed_count)
                ]
            ),
        )

    trace = SimpleNamespace(attempts=[])
    assert conformance._conformance_invariant_codes(  # noqa: SLF001 - direct receipt invariant
        store_for(status="succeeded", installed_count=3, result_revision_ids=("a", "b", "c")),
        run_id="run",
        trace=trace,
    ) == {"conformance.canonical_install_incomplete"}
    assert conformance._conformance_invariant_codes(  # noqa: SLF001 - direct receipt invariant
        store_for(status="failed", installed_count=1, result_revision_ids=("a",)),
        run_id="run",
        trace=trace,
    ) == {"conformance.partial_canonical_install"}


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

    cancelled = [dict(receipt) for receipt in receipts]
    cancelled[2]["status"] = "cancelled"
    quarantined = [dict(receipt) for receipt in receipts]
    quarantined[2]["status"] = "quarantined"
    assert conformance.qualification_issue_codes(
        receipts, profile_ids=["fixture"], sample_count=3
    ) == [
        "qualification.fixture.duplicate_run",
        "qualification.fixture.invariant",
        "qualification.fixture.sample_identity",
    ]
    assert conformance.qualification_issue_codes(
        cancelled, profile_ids=["fixture"], sample_count=3
    ) == [
        "qualification.fixture.duplicate_run",
        "qualification.fixture.invariant",
        "qualification.fixture.run_completion",
        "qualification.fixture.sample_identity",
    ]
    assert conformance.qualification_issue_codes(
        quarantined, profile_ids=["fixture"], sample_count=3
    ) == [
        "qualification.fixture.duplicate_run",
        "qualification.fixture.invariant",
        "qualification.fixture.run_completion",
        "qualification.fixture.sample_identity",
    ]


def _complete_receipts(*, profile_ids: tuple[str, ...] = ("fixture",)) -> list[dict[str, object]]:
    return [
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
        for profile_id in profile_ids
        for ordinal in range(1, 4)
    ]


def test_qualification_enforces_first_pass_attempt_and_identity_boundaries() -> None:
    receipts = _complete_receipts()
    receipts[0]["firstPass"] = {"total": 4, "accepted": 3}
    receipts[1]["firstPass"] = {"total": 4, "accepted": 3}
    receipts[2]["firstPass"] = {"total": 4, "accepted": 3}
    receipts[2]["maxAttemptsPerWorkUnit"] = 4
    assert conformance.qualification_issue_codes(
        receipts, profile_ids=["fixture"], sample_count=3
    ) == [
        "qualification.fixture.attempt_limit",
        "qualification.fixture.first_pass",
    ]

    identity_failure = _complete_receipts()
    identity_failure[1]["workloadHash"] = "wrong-workload"
    identity_failure[1]["sampleOrdinal"] = 1
    identity_failure[1]["runHash"] = "run-fixture-1"
    assert conformance.qualification_issue_codes(
        identity_failure, profile_ids=["fixture"], sample_count=3
    ) == [
        "qualification.fixture.duplicate_run",
        "qualification.fixture.sample_identity",
        "qualification.fixture.workload_identity",
    ]


def test_qualification_allows_audited_corrections_within_the_first_pass_budget() -> None:
    receipts = _complete_receipts()
    for receipt in receipts[1:]:
        receipt["issueCodes"] = ["semantic.corrected"]
        receipt["firstPass"] = {"total": 4, "accepted": 3}
    receipts[1]["maxAttemptsPerWorkUnit"] = 2
    assert conformance.qualification_issue_codes(
        receipts, profile_ids=["fixture"], sample_count=3
    ) == []


def test_qualification_rejects_true_install_invariants_and_missing_samples() -> None:
    receipts = _complete_receipts()
    receipts[0]["issueCodes"] = ["conformance.partial_canonical_install"]
    assert conformance.qualification_issue_codes(
        receipts, profile_ids=["fixture"], sample_count=3
    ) == ["qualification.fixture.invariant"]
    assert conformance.qualification_issue_codes(
        _complete_receipts()[:-1], profile_ids=["fixture"], sample_count=3
    ) == ["qualification.fixture.sample_count"]


def test_m15_qualification_requires_two_distinct_profiles_and_accepts_complete_matrix() -> None:
    assert conformance.m15_qualification_issue_codes(
        [], profile_ids=["only_one"]
    ) == ["qualification.m15.profile_identity"]
    assert conformance.m15_qualification_issue_codes(
        [], profile_ids=["same", "same"]
    ) == ["qualification.m15.profile_identity"]
    assert conformance.m15_qualification_issue_codes(
        _complete_receipts(profile_ids=("profile_a", "profile_b")),
        profile_ids=["profile_a", "profile_b"],
    ) == []


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
            "--runs",
            "3",
        ]
    ) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert len([line for line in captured.out.splitlines() if line]) == 6


def test_m15_cli_rejects_partial_shape_before_loading_runtime_config(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert conformance.main(
        ["--qualify-m15", "--profile", "fixture", "--runs", "1"]
    ) == 2
    assert "exactly two distinct profiles and three runs each" in capsys.readouterr().err
