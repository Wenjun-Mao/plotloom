"""Bounded real subprocesses exercise supervision rather than mock GC."""

import json
import os
import sys
import threading
import time
from pathlib import Path

import pytest

from plotloom_voice_lab.engines.catalog import CATALOG, snapshot
from plotloom_voice_lab.engines.process import EngineFailure, ProcessEngine
from plotloom_voice_lab.engines.resources import admission

CHILD = Path(__file__).parent / 'fixtures/process_child.py'


def setup_engine(tmp_path, monkeypatch, mode='ok', stage='creation', timeout=5, probe=lambda _: None):
    engine_id = 'qwen_design' if stage == 'creation' else 'index_base'
    runtime = {"python": sys.executable, "modelDir": str(tmp_path), "resourceWaitSeconds": .2,
               "timeoutSeconds": timeout, "testMode": mode}
    config = {engine_id: runtime}
    path = tmp_path / 'runtime.json'; path.write_text(json.dumps(config))
    monkeypatch.setenv('VOICE_LAB_RUNTIME_CONFIG', str(path))
    engine = ProcessEngine(config=config, resource_probe=probe, command_factory=lambda _: [sys.executable, str(CHILD)])
    return engine, snapshot(engine_id, stage)


def test_process_exit_native_result_and_no_api_torch(tmp_path, monkeypatch):
    engine, spec = setup_engine(tmp_path, monkeypatch)
    phases = []
    output, metrics = engine.run(spec, {'text': 'test', 'seed': 7}, tmp_path / 'job', phases.append, lambda _: None)
    assert output.is_file() and metrics['processId'] > 0
    assert phases == ['waiting_for_resources', 'loading_model', 'synthesizing']
    assert engine.process is None
    with pytest.raises(ProcessLookupError):
        os.kill(metrics['processId'], 0)
    assert 'torch' not in sys.modules


@pytest.mark.parametrize('mode,code', [('timeout','generation.timeout'), ('partial','runner.protocol_invalid')])
def test_timeout_and_partial_final_event_are_terminal(tmp_path, monkeypatch, mode, code):
    engine, spec = setup_engine(tmp_path, monkeypatch, mode, timeout=.3)
    with pytest.raises(EngineFailure, match=code):
        engine.run(spec, {'text': 'test', 'seed': 7}, tmp_path / 'job', lambda _: None, lambda _: None)
    assert engine.process is None


def test_classifier_evidence_precedes_failure_and_remains_available(tmp_path, monkeypatch):
    engine, spec = setup_engine(tmp_path, monkeypatch, 'fail', stage='reuse')
    observed = []
    with pytest.raises(EngineFailure, match='generation.failed'):
        engine.run(spec, {'text': 'test', 'seed': 7, 'delivery': {'mode': 'manual', 'vector': [0, .25, 0, 0, 0, 0, 0, 0]}},
                   tmp_path / 'job', lambda _: None, observed.append)
    assert observed == [{'mode': 'manual', 'effectiveVector': [0, .25, 0, 0, 0, 0, 0, 0]}]


def test_frozen_contract_and_runtime_changes_fail_before_dispatch(tmp_path, monkeypatch):
    engine, spec = setup_engine(tmp_path, monkeypatch)
    monkeypatch.setitem(CATALOG['qwen_design'], 'modelRevision', 'changed')
    with pytest.raises(EngineFailure, match='engine.snapshot_unavailable'):
        engine.run(spec, {'text': 'test', 'seed': 7}, tmp_path / 'job', lambda _: None, lambda _: None)
    assert not (tmp_path / 'job').exists()


def test_resource_wait_does_not_spawn_and_stop_reaps_group(tmp_path, monkeypatch):
    engine, spec = setup_engine(tmp_path, monkeypatch, probe=lambda _: 'busy')
    with pytest.raises(EngineFailure, match='resource.headroom_unavailable'):
        engine.run(spec, {'text': 'test', 'seed': 7}, tmp_path / 'job', lambda _: None, lambda _: None)
    assert engine.process is None and not (tmp_path / 'job').exists()
    engine, spec = setup_engine(tmp_path, monkeypatch, 'descendant')
    errors = []
    def run():
        try:
            engine.run(spec, {'text': 'test', 'seed': 7}, tmp_path / 'job', lambda _: None, lambda _: None)
        except EngineFailure as error:
            errors.append(str(error))
    thread = threading.Thread(target=run); thread.start()
    for _ in range(50):
        if (tmp_path / 'job/descendant.pid').exists(): break
        time.sleep(.02)
    assert (tmp_path / 'job/descendant.pid').exists()
    engine.stop(); thread.join(timeout=5)
    assert not thread.is_alive() and engine.process is None
    assert errors and errors[0] in {'generation.process_failed', 'generation.interrupted'}


def test_missing_memory_or_unreachable_comfy_fails_closed(monkeypatch):
    monkeypatch.setattr('plotloom_voice_lab.engines.resources.available_gib', lambda: None)
    assert admission({'minAvailableGiB': 1}) == 'resource.memory_headroom'
