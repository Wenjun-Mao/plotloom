from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from plotloom import alpha_acceptance
from plotloom.generation.contracts import ProviderCapabilities, ProviderResponse, ProviderUsage
from plotloom.persistence import SQLiteRepository
from plotloom.provider_profiles import PresetId, StageMaxOutputTokens, TextProviderProfileSnapshot


def _profile(profile_id: str) -> TextProviderProfileSnapshot:
    return TextProviderProfileSnapshot.model_validate({
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
        "stageMaxOutputTokens": StageMaxOutputTokens(story_bible=8192, story_graph=8192, scene_beats=4096, storyboard=4096),
        "presetId": PresetId.COMPATIBLE_V1,
    })


def _json_after(content: str, marker: str) -> Any:
    return json.JSONDecoder().raw_decode(content.rsplit(marker, 1)[1].lstrip())[0]


class _FixtureProvider:
    name = "fixture-provider"
    capabilities = ProviderCapabilities(json_schema=True)

    def generate(self, request, secret) -> ProviderResponse:
        assert secret is None
        prompt = "\n".join(message.content for message in request.messages)
        if "【不可变图骨架清单】" in prompt:
            topology = _json_after(prompt, "【不可变图骨架清单】")
            payload = {
                "nodes": [{"id": node["id"], "title": "固定节点", "summary": "角色继续前行。"} for node in topology["nodes"]],
                "edges": [{"id": edge["id"], "choiceText": "继续" if edge["kind"] == "choice" else None, "stateEffects": {"route": edge["id"]} if edge["kind"] == "choice" else {}} for edge in topology["edges"]],
                "joinContracts": [{"id": join["id"], "requiredStateKeys": [], "allowedDifferences": [], "reconciliation": "不同路线汇合。", "notes": ""} for join in topology["joinContracts"]],
            }
        elif "【目标故事节点】" in prompt:
            node = _json_after(prompt, "【目标故事节点】")
            scene_id, beat_id = f"scene-{node['id']}", f"beat-{node['id']}"
            state = {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}
            payload = {
                "scenes": [{"localSceneId": scene_id, "order": 1, "title": node["title"], "objective": "推进叙事", "locationId": None, "characterIds": [], "durationBudgetUnits": 1, "entryState": state, "exitState": state}],
                "beats": [{"localBeatId": beat_id, "sceneLocalId": scene_id, "order": 1, "description": "角色在雪中前行。", "purpose": "推进叙事", "visibleEvent": "角色握紧信件。", "immediateResult": "角色继续前行。", "dramaticChange": "继续前行", "entryState": state, "exitState": state, "continuityAnchors": [], "continuityDelta": {}}],
                "dialogueCues": [],
            }
        elif "【目标戏剧场景】" in prompt:
            scene = _json_after(prompt, "【目标戏剧场景】")
            beat_id = _json_after(prompt, "【该场景节拍】")[0]["id"]
            state = {"facts": {}, "entityStates": [], "screenDirection": None, "lighting": None, "sound": None, "notes": []}
            payload = {
                "shots": [{"localShotId": f"shot-{scene['id']}", "order": 1, "title": "信件特写", "shotSize": "medium", "durationUnits": 1, "cameraAngle": "", "cameraMovement": "", "composition": "", "visualIntent": "交代选择", "motionIntent": "稳定推进", "action": "角色握紧信件。", "transition": "硬切", "cueIds": [], "audioPlan": {"events": []}, "characterIds": [], "locationId": None, "propIds": [], "requiredEntityStates": [], "entryState": state, "exitState": state}],
                "primaryShotLocalIdByBeat": {beat_id: f"shot-{scene['id']}"}, "supportingBeatLinks": [],
            }
        else:
            payload = {"logline": "角色做出选择。", "premise": "一封信改变当下。", "genre": "", "tone": "", "audience": "", "narrativePromise": "", "visualLanguage": "", "themes": [], "worldRules": [], "knownFacts": [], "openQuestions": [], "sourceNotes": [], "characters": [], "locations": [], "props": []}
        content = json.dumps(payload, ensure_ascii=False)
        return ProviderResponse(provider=self.name, model=request.model, raw={"choices": [{"message": {"role": "assistant", "content": content}}]}, usage=ProviderUsage(input_tokens=7, output_tokens=11))


