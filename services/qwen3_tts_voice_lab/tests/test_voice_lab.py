from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from plotloom_voice_lab.app import create_app
from plotloom_voice_lab.store import Store


class FakeDesign:
    def __init__(self, fail_direction: str | None = None, duration: int = 2):
        self.fail_direction = fail_direction
        self.duration = duration

    def generate(self, text: str, direction: str, seed: int):
        if direction == self.fail_direction:
            raise RuntimeError("synthetic failure")
        samples = np.sin(np.linspace(0, 440 * 2 * np.pi, 24000 * self.duration)).astype(np.float32) * 0.2
        return samples, 24000


class FakeClone:
    def generate(self, text: str, reference: Path, reference_text: str, seed: int):
        assert reference.exists()
        assert reference_text == "同一句台词。"
        return np.zeros(24000 * 2, dtype=np.float32) + 0.1, 24000


class FakeEngine:
    def __init__(self, fail_direction: str | None = None, duration: int = 2):
        self.fail_direction = fail_direction
        self.duration = duration

    @contextmanager
    def design_session(self):
        yield FakeDesign(self.fail_direction, self.duration)

    @contextmanager
    def clone_session(self):
        yield FakeClone()


def wait_for(client: TestClient, path: str, terminal: set[str]):
    for _ in range(100):
        response = client.get(path)
        assert response.status_code == 200
        value = response.json()
        if value["status"] in terminal:
            return value
        time.sleep(0.02)
    raise AssertionError(f"job did not reach {terminal}")


def create_round(client: TestClient, directions: list[str]) -> str:
    response = client.post("/api/rounds", json={"auditionText": "同一句台词。", "directions": directions})
    assert response.status_code == 202
    return response.json()["roundId"]


def test_round_selection_clone_and_restart(tmp_path):
    app = create_app(tmp_path, FakeEngine())
    with TestClient(app) as client:
        round_id = create_round(client, ["方向一", "方向二"])
        complete = wait_for(client, f"/api/rounds/{round_id}", {"completed"})
        first, second = complete["candidates"]
        assert first["candidateId"] != second["candidateId"]
        assert first["h3Eligible"] and first["sourceSha256"] != first["h3Sha256"]
        assert client.get(f"/api/candidates/{first['candidateId']}/audio").status_code == 200
        assert client.get(f"/api/candidates/{first['candidateId']}/audio?kind=h3").status_code == 200
        selection = client.post("/api/selections", json={"candidateId": first["candidateId"]})
        assert selection.status_code == 201
        rejected = client.post("/api/clone-trials", json={"candidateId": second["candidateId"], "text": "新台词。"})
        assert rejected.status_code == 409
        clone = client.post("/api/clone-trials", json={"candidateId": first["candidateId"], "text": "新台词。"})
        assert clone.status_code == 202
        trial_id = clone.json()["trialId"]
        complete_clone = wait_for(client, f"/api/clone-trials/{trial_id}", {"completed"})
        assert complete_clone["sourceSha256"] == first["sourceSha256"]
        assert client.get(f"/api/clone-trials/{trial_id}/audio").status_code == 200
        assert client.get("/api/selections").json()["current"]["candidateId"] == first["candidateId"]

    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        assert client.get(f"/api/rounds/{round_id}").json()["candidates"][0]["sourceSha256"] == first["sourceSha256"]
        assert client.get("/api/selections").json()["current"]["candidateId"] == first["candidateId"]
        assert client.get(f"/api/clone-trials/{trial_id}").json()["audioSha256"] == complete_clone["audioSha256"]
        assert len(client.get(f"/api/clone-trials?candidateId={first['candidateId']}").json()["trials"]) == 1


