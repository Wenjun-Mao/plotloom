"""Actual Script API/receiving subprocesses, no model or project mutation."""
import json
import os
import shutil
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

from tests.creative_delivery_fixtures import _pilot_script

ROOT = Path(__file__).resolve().parents[1]


def script_case(tmp_path, *, planned=False):
    from plotloom.creative_handoff_contracts import CreativeHandoffRequest
    from plotloom.script_dialogue_compatibility import freeze_planned_storyboard_dialogue
    artifacts = {name: json.loads((ROOT / 'tests/fixtures/script-dialogue' / ('retained-' + name)).read_bytes())
        for name in ('outline.json', 'art.json', 'cast.json', 'admission.json')}
    admission = artifacts.pop('admission.json')
    if planned:
        admission['plannedStoryboardDialogue'] = freeze_planned_storyboard_dialogue(
            max_cut_seconds=15, language='zh-CN').model_dump(mode='json', by_alias=True)
    artifacts['script-admission.json'] = admission
    request = CreativeHandoffRequest(job_id='ch_' + 'a' * 32, project_id='script-fixture',
        section_id='pilot-script', stage='script', expected_stage_revision=0, source={'text': 'fixture'},
        input_artifacts=artifacts, creative_brief='Source-owned Script test',
        content_validation_contract='plotloom.typed-content-result.v1')
    inputs = tmp_path / 'package/inputs'
    inputs.mkdir(parents=True)
    for name, value in artifacts.items():
        (inputs / name).write_text(json.dumps(value))
    script = _pilot_script() | {'lang': 'en', 'sectionBindings': admission['sectionBindings']}
    for ep in script['episodes']:
        ep['targetSeconds'] = 5
        ep['scenes'][0]['flow'] = ep['scenes'][0]['flow'][:2]
        ep['scenes'][0]['sceneId'] = artifacts['art.json']['scenes'][0]['id']
        ep['scenes'][0]['lighting'] = artifacts['art.json']['scenes'][0]['lighting'][0]['state']
    return request, script


def run_validator(tmp_path, request, script, *, planned=False):
    package = tmp_path / 'package/request.json'
    package.write_text(json.dumps(request.model_dump(mode='json', by_alias=True)))
    candidate = tmp_path / 'script.json'
    candidate.write_text(json.dumps(script))
    command = ([sys.executable, '-B', str(ROOT / 'scripts/script_receiving.py'), 'validate', str(candidate), '--request', str(package)]
        if planned else [shutil.which('node'), str(ROOT / 'scripts/script-content-validation.mjs'), str(candidate), str(package)])
    return subprocess.run(command, capture_output=True, timeout=20,
        env=os.environ | {'PLOTLOOM_NODE': str(Path(shutil.which('node')).resolve())})


@pytest.mark.parametrize('planned', [False, True])
def test_script_normal_content_rejection_has_exact_hash_but_success_keeps_receiving(tmp_path, planned):
    request, script = script_case(tmp_path, planned=planned)
    # Fixed estimator/tolerance: 2 action beats estimate 5 seconds.
    script['episodes'][0]['targetSeconds'] = 50
    result = run_validator(tmp_path, request, script, planned=planned)
    assert result.returncode == 42, result.stderr.decode()
    rejection = json.loads(result.stdout)
    assert rejection['candidateHash'] == sha256((tmp_path / 'script.json').read_bytes()).hexdigest()
    assert rejection['issues'] == [{'code': 'candidate_content_invalid', 'fieldPaths': ['$'], 'repairFacts': {}}]
    assert rejection['displayDiagnostics'] and result.stderr == b''
    script['episodes'][0]['targetSeconds'] = 5
    result = run_validator(tmp_path, request, script, planned=planned)
    assert result.returncode == 0, result.stderr.decode()


@pytest.mark.parametrize('mutation', ['input', 'parser', 'params', 'prior-hash', 'planned-binding'])
def test_script_authority_parser_and_parameter_errors_never_return_typed_rejection(tmp_path, mutation):
    request, script = script_case(tmp_path, planned=True)
    if mutation in {'params', 'prior-hash'}:
        # Test-only raw packet probes the adapter before the host's typed lineage checks.
        raw = request.model_dump(mode='json', by_alias=True)
        prior = json.dumps(script)
        raw['textCorrection'] = {'priorCandidateJson': prior, 'rejection': {
            'candidateHash': sha256(prior.encode()).hexdigest() if mutation == 'params' else '0' * 64}}
        (tmp_path / 'package/request.json').write_text(json.dumps(raw))
        if mutation == 'params':
            script['params'] = {'tolerance': 0.99}
        (tmp_path / 'script.json').write_text(json.dumps(script))
        result = subprocess.run([shutil.which('node'), str(ROOT / 'scripts/script-content-validation.mjs'),
            str(tmp_path / 'script.json'), str(tmp_path / 'package/request.json')], capture_output=True)
    else:
        if mutation == 'input':
            (tmp_path / 'package/inputs/art.json').write_text('{}')
        if mutation == 'planned-binding':
            script['sectionBindings'][0]['sectionId'] = 'foreign'
        result = run_validator(tmp_path, request, script, planned=True)
        if mutation == 'parser':
            (tmp_path / 'script.json').write_text('{')
            result = subprocess.run([shutil.which('node'), str(ROOT / 'scripts/script-content-validation.mjs'),
                str(tmp_path / 'script.json'), str(tmp_path / 'package/request.json')], capture_output=True)
    assert result.returncode == 1 and result.stdout == b'', result.stdout


def test_script_receipt_counts_correction_as_accepted_but_never_first_pass():
    from plotloom.alpha_receipts import NativeOperationReceipt
    row = NativeOperationReceipt(stage='script', attempt_count=2, accepted=True, first_pass=False, binding_hash='a' * 64)
    assert not row.first_pass
    with pytest.raises(ValueError):
        NativeOperationReceipt(stage='script', attempt_count=3, accepted=True, first_pass=False, binding_hash='a' * 64)


@pytest.mark.parametrize('limit,expected', [(0, 0), (1, 1), (2, 1)])
def test_script_limit_honors_frozen_zero_and_never_expands_to_extra_attempts(limit, expected):
    from types import SimpleNamespace
    from plotloom.text_correction_contracts import automatic_correction_limit
    policy = SimpleNamespace(text_correction_limit=limit,
        executor_binding=SimpleNamespace(text_correction_contract='plotloom.text-correction.v3'))
    assert automatic_correction_limit(policy, 'script') == expected
    policy.executor_binding.text_correction_contract = 'plotloom.text-correction.v2'
    assert automatic_correction_limit(policy, 'script') == 0


def test_unbound_retained_launch_has_no_script_correction_authority():
    from types import SimpleNamespace
    from plotloom.text_correction_contracts import automatic_correction_limit
    assert automatic_correction_limit(SimpleNamespace(text_correction_limit=1, executor_binding=None), 'script') == 0
