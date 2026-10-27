"""Actual source-owned Storyboard result and receiving boundaries, provider-free."""
import json
import shutil
import subprocess
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
from pathlib import Path

import pytest

from tests.storyboard_correction_fixtures import ROOT, storyboard_case, run_typed


@pytest.mark.parametrize('saved', [False, True])
def test_normal_storyboard_issues_are_typed_but_valid_render_is_unchanged(tmp_path, saved):
    request, board = storyboard_case(tmp_path, saved=saved)
    good = deepcopy(board)
    board['episodes'][0]['segments'][0]['cuts'][0]['seconds'] = 100
    result = run_typed(tmp_path, request, board)
    assert result.returncode == 42, result.stderr.decode()
    rejection = json.loads(result.stdout)
    assert rejection['candidateHash'] == sha256((tmp_path / 'storyboard.json').read_bytes()).hexdigest()
    assert rejection['issues'] == [{'code': 'candidate_content_invalid', 'fieldPaths': ['$'], 'repairFacts': {}}]
    assert rejection['displayDiagnostics'] and result.stderr == b''
    result = run_typed(tmp_path, request, good)
    assert result.returncode == 0, result.stderr.decode()
    adapter = 'brief-storyboard-style.mjs' if saved else 'storyboard-receiving.mjs'
    command = [shutil.which('node'), str(ROOT / 'scripts' / adapter), 'render',
        str(tmp_path / 'storyboard.json'), '--request', str(tmp_path / 'package/request.json')]
    first = subprocess.run(command, capture_output=True, check=True).stdout
    assert b'<html' in first.lower()
    assert run_typed(tmp_path, request, good).returncode == 0
    assert subprocess.run(command, capture_output=True, check=True).stdout == first


@pytest.mark.parametrize('mutation', ['input', 'parser', 'timing', 'mapping', 'source', 'frozen-timing',
    'style', 'prior-hash', 'prior-parser', 'receiving', 'missing-mapping', 'routes', 'budget', 'script-identity'])
def test_authority_parser_and_receiving_failures_are_not_typed(tmp_path, mutation):
    request, board = storyboard_case(tmp_path)
    if mutation == 'input': (tmp_path / 'package/inputs/cast.json').write_text('{}')
    elif mutation == 'timing': board['params']['maxSegmentSeconds'] = 16
    elif mutation == 'mapping': board['episodes'][0]['ep'] = 99
    elif mutation in {'source', 'frozen-timing', 'style', 'missing-mapping', 'routes', 'budget', 'script-identity'}:
        artifacts = deepcopy(request.input_artifacts)
        if mutation == 'source': request = request.model_copy(update={'source': {'acceptedScriptRevision': 999}})
        elif mutation == 'frozen-timing': artifacts['dialogue-timing-contract.json']['contentHash'] = '0' * 64
        elif mutation == 'style': artifacts['storyboard-style-contract.json']['contentHash'] = '0' * 64
        elif mutation == 'missing-mapping':
            artifacts['storyboard-admission.json'].pop('sectionBindings')
            board.pop('episodes')
        elif mutation == 'routes': artifacts['storyboard-admission.json'].pop('completeRouteSectionIds')
        elif mutation == 'budget': artifacts['storyboard-admission.json']['targetPlaythroughSeconds'] = None
        else: artifacts['storyboard-admission.json']['scriptRevision'] = None
        request = request.model_copy(update={'input_artifacts': artifacts})
        for name, value in artifacts.items(): (tmp_path / 'package/inputs' / name).write_text(json.dumps(value))
    elif mutation == 'receiving':
        # Source-owned upstream API accepts this, while canonical dialogue minima refuse it.
        contract = deepcopy(request.input_artifacts['dialogue-timing-contract.json'])
        assert contract['lines']
        contract['lines'][0]['minimumDurationUnits'] = 100000
        from plotloom.creative_handoff_identity import canonical_json
        contract['contentHash'] = sha256(canonical_json({k: v for k, v in contract.items() if k != 'contentHash'})).hexdigest()
        artifacts = dict(request.input_artifacts) | {'dialogue-timing-contract.json': contract}
        request = request.model_copy(update={'input_artifacts': artifacts})
        (tmp_path / 'package/inputs/dialogue-timing-contract.json').write_text(json.dumps(contract))
    result = run_typed(tmp_path, request, board)
    if mutation in {'parser', 'prior-hash', 'prior-parser'}:
        raw = request.model_dump(mode='json', by_alias=True)
        if mutation == 'parser': (tmp_path / 'storyboard.json').write_text('{')
        else:
            prior = '{' if mutation == 'prior-parser' else json.dumps(board)
            raw['textCorrection'] = {'priorCandidateJson': prior,
                'rejection': {'candidateHash': sha256(prior.encode()).hexdigest() if mutation == 'prior-parser' else '0' * 64}}
            (tmp_path / 'package/request.json').write_text(json.dumps(raw))
        result = subprocess.run([shutil.which('node'), str(ROOT / 'scripts/storyboard-content-validation.mjs'),
            str(tmp_path / 'storyboard.json'), str(tmp_path / 'package/request.json')], capture_output=True)
    assert result.returncode == 1 and result.stdout == b'', result.stdout


