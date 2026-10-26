from __future__ import annotations

import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from plotloom_voice_lab.app import create_app as production_app
from fixtures.shared_lane import SharedLaneFixture


def create_app(data_dir, engine=None):
    return production_app(data_dir, engine, lane_client=SharedLaneFixture(data_dir))


class FakeDesign:
    def __init__(self, fail_direction: str | None = None, duration: int = 2, observed: list[str] | None = None):
        self.fail_direction, self.duration, self.observed = fail_direction, duration, observed

    def generate(self, text: str, direction: str, seed: int):
        if self.observed is not None:
            self.observed.append(direction)
        if self.fail_direction and direction.endswith(self.fail_direction):
            raise RuntimeError("synthetic failure")
        return np.full(24000 * self.duration, 0.1, dtype=np.float32), 24000


class FakeClone:
    def generate(self, text: str, reference: Path, reference_text: str, seed: int):
        assert reference.is_file() and reference_text.strip()
        return np.full(48000, 0.2, dtype=np.float32), 24000


class FakeEngine:
    def __init__(self, fail_direction: str | None = None, duration: int = 2):
        self.fail_direction, self.duration = fail_direction, duration
        self.observed_directions: list[str] = []

    def design(self):
        return FakeDesign(self.fail_direction, self.duration, self.observed_directions)

    def availability(self):
        return {key: True for key in ("qwen_design", "moss_design", "qwen_base", "index_base")}

    def stop(self):
        pass

    def release_confirmed(self):
        return True

    def run(self, snapshot, values, output_dir, phase, evidence):
        phase("loading_model")
        phase("synthesizing")
        if snapshot["stage"] == "creation":
            audio, rate = self.design().generate(values["text"], values["direction"], values["seed"])
        else:
            audio, rate = FakeClone().generate(values["text"], Path(values["reference"]), values["referenceText"], values["seed"])
            control = values["delivery"]
            mode = control.get("mode", "none")
            record = {"mode": mode}
            if mode != "none":
                vector = control.get("vector", [0, .85, 0, 0, 0, 0, 0, 0])
                record.update(effectiveVector=vector)
                if mode == "text":
                    record.update(rawVector=vector, classifierSeconds=.1)
            evidence(record)
        output_dir.mkdir(parents=True)
        path = output_dir / "audio.wav"
        # Native rate varies with engine; the worker must not force 24 kHz.
        rate = snapshot["sampleRate"]
        sf.write(path, audio[:rate * self.duration], rate, subtype="FLOAT")
        return path, {"processElapsedSeconds": .1, "peakTorchGiB": 0, "processId": 0}


class BlockingDesign(FakeDesign):
    def __init__(self, started: threading.Event, release: threading.Event):
        super().__init__()
        self.started, self.release = started, release

    def generate(self, text: str, direction: str, seed: int):
        if direction.endswith("方向二"):
            self.started.set()
            if not self.release.wait(timeout=10):
                raise TimeoutError("test did not release design generation")
        return super().generate(text, direction, seed)


class BlockingEngine(FakeEngine):
    def __init__(self, started: threading.Event, release: threading.Event):
        super().__init__()
        self.started, self.release = started, release

    def design(self):
        return BlockingDesign(self.started, self.release)


def wait_for(client: TestClient, path: str):
    for _ in range(150):
        result = client.get(path)
        assert result.status_code == 200
        value = result.json()
        if value["status"] not in {"queued", "running"}:
            return value
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def project(client: TestClient, name: str = "声线项目") -> dict:
    result = client.post("/api/projects", json={"name": name})
    assert result.status_code == 201
    p = result.json()
    result = client.put(f"/api/projects/{p['projectId']}", json={
        "expectedRevision": p["revision"], "name": name,
        "brief": "人物方向", "auditionText": "同一句台词。",
    })
    assert result.status_code == 200
    return result.json()


def candidate(client: TestClient, p: dict, direction: str = "方向一") -> tuple[dict, dict]:
    result = client.post(f"/api/projects/{p['projectId']}/candidates", json={
        "expectedProjectRevision": p["revision"], "direction": direction, "engineId": "qwen_design",
    })
    assert result.status_code == 201, result.text
    p = result.json()
    return p, p["candidates"][-1]


def generate(client: TestClient, p: dict, c: dict) -> dict:
    response = client.post(f"/api/candidates/{c['candidateId']}/generations", json={
        "expectedProjectRevision": p["revision"], "expectedCandidateRevision": c["revision"],
    })
    assert response.status_code == 202, response.text
    return wait_for(client, f"/api/generations/{response.json()['generationId']}")
