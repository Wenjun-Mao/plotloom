"""Reopen the retained V2 creator and its latest successful playable package."""
import argparse
import json
from pathlib import Path
import signal
import sys

import uvicorn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'services/creator_workbench'))
from isolated import RuntimeConfig, compose
from scripts.prototypes.prototype_publication import publish_baseline, refresh_player, register


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator-task', help='Actual attending Codex task; omit for owner authoring')
    parser.add_argument('--refresh-player', action='store_true', help='Explicitly rebuild unchanged story/media with the current player assets')
    args = parser.parse_args()
    root = ROOT / '.local/last-projection-v2'
    config = RuntimeConfig(root / 'runtime-current', ROOT / 'src/plotloom/static',
        Path('/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex'),
        Path('/Users/wjmao/.local/state/plotloom/last-projection-v2-01a19575/bridge.token'), 8865, 8866, True)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    with compose(config) as runtime:
        storage = runtime.app.state.project_folder_storage
        pid = '048c1802-ee26-449b-bb87-039b3896260a'
        presentation = json.loads((ROOT / '.local/last-projection-resume/original-player-export-presentation.json').read_text())
        publish_baseline(storage, pid, root, presentation)
        if args.refresh_player:
            refresh_player(storage, pid, root)
        register(runtime.app, storage, pid, root, args.operator_task)
        uvicorn.Server(uvicorn.Config(runtime.app, host='127.0.0.1', port=8865)).run(sockets=[runtime.socket])


if __name__ == '__main__':
    main()