class _FixtureResolver:
    def __init__(self) -> None:
        self.provider = _FixtureProvider()

    def resolve(self, provider_snapshot):
        return self.provider, str(provider_snapshot["textModel"])


def _source_database(tmp_path: Path) -> Path:
    path = tmp_path / "source.sqlite3"
    source = SQLiteRepository(f"sqlite:///{path}")
    try:
        source.bootstrap_default_text_provider_profile(_profile("default"))
        for profile_id in ("real_looking_a", "real_looking_b"):
            source.create_text_provider_profile(profile_id, profile_id, configuration=_profile(profile_id))
    finally:
        source.close()
    return path


def _file_state(path: Path) -> tuple[bytes, int, int, int] | None:
    if not path.exists():
        return None
    stat = path.stat()
    return path.read_bytes(), stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def _profile_payload(profile_id: str, version: int) -> dict[str, Any]:
    payload = _profile(profile_id).model_dump(mode="json", by_alias=True)
    payload["profileVersion"] = version
    payload["profileHash"] = ""
    return TextProviderProfileSnapshot.model_validate(payload).model_dump(mode="json", by_alias=True)


def test_alpha_runs_full_18_cell_fixture_matrix_writes_blinded_reviews_and_cleans_up(tmp_path: Path, monkeypatch) -> None:
    source_path = _source_database(tmp_path)
    review_directory = tmp_path / "untracked-review"
    roots: list[Path] = []
    real_temporary_directory = tempfile.TemporaryDirectory

    class _TrackedTemporaryDirectory(real_temporary_directory):
        def __enter__(self):
            path = super().__enter__()
            roots.append(Path(path))
            return path

    monkeypatch.setattr(alpha_acceptance.tempfile, "TemporaryDirectory", _TrackedTemporaryDirectory)
    result = alpha_acceptance.run_alpha_acceptance(
        source_database_url=f"sqlite:///{source_path}",
        profile_ids=["real_looking_a", "real_looking_b"],
        review_directory=review_directory,
        provider_resolver=_FixtureResolver(),
        commit_sha="a" * 40,
    )

    assert len(result.receipts) == 18
    assert result.qualification_issues == ()
    assert alpha_acceptance.alpha_qualification_issue_codes(result.receipts) == []
    assert {receipt["profileId"] for receipt in result.receipts} == {"profile-01", "profile-02"}
    assert {receipt["storyId"] for receipt in result.receipts} == {"story-01", "story-02", "story-03"}
    assert {receipt["sampleId"] for receipt in result.receipts} == {
        f"{story}-repeat-{repeat:02d}" for story in ("story-01", "story-02", "story-03") for repeat in range(1, 4)
    }
    expected_fields = {"commit", "profileId", "storyId", "sampleId", "contractHash", "status", "issueCodes", "durationMilliseconds", "tokens", "scores"}
    assert all(set(receipt) == expected_fields for receipt in result.receipts)
    assert all(receipt["commit"] == "a" * 40 for receipt in result.receipts)
    assert all(receipt["status"] == "succeeded" for receipt in result.receipts)
    assert all(receipt["scores"] == {"firstPass": {"total": 4, "accepted": 4, "rejected": 0, "outcomeUnknown": 0, "cancelled": 0, "notRun": 0}, "maxAttemptsPerWorkUnit": 1} for receipt in result.receipts)
    receipt_text = json.dumps(result.receipts, ensure_ascii=False)
    for forbidden in ("real_looking_a", "real_looking_b", "fixture-provider", "fixture-model", "127.0.0.1", "http://", "prompt", "response"):
        assert forbidden not in receipt_text
    assert roots and all(not root.exists() for root in roots)

    assert [path.name for path in result.review_paths] == [f"review-{ordinal:02d}.json" for ordinal in range(1, 7)]
    assert sorted(path.name for path in review_directory.iterdir()) == [f"review-{ordinal:02d}.json" for ordinal in range(1, 7)]
    for review_path in result.review_paths:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
        assert set(payload) == {"storyBible", "storyGraph", "sceneBeats", "storyboard"}
        review_text = review_path.read_text(encoding="utf-8")
        for forbidden in ("profileId", "provider", "fixture", "endpoint", "prompt", "response", "runId", "real_looking"):
            assert forbidden not in review_text


