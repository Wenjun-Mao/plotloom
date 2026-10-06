"""Freeze reviewed exact-size references and the three comparison graphs."""
from __future__ import annotations

import argparse
import json
import sys
import wave
from hashlib import sha256
from pathlib import Path

from contract import AUDIO, CASE_IDS, FP16, INT8, INT8_SHA256, digest, fingerprint, save
from PIL import Image


def freeze(root: Path, source: Path):
    if (root / 'cases.json').exists() or (root / 'receipt.json').exists():
        raise RuntimeError('Experiment already frozen; no overwrite/replay')
    memory_sha = digest(root / 'memory_trace.py')
    input_root = root / 'input'
    model_root = Path('/home/wjmao/models/comfyui-h3')
    template_path = source / 'services/minimax_h3_gateway/src/plotloom_h3_gateway/profiles/minimax_h3_template_v2.json'
    template = json.loads(template_path.read_text())['prompt']
    sys.path.insert(0, str(source / 'services/minimax_h3_gateway/tools'))
    sys.path.insert(0, str(source / 'services/minimax_h3_gateway/src'))
    from h3_prompt_robustness_study import RECIPES, render_workflow
    from plotloom_h3_gateway.profile_catalog import H3Resolution
    from plotloom_h3_gateway.voice_reference import (
        VOICE_MODEL,
        VoiceExecution,
        render_voice_workflow,
    )
    cases, assets = [], []
    prompts = {
        'landscape': ('Visual: cinematic realism. The same female astronaut sits inside a spacecraft capsule, '
            'with Earth visible through the window beside her. Preserve the helmet, face, suit and capsule. '
            'She gently turns toward the camera and exhales. Locked camera, natural small movements. '
            'No captions, subtitles, typography, or new written language.\n'
            'Audio: she says once in Mandarin: 我们回家吧。 Only the audio track contains the dialogue. '
            'Quiet spacecraft room tone. No additional speech.'),
        'portrait': ('Visual: cinematic realism. The same female astronaut stands beside a spacecraft corridor '
            'window with Earth outside. Preserve her face, dark workwear and corridor. '
            'She slowly looks toward the camera and exhales. Locked camera, natural small movements. '
            'No captions, subtitles, typography, or new written language.\n'
            'Audio: she says once in Mandarin: 我们回家吧。 Only the audio track contains the dialogue. '
            'Quiet spacecraft room tone. No additional speech.'),
        'voice': ('<Picture 1> is the exact first frame. <Audio 1> is the woman\'s voice reference. '
            'One continuous cinematic portrait shot of the same Chinese female lighthouse keeper in dark '
            'workwear in the lantern room. Preserve her face and clothing. Locked camera, natural small '
            'gestures, keep her face and mouth visible. She speaks once in Mandarin, firmly and decisively '
            'because time is running out, without fear or panic: '
            '<d>[Chinese] 等等，别打开那扇门！控制台还在报警，先把电源切断！</d> '
            'Begin speaking promptly and complete the line, then remain silent. Quiet rain and natural '
            'synchronized sound. No other voices, no repeated words, no subtitles or typography.'),
    }
    for name, width, height in [('landscape', 1280, 704), ('portrait', 704, 1280), ('voice', 576, 1024)]:
        image = input_root / f'{name}.png'
        with Image.open(image) as pixels:
            if pixels.size != (width, height):
                raise RuntimeError('Reference geometry differs; no automatic preparation')
        assets.append({'path': str(image), 'sha256': digest(image)})
        if name != 'voice':
            graph = render_workflow(template, recipe=RECIPES[1], prompt=prompts[name], seed=20261006,
                input_name=image.name, output_prefix='__FROZEN__', width=width, height=height, frame_count=124)
        else:
            audio = input_root / 'performance.wav'
            with wave.open(str(audio)) as wav:
                duration = wav.getnframes() / wav.getframerate()
                if wav.getframerate() != 32000 or wav.getnchannels() != 1 or not 1 <= duration <= 5.167:
                    raise RuntimeError('Retained performance reference does not fit')
            audio_hash = digest(audio)
            assets.append({'path': str(audio), 'sha256': audio_hash})
            execution = VoiceExecution(H3Resolution('576x1024', width, height), 5, 124, 20260923,
                sha256(prompts[name].encode()).hexdigest(), image.name, audio.name,
                digest(image), digest(image), audio_hash, audio_hash)
            graph = render_voice_workflow(template, execution=execution, prompt=prompts[name])
            graph['92']['inputs']['filename_prefix'] = '__FROZEN__'
        cases.append({'id': name, 'width': width, 'height': height, 'graph': graph,
                      'graphSha256': fingerprint(graph), 'dialogue': ('我们回家吧。' if name != 'voice'
                          else '等等，别打开那扇门！控制台还在报警，先把电源切断！')})
    for folder, filename in [('vae', FP16), ('vae', INT8), ('vae', AUDIO),
            ('diffusion_models', 'minimax_h3_fl2va_pruned_fp8_scaled.safetensors'),
            ('diffusion_models', VOICE_MODEL),
            ('text_encoders', 'qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors'),
            ('loras', RECIPES[1].lora_file)]:
        path = model_root / folder / filename
        value = digest(path)
        if filename == INT8 and value != INT8_SHA256:
            raise RuntimeError('Official INT8 hash differs')
        assets.append({'path': str(path), 'sha256': value})
    frozen = {'cases': cases, 'assets': assets, 'templateSha256': digest(template_path),
              'sourceCaseOrder': CASE_IDS, 'inputPreparation': 'retained bytes; no resize/crop/pad',
              'memoryInterpretation': '1Hz UMA host availability/RSS; never add them; HWM is cumulative'}
    save(root / 'cases.json', frozen)
    save(root / 'receipt.json', {'status': 'running', 'generationCallCap': 12, 'calls': [],
                               'smokes': {}, 'casesSha256': fingerprint(frozen),
                               'memoryObserverSha256': memory_sha})
    print(json.dumps({'status': 'frozen', 'caseCount': 3, 'caseHash': fingerprint(frozen)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    options = parser.parse_args()
    freeze(options.root, options.source)
