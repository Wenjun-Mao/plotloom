"""Bounded operator experiment, never imported by the gateway runtime."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

IMAGE = 'sha256:db0010004575a508b5ac67fb36ea4ab83cf1964a84e70932019749f330c64110'
COMMIT = '6b747c0428c343e1417219641db93a4fb7cb69ae'
FP16 = 'minimax_h3_video_vae_fp16.safetensors'
INT8 = 'minimax_h3_video_vae_int8_convrot.safetensors'
AUDIO = 'minimax_h3_audio_vae_fp32.safetensors'
INT8_REVISION = 'e5eb578a89295337b8ff433a035929ce0279e0b6'
INT8_SHA256 = '52a2c8c73583c86e4f41cdcce3a6ad0ea562987bc0bf3d60a0cef5f5c8e60c0e'
ARMS = {
    'A': {'checkpoint': FP16, 'dtype': 'bfloat16', 'fast': False},
    'B': {'checkpoint': FP16, 'dtype': 'float16', 'fast': False},
    'C': {'checkpoint': FP16, 'dtype': 'float16', 'fast': True},
    'D': {'checkpoint': INT8, 'dtype': 'float16', 'fast': True},
}
# Dynamic VRAM retains checkpoint-storage weights and casts them on demand.
# Raw Parameter.dtype is not the same fact as a GPU compute activation dtype.
# Permit only that arm's immutable storage form plus its execution precision.
PARAMETER_STORAGE = {
    'A': {'torch.float16', 'torch.bfloat16'},
    'B': {'torch.float16'},
    'C': {'torch.float16'},
    # The pinned INT8 file also stores FP32 biases, normalization/scale values
    # and quantization metadata; dynamic loading retains some as parameters.
    'D': {'torch.float16', 'torch.float32', 'torch.int8', 'torch.uint8'},
}
AUDIO_PARAMETER_STORAGE = {'torch.float32', 'torch.bfloat16'}
CASE_IDS = ('landscape', 'portrait', 'voice')


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def save(path: Path, value) -> None:
    """Atomic private evidence, including uncertainty before a sole submission."""
    staging = path.with_suffix('.tmp')
    fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    staging.replace(path)


def graph_for(case: dict, arm: str) -> dict:
    if fingerprint(case['graph']) != case['graphSha256']:
        raise ValueError('Frozen graph changed')
    graph = copy.deepcopy(case['graph'])
    if graph['105:24']['inputs'] != {'vae_name': AUDIO}:
        raise ValueError('Audio binding changed')
    if graph['105:107']['inputs']['value'] != 124:
        raise ValueError('Frame contract changed')
    graph['105:11'] = {'class_type': 'QualificationVideoVAELoader', 'inputs': {
        'vae_name': ARMS[arm]['checkpoint'], 'precision': ARMS[arm]['dtype'],
    }}
    graph['92']['inputs']['filename_prefix'] = f'{arm}_{case["id"]}'
    return graph


def claim(receipt: dict, arm: str, case_id: str) -> dict:
    """A rejected request consumes its cell too. No replacement or retry mode."""
    if arm not in ARMS or case_id not in CASE_IDS:
        raise ValueError('Unknown experiment cell')
    if receipt['status'] != 'running' or len(receipt['calls']) >= 12:
        raise ValueError('Experiment stopped or call cap exhausted')
    if any(x['arm'] == arm and x['caseId'] == case_id for x in receipt['calls']):
        raise ValueError('Cell already claimed; refuse replay')
    item = {'arm': arm, 'caseId': case_id, 'state': 'outcome_unknown'}
    receipt['calls'].append(item)
    return item


def validate_observations(events: list[dict], arm: str, *, smoke: bool) -> None:
    stages = [event for event in events if event.get('kind') == 'stage']
    expected = 'torch.' + ARMS[arm]['dtype']
    for kind, dtype in [('video', expected), ('audio', 'torch.bfloat16')]:
        relevant = [x for x in stages if x['vaeKind'] == kind]
        required = {'encode', 'decode'} if kind == 'video' or smoke else {'decode'}
        if not required <= {x['operation'] for x in relevant}:
            raise ValueError(f'{kind} stage missing; cache or observer gap')
        if any(not x['computeActivations'] or any(a['dtype'] != dtype or a['device'] != 'cuda:0'
                for a in x['computeActivations']) or not x['ok'] for x in relevant):
            raise ValueError(f'{kind} precision/device invariant failed')
        storage = PARAMETER_STORAGE[arm] if kind == 'video' else AUDIO_PARAMETER_STORAGE
        if any(not x['parameterDtypes'] or set(x['parameterDtypes']) - storage
               for x in relevant):
            raise ValueError(f'{kind} checkpoint/parameter storage invariant failed')
        outer = [x for x in events if x.get('kind') == 'outer_stage' and x['vaeKind'] == kind]
        if not required <= {x['operation'] for x in outer} or any(x['effectiveDtype'] != dtype for x in outer):
            raise ValueError(f'{kind} loader/outer precision proof missing')
    kernels = [x for x in events if x.get('kind') == 'kernel']
    if any(x['kernel'] in {'fp16_conv3d', 'fp16_linear'} and x['vaeKind'] != 'video' for x in kernels):
        raise ValueError('FP16 optimization escaped video-only scope')
    if ARMS[arm]['fast']:
        if not any(x['kernel'] == 'fp16_conv3d' and x['vaeKind'] == 'video' for x in kernels):
            raise ValueError('FP16 accumulation dispatch not demonstrated')
    elif any(x['kernel'] in {'fp16_conv3d', 'fp16_linear'} for x in kernels):
        raise ValueError('Unexpected fast dispatch in control arm')
    if arm == 'D' and not any(x['kernel'].startswith('int8_') and x['vaeKind'] == 'video' for x in kernels):
        raise ValueError('INT8 dispatch not demonstrated')
