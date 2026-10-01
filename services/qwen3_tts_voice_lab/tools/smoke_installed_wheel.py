"""CPU-only wheel smoke outside the checkout, using exported locked dependencies."""

import argparse
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wheel', type=Path, required=True)
    parser.add_argument('--requirements', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='voice-lab-wheel-') as temporary:
        root = Path(temporary)
        subprocess.run(['uv', 'venv', '--python', '3.12', str(root / 'env')], check=True)
        python = root / 'env/bin/python'
        subprocess.run(['uv', 'pip', 'sync', '--python', str(python), '--require-hashes', str(args.requirements.resolve())], check=True)
        subprocess.run(['uv', 'pip', 'install', '--python', str(python), '--no-deps', str(args.wheel.resolve())], check=True)
        code = """import sys,tempfile
from pathlib import Path
from plotloom_voice_lab.app import create_app, WEB_DIR
from plotloom_voice_lab.engines.protocol import RunnerRequest
from plotloom_voice_lab.dispatch import ExecutionGrant
assert 'torch' not in sys.modules
with tempfile.TemporaryDirectory() as temporary:
 app=create_app(Path(temporary))
 assert '/api/voice-takes' in {r.path for r in app.routes}
 assert '/internal/executions' in {r.path for r in app.routes}
 assert app.state.store.db_path.exists()
 for name in ('index.html','app.js','reuse.js','takes.js','styles.css'):
  assert (WEB_DIR/name).is_file()
 assert not str(WEB_DIR).startswith(sys.argv[1])
print('installed Voice Lab wheel, routes, assets and runner contracts passed')
"""
        subprocess.run([str(python), '-c', code, str(Path.cwd())], cwd=root,
                       env={**os.environ, 'VOICE_LAB_DATA_ROOT': str(root / 'data')}, check=True)


if __name__ == '__main__':
    main()