def test_alpha_qualification_enforces_first_pass_and_unknown_outcome_invariants(tmp_path: Path) -> None:
    source_path = _source_database(tmp_path)
    result = alpha_acceptance.run_alpha_acceptance(
        source_database_url=f"sqlite:///{source_path}",
        profile_ids=["real_looking_a", "real_looking_b"],
        review_directory=tmp_path / "reviews",
        provider_resolver=_FixtureResolver(),
    )
    receipts = [dict(receipt) for receipt in result.receipts]
    for index in (0, 1):
        receipts[index] = {
            **receipts[index],
            "issueCodes": ["provider.outcome_unknown"] if index == 0 else [],
            "scores": {**receipts[index]["scores"], "firstPass": {**receipts[index]["scores"]["firstPass"], "accepted": 0}},
        }
    issues = alpha_acceptance.alpha_qualification_issue_codes(receipts)
    assert "alpha.matrix.invariant" in issues
    assert "alpha.profile-01.first_pass" in issues


def test_alpha_refuses_to_overwrite_review_directory(tmp_path: Path) -> None:
    review_directory = tmp_path / "reviews"
    review_directory.mkdir()
    (review_directory / "keep.txt").write_text("do not replace", encoding="utf-8")
    try:
        alpha_acceptance.run_alpha_acceptance(
            source_database_url="sqlite:///unused.sqlite3",
            profile_ids=["a", "b"],
            review_directory=review_directory,
            provider_resolver=_FixtureResolver(),
        )
    except ValueError as error:
        assert "must be empty" in str(error)
    else:
        raise AssertionError("nonempty review output must be refused")


