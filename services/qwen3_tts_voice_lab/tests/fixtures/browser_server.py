"""Real FastAPI/file-SQLite UI fixture, using the tested non-GPU engine."""

import os
import sys
from pathlib import Path

import uvicorn
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent.parent))
from fixtures.producer import FakeEngine, create_app


class BrowserEngine(FakeEngine):
    def run(self, snapshot, values, output_dir, phase, evidence):
        path, metrics = super().run(snapshot, values, output_dir, phase, evidence)
        if snapshot['stage'] == 'reuse':
            # Finite over-range FLOAT output stays playable and visibly warned.
            audio, rate = sf.read(path)
            sf.write(path, audio * 8, rate, subtype='FLOAT')
        return path, metrics


uvicorn.run(create_app(Path(os.environ['VOICE_LAB_BROWSER_DATA']), BrowserEngine()), host='127.0.0.1', port=8898)
