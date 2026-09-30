"""Offline guardrails for the pinned, no-replay runtime experiment."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def study():
    tools = Path(__file__).parents[3] / 'services/minimax_h3_gateway/tools'
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    spec = importlib.util.spec_from_file_location('h3_runtime_qualification', tools / 'h3_runtime_qualification.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_comparison_hash_ignores_only_output_destination(study):
    graph = {'92': {'inputs': {'filename_prefix': 'baseline'}}, 'model': {'seed': 123}}
    baseline = study.graph_hash(graph)
    graph['92']['inputs']['filename_prefix'] = 'candidate'
    assert study.graph_hash(graph) == baseline
    graph['model']['seed'] = 124
    assert study.graph_hash(graph) != baseline


@pytest.mark.parametrize('phase', ['baseline', 'candidate'])
def test_existing_receipt_cannot_trigger_replay(study, tmp_path, monkeypatch, phase):
    monkeypatch.setattr(study, 'WORK', tmp_path)
    (tmp_path / f'{phase}-receipt.json').write_text('{}')
    with pytest.raises(RuntimeError, match='cannot be replayed'):
        study.run(phase)


def test_memory_observer_targets_comfy_not_container_init(study, monkeypatch):
    monkeypatch.setattr(study.subprocess, 'check_output', lambda *args, **kwargs:
                        'PID COMMAND\n7 /sbin/docker-init\n9 python main.py --port 8188\n')
    assert study.comfy_pid() == 9
    monkeypatch.setattr(study.subprocess, 'check_output', lambda *args, **kwargs:
                        'PID COMMAND\n7 /sbin/docker-init\n')
    with pytest.raises(RuntimeError, match='one ComfyUI process'):
        study.comfy_pid()


def test_receipt_is_atomic_and_contains_only_supplied_evidence(study, tmp_path):
    path = tmp_path / 'receipt.json'
    study.save(path, {'status': 'outcome_unknown', 'generationCalls': 1})
    assert json.loads(path.read_text()) == {'status': 'outcome_unknown', 'generationCalls': 1}
    assert not path.with_suffix('.tmp').exists()


def test_candidate_refuses_production_user_mount(study, monkeypatch):
    details = [{'Mounts': [{'Destination': '/opt/ComfyUI/user', 'Source': str(study.ROOT / 'data/user'), 'RW': True}]}]
    monkeypatch.setattr(study.subprocess, 'check_output', lambda *args, **kwargs: json.dumps(details))
    with pytest.raises(RuntimeError, match='metadata must remain isolated'):
        study.runtime_mounts('candidate')


def test_candidate_records_exact_isolated_mounts(study, monkeypatch):
    details = [{'Mounts': [
        {'Destination': '/opt/ComfyUI/user', 'Source': str(study.WORK / 'candidate-user'), 'RW': True},
        {'Destination': '/opt/ComfyUI/models', 'Source': '/home/wjmao/models/comfyui-h3', 'RW': True},
    ]}]
    monkeypatch.setattr(study.subprocess, 'check_output', lambda *args, **kwargs: json.dumps(details))
    assert study.runtime_mounts('candidate')[0]['source'] == str(study.WORK / 'candidate-user')


def test_explicit_candidate_mount_cannot_point_at_production(study):
    with pytest.raises(RuntimeError, match='cannot be the production'):
        study.runtime_mounts('candidate', candidate_user=study.ROOT / 'data/user')


@pytest.mark.parametrize('call_cap', [0, 4])
def test_invalid_call_cap_stops_before_a_generation_session(study, monkeypatch, tmp_path, call_cap):
    monkeypatch.setattr(study, 'WORK', tmp_path)
    monkeypatch.setattr(study, 'runtime_mounts', lambda *args, **kwargs: [])
    monkeypatch.setattr(study.subprocess, 'check_output', lambda *args, **kwargs: study.BASE_COMMIT)
    monkeypatch.setattr(study, 'comfy_pid', lambda: 9)
    monkeypatch.setattr(study, 'digest', lambda path: 'template-hash')
    monkeypatch.setattr(study.requests, 'Session', lambda: pytest.fail('No generation session allowed'))
    (tmp_path / 'cases.json').write_text(json.dumps({'templateSha256': 'template-hash', 'cases': [{}]}))
    with pytest.raises(RuntimeError, match='Invalid bounded generation call cap'):
        study.run('baseline', call_cap=call_cap)


@pytest.mark.parametrize('valid_base', [False, True])
def test_build_wrapper_refuses_wrong_base_and_builds_from_immutable_id(tmp_path, valid_base):
    wrapper = Path(__file__).parents[3] / 'services/minimax_h3_gateway/tools/comfy038-build.sh'
    expected = 'sha256:d45ca7983d4eda39cdd4df3bd03921b28754b2c15ce17f906032ef4dafd1cabc'
    calls = tmp_path / 'calls.txt'
    fake_docker = tmp_path / 'docker'
    fake_docker.write_text(
        '#!/bin/sh\n'
        'if [ "$1" = image ]; then printf "%s\\n" "$FAKE_IMAGE_ID"; exit 0; fi\n'
        'printf "%s\\n" "$@" > "$BUILD_CALLS"\n'
    )
    fake_docker.chmod(0o755)
    result = subprocess.run(['bash', str(wrapper)], check=False, capture_output=True, text=True, env={
        **os.environ, 'PATH': f'{tmp_path}:{os.environ["PATH"]}',
        'FAKE_IMAGE_ID': expected if valid_base else 'sha256:unexpected', 'BUILD_CALLS': str(calls),
    })
    if valid_base:
        assert result.returncode == 0
        assert f'BASE_IMAGE={expected}' in calls.read_text().splitlines()
        assert 'BASE_IMAGE=spark-comfyui:keep-h3-v035-20260930' not in calls.read_text()
    else:
        assert result.returncode != 0
        assert 'baseline image identity differs' in result.stderr
        assert not calls.exists()
