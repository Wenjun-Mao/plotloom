"""Real process protocol fixture; no inference libraries required."""

import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path

request = json.loads(Path(sys.argv[1]).read_text())
events = Path(request['events'])
mode = request['runtime'].get('testMode', 'ok')


def emit(value):
    with events.open('a') as stream:
        stream.write(json.dumps(value) + '\n'); stream.flush(); os.fsync(stream.fileno())


emit({'kind': 'phase', 'phase': 'loading_model'})
if mode in {'timeout', 'descendant'}:
    if mode == 'descendant':
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        (events.parent / 'descendant.pid').write_text(str(child.pid))
    time.sleep(60)
if mode == 'partial':
    with events.open('a') as stream:
        stream.write('{"kind":'); stream.flush()
    raise SystemExit(0)
if request['snapshot']['stage'] == 'reuse':
    emit({'kind': 'delivery', 'evidence': {'mode': 'manual', 'effectiveVector': [0, .25, 0, 0, 0, 0, 0, 0]}})
if mode == 'fail':
    emit({'kind': 'failure', 'errorCode': 'generation.failed'})
    raise SystemExit(1)
emit({'kind': 'phase', 'phase': 'synthesizing'})
with wave.open(request['output'], 'wb') as audio:
    audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(request['snapshot']['sampleRate'])
    audio.writeframes(b'\x00\x00' * request['snapshot']['sampleRate'])
emit({'kind': 'complete', 'peakTorchGiB': 0})