def test_source_profile_loader_is_read_only_and_keeps_live_wal_visible(tmp_path: Path, monkeypatch) -> None:
    source_path = _source_database(tmp_path)
    writer = sqlite3.connect(source_path)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute(
            "INSERT INTO v2_text_provider_profiles (id, display_name, settings, revision, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("wal_visible", "wal_visible", json.dumps(_profile("wal_visible").model_dump(mode="json", by_alias=True)), 1, "2026-09-04T00:00:00", "2026-09-04T00:00:00"),
        )
        writer.commit()
        watched_paths = [source_path, source_path.with_name(f"{source_path.name}-wal"), source_path.with_name(f"{source_path.name}-shm")]
        before = {path: _file_state(path) for path in watched_paths}
        assert before[source_path.with_name(f"{source_path.name}-wal")] is not None

        def repository_must_not_be_used(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("source profile loading must not initialize SQLiteRepository or its migrator")

        monkeypatch.setattr(alpha_acceptance, "SQLiteRepository", repository_must_not_be_used)
        profiles = alpha_acceptance._load_named_profiles(f"sqlite:///{source_path}", ["wal_visible"])

        assert [profile.profile_id for profile in profiles] == ["wal_visible"]
        assert {path: _file_state(path) for path in watched_paths} == before
    finally:
        writer.close()


def test_source_profile_loader_uses_consistent_snapshot_during_writer_checkpoint_pressure(tmp_path: Path) -> None:
    source_path = _source_database(tmp_path)
    updates_path = tmp_path / "profile-updates.json"
    updates_path.write_text(json.dumps([
        {
            "a": _profile_payload("real_looking_a", version),
            "b": _profile_payload("real_looking_b", version),
            "version": version,
        }
        for version in range(2, 202)
    ]), encoding="utf-8")
    writer = subprocess.Popen([
        sys.executable,
        "-c",
        """
import json
import sqlite3
import sys
import time

database_path, updates_path = sys.argv[1:]
updates = json.loads(open(updates_path, encoding=\"utf-8\").read())
connection = sqlite3.connect(database_path, timeout=10)
connection.execute(\"PRAGMA journal_mode=WAL\")
connection.execute(\"PRAGMA wal_autocheckpoint=0\")
for update in updates:
    connection.execute(\"BEGIN IMMEDIATE\")
    connection.execute(\"UPDATE v2_text_provider_profiles SET settings = ?, revision = ? WHERE id = ?\", (json.dumps(update[\"a\"]), update[\"version\"], \"real_looking_a\"))
    connection.execute(\"UPDATE v2_text_provider_profiles SET settings = ?, revision = ? WHERE id = ?\", (json.dumps(update[\"b\"]), update[\"version\"], \"real_looking_b\"))
    connection.commit()
    connection.execute(\"PRAGMA wal_checkpoint(PASSIVE)\").fetchall()
    time.sleep(0.002)
connection.close()
""",
        str(source_path),
        str(updates_path),
    ])
    observed_versions: set[int] = set()
    while writer.poll() is None:
        profiles = alpha_acceptance._load_named_profiles(
            f"sqlite:///{source_path}",
            ["real_looking_a", "real_looking_b"],
        )
        assert profiles[0].profile_version == profiles[1].profile_version
        observed_versions.add(profiles[0].profile_version)
    assert writer.wait(timeout=10) == 0
    assert observed_versions


def test_source_profile_loader_does_not_deadlock_a_reserved_rollback_writer(tmp_path: Path) -> None:
    source_path = _source_database(tmp_path)
    with sqlite3.connect(source_path) as connection:
        assert connection.execute("PRAGMA journal_mode=DELETE").fetchone()[0].lower() == "delete"
    update = {
        "a": _profile_payload("real_looking_a", 2),
        "b": _profile_payload("real_looking_b", 2),
    }
    update_path = tmp_path / "rollback-update.json"
    ready_path = tmp_path / "writer-ready"
    update_path.write_text(json.dumps(update), encoding="utf-8")
    writer = subprocess.Popen([
        sys.executable,
        "-c",
        """
import json
import sqlite3
import sys
import time
from pathlib import Path

database_path, update_path, ready_path = sys.argv[1:]
update = json.loads(Path(update_path).read_text(encoding=\"utf-8\"))
connection = sqlite3.connect(database_path, timeout=1)
connection.execute(\"BEGIN IMMEDIATE\")
connection.execute(\"UPDATE v2_text_provider_profiles SET settings = ?, revision = 2 WHERE id = ?\", (json.dumps(update[\"a\"]), \"real_looking_a\"))
connection.execute(\"UPDATE v2_text_provider_profiles SET settings = ?, revision = 2 WHERE id = ?\", (json.dumps(update[\"b\"]), \"real_looking_b\"))
Path(ready_path).write_text(\"reserved\", encoding=\"utf-8\")
time.sleep(0.4)
connection.commit()
connection.close()
""",
        str(source_path),
        str(update_path),
        str(ready_path),
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 5
    while not ready_path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert ready_path.exists(), writer.communicate(timeout=5)

    profiles = alpha_acceptance._load_named_profiles(
        f"sqlite:///{source_path}",
        ["real_looking_a", "real_looking_b"],
    )
    stdout, stderr = writer.communicate(timeout=5)
    assert writer.returncode == 0, (stdout, stderr)
    assert [profile.profile_version for profile in profiles] == [2, 2]

    watched_paths = [
        source_path,
        source_path.with_name(f"{source_path.name}-journal"),
        source_path.with_name(f"{source_path.name}-wal"),
        source_path.with_name(f"{source_path.name}-shm"),
    ]
    before = {path: _file_state(path) for path in watched_paths}
    stable_profiles = alpha_acceptance._load_named_profiles(
        f"sqlite:///{source_path}",
        ["real_looking_a", "real_looking_b"],
    )
    assert [profile.profile_version for profile in stable_profiles] == [2, 2]
    assert {path: _file_state(path) for path in watched_paths} == before


def test_source_profile_snapshot_rejects_a_recreated_shm_inode(tmp_path: Path, monkeypatch) -> None:
    source_path = _source_database(tmp_path)
    writer = sqlite3.connect(source_path)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute(
            "UPDATE v2_text_provider_profiles SET updated_at = ? WHERE id = ?",
            ("2026-09-04T00:00:00", "real_looking_a"),
        )
        writer.commit()
        source_shm_path = source_path.with_name(f"{source_path.name}-shm")
        assert source_shm_path.exists()
        original_copyfile = alpha_acceptance.shutil.copyfile

        def recreate_shm_after_main_copy(source: str | Path, destination: str | Path, *args: object, **kwargs: object) -> str | Path:
            copied = original_copyfile(source, destination, *args, **kwargs)
            if Path(source) == source_path:
                contents = source_shm_path.read_bytes()
                source_shm_path.unlink()
                source_shm_path.write_bytes(contents)
            return copied

        monkeypatch.setattr(alpha_acceptance.shutil, "copyfile", recreate_shm_after_main_copy)
        copied_path = tmp_path / "snapshot.sqlite3"
        try:
            alpha_acceptance._copy_stable_source_sqlite_pair(source_path, copied_path)
        except RuntimeError as error:
            assert "changed during snapshot" in str(error)
        else:
            raise AssertionError("a recreated WAL-index inode must invalidate the snapshot")
        assert not copied_path.exists()
    finally:
        writer.close()


def test_alpha_rejects_relative_or_checkout_review_directories(tmp_path: Path) -> None:
    source_path = _source_database(tmp_path)
    for directory, expected_message in (
        (Path("relative-alpha-review"), "absolute path"),
        (Path.cwd() / ".alpha-review-must-not-be-created", "outside the source checkout"),
    ):
        try:
            alpha_acceptance.run_alpha_acceptance(
                source_database_url=f"sqlite:///{source_path}",
                profile_ids=["real_looking_a", "real_looking_b"],
                review_directory=directory,
                provider_resolver=_FixtureResolver(),
            )
        except ValueError as error:
            assert expected_message in str(error)
        else:
            raise AssertionError("unsafe review output must be refused")


def test_alpha_cli_returns_one_for_qualification_failure(tmp_path: Path, monkeypatch, capsys) -> None:
    receipt = {
        "commit": "a" * 40,
        "contractHash": alpha_acceptance.alpha_contract_hash(),
        "profileId": "profile-01",
        "storyId": "story-01",
        "sampleId": "story-01-repeat-01",
        "status": "failed",
        "issueCodes": [],
        "durationMilliseconds": 0,
        "tokens": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
        "scores": {"firstPass": {"total": 4, "accepted": 0, "rejected": 4, "outcomeUnknown": 0, "cancelled": 0, "notRun": 0}, "maxAttemptsPerWorkUnit": 1},
    }
    monkeypatch.setattr(
        alpha_acceptance,
        "run_alpha_acceptance",
        lambda **_kwargs: alpha_acceptance.AlphaAcceptanceResult((receipt,), (), ("alpha.matrix.run_completion",)),
    )

    assert alpha_acceptance.main([
        "--profile", "one",
        "--profile", "two",
        "--review-directory", str(tmp_path / "review"),
        "--commit", "a" * 40,
    ]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == receipt
    assert "Alpha qualification failed: alpha.matrix.run_completion" in captured.err


def test_alpha_late_qualification_failure_never_publishes_partial_review_pack(tmp_path: Path, monkeypatch) -> None:
    source_path = _source_database(tmp_path)
    review_directory = tmp_path / "review-pack"
    original_receipt_for = alpha_acceptance._receipt_for
    receipt_count = 0

    def late_failed_receipt(*args: object, **kwargs: object) -> dict[str, Any]:
        nonlocal receipt_count
        receipt_count += 1
        receipt = original_receipt_for(*args, **kwargs)
        return {**receipt, "status": "failed"} if receipt_count == 18 else receipt

    monkeypatch.setattr(alpha_acceptance, "_receipt_for", late_failed_receipt)
    result = alpha_acceptance.run_alpha_acceptance(
        source_database_url=f"sqlite:///{source_path}",
        profile_ids=["real_looking_a", "real_looking_b"],
        review_directory=review_directory,
        provider_resolver=_FixtureResolver(),
        commit_sha="a" * 40,
    )

    assert "alpha.matrix.run_completion" in result.qualification_issues
    assert result.review_paths == ()
    assert not review_directory.exists()
    assert not list(tmp_path.glob(".review-pack.plotloom-stage-*"))


def test_alpha_cli_rejects_non_commit_sha(tmp_path: Path, capsys) -> None:
    try:
        alpha_acceptance.main([
            "--profile", "one",
            "--profile", "two",
            "--review-directory", str(tmp_path / "review"),
            "--commit", "not-a-commit",
        ])
    except SystemExit as error:
        assert error.code == 2
    else:
        raise AssertionError("invalid commit SHA must be rejected by the CLI parser")
    assert "40-character hexadecimal Git commit SHA" in capsys.readouterr().err
