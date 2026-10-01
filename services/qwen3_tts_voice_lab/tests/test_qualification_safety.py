"""Qualification observers refuse duplicate or unproven dispatches locally."""

import importlib
import json
import os
import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[1] / 'tools'


@pytest.mark.parametrize('module,args', [
    ('verify_published_h3', ['--workflow-receipt', 'unused']),
    ('verify_resident_reuse', ['--reference-trial-id', 'unused', '--resident-state', 'cold_comfy']),
    ('verify_idle_restart', ['--project-id', 'unused', '--original-trial-id', 'unused']),
    ('qualify_workflow', []),
    ('qualify_published_takes', []),
    ('observe_published_takes', ['--source-receipt', 'unused']),
])
def test_existing_receipt_never_replays(tmp_path, monkeypatch, module, args):
    monkeypatch.syspath_prepend(str(TOOLS))
    observer = importlib.import_module(module)
    receipt = tmp_path / 'started.json'
    receipt.write_text('{}')
    monkeypatch.setattr(sys, 'argv', [module, '--receipt', str(receipt), *args])
    if hasattr(observer, 'api'):
        monkeypatch.setattr(observer, 'api', lambda *a, **k: pytest.fail('unexpected request'))
    else:
        monkeypatch.setattr(observer.subprocess, 'check_output', lambda *a, **k: pytest.fail('unexpected runtime inspection'))
    with pytest.raises(ValueError, match='receipt_exists_no_(replay|repeat)'):
        observer.main()


@pytest.mark.parametrize('record', [
    {'generationCalls': 0, 'accepted': {'id': 'h3_test'}},
    {'generationCalls': 1},
])
def test_resume_requires_one_known_accepted_job(tmp_path, monkeypatch, record):
    monkeypatch.syspath_prepend(str(TOOLS))
    observer = importlib.import_module('verify_published_h3')
    receipt = tmp_path / 'started.json'
    receipt.write_text(json.dumps(record))
    monkeypatch.setattr(sys, 'argv', ['observer', '--receipt', str(receipt),
                                    '--workflow-receipt', 'unused', '--resume-observation'])
    monkeypatch.setattr(observer, 'api', lambda *a, **k: pytest.fail('unexpected request'))
    with pytest.raises(AssertionError, match='no_accepted_job'):
        observer.main()


def test_only_one_concurrent_invocation_claims_receipt(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    receipts = importlib.import_module('qualification_receipts')
    path = tmp_path / 'new-operation.json'

    def attempt(_):
        try:
            receipts.claim_receipt(path)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        admitted = list(pool.map(attempt, range(16)))
    assert sum(admitted) == 1
    assert json.loads(path.read_text())['generationCalls'] == 0
    assert path.stat().st_mode & 0o777 == 0o600


def test_claim_syncs_file_and_parent(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    receipts = importlib.import_module('qualification_receipts')
    original_sync = os.fsync
    directory_flags = []

    def observed_sync(descriptor):
        directory_flags.append(stat.S_ISDIR(os.fstat(descriptor).st_mode))
        original_sync(descriptor)

    monkeypatch.setattr(receipts.os, 'fsync', observed_sync)
    receipts.claim_receipt(tmp_path / 'new-operation.json')
    assert directory_flags == [False, True]


def test_video_observer_recognizes_all_nonterminal_gateway_states(monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    observer = importlib.import_module('qualify_published_takes')
    assert observer.ACTIVE_VIDEO_STATES == {'queued', 'submitting', 'submitted', 'running', 'transfer_pending'}
    assert not observer.ACTIVE_VIDEO_STATES.intersection({'succeeded', 'failed', 'cancelled', 'outcome_unknown'})
