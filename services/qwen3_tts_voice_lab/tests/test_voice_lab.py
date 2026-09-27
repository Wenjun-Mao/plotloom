from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from plotloom_voice_lab.app import create_app
from plotloom_voice_lab.media import file_sha256, persist_candidate
from plotloom_voice_lab.store import Store


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
        assert reference.is_file() and reference_text == "同一句台词。"
        return np.full(48000, 0.2, dtype=np.float32), 24000


class FakeEngine:
    def __init__(self, fail_direction: str | None = None, duration: int = 2):
        self.fail_direction, self.duration = fail_direction, duration
        self.observed_directions: list[str] = []

    @contextmanager
    def design_session(self):
        yield FakeDesign(self.fail_direction, self.duration, self.observed_directions)

    @contextmanager
    def clone_session(self):
        yield FakeClone()


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
        "expectedProjectRevision": p["revision"], "direction": direction,
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


def test_project_candidate_replacement_publication_and_restart(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        assert client.get("/api/projects").json() == {"projects": []}
        assert "project" not in client.get("/").text.lower().split("<body>")[0]
        p = project(client)
        p, first = candidate(client, p)
        first_id = first["candidateId"]
        original = generate(client, p, first)
        assert original["status"] == "completed" and original["h3Eligible"]
        original_path = Path(client.app.state.store.generations.get(original["generationId"], private=True)["sourcePath"])
        original_hash = file_sha256(original_path)
        p = client.get(f"/api/projects/{p['projectId']}").json()
        p, second = candidate(client, p, "方向二")
        second_gen = generate(client, p, second)
        p = client.get(f"/api/projects/{p['projectId']}").json()
        first = p["candidates"][0]
        assert client.post(f"/api/projects/{p['projectId']}/selections", json={"generationId": original["generationId"]}).status_code == 201
        assert client.post("/api/voices", json={"projectId": p["projectId"], "generationId": second_gen["generationId"]}).status_code == 409
        voice = client.post("/api/voices", json={"projectId": p["projectId"], "generationId": original["generationId"]}).json()
        assert voice["sourceSha256"] == original_hash
        assert client.get(f"/api/voices/{voice['voiceId']}/audio").status_code == 200
        regenerated = generate(client, p, first)
        assert regenerated["status"] == "completed" and regenerated["generationId"] != original["generationId"]
        assert not original_path.exists()
        assert client.get(f"/api/generations/{original['generationId']}/audio").status_code == 409
        assert client.post("/api/voices", json={"projectId": p["projectId"], "generationId": original["generationId"]}).json()["voiceId"] == voice["voiceId"]
        p = client.get(f"/api/projects/{p['projectId']}").json()
        assert p["candidates"][0]["candidateId"] == first_id
        assert p["candidates"][1]["currentGeneration"]["sourceSha256"] == second_gen["sourceSha256"]
        assert p["selectedGenerationId"] is None
        assert client.request("DELETE", f"/api/projects/{p['projectId']}", json={"expectedRevision": p["revision"], "confirmName": p["name"]}).status_code == 204
        assert client.get(f"/api/projects/{p['projectId']}").status_code == 404
        assert client.get(f"/api/voices/{voice['voiceId']}/audio").status_code == 200
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        assert client.get(f"/api/voices/{voice['voiceId']}").json()["sourceSha256"] == original_hash


def test_failed_replacement_retains_old_and_revision_guard(tmp_path):
    engine = FakeEngine()
    with TestClient(create_app(tmp_path, engine)) as client:
        p = project(client)
        p, c = candidate(client, p)
        old = generate(client, p, c)
        p = client.get(f"/api/projects/{p['projectId']}").json()
        c = p["candidates"][0]
        conflict = client.put(f"/api/projects/{p['projectId']}", json={
            "expectedRevision": 1, "name": "stale", "brief": "", "auditionText": "同一句台词。",
        })
        assert conflict.status_code == 409 and conflict.json()["detail"]["code"] == "project.revision_conflict"
        engine.fail_direction = "方向一"
        failed = generate(client, p, c)
        assert failed["status"] == "failed"
        fresh = client.get(f"/api/projects/{p['projectId']}").json()["candidates"][0]
        assert fresh["currentGeneration"]["generationId"] == old["generationId"]
        assert client.get(f"/api/generations/{old['generationId']}/audio").status_code == 200


def test_selection_clone_and_corruption_guard(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        p = project(client)
        p, c = candidate(client, p)
        gen = generate(client, p, c)
        assert client.post("/api/clone-trials", json={"projectId": p["projectId"], "generationId": gen["generationId"], "text": "新台词。"}).status_code == 409
        assert client.post(f"/api/projects/{p['projectId']}/selections", json={"generationId": gen["generationId"]}).status_code == 201
        trial = client.post("/api/clone-trials", json={"projectId": p["projectId"], "generationId": gen["generationId"], "text": "新台词。"}).json()
        assert wait_for(client, f"/api/clone-trials/{trial['trialId']}")["status"] == "completed"
        assert client.get(f"/api/clone-trials/{trial['trialId']}/audio").status_code == 200
        source = Path(client.app.state.store.generations.get(gen["generationId"], private=True)["sourcePath"])
        source.write_bytes(b"tampered")
        assert client.get(f"/api/generations/{gen['generationId']}/audio").status_code == 409
        assert client.post("/api/voices", json={"projectId": p["projectId"], "generationId": gen["generationId"]}).status_code == 409


def test_interrupted_job_not_replayed_and_old_routes_removed(tmp_path):
    store = Store(tmp_path)
    p = store.projects.create("测试")
    p = store.projects.update(p["projectId"], p["revision"], "测试", "", "同一句台词。")
    p = store.projects.add_candidate(p["projectId"], p["revision"], "方向一")
    generation = store.generations.create(p["candidates"][0]["candidateId"], p["revision"], 1, 7)
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        assert client.get(f"/api/generations/{generation['generationId']}").json()["status"] == "interrupted"
        assert client.post('/api/rounds', json={}).status_code == 404
        assert client.post('/api/selections', json={}).status_code == 404
        assert not list((tmp_path / "assets").glob("**/*.wav"))


def test_legacy_migration_preserves_checked_audio(tmp_path):
    db_path = tmp_path / "voice_lab.sqlite3"
    media = persist_candidate(tmp_path, "vc_" + "a" * 32, "vg_" + "b" * 32, np.ones(48000, dtype=np.float32) * .1, 24000)
    db = sqlite3.connect(db_path)
    db.executescript("""
        CREATE TABLE rounds (id TEXT PRIMARY KEY,audition_text TEXT,status TEXT,error_code TEXT,created_at TEXT,updated_at TEXT);
        CREATE TABLE candidates (id TEXT PRIMARY KEY,round_id TEXT,ordinal INTEGER,direction TEXT,seed INTEGER,model_id TEXT,model_revision TEXT,status TEXT,error_code TEXT,source_path TEXT,source_sha256 TEXT,source_duration_seconds REAL,source_sample_rate INTEGER,h3_path TEXT,h3_sha256 TEXT,h3_eligible INTEGER,preparation_version TEXT,created_at TEXT,updated_at TEXT);
        CREATE TABLE selections (id TEXT PRIMARY KEY,candidate_id TEXT,selected_at TEXT);
        CREATE TABLE clone_trials (id TEXT PRIMARY KEY,candidate_id TEXT,text TEXT,seed INTEGER,model_id TEXT,model_revision TEXT,source_sha256 TEXT,status TEXT,error_code TEXT,audio_path TEXT,audio_sha256 TEXT,duration_seconds REAL,sample_rate INTEGER,created_at TEXT,updated_at TEXT);
    """)
    stamp = "2026-09-26T00:00:00+00:00"
    db.execute("INSERT INTO rounds VALUES (?,?,?,?,?,?)", ("vr_legacy", "同一句台词。", "completed", None, stamp, stamp))
    db.execute("INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        "vc_" + "a" * 32, "vr_legacy", 1, "试验方向", 7, "model", "revision", "completed", None,
        media["sourcePath"], media["sourceSha256"], media["sourceDurationSeconds"], 24000,
        media["h3Path"], media["h3Sha256"], 1, media["preparationVersion"], stamp, stamp,
    ))
    db.execute("INSERT INTO selections VALUES (?,?,?)", ("vs_legacy", "vc_" + "a" * 32, stamp))
    db.commit(); db.close()
    store = Store(tmp_path)
    projects = store.projects.list()
    assert len(projects) == 1 and "pilot" in projects[0]["name"]
    migrated = store.projects.get(projects[0]["projectId"])
    assert migrated["candidates"][0]["currentGeneration"]["sourceSha256"] == media["sourceSha256"]
    assert migrated["selectedGenerationId"] == migrated["candidates"][0]["currentGeneration"]["generationId"]
    assert Path(media["sourcePath"]).is_file()
    assert sqlite3.connect(db_path).execute("PRAGMA user_version").fetchone()[0] == 2


def test_invalid_requests_and_non_h3_clip(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine(duration=11))) as client:
        assert client.post("/api/projects", json={"name": " "}).status_code == 422
        assert client.get("/api/candidates/vc_" + "0" * 32 + "/generations").status_code == 404
        p = project(client)
        assert client.post(f"/api/projects/{p['projectId']}/candidates", json={"expectedProjectRevision": p["revision"], "direction": " "}).status_code == 422
        p, c = candidate(client, p)
        gen = generate(client, p, c)
        assert gen["status"] == "completed" and not gen["h3Eligible"]
        assert client.get(f"/api/generations/{gen['generationId']}/audio").status_code == 200
        assert client.get(f"/api/generations/{gen['generationId']}/audio?kind=h3").status_code == 409
        assert client.post(f"/api/projects/{p['projectId']}/selections", json={"generationId": gen["generationId"]}).status_code == 201
        assert client.post("/api/voices", json={"projectId": p["projectId"], "generationId": gen["generationId"]}).status_code == 409


