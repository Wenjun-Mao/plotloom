from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import pytest

from plotloom import conformance
from plotloom.generation.contracts import ProviderCapabilities, ProviderResponse, ProviderUsage
from plotloom.persistence import SQLiteRepository
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


def _json_after(content: str, marker: str) -> Any:
    """Read the first labelled JSON value, ignoring instructional echoes.

    Prompt copy is allowed to mention a context label after the structured
    context itself.  A fixture must therefore find a label occurrence that is
    actually followed by JSON instead of relying on whether prose is rendered
    before or after the context block.
    """

    decoder = json.JSONDecoder()
    offset = 0
    while (index := content.find(marker, offset)) != -1:
        remainder = content[index + len(marker) :].lstrip()
        try:
            return decoder.raw_decode(remainder)[0]
        except json.JSONDecodeError:
            offset = index + len(marker)
    raise AssertionError(f"no JSON value follows marker {marker!r}")


def test_fixed_workload_preserves_storyboard_capacity_for_multi_beat_scenes() -> None:
    assert conformance.CONFORMANCE_WORKLOAD_VERSION == "fixed_chinese_interactive_story.v8"
    assert conformance.FIXED_CHINESE_BRIEF.shots_per_scene_min == 1
    assert conformance.FIXED_CHINESE_BRIEF.shots_per_scene_max == 4


class _FixtureProvider:
    name = "fixture-provider"
    capabilities = ProviderCapabilities(json_schema=True)

    def generate(self, request, secret) -> ProviderResponse:
        assert secret is None
        prompt = "\n".join(message.content for message in request.messages)
        if "【不可变图骨架清单】" in prompt:
            topology = _json_after(prompt, "【不可变图骨架清单】")
            payload = {
                "nodes": [
                    {"id": node["id"], "title": "雾港节点", "summary": "摆渡人继续前行。"}
                    for node in topology["nodes"]
                ],
                "edges": [
                    {
                        "id": edge["id"],
                        "choiceText": "继续" if edge["kind"] == "choice" else None,
                        "stateEffects": {"route": edge["id"]} if edge["kind"] == "choice" else {},
                    }
                    for edge in topology["edges"]
                ],
                "joinContracts": [
                    {
                        "id": join["id"],
                        "requiredStateKeys": [],
                        "allowedDifferences": [],
                        "reconciliation": "不同路线在雾港汇合。",
                        "notes": "",
                    }
                    for join in topology["joinContracts"]
                ],
            }
        elif "【目标故事节点】" in prompt:
            node = _json_after(prompt, "【目标故事节点】")
            scene_id = f"scene-{node['id']}"
            beat_id = f"beat-{node['id']}"
            payload = {
                "scenes": [{"localSceneId": scene_id, "order": 1, "title": node["title"], "objective": "穿过雾港", "locationId": None, "characterIds": [], "durationWeight": 1, "entryState": {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}, "exitState": {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}}],
                "beats": [{"localBeatId": beat_id, "sceneLocalId": scene_id, "order": 1, "description": "船钟在雾中响起。", "purpose": "推进叙事", "visibleEvent": "摆渡人握紧船钟。", "immediateResult": "摆渡人继续前行。", "dramaticChange": "继续前行", "entryState": {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}, "exitState": {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}, "continuityAnchors": [], "continuityDelta": {}}],
                "dialogueCues": [],
            }
        elif "【目标戏剧场景】" in prompt:
            scene = _json_after(prompt, "【目标戏剧场景】")
            beats = _json_after(prompt, "【该场景节拍】")
            beat_id = beats[0]["id"]
            shot_id = f"shot-{scene['id']}"
            payload = {
                "shots": [{"localShotId": shot_id, "order": 1, "title": "船钟特写", "shotSize": "medium", "durationUnits": 1, "cameraAngle": "", "cameraMovement": "", "composition": "", "visualIntent": "交代船钟与人物关系", "motionIntent": "稳定推进", "action": "摆渡人握紧船钟。", "transition": "硬切", "cueIds": [], "audioPlan": {"events": []}, "characterIds": [], "locationId": None, "propIds": [], "requiredEntityStates": [], "entryState": {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}, "exitState": {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}}],
                "primaryShotLocalIdByBeat": {beat_id: shot_id},
                "supportingBeatLinks": [],
            }
        else:
            payload = {"logline": "摆渡人做出选择。", "premise": "未来的信改变当下。", "genre": "", "tone": "", "audience": "", "narrativePromise": "", "visualLanguage": "", "themes": [], "worldRules": [], "knownFacts": [], "openQuestions": [], "sourceNotes": [], "characters": [], "locations": [], "props": []}
        content = json.dumps(payload, ensure_ascii=False)
        return ProviderResponse(
            provider=self.name,
            model=request.model,
            raw={"choices": [{"message": {"role": "assistant", "content": content}}]},
            usage=ProviderUsage(input_tokens=7, output_tokens=11),
        )


class _FixtureResolver:
    def __init__(self) -> None:
        self.provider = _FixtureProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


