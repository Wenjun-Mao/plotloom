"""Independent stage selection, native audio and retained identity contracts."""

import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from plotloom_voice_lab.app import create_app
from plotloom_voice_lab.contracts import DeliveryControl
from plotloom_voice_lab.media import file_sha256, persist_candidate_file, persist_clone_file
from plotloom_voice_lab.migration import SCHEMA
from plotloom_voice_lab.store import Store
from test_voice_lab import FakeEngine, candidate, generate, project, wait_for


def test_paired_creation_and_all_independent_reuse_combinations(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        p = project(client)
        response = client.post(f"/api/projects/{p['projectId']}/paired-generations", json={
            "expectedProjectRevision": p["revision"], "directions": ["同一方向"], "seed": 17,
        })
        assert response.status_code == 202, response.text
        ids = response.json()["generationIds"]
        assert len(ids) == 2
        for generation_id in ids:
            assert wait_for(client, f"/api/generations/{generation_id}")["status"] == "completed"
        p = client.get(f"/api/projects/{p['projectId']}").json()
        left, right = p["candidates"]
        assert left["engineId"] == "qwen_design" and right["engineId"] == "moss_design"
        assert left["designBinding"] == right["designBinding"]
        assert left["currentGeneration"]["seed"] == right["currentGeneration"]["seed"] == 17
        for source in ids:
            client.post(f"/api/projects/{p['projectId']}/selections", json={"generationId": source})
            for engine in ("qwen_base", "index_base"):
                response = client.post("/api/clone-trials", json={
                    "projectId": p["projectId"], "generationId": source, "engineId": engine, "text": "新台词。",
                })
                assert response.status_code == 202, response.text
                trial = wait_for(client, f"/api/clone-trials/{response.json()['trialId']}")
                assert trial["status"] == "completed"
                assert trial["engineId"] == engine
                assert trial["sampleRate"] == (22050 if engine == "index_base" else 24000)
                assert trial["executionDetails"] == {"mode": "none"}
        # An invalid paired operation admits no partial slots/jobs.
        before = len(p["candidates"])
        response = client.post(f"/api/projects/{p['projectId']}/paired-generations", json={
            "expectedProjectRevision": p["revision"], "directions": ["new"], "engineIds": ["qwen_design", "index_base"],
        })
        assert response.status_code == 422
        assert len(client.get(f"/api/projects/{p['projectId']}").json()["candidates"]) == before


@pytest.mark.parametrize("control", [
    {"mode": "manual", "vector": [0] * 7}, {"mode": "manual", "vector": [1.1] + [0] * 7},
    {"mode": "manual", "vector": [-.1] + [0] * 7}, {"mode": "manual", "vector": [float('nan')] + [0] * 7},
    {"mode": "text", "description": " "}, {"mode": "text", "description": "坚定", "vector": [0] * 8},
    {"mode": "none", "description": "坚定"},
])
def test_invalid_delivery_control(control):
    with pytest.raises(ValueError):
        DeliveryControl.model_validate(control)


def test_index_actual_evidence_and_qwen_rejection(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        p = project(client); p, c = candidate(client, p); g = generate(client, p, c)
        client.post(f"/api/projects/{p['projectId']}/selections", json={"generationId": g["generationId"]})
        body = {"projectId": p["projectId"], "generationId": g["generationId"], "text": "坚定的新台词。",
                "engineId": "index_base", "delivery": {"mode": "text", "description": "坚定、果断、时间紧迫"}}
        response = client.post('/api/clone-trials', json=body)
        trial = wait_for(client, f"/api/clone-trials/{response.json()['trialId']}")
        assert trial["delivery"]["description"] == body["delivery"]["description"]
        assert trial["executionDetails"]["rawVector"] == trial["executionDetails"]["effectiveVector"]
        assert trial["executionDetails"]["classifierSeconds"] == .1
        assert client.get(f"/api/clone-trials/{trial['trialId']}/progress").json()["executionDetails"] == trial["executionDetails"]
        body["engineId"] = "qwen_base"
        assert client.post('/api/clone-trials', json=body).status_code == 422
        body["engineId"] = "moss_design"
        assert client.post('/api/clone-trials', json=body).status_code == 422


def test_engine_change_keeps_old_audio_but_rejects_stale_selection(tmp_path):
    with TestClient(create_app(tmp_path, FakeEngine())) as client:
        p = project(client); p, c = candidate(client, p); old = generate(client, p, c)
        edited = client.put(f"/api/candidates/{c['candidateId']}", json={
            "expectedProjectRevision": p["revision"], "expectedCandidateRevision": c["revision"],
            "direction": c["direction"], "engineId": "moss_design",
        }).json()
        assert not edited["candidates"][0]["currentDesignMatches"]
        assert client.get(f"/api/generations/{old['generationId']}/audio").status_code == 200
        response = client.post(f"/api/projects/{p['projectId']}/selections", json={"generationId": old["generationId"]})
        assert response.status_code == 409 and response.json()["detail"]["code"] == "generation.design_stale"
        new = generate(client, edited, edited["candidates"][0])
        assert new["engineId"] == "moss_design" and old["executionSnapshot"]["engineId"] == "qwen_design"
        assert client.get(f"/api/generations/{old['generationId']}/audio").status_code == 409


def test_native_float_not_clipped_and_derivative_gain_recorded(tmp_path):
    native = tmp_path / 'native.wav'
    sf.write(native, np.full(48000, 1.5), 24000, subtype='FLOAT')
    digest = file_sha256(native)
    media = persist_candidate_file(tmp_path, 'candidate', 'generation', native, 24000)
    assert media['sourceSha256'] == digest
    assert sf.read(media['sourcePath'])[0].max() == 1.5
    assert media['audioDetails']['warnings'] == ['audio.peak_exceeds_full_scale']
    assert media['audioDetails']['h3Preparation']['gain'] < 1
    assert sf.read(media['h3Path'])[0].max() <= .981
    with pytest.raises(ValueError):
        persist_candidate_file(tmp_path, 'other', 'other', native, 22050)


@pytest.mark.parametrize('level, warning', [(32767 / 32768, True), (-1, True), (.8, False)])
def test_native_pcm_full_scale_warning_preserves_original_bytes(tmp_path, level, warning):
    native = tmp_path / 'native.wav'
    sf.write(native, np.full(22050, level, dtype=np.float32), 22050, subtype='PCM_16')
    digest = file_sha256(native)
    media = persist_clone_file(tmp_path, 'trial', native, 22050)
    assert media['audioSha256'] == digest
    assert media['audioDetails']['warnings'] == (['audio.possible_source_clipping'] if warning else [])


def test_failed_moss_pair_keeps_qwen_result_and_failed_reuse_keeps_evidence(tmp_path):
    from plotloom_voice_lab.engines.process import EngineFailure
    class FailingEngine(FakeEngine):
        def run(self, spec, values, output_dir, phase, evidence):
            if spec['engineId'] == 'moss_design':
                raise EngineFailure('generation.process_failed')
            if spec['engineId'] == 'index_base':
                evidence({'mode': 'text', 'rawVector': [0, .85, 0, 0, 0, 0, 0, 0],
                          'effectiveVector': [0, .85, 0, 0, 0, 0, 0, 0], 'classifierSeconds': .2})
                raise EngineFailure('generation.process_failed')
            return super().run(spec, values, output_dir, phase, evidence)
    with TestClient(create_app(tmp_path, FailingEngine())) as client:
        p = project(client)
        response = client.post(f"/api/projects/{p['projectId']}/paired-generations", json={
            'expectedProjectRevision': p['revision'], 'directions': ['同一方向'],
        })
        left, right = response.json()['generationIds']
        qwen = wait_for(client, f'/api/generations/{left}')
        moss = wait_for(client, f'/api/generations/{right}')
        assert qwen['status'] == 'completed' and moss['status'] == 'failed'
        client.post(f"/api/projects/{p['projectId']}/selections", json={'generationId': left})
        clone = client.post('/api/clone-trials', json={
            'projectId': p['projectId'], 'generationId': left, 'engineId': 'index_base', 'text': '新台词。',
            'delivery': {'mode': 'text', 'description': '坚定、果断'},
        }).json()
        result = wait_for(client, f"/api/clone-trials/{clone['trialId']}")
        assert result['status'] == 'failed' and result['executionDetails']['rawVector'][1] == .85
        assert client.get(f'/api/generations/{left}/audio').status_code == 200


def test_v2_migration_preserves_model_identity_and_published_hashes(tmp_path):
    db = sqlite3.connect(tmp_path / 'voice_lab.sqlite3')
    db.executescript(SCHEMA)
    db.execute('PRAGMA user_version=2')
    # Older published identities must not be relabeled as current snapshots.
    stamp = '2026-09-27'
    db.execute('''INSERT INTO voices
        (id,source_project_id,source_candidate_id,source_generation_id,transcript,brief,direction,model_id,model_revision,seed,
         source_path,source_sha256,h3_path,h3_sha256,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        'voice_old', 'project_old', 'candidate_old', 'generation_old', 'line',
        'brief', 'direction', 'retained_model', 'retained_revision', 7,
        'source_path', 'exact_source_hash', 'h3_path', 'exact_h3_hash', stamp,
    ))
    db.commit(); db.close()
    store = Store(tmp_path)
    value = store.voices.get('voice_old')
    assert value['sourceSha256'] == 'exact_source_hash' and value['h3Sha256'] == 'exact_h3_hash'
    assert value['executionSnapshot'] == {'schemaVersion': 0, 'engineId': 'qwen_design',
                                         'modelId': 'retained_model', 'modelRevision': 'retained_revision'}
    assert Store(tmp_path).voices.get('voice_old') == value
