#!/usr/bin/env python3
"""Optional offline faster-whisper recognition using an explicit local runtime/model."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from common import number, probe, sha


def recognize(video, interpreter, model, output):
    video = Path(video).resolve(); interpreter = Path(os.path.abspath(interpreter))
    model = Path(model).resolve(); output = Path(output).resolve()
    if not video.is_file() or not interpreter.is_file() or not os.access(interpreter, os.X_OK):
        raise ValueError('existing video and executable Python interpreter required')
    if not model.is_dir() or not all((model / name).is_file() for name in ('config.json', 'model.bin', 'tokenizer.json')):
        raise ValueError('local faster-whisper model directory is incomplete')
    if output.exists() or output == video or output.is_relative_to(model):
        raise ValueError('output must be a new file outside source and model')
    meta = probe(video); video_hash = sha(video)
    env = os.environ.copy()
    env.update({'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_DATASETS_OFFLINE': '1'})
    # The subprocess executes only this trusted file; no user text enters code or shell.
    result = subprocess.run([str(interpreter), str(Path(__file__).resolve()), '_worker', str(video), str(model)],
                            capture_output=True, check=False, env=env)
    if result.returncode:
        raise ValueError('local ASR failed: ' + result.stderr.decode(errors='replace')[-1200:])
    segments = json.loads(result.stdout)
    for segment in segments:
        a, b = number(segment.get('start'), 'ASR start'), number(segment.get('end'), 'ASR end')
        if a < 0 or b < a or b > meta['durationSeconds'] + 0.05 or not isinstance(segment.get('text'), str):
            raise ValueError('local ASR returned an invalid segment')
    if sha(video) != video_hash:
        raise ValueError('source changed during recognition')
    payload = {'sourceSha256': video_hash, 'method': 'local faster-whisper; automatic language; no source hints',
               'modelPath': str(model), 'settings': {'device': 'cpu', 'computeType': 'int8', 'cpuThreads': 4,
                   'audio': 'ffmpeg 16 kHz mono float32 PCM', 'language': 'automatic',
                   'beamSize': 5, 'temperature': 0, 'vadFilter': False, 'wordTimestamps': True,
                   'initialPrompt': None, 'hotwords': None}, 'segments': segments,
               'limits': ['Recognition is fallible and is not a perceptual listening judgment.']}
    # Exclusive creation protects retained artifacts; no output until recognition succeeds.
    with output.open('x', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2); f.write('\n')
    return output


def worker(video, model):
    from faster_whisper import WhisperModel
    import numpy as np
    # Decode locally with ffmpeg to avoid incompatible PyAV input APIs.
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True, check=True)
    audio = np.frombuffer(decoded.stdout, dtype='<f4')
    if not len(audio): raise ValueError('source has no decodable audio')
    engine = WhisperModel(model, device='cpu', compute_type='int8', local_files_only=True, cpu_threads=4)
    segments, _ = engine.transcribe(audio, beam_size=5, temperature=0, vad_filter=False,
                                    word_timestamps=True, initial_prompt=None, hotwords=None)
    print(json.dumps([{'start': s.start, 'end': s.end, 'text': s.text} for s in segments], ensure_ascii=False))


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '_worker':
        worker(sys.argv[2], sys.argv[3]); return
    p = argparse.ArgumentParser()
    p.add_argument('video'); p.add_argument('--python', required=True); p.add_argument('--model', required=True); p.add_argument('--output', required=True)
    a = p.parse_args()
    try:
        print(json.dumps({'asr': str(recognize(a.video, a.python, a.model, a.output))}))
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as e:
        p.exit(2, f'error: {e}\n')

if __name__ == '__main__': main()
