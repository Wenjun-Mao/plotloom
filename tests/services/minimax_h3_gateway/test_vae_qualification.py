"""Offline experiment controls; never load Torch or submit a provider request."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).parents[3] / 'services/minimax_h3_gateway/tools/vae_qualification'


def load(name):
    sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location(name, TOOLS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


C = load('contract')
R = load('run_arm')
M = load('maintenance')
V = load('review')


def case():
    graph = {'105:24': {'inputs': {'vae_name': C.AUDIO}},
             '105:107': {'inputs': {'value': 124}},
             '105:11': {'inputs': {'vae_name': C.FP16}},
             '92': {'inputs': {'filename_prefix': 'frozen'}},
             'sampler': {'seed': 15}}
    return {'id': 'landscape', 'graph': graph, 'graphSha256': C.fingerprint(graph)}


@pytest.mark.parametrize('arm', C.ARMS)
def test_only_video_loader_and_output_change(arm):
    frozen = case()
    changed = C.graph_for(frozen, arm)
    assert changed['105:11']['inputs'] == {'vae_name': C.ARMS[arm]['checkpoint'],
                                         'precision': C.ARMS[arm]['dtype']}
    for key in ('105:24', '105:107', 'sampler'):
        assert changed[key] == frozen['graph'][key]
    assert frozen['graph']['105:11']['inputs']['vae_name'] == C.FP16


@pytest.mark.parametrize('mutate', ['hash', 'audio', 'frames'])
def test_frozen_control_tamper_refused(mutate):
    frozen = case()
    if mutate == 'hash':
        frozen['graph']['sampler']['seed'] = 16
    else:
        frozen['graph']['105:24' if mutate == 'audio' else '105:107']['inputs'] = (
            {'vae_name': 'other'} if mutate == 'audio' else {'value': 192})
        frozen['graphSha256'] = C.fingerprint(frozen['graph'])
    with pytest.raises(ValueError):
        C.graph_for(frozen, 'A')


def test_twelve_cells_claimed_once_including_failed_attempts():
    receipt = {'status': 'running', 'calls': []}
    C.claim(receipt, 'A', 'landscape')['state'] = 'request_rejected'
    with pytest.raises(ValueError, match='replay'):
        C.claim(receipt, 'A', 'landscape')
    for arm in C.ARMS:
        for name in C.CASE_IDS:
            if (arm, name) != ('A', 'landscape'):
                C.claim(receipt, arm, name)
    assert len(receipt['calls']) == 12
    with pytest.raises(ValueError, match='cap'):
        C.claim(receipt, 'D', 'voice')


@pytest.mark.parametrize('status', ['stopped', 'completed'])
def test_terminal_receipt_never_dispatches(status):
    with pytest.raises(ValueError, match='stopped'):
        C.claim({'status': status, 'calls': []}, 'A', 'landscape')


def events(arm):
    result = []
    for kind in ('video', 'audio'):
        dtype = 'torch.' + (C.ARMS[arm]['dtype'] if kind == 'video' else 'bfloat16')
        for operation in ('encode', 'decode'):
            result.append({'kind': 'stage', 'vaeKind': kind, 'operation': operation,
                'stagingDevice': 'cpu', 'computeActivations': [{'dtype': dtype, 'device': 'cuda:0', 'count': 1}],
                'parameterDtypes': {dtype: 100}, 'ok': True})
            result.append({'kind': 'outer_stage', 'vaeKind': kind, 'operation': operation,
                           'effectiveDtype': dtype})
    return result


def test_symbol_availability_does_not_prove_fast_or_int8_dispatch():
    with pytest.raises(ValueError, match='dispatch'):
        C.validate_observations(events('C'), 'C', smoke=True)
    values = events('D') + [{'kind': 'kernel', 'vaeKind': 'video', 'kernel': 'fp16_conv3d'}]
    with pytest.raises(ValueError, match='INT8'):
        C.validate_observations(values, 'D', smoke=True)
    values.append({'kind': 'kernel', 'vaeKind': 'video', 'kernel': 'int8_linear'})
    C.validate_observations(values, 'D', smoke=True)


def test_audio_precision_and_missing_decode_refused():
    values = events('A')
    values[-2]['computeActivations'][0]['dtype'] = 'torch.float32'
    with pytest.raises(ValueError, match='precision'):
        C.validate_observations(values, 'A', smoke=True)
    with pytest.raises(ValueError, match='missing'):
        C.validate_observations(events('A')[:1], 'A', smoke=False)


def test_atomic_private_uncertainty(tmp_path):
    path = tmp_path / 'receipt.json'
    C.save(path, {'state': 'outcome_unknown'})
    assert json.loads(path.read_text())['state'] == 'outcome_unknown'
    assert path.stat().st_mode & 0o777 == 0o600
    assert not path.with_suffix('.tmp').exists()


def test_unknown_post_is_written_before_request_and_never_replayed():
    item = {}
    saved = []
    class Session:
        calls = 0
        def get(self, *_args, **_kwargs):
            class Reply:
                def raise_for_status(self):
                    pass
                def json(self):
                    return {'queue_running': [], 'queue_pending': []}
            return Reply()
        def post(self, *_args, **_kwargs):
            self.calls += 1
            assert saved == ['outcome_unknown']
            raise TimeoutError('unknown dispatch')
    session = Session()
    with pytest.raises(TimeoutError):
        R.submit_once(session, 'http://loopback', {}, item, lambda: saved.append(item['state']))
    assert session.calls == 1
    assert item['state'] == 'outcome_unknown'


def test_existing_arm_receipt_refused_before_http(tmp_path):
    C.save(tmp_path / 'receipt.json', {'status': 'running', 'smokes': {'A': {}}, 'calls': []})
    with pytest.raises(RuntimeError, match='replay'):
        R.run(tmp_path, 'A', 'http://invalid')


def test_stopped_receipt_refuses_new_arm_before_smoke(tmp_path):
    C.save(tmp_path / 'receipt.json', {'status': 'stopped', 'smokes': {}, 'calls': []})
    with pytest.raises(RuntimeError, match='every new GPU request'):
        R.run(tmp_path, 'B', 'http://invalid')


def test_concurrent_operator_cannot_enter_receipt(tmp_path):
    import fcntl
    with (tmp_path / 'execution.lock').open('a') as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BlockingIOError):
            R.run(tmp_path, 'A', 'http://invalid')


def test_cpu_staging_allowed_only_with_gpu_compute_and_parameter_proof():
    C.validate_observations(events('A'), 'A', smoke=True)
    values = events('A')
    values[0]['computeActivations'][0]['device'] = 'cpu'
    with pytest.raises(ValueError, match='precision/device'):
        C.validate_observations(values, 'A', smoke=True)
    values = events('A')
    values[0]['parameterDtypes'] = {'torch.float32': 100}
    with pytest.raises(ValueError, match='parameter storage'):
        C.validate_observations(values, 'A', smoke=True)


def test_dynamic_storage_is_distinct_from_compute_precision():
    values = events('A')
    for entry in values:
        if entry['kind'] == 'stage':
            entry['parameterDtypes'] = ({'torch.float16': 486, 'torch.bfloat16': 73}
                if entry['vaeKind'] == 'video' else {'torch.float32': 368, 'torch.bfloat16': 292})
    C.validate_observations(values, 'A', smoke=True)
    values[0]['computeActivations'][0]['dtype'] = 'torch.float16'
    with pytest.raises(ValueError, match='precision/device'):
        C.validate_observations(values, 'A', smoke=True)


def test_official_int8_float32_storage_does_not_allow_float32_compute():
    values = events('D') + [
        {'kind': 'kernel', 'vaeKind': 'video', 'kernel': 'fp16_conv3d'},
        {'kind': 'kernel', 'vaeKind': 'video', 'kernel': 'int8_linear'},
    ]
    for entry in values:
        if entry['kind'] == 'stage' and entry['vaeKind'] == 'video':
            entry['parameterDtypes'] = {'torch.float16': 252, 'torch.float32': 307}
    C.validate_observations(values, 'D', smoke=True)
    values[0]['computeActivations'][0]['dtype'] = 'torch.float32'
    with pytest.raises(ValueError, match='precision/device'):
        C.validate_observations(values, 'D', smoke=True)


def test_restoration_ignores_mount_order_not_binding_changes():
    original = {'image': 'fixed', 'mounts': [
        {'Destination': '/user', 'Source': '/production-user', 'RW': True},
        {'Destination': '/models', 'Source': '/models', 'RW': False}]}
    reordered = {'image': 'fixed', 'mounts': list(reversed(original['mounts']))}
    assert M.canonical_configuration(original) == M.canonical_configuration(reordered)
    reordered['mounts'][0] = {**reordered['mounts'][0], 'RW': True}
    assert M.canonical_configuration(original) != M.canonical_configuration(reordered)


def test_review_preserves_timing_scopes_and_memory_views():
    observations = [
        {'kind': 'stage', 'vaeKind': 'video', 'operation': 'decode', 'cudaElapsedMs': 11},
        {'kind': 'outer_stage', 'vaeKind': 'video', 'operation': 'decode', 'synchronizedWallMs': 17},
        {'kind': 'model_management', 'vaeKind': 'video', 'wallMs': 3},
        {'kind': 'kernel', 'vaeKind': 'video', 'kernel': 'int8_linear', 'count': 7},
        {'kind': 'kernel', 'vaeKind': 'video', 'kernel': 'int8_linear', 'count': 2},
    ]
    memory = {'minAvailableKiB': 123, 'peakRssKiBByLabel': {'comfy': 987}}
    item = {'arm': 'D', 'caseId': 'voice', 'state': 'passed', 'elapsedMs': 45,
            'observations': observations, 'hostMemory': memory, 'outputSha256': 'output',
            'graphSha256': 'graph', 'fullDecode': 'passed', 'media': {}}
    value = V.summarize(item)
    assert value['timing']['video_decode'] == {'calls': 1, 'innerCudaMs': 11, 'outerWallMs': 17}
    assert value['timing']['video_modelManagementMs'] == 3
    assert value['kernels'] == {'video:int8_linear': 9}
    assert value['hostMemory'] == memory
    assert 'observations' not in value and 'outputPath' not in value


def test_review_refuses_incomplete_comparison_before_media_processing(tmp_path):
    frozen = {'cases': []}
    C.save(tmp_path / 'cases.json', frozen)
    C.save(tmp_path / 'receipt.json', {'casesSha256': C.fingerprint(frozen), 'calls': []})
    with pytest.raises(ValueError, match='twelve ordered'):
        V.build(tmp_path)


def test_review_refuses_changed_copied_input_before_media_processing(tmp_path):
    (tmp_path / 'input').mkdir()
    (tmp_path / 'input/landscape.png').write_bytes(b'changed')
    frozen = {'cases': [], 'assets': [{'path': '/spark/input/landscape.png', 'sha256': 'original'}]}
    C.save(tmp_path / 'cases.json', frozen)
    C.save(tmp_path / 'receipt.json', {'casesSha256': C.fingerprint(frozen),
        'calls': [{'arm': arm, 'caseId': name} for arm in C.ARMS for name in C.CASE_IDS],
        'smokes': {arm: {'state': 'passed'} for arm in C.ARMS}})
    with pytest.raises(ValueError, match='Copied frozen input'):
        V.build(tmp_path)