def test_conformance_runs_the_production_four_stage_loop_and_deletes_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_path = tmp_path / "source.sqlite3"
    source = SQLiteRepository(f"sqlite:///{source_path}")
    try:
        source.bootstrap_default_text_provider_profile(_profile("default"))
        source.create_text_provider_profile(
            "fixture",
            "Fixture",
            configuration=_profile("fixture"),
        )
    finally:
        source.close()

    created_roots: list[Path] = []
    real_temporary_directory = tempfile.TemporaryDirectory

    class _TrackedTemporaryDirectory(real_temporary_directory):
        def __enter__(self):
            path = super().__enter__()
            created_roots.append(Path(path))
            return path

    monkeypatch.setattr(conformance.tempfile, "TemporaryDirectory", _TrackedTemporaryDirectory)
    receipts = conformance.run_conformance(
        source_database_url=f"sqlite:///{source_path}",
        profile_ids=["fixture"],
        sample_count=2,
        provider_resolver=_FixtureResolver(),
    )

    assert len(receipts) == 2
    for receipt in receipts:
        assert set(receipt) == {
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
        assert receipt["profileId"] == "fixture"
        assert receipt["workloadHash"] == conformance.conformance_workload_hash()
        assert receipt["status"] == "succeeded"
        assert receipt["topologyHash"]
        assert receipt["issueCodes"] == []
        assert receipt["tokens"] == {"inputTokens": 140, "outputTokens": 220, "totalTokens": 360}
        assert receipt["firstPass"] == {
            "total": 4,
            "accepted": 4,
            "rejected": 0,
            "outcomeUnknown": 0,
            "cancelled": 0,
            "notRun": 0,
        }
        assert receipt["maxAttemptsPerWorkUnit"] == 1
        serialized = json.dumps(receipt, ensure_ascii=False)
        assert "雾港" not in serialized
        assert "127.0.0.1" not in serialized
        assert "fixture-model" not in serialized
    assert created_roots and all(not path.exists() for path in created_roots)

    assert conformance.qualification_issue_codes(
        receipts,
        profile_ids=["fixture"],
        sample_count=2,
    ) == []


def test_conformance_closes_prepared_repositories_when_later_initialization_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_path = tmp_path / "source.sqlite3"
    source = SQLiteRepository(f"sqlite:///{source_path}")
    try:
        source.bootstrap_default_text_provider_profile(_profile("default"))
        source.create_text_provider_profile(
            "fixture",
            "Fixture",
            configuration=_profile("fixture"),
        )
    finally:
        source.close()

    repository_type = conformance.SQLiteRepository
    real_close = repository_type.close
    prepared: list[SQLiteRepository] = []
    closed: list[SQLiteRepository] = []

    def tracked_close(repository: SQLiteRepository) -> None:
        if repository in prepared:
            closed.append(repository)
        real_close(repository)

    def repository_factory(database_url: str) -> SQLiteRepository:
        if "plotloom-conformance-" in database_url:
            if prepared:
                raise RuntimeError("fixture initialization failure")
            repository = repository_type(database_url)
            prepared.append(repository)
            return repository
        return repository_type(database_url)

    monkeypatch.setattr(repository_type, "close", tracked_close)
    monkeypatch.setattr(conformance, "SQLiteRepository", repository_factory)

    with pytest.raises(RuntimeError, match="fixture initialization failure"):
        conformance.run_conformance(
            source_database_url=f"sqlite:///{source_path}",
            profile_ids=["fixture"],
            sample_count=2,
            provider_resolver=_FixtureResolver(),
        )

    assert len(prepared) == 1
    assert closed == prepared


def test_m15_conformance_runs_two_profiles_three_times_through_the_real_fixture_path(
    tmp_path: Path,
) -> None:
    """Exercise the strict gate with receipts emitted by the production runner.

    The profile/sample matrix must not be simulated with hand-written receipt
    dictionaries: this verifies that the runner creates separate disposable
    repositories, executes all four stages, and returns evidence accepted by
    the exact M1.5 evaluator.
    """

    source_path = tmp_path / "m15-source.sqlite3"
    source = SQLiteRepository(f"sqlite:///{source_path}")
    try:
        source.bootstrap_default_text_provider_profile(_profile("default"))
        for profile_id in ("fixture_a", "fixture_b"):
            source.create_text_provider_profile(
                profile_id,
                profile_id,
                configuration=_profile(profile_id),
            )
    finally:
        source.close()

    profile_ids = ["fixture_a", "fixture_b"]
    receipts = conformance.run_conformance(
        source_database_url=f"sqlite:///{source_path}",
        profile_ids=profile_ids,
        sample_count=3,
        provider_resolver=_FixtureResolver(),
        parallel_profiles=True,
    )

    assert len(receipts) == 6
    expected_first_pass = {
        "total": 4,
        "accepted": 4,
        "rejected": 0,
        "outcomeUnknown": 0,
        "cancelled": 0,
        "notRun": 0,
    }
    for profile_id in profile_ids:
        samples = [receipt for receipt in receipts if receipt["profileId"] == profile_id]
        assert [sample["sampleOrdinal"] for sample in samples] == [1, 2, 3]
        assert all(sample["status"] == "succeeded" for sample in samples)
        assert all(sample["firstPass"] == expected_first_pass for sample in samples)
        assert all(sample["maxAttemptsPerWorkUnit"] == 1 for sample in samples)

    assert conformance.m15_qualification_issue_codes(
        receipts,
        profile_ids=profile_ids,
    ) == []


def test_qualification_requires_stage_level_first_pass_rate_and_attempt_limit() -> None:
    receipts = [
        {
            "profileId": "fixture",
            "profileHash": "profile-hash",
            "workloadHash": conformance.conformance_workload_hash(),
            "sampleOrdinal": ordinal,
            "runHash": f"run-{ordinal}",
            "status": "succeeded",
            "issueCodes": [],
            "firstPass": {"total": 4, "accepted": 3},
            "maxAttemptsPerWorkUnit": 4 if ordinal == 3 else 3,
        }
        for ordinal in range(1, 4)
    ]
    assert conformance.qualification_issue_codes(
        receipts,
        profile_ids=["fixture"],
        sample_count=3,
    ) == [
        "qualification.fixture.attempt_limit",
        "qualification.fixture.first_pass",
    ]


def test_qualification_rejects_mixed_workloads_and_duplicate_sample_identity() -> None:
    receipts = [
        {
            "profileId": "fixture",
            "profileHash": "profile-hash",
            "workloadHash": (
                "wrong-workload"
                if ordinal == 2
                else conformance.conformance_workload_hash()
            ),
            "sampleOrdinal": 1 if ordinal == 2 else ordinal,
            "runHash": "duplicate-run" if ordinal < 3 else "run-3",
            "status": "succeeded",
            "issueCodes": [],
            "firstPass": {"total": 4, "accepted": 4},
            "maxAttemptsPerWorkUnit": 1,
        }
        for ordinal in range(1, 4)
    ]

    assert conformance.qualification_issue_codes(
        receipts,
        profile_ids=["fixture"],
        sample_count=3,
    ) == [
        "qualification.fixture.duplicate_run",
        "qualification.fixture.sample_identity",
        "qualification.fixture.workload_identity",
    ]


def test_qualification_allows_audited_corrections_within_first_pass_budget() -> None:
    receipts = [
        {
            "profileId": "fixture",
            "profileHash": "profile-hash",
            "workloadHash": conformance.conformance_workload_hash(),
            "sampleOrdinal": ordinal,
            "runHash": f"run-{ordinal}",
            "status": "succeeded",
            "issueCodes": ["semantic.corrected"] if ordinal == 2 else [],
            "firstPass": {
                "total": 4,
                "accepted": 4 if ordinal == 1 else 3,
            },
            "maxAttemptsPerWorkUnit": 2 if ordinal == 2 else 1,
        }
        for ordinal in range(1, 4)
    ]

    assert conformance.qualification_issue_codes(
        receipts,
        profile_ids=["fixture"],
        sample_count=3,
    ) == []


def test_qualification_rejects_true_conformance_invariant_codes() -> None:
    receipts = [
        {
            "profileId": "fixture",
            "profileHash": "profile-hash",
            "workloadHash": conformance.conformance_workload_hash(),
            "sampleOrdinal": ordinal,
            "runHash": f"run-{ordinal}",
            "status": "succeeded",
            "issueCodes": (
                ["conformance.partial_canonical_install"] if ordinal == 1 else []
            ),
            "firstPass": {"total": 4, "accepted": 4},
            "maxAttemptsPerWorkUnit": 1,
        }
        for ordinal in range(1, 4)
    ]

    assert conformance.qualification_issue_codes(
        receipts,
        profile_ids=["fixture"],
        sample_count=3,
    ) == ["qualification.fixture.invariant"]


def test_m15_qualification_requires_two_distinct_profiles() -> None:
    assert conformance.m15_qualification_issue_codes(
        [],
        profile_ids=["only_one"],
    ) == ["qualification.m15.profile_identity"]
    assert conformance.m15_qualification_issue_codes(
        [],
        profile_ids=["same", "same"],
    ) == ["qualification.m15.profile_identity"]


def test_m15_qualification_accepts_two_profiles_with_three_complete_samples() -> None:
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

    assert conformance.m15_qualification_issue_codes(
        receipts,
        profile_ids=["profile_a", "profile_b"],
    ) == []


def test_m15_cli_emits_six_receipts_on_a_passing_strict_batch(
    monkeypatch,
    capsys,
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

    class _Settings:
        database_url = "sqlite:///unused.sqlite3"

        @staticmethod
        def text_api_key_for_profile(profile_id: str):
            del profile_id
            return None

    class _SettingsFactory:
        @staticmethod
        def from_env() -> _Settings:
            return _Settings()

    monkeypatch.setattr(conformance, "PlotloomSettings", _SettingsFactory)
    monkeypatch.setattr(conformance, "run_conformance", lambda **_: receipts)

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


def test_m15_cli_rejects_partial_shape_before_loading_runtime_config(capsys) -> None:
    assert conformance.main(
        ["--qualify-m15", "--profile", "fixture", "--runs", "1"]
    ) == 2
    assert "exactly two distinct profiles and three runs each" in capsys.readouterr().err