def test_clone_reference_is_pinned_across_replacement(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        p = project(client)
        p, c = candidate(client, p)
        old = generate(client, p, c)
        assert client.post(f"/api/projects/{p['projectId']}/selections", json={"generationId": old["generationId"]}).status_code == 201
        store = client.app.state.store
        queued = store.clones.create(p["projectId"], old["generationId"], "新台词。", 19)
        pinned = Path(store.clones.get(queued["trialId"], private=True)["referencePath"])
        assert file_sha256(pinned) == old["sourceSha256"]
        p = client.get(f"/api/projects/{p['projectId']}").json()
        new = generate(client, p, p["candidates"][0])
        assert new["status"] == "completed" and pinned.is_file()
        client.app.state.worker.submit("clone", queued["trialId"])
        assert wait_for(client, f"/api/clone-trials/{queued['trialId']}")["status"] == "completed"


def test_project_isolation_and_busy_deletion(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        first = project(client, "甲")
        second = project(client, "乙")
        first, candidate_one = candidate(client, first)
        assert client.get(f"/api/projects/{second['projectId']}").json()["candidates"] == []
        generation = client.app.state.store.generations.create(candidate_one["candidateId"], first["revision"], 1, 3)
        deletion = client.request("DELETE", f"/api/projects/{first['projectId']}", json={
            "expectedRevision": first["revision"], "confirmName": "甲",
        })
        assert deletion.status_code == 409 and deletion.json()["detail"]["code"] == "project.busy"
        assert client.get(f"/api/generations/{generation['generationId']}").json()["status"] == "queued"


def test_shared_brief_is_frozen_and_sent_to_design_engine(tmp_path):
    engine = FakeEngine()
    with TestClient(create_app(tmp_path, engine)) as client:
        p = project(client)
        p, c = candidate(client, p)
        gen = generate(client, p, c)
        assert gen["brief"] == "人物方向"
        assert engine.observed_directions == ["人物方向\n方向一"]
        p = client.put(f"/api/projects/{p['projectId']}", json={
            "expectedRevision": p["revision"], "name": p["name"],
            "brief": "另一个方向", "auditionText": p["auditionText"],
        }).json()
        assert client.get(f"/api/generations/{gen['generationId']}").json()["brief"] == "人物方向"


def test_candidate_edit_has_its_own_revision_and_frozen_generation(tmp_path):
    engine = FakeEngine()
    with TestClient(create_app(tmp_path, engine)) as client:
        p = project(client)
        p, c = candidate(client, p)
        response = client.put(f"/api/candidates/{c['candidateId']}", json={
            "expectedProjectRevision": p["revision"],
            "expectedCandidateRevision": c["revision"], "direction": "新的方向",
        })
        assert response.status_code == 200
        edited = response.json()
        current = edited["candidates"][0]
        assert current["candidateId"] == c["candidateId"] and current["revision"] == 2
        stale = client.put(f"/api/candidates/{c['candidateId']}", json={
            "expectedProjectRevision": edited["revision"],
            "expectedCandidateRevision": 1, "direction": "过期修改",
        })
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "candidate.revision_conflict"
        generated = generate(client, edited, current)
        assert generated["direction"] == "新的方向"
        assert engine.observed_directions == ["人物方向\n新的方向"]


def test_cleanup_debt_retries_without_repointing_old_audio(tmp_path, monkeypatch):
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        p = project(client)
        p, c = candidate(client, p)
        old = generate(client, p, c)
        store = client.app.state.store
        old_path = Path(store.generations.get(old["generationId"], private=True)["sourcePath"])
        original_unlink = Path.unlink

        def blocked_unlink(path, *args, **kwargs):
            if path == old_path:
                raise OSError("simulated cleanup failure")
            return original_unlink(path, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", blocked_unlink)
        p = client.get(f"/api/projects/{p['projectId']}").json()
        new = generate(client, p, p["candidates"][0])
        assert new["status"] == "completed" and old_path.exists()
        assert store.generations.get(old["generationId"], private=True)["sourcePath"] is None
        with store.connection() as db:
            assert db.execute("SELECT COUNT(*) FROM cleanup_debts").fetchone()[0] == 1
        monkeypatch.setattr(Path, "unlink", original_unlink)
        assert store.run_cleanup() == 1 and not old_path.exists()
        with store.connection() as db:
            assert db.execute("SELECT COUNT(*) FROM cleanup_debts").fetchone()[0] == 0


def test_migration_rejects_corrupt_legacy_audio_without_schema_switch(tmp_path):
    # A corrupt path must fail the transaction, retaining the legacy tables for repair.
    db_path = tmp_path / "voice_lab.sqlite3"
    corrupt = tmp_path / "assets" / "vc_bad" / "source.wav"
    corrupt.parent.mkdir(parents=True)
    corrupt.write_bytes(b"wrong bytes")
    db = sqlite3.connect(db_path)
    db.executescript("""
        CREATE TABLE rounds (id TEXT PRIMARY KEY,audition_text TEXT,status TEXT,error_code TEXT,created_at TEXT,updated_at TEXT);
        CREATE TABLE candidates (id TEXT PRIMARY KEY,round_id TEXT,ordinal INTEGER,direction TEXT,seed INTEGER,model_id TEXT,model_revision TEXT,status TEXT,error_code TEXT,source_path TEXT,source_sha256 TEXT,source_duration_seconds REAL,source_sample_rate INTEGER,h3_path TEXT,h3_sha256 TEXT,h3_eligible INTEGER,preparation_version TEXT,created_at TEXT,updated_at TEXT);
        CREATE TABLE selections (id TEXT PRIMARY KEY,candidate_id TEXT,selected_at TEXT);
        CREATE TABLE clone_trials (id TEXT PRIMARY KEY,candidate_id TEXT,text TEXT,seed INTEGER,model_id TEXT,model_revision TEXT,source_sha256 TEXT,status TEXT,error_code TEXT,audio_path TEXT,audio_sha256 TEXT,duration_seconds REAL,sample_rate INTEGER,created_at TEXT,updated_at TEXT);
    """)
    db.execute("INSERT INTO rounds VALUES (?,?,?,?,?,?)", ("round", "line", "completed", None, "now", "now"))
    db.execute("INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        "vc_bad", "round", 1, "direction", 1, "model", "revision", "completed", None,
        str(corrupt), "0" * 64, 2, 24000, None, None, 0, "version", "now", "now",
    ))
    db.commit(); db.close()
    with pytest.raises(ValueError, match="legacy.audio_corrupt"):
        Store(tmp_path)
    db = sqlite3.connect(db_path)
    assert db.execute("SELECT name FROM sqlite_master WHERE name='rounds'").fetchone()
    assert db.execute("SELECT name FROM sqlite_master WHERE name='projects'").fetchone() is None
    assert db.execute("PRAGMA user_version").fetchone()[0] == 0
    db.close()
