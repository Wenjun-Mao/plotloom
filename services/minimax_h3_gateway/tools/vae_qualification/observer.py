"""Same-process observers; no new GPU context and no replaced math kernels."""
from __future__ import annotations

import contextvars
import functools
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

SCOPE = contextvars.ContextVar('vae_qualification_scope', default='outside_vae')
COUNTS = contextvars.ContextVar('vae_qualification_counts', default=None)
INSTALLED = False
OUTSIDE_SEEN = set()


def emit(value):
    path = Path(os.environ['H3_QUALIFICATION_EVENTS'])
    value['monotonicSeconds'] = time.monotonic()
    value['arm'] = os.environ['H3_QUALIFICATION_ARM']
    with path.open('a') as stream:
        stream.write(json.dumps(value) + '\n')
        stream.flush()


def observe_kernel(original, name):
    @functools.wraps(original)
    def run(*args, **kwargs):
        # Successful return proves a dispatch, not just an available symbol.
        result = original(*args, **kwargs)
        counts = COUNTS.get()
        if counts is not None:
            counts[name] += 1
        elif name not in OUTSIDE_SEEN:
            emit({'kind': 'kernel', 'kernel': name, 'vaeKind': 'outside_vae', 'count': 1})
            OUTSIDE_SEEN.add(name)
        return result
    return run


def observe_stage(original, vae_kind, operation, torch):
    @functools.wraps(original)
    def run(self, tensor, *args, **kwargs):
        token = SCOPE.set(vae_kind)
        counts = Counter()
        counter_token = COUNTS.set(counts)
        activations = Counter()
        def compute_input(_module, inputs):
            x = inputs[0]
            activations[(str(x.dtype), str(x.device))] += 1
        hook = getattr(self, 'encoder' if operation == 'encode' else 'decoder').register_forward_pre_hook(compute_input)
        torch.cuda.synchronize()
        started = time.monotonic()
        start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        start.record()
        ok = False
        try:
            result = original(self, tensor, *args, **kwargs)
            ok = True
            return result
        finally:
            prior_error = sys.exc_info()[1]
            try:
                end.record()
                torch.cuda.synchronize()
                for name, count in counts.items():
                    emit({'kind': 'kernel', 'kernel': name, 'vaeKind': vae_kind, 'count': count})
                emit({'kind': 'stage', 'vaeKind': vae_kind, 'operation': operation,
                      'stagingDtype': str(tensor.dtype), 'stagingDevice': str(tensor.device),
                      'computeActivations': [{'dtype': dtype, 'device': device, 'count': count}
                          for (dtype, device), count in activations.items()],
                      'shape': list(tensor.shape), 'parameterDtypes': dict(Counter(
                          str(p.dtype) for p in self.parameters())), 'ok': ok,
                      'cudaElapsedMs': start.elapsed_time(end),
                      'synchronizedWallMs': (time.monotonic() - started) * 1000,
                      'torchAllocatedBytes': torch.cuda.memory_allocated(),
                      'torchReservedBytes': torch.cuda.memory_reserved()})
            except Exception as error:
                emit({'kind': 'observer_error', 'errorType': type(error).__name__, 'vaeKind': vae_kind})
                if prior_error is None:
                    raise
            finally:
                hook.remove()
                SCOPE.reset(token)
                COUNTS.reset(counter_token)
    return run


def observe_outer(original, operation, torch):
    @functools.wraps(original)
    def run(self, *args, **kwargs):
        name = self.first_stage_model.__class__.__name__
        if name not in {'MiniMaxH3VideoVAE', 'MiniMaxH3AudioVAE'}:
            return original(self, *args, **kwargs)
        kind = 'video' if name == 'MiniMaxH3VideoVAE' else 'audio'
        token = SCOPE.set(kind + '_wrapper')
        torch.cuda.synchronize()
        started = time.monotonic()
        try:
            result = original(self, *args, **kwargs)
            torch.cuda.synchronize()
            emit({'kind': 'outer_stage', 'vaeKind': kind, 'operation': operation,
                  'effectiveDtype': str(self.vae_dtype),
                  'synchronizedWallMs': (time.monotonic() - started) * 1000})
            return result
        finally:
            SCOPE.reset(token)
    return run


def observe_load(original, torch):
    @functools.wraps(original)
    def run(*args, **kwargs):
        kind = SCOPE.get()
        if not kind.endswith('_wrapper'):
            return original(*args, **kwargs)
        torch.cuda.synchronize()
        started = time.monotonic()
        result = original(*args, **kwargs)
        torch.cuda.synchronize()
        emit({'kind': 'model_management', 'vaeKind': kind.removesuffix('_wrapper'),
              'operation': 'load_models_gpu', 'wallMs': (time.monotonic() - started) * 1000})
        return result
    return run


def install():
    global INSTALLED
    if INSTALLED:
        return
    import comfy.model_management
    import comfy.sd
    import comfy_kitchen as ck
    import torch
    from comfy.ldm.minimax.audio_vae import MiniMaxH3AudioVAE
    from comfy.ldm.minimax.vae import MiniMaxH3VideoVAE
    for name in ('fp16_conv3d', 'fp16_linear', 'int8_linear', 'int8_attention',
                 'group_norm_silu_pad3d', 'rms_rope_split_half', 'rms_rope_split_half_'):
        if hasattr(ck, name):
            setattr(ck, name, observe_kernel(getattr(ck, name), name))
    for cls, kind in [(MiniMaxH3VideoVAE, 'video'), (MiniMaxH3AudioVAE, 'audio')]:
        for operation in ('encode', 'decode'):
            setattr(cls, operation, observe_stage(getattr(cls, operation), kind, operation, torch))
    for operation in ('encode', 'decode'):
        setattr(comfy.sd.VAE, operation, observe_outer(getattr(comfy.sd.VAE, operation), operation, torch))
    comfy.model_management.load_models_gpu = observe_load(comfy.model_management.load_models_gpu, torch)
    emit({'kind': 'observer', 'torchVersion': torch.__version__,
          'fp16Accumulation': torch.backends.cuda.matmul.allow_fp16_accumulation})
    INSTALLED = True