@pytest.mark.parametrize('version', ['plotloom.text-correction.v2', 'plotloom.text-correction.v3', 'plotloom.text-correction.v4'])
@pytest.mark.parametrize('limit', [0, 1, 2])
def test_storyboard_v4_only_caps_one_and_v3_retains_script(version, limit):
    from plotloom.text_correction_contracts import automatic_correction_limit
    policy = SimpleNamespace(text_correction_limit=limit,
        executor_binding=SimpleNamespace(text_correction_contract=version, text_correction_limit=None))
    assert automatic_correction_limit(policy, 'storyboard') == (min(limit, 1) if version.endswith('v4') else 0)
    assert automatic_correction_limit(policy, 'script') == (min(limit, 1) if version.endswith(('v3', 'v4')) else 0)


def test_storyboard_correction_accounting_preserves_eight_operations_and_no_third():
    from plotloom.alpha_receipts import NativeOperationReceipt
    from plotloom.alpha_workloads import NATIVE_OPERATIONS
    assert len(NATIVE_OPERATIONS) == 8
    assert not NativeOperationReceipt(stage='storyboard', attempt_count=2, accepted=True, first_pass=False, binding_hash='a' * 64).first_pass
    with pytest.raises(ValueError):
        NativeOperationReceipt(stage='storyboard', attempt_count=3, accepted=True, first_pass=False, binding_hash='a' * 64)


def test_prior_v3_receipt_cannot_qualify_current_prospective_v4():
    from plotloom.alpha_receipts import NativeSampleReceipt
    from tests.alpha_acceptance_support import native_receipts
    raw = native_receipts()[0]
    assert NativeSampleReceipt.model_validate(raw).version == 'alpha_native_codex_three_story.v4'
    with pytest.raises(ValueError):
        NativeSampleReceipt.model_validate(raw | {'version': 'alpha_native_codex_three_story.v3'})


@pytest.mark.parametrize('saved', [False, True])
def test_typed_storyboard_plan_and_real_read_paths_bind_the_actual_adapter(tmp_path, saved):
    from plotloom.creative_handoff_exchange import CreativeHandoffExchange
    from plotloom.codex_exec_resources import codex_exec_source_resources
    from plotloom.codex_exec_validation import validation_plan_from_package
    request, _board = storyboard_case(tmp_path, saved=saved)
    exchange = CreativeHandoffExchange(tmp_path / 'exchange')
    pin = exchange.current_execution_pin('storyboard')
    paths = exchange.write_package(request, pin, executor_backend='codex_exec', plotloom_code_revision='a' * 40)
    raw = json.loads((Path(paths['packagePath']) / 'request.json').read_bytes())
    plan = validation_plan_from_package(raw)
    assert plan.steps[0].argv == ('{source}/scripts/storyboard-content-validation.mjs', '{candidate}', '{package}/request.json')
    old = 'brief-storyboard-style.mjs' if saved else 'storyboard-receiving.mjs'
    assert plan.steps[1].argv[0] == '{source}/scripts/' + old
    assert (ROOT / 'scripts/storyboard-content-validation.mjs').resolve() in codex_exec_source_resources(ROOT, raw).read_paths
    from plotloom.alpha_provenance import preflight_plan_identity
    assert preflight_plan_identity(Path(paths['packagePath']))[2] == plan.plan_hash
    ordinary = request.model_copy(update={'job_id': 'ch_' + 's' * 32, 'content_validation_contract': None})
    manual = exchange.write_package(ordinary, pin, executor_backend='codex_exec', plotloom_code_revision='a' * 40)
    with pytest.raises(ValueError, match='typed content boundary'):
        preflight_plan_identity(Path(manual['packagePath']))
