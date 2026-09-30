"""Execution arguments are bound to the frozen contract, not nearby literals."""

import sys
from types import SimpleNamespace

import pytest

from plotloom_voice_lab.engines.catalog import snapshot, EMOTIONS
from plotloom_voice_lab.engines.protocol import RunnerRequest


def test_qwen_uses_frozen_generation_settings(tmp_path, monkeypatch):
    from plotloom_voice_lab.engines.qwen import generate
    calls = {}
    class Model:
        @classmethod
        def from_pretrained(cls, path, **kwargs): calls['load'] = kwargs; return cls()
        def generate_voice_design(self, **kwargs): calls['generation'] = kwargs; return [[.1] * 24000], 24000
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(bfloat16='BF16'))
    monkeypatch.setitem(sys.modules, 'qwen_tts', SimpleNamespace(Qwen3TTSModel=Model))
    spec = snapshot('qwen_design', 'creation'); spec['settings'].update(attention='reviewed_attention', language='reviewed_language', doSample=False)
    request = RunnerRequest(snapshot=spec, runtime={'modelDir': 'model'}, text='台词', direction='方向', seed=7,
                            output=str(tmp_path / 'audio.wav'), events=str(tmp_path / 'events'))
    generate(request, lambda *_args, **_kwargs: None)
    assert calls['load']['dtype'] == 'BF16' and calls['load']['attn_implementation'] == 'reviewed_attention'
    assert calls['generation']['language'] == 'reviewed_language' and calls['generation']['do_sample'] is False


def test_index_observes_native_classifier_without_changing_scores_before_failure(tmp_path, monkeypatch):
    from plotloom_voice_lab.engines.index import generate
    calls, events = {}, []
    scores = dict(zip(EMOTIONS, [0, .85, 0, .05, .05, 0, .05, 0]))
    class Index:
        def __init__(self, **kwargs):
            calls['load'] = kwargs
            self.qwen_emo = SimpleNamespace(inference=lambda description: scores)
        def infer(self, **kwargs):
            calls['synthesis'] = kwargs
            assert self.qwen_emo.inference(kwargs['emo_text']) is scores
            assert any(event[0] == 'delivery' for event in events)
            raise RuntimeError('synthesis failed after classification')
    monkeypatch.setitem(sys.modules, 'indextts.infer_v2', SimpleNamespace(IndexTTS2=Index))
    spec = snapshot('index_base', 'reuse')
    request = RunnerRequest(snapshot=spec, runtime={'modelDir': 'model', 'auxPaths': {}}, text='真实台词', reference='reference.wav', seed=7,
        delivery={'mode': 'text', 'description': '坚定、果断、时间紧迫'}, output=str(tmp_path / 'audio.wav'), events='events')
    with pytest.raises(RuntimeError, match='synthesis failed'):
        generate(request, lambda kind, **fields: events.append((kind, fields)))
    observed = next(fields['evidence'] for kind, fields in events if kind == 'delivery')
    assert observed.rawVector == observed.effectiveVector == list(scores.values())
    assert calls['synthesis']['text'] == '真实台词' and calls['synthesis']['emo_text'] == '坚定、果断、时间紧迫'
    assert calls['load']['use_qwen_emo'] is True
    assert calls['synthesis']['emo_alpha'] == spec['settings']['emoAlpha']
    assert calls['synthesis']['use_random'] == spec['settings']['useRandom']


def test_moss_custom_processor_uses_qualified_kwargs_and_frozen_decoding(tmp_path, monkeypatch):
    from contextlib import nullcontext
    import numpy as np
    import soundfile as sf
    from plotloom_voice_lab.engines.moss import generate
    calls = {}
    class Tensor:
        def to(self, *_args): return self
        def detach(self): return self
        def float(self): return self
        def cpu(self): return self
        def numpy(self): return np.zeros(24000, dtype=np.float32)
    class Processor:
        audio_tokenizer = Tensor()
        model_config = SimpleNamespace(sampling_rate=24000)
        @classmethod
        def from_pretrained(cls, path, *, codec_path, trust_remote_code, normalize_inputs):
            calls['processor'] = (path, codec_path, trust_remote_code, normalize_inputs)
            return cls()
        def build_user_message(self, **kwargs): return kwargs
        def __call__(self, *_args, **_kwargs): return {'input_ids': Tensor(), 'attention_mask': Tensor()}
        def decode(self, _result): return [SimpleNamespace(audio_codes_list=[Tensor()])]
    class Model:
        @classmethod
        def from_pretrained(cls, path, **kwargs): calls['model'] = kwargs; return cls()
        def to(self, *_args): return self
        def eval(self): pass
        def generate(self, **kwargs): calls['generation'] = kwargs; return 'native outputs'
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(bfloat16='BF16', inference_mode=nullcontext,
        backends=SimpleNamespace(cuda=SimpleNamespace(enable_cudnn_sdp=lambda _value: None))))
    monkeypatch.setitem(sys.modules, 'transformers', SimpleNamespace(AutoProcessor=Processor, AutoModel=Model))
    spec = snapshot('moss_design', 'creation'); spec['settings']['audio_top_k'] = 23
    request = RunnerRequest(snapshot=spec, runtime={'modelDir': 'model', 'codecDir': 'codec'},
        text='台词', direction='方向', seed=7, output=str(tmp_path / 'audio.wav'), events='events')
    generate(request, lambda *_args, **_kwargs: None)
    assert calls['processor'] == ('model', 'codec', True, True)
    assert calls['model']['local_files_only'] is True and calls['generation']['audio_top_k'] == 23
    assert sf.info(request.output).subtype == 'FLOAT'


def test_runner_distinguishes_torch_oom_without_guessing_other_failures(monkeypatch):
    from plotloom_voice_lab.engines.runner import failure_code
    class Oom(RuntimeError): pass
    class Accelerator(RuntimeError): pass
    monkeypatch.setitem(sys.modules, 'torch', SimpleNamespace(OutOfMemoryError=Oom, AcceleratorError=Accelerator))
    assert failure_code(Oom('allocation failed')) == 'generation.oom'
    assert failure_code(Accelerator('CUDA error: out of memory')) == 'generation.oom'
    assert failure_code(Accelerator('illegal memory access')) == 'generation.failed'
    assert failure_code(RuntimeError('user text mentions out of memory')) == 'generation.failed'
    assert failure_code(FileNotFoundError('model')) == 'model.unavailable'