def test_partial_batch_and_failed_candidate_visible(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine("坏方向"))) as client:
        round_id = create_round(client, ["好方向", "坏方向"])
        result = wait_for(client, f"/api/rounds/{round_id}", {"partial"})
        assert [item["status"] for item in result["candidates"]] == ["completed", "failed"]
        assert result["candidates"][1]["errorCode"] == "generation.failed"
        assert client.post("/api/selections", json={"candidateId": result["candidates"][1]["candidateId"]}).status_code == 409


def test_interrupted_round_is_not_replayed(tmp_path):
    store = Store(tmp_path)
    round_id = store.create_round("同一句台词。", ["方向一", "方向二"])
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        result = client.get(f"/api/rounds/{round_id}").json()
        assert result["status"] == "interrupted"
        assert all(item["status"] == "interrupted" for item in result["candidates"])
        assert not list((tmp_path / "assets").glob("**/*.wav"))


def test_rejection_and_corruption(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        for payload in [
            {"auditionText": "同一句台词。", "directions": ["一", "二", "三"]},
            {"auditionText": "同一句台词。", "directions": ["一", " "]},
            {"auditionText": "同一句台词。", "directions": ["一", "二"], "profileId": "legacy"},
        ]:
            assert client.post("/api/rounds", json=payload).status_code == 422
        round_id = create_round(client, ["一", "二"])
        candidate = wait_for(client, f"/api/rounds/{round_id}", {"completed"})["candidates"][0]
        source = Path(client.app.state.store.get_candidate(candidate["candidateId"], private=True)["sourcePath"])
        source.write_bytes(b"tampered")
        assert client.get(f"/api/candidates/{candidate['candidateId']}/audio").status_code == 409
        assert client.post("/api/selections", json={"candidateId": candidate["candidateId"]}).status_code == 409


@pytest.mark.parametrize("count", [2, 4, 6, 8])
def test_each_supported_candidate_count_has_distinct_ids_and_seeds(tmp_path, count):
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        round_id = create_round(client, [f"方向 {index}" for index in range(count)])
        result = wait_for(client, f"/api/rounds/{round_id}", {"completed"})
        assert len(result["candidates"]) == count
        assert len({item["candidateId"] for item in result["candidates"]}) == count
        assert all(0 <= item["seed"] < 2**32 for item in result["candidates"])
        assert all(item["modelRevision"].startswith("weights-sha256:") for item in result["candidates"])
        assert "sourcePath" not in str(result)


def test_long_candidate_remains_reviewable_but_not_h3_eligible(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine(duration=11))) as client:
        round_id = create_round(client, ["方向一", "方向二"])
        result = wait_for(client, f"/api/rounds/{round_id}", {"completed"})
        candidate = result["candidates"][0]
        assert not candidate["h3Eligible"]
        assert candidate["errorCode"] == "h3.duration_out_of_range"
        assert client.get(f"/api/candidates/{candidate['candidateId']}/audio").status_code == 200
        assert client.get(f"/api/candidates/{candidate['candidateId']}/audio?kind=h3").status_code == 409


def test_h3_preparation_failure_keeps_original_candidate_reviewable(tmp_path, monkeypatch):
    def fail_preparation(*_args, **_kwargs):
        raise RuntimeError("synthetic resampling failure")

    monkeypatch.setattr("plotloom_voice_lab.media.resample_poly", fail_preparation)
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        round_id = create_round(client, ["方向一", "方向二"])
        result = wait_for(client, f"/api/rounds/{round_id}", {"completed"})
        assert all(item["status"] == "completed" for item in result["candidates"])
        assert all(item["errorCode"] == "h3.preparation_failed" for item in result["candidates"])
        assert all(not item["h3Eligible"] for item in result["candidates"])
        for item in result["candidates"]:
            assert client.get(f"/api/candidates/{item['candidateId']}/audio").status_code == 200
            assert client.get(f"/api/candidates/{item['candidateId']}/audio?kind=h3").status_code == 409
        assert client.post("/api/selections", json={"candidateId": result["candidates"][0]["candidateId"]}).status_code == 201
